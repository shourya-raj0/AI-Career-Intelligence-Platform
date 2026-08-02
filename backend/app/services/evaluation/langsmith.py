"""LangSmith tracing and evaluation integration.

Everything here degrades gracefully: without ``LANGSMITH_API_KEY`` (or the
tracing env vars) the helpers return ``False``/empty results instead of
raising, so the benchmark works offline. When configured, LangGraph pipelines
auto-trace and the benchmark dataset/results are pushed to LangSmith so the
precision/agreement numbers are reproducible and reviewable in the UI.
"""

from __future__ import annotations

import os
from typing import Any

PROJECT_NAME = os.getenv("LANGSMITH_PROJECT", "career-intelligence-evaluation")
DATASET_NAME = "career-profile-job-agreement"

_TRACING_ENV_VARS = ("LANGSMITH_API_KEY", "LANGSMITH_TRACING", "LANGCHAIN_TRACING_V2")


def tracing_available() -> bool:
    """True when LangSmith credentials (or tracing) are configured."""
    if not any(os.getenv(var) for var in _TRACING_ENV_VARS):
        return False
    try:
        import langsmith  # noqa: F401

        return True
    except ImportError:
        return False


def enable_tracing(project: str = PROJECT_NAME) -> bool:
    """Enable LangSmith auto-tracing for LangGraph runs.

    Sets the env vars LangGraph inspects at invocation time. Returns ``False``
    (without side effects) when LangSmith is not configured.
    """
    if not tracing_available():
        return False
    os.environ.setdefault("LANGSMITH_TRACING", "true")
    os.environ.setdefault("LANGSMITH_PROJECT", project)
    return True


def _client() -> Any:
    from langsmith import Client

    return Client()


def get_or_create_dataset() -> tuple[Any, bool]:
    """Return the benchmark ``Dataset``, creating it if missing."""
    client = _client()
    try:
        dataset = client.create_dataset(
            DATASET_NAME,
            description="Human-labeled profile-job pairs for precision and agreement evals.",
        )
        return dataset, True
    except Exception:
        datasets = client.list_datasets(dataset_name=DATASET_NAME)
        for dataset in datasets:
            if dataset.name == DATASET_NAME:
                return dataset, False
        raise


def upload_dataset(cases: list[Any]) -> dict:
    """Upload benchmark cases as LangSmith dataset examples.

    ``cases`` are :class:`~app.services.evaluation.models.BenchmarkCase`.
    Returns a summary dict, or ``{"uploaded": False}`` when unconfigured.
    """
    if not tracing_available():
        return {"uploaded": False, "reason": "LangSmith not configured"}
    try:
        dataset, _created = get_or_create_dataset()
        examples = [
            {
                "inputs": {
                    "github_username": case.github_username or "",
                    "case_id": case.case_id,
                    "job_titles": [job.title for job in case.jobs],
                },
                "outputs": {
                    "human_relevance": [job.human_relevance for job in case.jobs],
                    "human_ranks": [job.human_rank for job in case.jobs],
                },
            }
            for case in cases
        ]
        _client().create_examples(dataset_id=dataset.id, examples=examples)
        return {"uploaded": True, "dataset": DATASET_NAME, "examples": len(examples)}
    except Exception as exc:  # pragma: no cover - depends on live service state
        return {"uploaded": False, "reason": str(exc)}


def log_report(report: Any, project: str = PROJECT_NAME) -> dict:
    """Create a LangSmith run recording the benchmark report."""
    if not tracing_available():
        return {"logged": False, "reason": "LangSmith not configured"}
    try:
        _client().create_run(
            name="benchmark",
            run_type="chain",
            inputs={"dataset_size": report.dataset_size, "threshold": report.threshold},
            outputs=report.model_dump(mode="json"),
            project_name=project,
        )
        return {"logged": True, "project": project}
    except Exception as exc:  # pragma: no cover - depends on live service state
        return {"logged": False, "reason": str(exc)}
