"""Benchmark runner.

Executes the matching pipeline against a labeled :class:`BenchmarkCase`
dataset, records per-stage latency, and computes precision@K, rank-correlation,
and human-agreement metrics. Profiles are taken from dataset snapshots by
default (offline); pass ``live=True`` to build profiles through the LangGraph
pipeline instead.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from app.services.developer_profile.models import DeveloperProfile
from app.services.evaluation.metrics import (
    average_precision,
    binarize,
    cohens_kappa,
    agreement_rate,
    kendall_tau,
    percentile,
    precision_at_all_ks,
    reciprocal_rank,
    recall_at_k,
)
from app.services.evaluation.models import BenchmarkCase, BenchmarkReport, MetricsResult
from app.services.jobs.embedding import JobEmbedder
from app.services.jobs.models import Job
from app.services.jobs.normalizer import JobNormalizer
from app.services.jobs.parser import SkillParser
from app.services.matching.ranking import JobRanker

DEFAULT_DATASET = Path(__file__).resolve().parents[3] / "data" / "evaluation_dataset.json"
DEFAULT_REPORT_DIR = Path(__file__).resolve().parents[3] / "data" / "evaluation_reports"


class LatencyTracker:
    """Records elapsed wall-clock time per named stage."""

    def __init__(self) -> None:
        self._starts: dict[str, float] = {}

    def start(self, name: str) -> None:
        self._starts[name] = time.perf_counter()

    def stop(self, name: str) -> float:
        elapsed_ms = (time.perf_counter() - self._starts.pop(name)) * 1000.0
        return round(elapsed_ms, 2)


class BenchmarkRunner:
    """Runs the benchmark and aggregates :class:`MetricsResult` objects."""

    def __init__(
        self,
        ranker: JobRanker | None = None,
        normalizer: JobNormalizer | None = None,
        parser: SkillParser | None = None,
        embedder: JobEmbedder | None = None,
        threshold: float = 60.0,
        live: bool = False,
    ) -> None:
        self._ranker = ranker or JobRanker()
        self._normalizer = normalizer or JobNormalizer()
        self._parser = parser or SkillParser()
        self._embedder = embedder or JobEmbedder()
        self._threshold = threshold
        self._live = live

    def run(self, cases: list[BenchmarkCase], dataset_path: str = "") -> BenchmarkReport:
        """Evaluate ``cases`` and return the aggregated report."""
        results = [self._evaluate_case(case) for case in cases]
        report = BenchmarkReport(
            dataset_path=dataset_path,
            dataset_size=len(results),
            threshold=self._threshold,
            cases=results,
        )
        report.average = self._aggregate_averages(results)
        report.latency_p95_ms = self._aggregate_latency_p95(results)
        return report

    def _evaluate_case(self, case: BenchmarkCase) -> MetricsResult:
        tracker = LatencyTracker()

        tracker.start("profile")
        profile = self._build_profile(case)
        profile_ms = tracker.stop("profile")

        tracker.start("job_prepare")
        jobs = self._prepare_jobs(case)
        job_prepare_ms = tracker.stop("job_prepare")

        tracker.start("ranking")
        ranked = self._ranker.rank(profile, jobs)
        ranking_ms = tracker.stop("ranking")

        tracker.start("total")
        total_ms = profile_ms + job_prepare_ms + ranking_ms
        tracker.stop("total")

        return self._to_metrics(
            case,
            ranked,
            stage={"profile": profile_ms, "job_prepare": job_prepare_ms, "ranking": ranking_ms},
            total_ms=total_ms,
        )

    def _to_metrics(
        self,
        case: BenchmarkCase,
        ranked: list[Any],
        stage: dict[str, float],
        total_ms: float,
    ) -> MetricsResult:
        paired = _paired(case.jobs, ranked)
        relevant_ids = {
            job.id for job, _match in paired if job.human_relevance
        }
        ranked_ids = [match.job.external_id for _job, match in paired]

        precision = precision_at_all_ks(ranked_ids, relevant_ids)
        human_flags = [job.human_relevance for job, _match in paired]
        system_flags = binarize([match.match_score for _job, match in paired], self._threshold)
        human_ranks = [job.human_rank for job, _match in paired]
        system_ranks = [float(position) for position in range(1, len(paired) + 1)]

        return MetricsResult(
            case_id=case.case_id,
            precision_at_1=precision["precision_at_1"],
            precision_at_3=precision["precision_at_3"],
            precision_at_5=precision["precision_at_5"],
            average_precision_at_10=average_precision(ranked_ids, relevant_ids),
            recall_at_3=recall_at_k(ranked_ids, relevant_ids, 3),
            mrr=reciprocal_rank(ranked_ids, relevant_ids),
            kendall_tau=kendall_tau(system_ranks, human_ranks),
            human_agreement_rate=agreement_rate(human_flags, system_flags),
            cohens_kappa=cohens_kappa(human_flags, system_flags),
            total_latency_ms=total_ms,
            stage_latencies_ms=stage,
        )

    def _build_profile(self, case: BenchmarkCase) -> DeveloperProfile:
        if case.profile is not None:
            return case.profile
        if self._live and case.github_username:
            from app.graph import run_pipeline

            state = run_pipeline(case.github_username)
            if state.get("developer_profile") is None:
                raise ValueError(
                    f"case {case.case_id}: pipeline produced no developer profile"
                )
            return state["developer_profile"]
        raise ValueError(
            f"case {case.case_id}: no profile snapshot and not running live"
        )

    def _prepare_jobs(self, case: BenchmarkCase) -> list[Job]:
        jobs: list[Job] = []
        for benchmark_job in case.jobs:
            raw = {
                "id": benchmark_job.id,
                "title": benchmark_job.title,
                "description": benchmark_job.description,
                "url": benchmark_job.url,
                "companyName": benchmark_job.company,
                "jobGeo": benchmark_job.location,
                "jobType": [benchmark_job.employment_type] if benchmark_job.employment_type else None,
            }
            normalized = self._normalizer.normalize([raw])
            if not normalized:
                continue
            job = normalized[0]
            job.required_skills = self._parser.extract_skills(job.title, job.description)
            embedded = self._embedder.embed_documents([job.search_text()])
            job.embedding = embedded[0]
            jobs.append(job)
        return jobs

    @staticmethod
    def _aggregate_averages(results: list[MetricsResult]) -> dict[str, float]:
        fields = [
            "precision_at_1",
            "precision_at_3",
            "precision_at_5",
            "average_precision_at_10",
            "recall_at_3",
            "mrr",
            "kendall_tau",
            "human_agreement_rate",
            "cohens_kappa",
        ]
        averaged: dict[str, float] = {}
        for field in fields:
            values = [
                getattr(result, field)
                for result in results
                if getattr(result, field) is not None
            ]
            averaged[field] = round(sum(values) / len(values), 4) if values else 0.0
        averaged["total_latency_ms"] = round(
            sum(r.total_latency_ms for r in results) / len(results), 2
        ) if results else 0.0
        return averaged

    @staticmethod
    def _aggregate_latency_p95(results: list[MetricsResult]) -> dict[str, float]:
        stage_names = {name for r in results for name in r.stage_latencies_ms}
        aggregated: dict[str, float] = {}
        for stage in stage_names:
            values = [r.stage_latencies_ms[stage] for r in results if stage in r.stage_latencies_ms]
            aggregated[stage] = round(percentile(values, 95), 2)
        aggregated["total"] = round(percentile([r.total_latency_ms for r in results], 95), 2)
        return aggregated


def _paired(case_jobs: list, ranked: list[Any]) -> list[tuple]:
    """Return ``(benchmark_job, match)`` pairs aligned by external job id.

    The normalizer rewrites ``Job.id`` to ``"source:external_id"``, so the
    original benchmark id survives as ``external_id``.
    """
    by_external_id = {job.id: job for job in case_jobs}
    pairs: list[tuple] = []
    for match in ranked:
        job = by_external_id.get(match.job.external_id)
        if job is not None:
            pairs.append((job, match))
    return pairs


def load_dataset(path: str | Path = DEFAULT_DATASET) -> list[BenchmarkCase]:
    """Load and validate a benchmark dataset from a JSON file."""
    dataset_path = Path(path)
    with dataset_path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    cases = payload.get("cases", payload) if isinstance(payload, dict) else payload
    return [BenchmarkCase.model_validate(case) for case in cases]


def save_report(report: BenchmarkReport, report_dir: str | Path = DEFAULT_REPORT_DIR) -> Path:
    """Write ``report`` as JSON under ``report_dir`` and return its path."""
    output_dir = Path(report_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"benchmark_{report.generated_at.replace(':', '-').replace('.', '-')}.json"
    path.write_text(json.dumps(report.model_dump(mode="json"), indent=2), encoding="utf-8")
    return path
