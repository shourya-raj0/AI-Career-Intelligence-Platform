"""Evaluation service.

Sprint 8 — measurement and validation of the matching pipeline:
- :mod:`metrics` — pure Precision@K, rank-correlation, and human-agreement math
- :mod:`benchmark` — runs the pipeline against labeled profile-job cases and
  records per-stage latency
- :mod:`langsmith` — optional LangSmith tracing and dataset upload
"""

from app.services.evaluation.benchmark import (
    DEFAULT_DATASET,
    DEFAULT_REPORT_DIR,
    BenchmarkRunner,
    load_dataset,
    save_report,
)
from app.services.evaluation.langsmith import (
    enable_tracing,
    log_report,
    tracing_available,
    upload_dataset,
)
from app.services.evaluation.models import (
    BenchmarkCase,
    BenchmarkJob,
    BenchmarkReport,
    MetricsResult,
)

__all__ = [
    "BenchmarkCase",
    "BenchmarkJob",
    "BenchmarkReport",
    "BenchmarkRunner",
    "DEFAULT_DATASET",
    "DEFAULT_REPORT_DIR",
    "MetricsResult",
    "enable_tracing",
    "load_dataset",
    "log_report",
    "save_report",
    "tracing_available",
    "upload_dataset",
]
