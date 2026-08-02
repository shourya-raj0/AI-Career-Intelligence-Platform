"""Pipeline state for the LangGraph orchestration layer.

``PipelineState`` is the single shared object that flows through the graph.
Service results are stored as structured models; business logic never lives in
the graph. Fields for stages whose services do not exist yet (jobs, matching,
recommendations, explanations) are present so the contract is stable and the
schema does not change as those stages land.

Note: this module intentionally omits ``from __future__ import annotations``
because LangGraph resolves the state schema via ``get_type_hints`` and needs
the referenced models importable at runtime.
"""

from typing import TypedDict

from pydantic import BaseModel

from app.services.developer_profile.models import DeveloperProfile
from app.services.github.analyzer import GitHubAnalysisReport

MAX_ANALYSIS_ATTEMPTS = 3


class PipelineError(BaseModel):
    """A structured error recorded by a node during pipeline execution."""

    node: str
    message: str
    retryable: bool = False


class PipelineState(TypedDict, total=False):
    """The shared state object flowing through the pipeline graph."""

    github_username: str
    github_report: GitHubAnalysisReport
    developer_profile: DeveloperProfile
    job_preferences: dict | None
    job_postings: list | None
    ranked_jobs: list | None
    recommendations: list | None
    explanations: list | None
    errors: list[PipelineError]
    retries: int
