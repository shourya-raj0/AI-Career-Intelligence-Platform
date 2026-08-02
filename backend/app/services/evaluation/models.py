"""Evaluation output models.

:class:`BenchmarkCase` is the schema for one labeled profile-job set in the
benchmark dataset. :class:`MetricsResult` carries the per-case numbers
(precision@K, human agreement, latency) and :class:`BenchmarkReport`
aggregates them across the whole dataset.
"""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field

from app.services.developer_profile.models import DeveloperProfile


class BenchmarkJob(BaseModel):
    """A job posting plus its human relevance label inside a benchmark case."""

    id: str = ""
    title: str
    company: str | None = None
    location: str | None = None
    description: str = ""
    url: str = ""
    employment_type: str | None = None
    human_relevance: int = 1
    human_rank: int | None = None


class BenchmarkCase(BaseModel):
    """One labeled profile-job set used for evaluation.

    ``profile`` may carry a serialized :class:`DeveloperProfile` snapshot so
    the benchmark runs offline. When it is ``None`` and ``github_username`` is
    set, the runner can build the profile live through the pipeline.
    """

    case_id: str
    github_username: str | None = None
    profile: DeveloperProfile | None = None
    jobs: list[BenchmarkJob] = Field(default_factory=list)


class MetricsResult(BaseModel):
    """Per-case evaluation metrics."""

    case_id: str
    precision_at_1: float | None = None
    precision_at_3: float | None = None
    precision_at_5: float | None = None
    average_precision_at_10: float = 0.0
    recall_at_3: float | None = None
    mrr: float = 0.0
    kendall_tau: float | None = None
    human_agreement_rate: float | None = None
    cohens_kappa: float | None = None
    total_latency_ms: float = 0.0
    stage_latencies_ms: dict[str, float] = Field(default_factory=dict)


class BenchmarkReport(BaseModel):
    """Aggregated metrics across all benchmark cases."""

    dataset_path: str = ""
    dataset_size: int = 0
    threshold: float = 60.0
    generated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    average: dict[str, float] = Field(default_factory=dict)
    latency_p95_ms: dict[str, float] = Field(default_factory=dict)
    cases: list[MetricsResult] = Field(default_factory=list)
    langsmith: dict = Field(default_factory=dict)
