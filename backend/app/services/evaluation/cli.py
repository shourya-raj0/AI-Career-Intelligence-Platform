"""Command-line interface for running the evaluation benchmark.

Usage (from ``backend/``)::

    python -m app.services.evaluation.cli                  # offline, seed dataset
    python -m app.services.evaluation.cli --live           # build profiles via pipeline
    python -m app.services.evaluation.cli --dataset path.json
    python -m app.services.evaluation.cli --langsmith      # push dataset + report to LangSmith
    python -m app.services.evaluation.cli --threshold 55
"""

from __future__ import annotations

import argparse
import sys

from app.services.evaluation.benchmark import (
    DEFAULT_DATASET,
    BenchmarkRunner,
    load_dataset,
    save_report,
)
from app.services.evaluation.langsmith import enable_tracing, log_report, upload_dataset


def _print_report(report, path: str) -> None:
    print(f"Dataset: {path or DEFAULT_DATASET}")
    print(f"Cases:   {report.dataset_size}")
    print(f"Relevance threshold: {report.threshold}")
    print("\nAverage metrics")
    for name, value in report.average.items():
        print(f"  {name:<24} {value}")
    print("\nLatency (p95 ms per stage)")
    for name, value in report.latency_p95_ms.items():
        print(f"  {name:<24} {value}")
    print("\nPer-case")
    for case in report.cases:
        print(
            f"  {case.case_id:<16} P@1={case.precision_at_1}  P@3={case.precision_at_3}  "
            f"kappa={_fmt(case.cohens_kappa)}  kendall={_fmt(case.kendall_tau)}  "
            f"total_ms={case.total_latency_ms}"
        )


def _fmt(value: float | None) -> str:
    return f"{value:.3f}" if value is not None else "n/a"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the career-matching benchmark.")
    parser.add_argument("--dataset", default=str(DEFAULT_DATASET), help="JSON dataset path")
    parser.add_argument("--live", action="store_true", help="Build profiles via the pipeline")
    parser.add_argument("--threshold", type=float, default=60.0, help="Relevance threshold")
    parser.add_argument("--langsmith", action="store_true", help="Push to LangSmith")
    parser.add_argument("--no-save", action="store_true", help="Skip writing the report file")
    args = parser.parse_args(argv)

    tracing = enable_tracing()
    print(f"LangSmith tracing: {'enabled' if tracing else 'not configured (offline)'}")

    cases = load_dataset(args.dataset)
    runner = BenchmarkRunner(threshold=args.threshold, live=args.live)
    report = runner.run(cases, dataset_path=args.dataset)

    if args.langsmith:
        report.langsmith = upload_dataset(cases)
        report.langsmith.update(log_report(report))
        print(f"LangSmith: {report.langsmith}")

    _print_report(report, args.dataset)

    if not args.no_save:
        path = save_report(report)
        print(f"\nReport written to {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
