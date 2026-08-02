"""Application service (facade) layer.

:class:`CareerIntelligenceService` is the single application-level entry point
the API talks to. It composes the existing domain services — the LangGraph
pipeline, GitHub analysis, job intelligence, matching, and career guidance —
and translates domain failures into typed :class:`app.core.exceptions.AppError`
subtypes so the HTTP layer stays a thin adapter.

No business logic is re-implemented here; this facade only coordinates the
existing services. ``close()`` releases process-wide resources (job cache).
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from app.core.exceptions import PipelineFailedError, PipelineRateLimitError
from app.core.validation import validate_github_username
from app.graph import run_pipeline
from app.graph.state import PipelineError
from app.services.developer_profile.models import DeveloperProfile
from app.services.github.analyzer import GitHubAnalysisReport, GitHubAnalyzer
from app.services.jobs.fetcher import JobAPIError
from app.services.jobs.models import Job, JobQuery
from app.services.jobs.pipeline import JobIntelligence
from app.services.matching.models import MatchResult
from app.services.matching.ranking import JobRanker
from app.services.recommendations.guidance import CareerGuidanceEngine
from app.services.recommendations.models import CareerGuidance


class AnalysisResponse(BaseModel):
    """Result of a pipeline run for a GitHub username."""

    github_username: str
    github_report: GitHubAnalysisReport | None = None
    developer_profile: DeveloperProfile | None = None
    errors: list[PipelineError] = Field(default_factory=list)


class DashboardResult(BaseModel):
    """Everything the frontend dashboard needs from one orchestration call."""

    profile: DeveloperProfile | None = None
    report: GitHubAnalysisReport | None = None
    ranked_jobs: list[MatchResult] = Field(default_factory=list)
    guidance: CareerGuidance | None = None
    warnings: list[str] = Field(default_factory=list)


class CareerIntelligenceService:
    """Coordinates the platform's intelligence services for the API layer."""

    def __init__(
        self,
        analyzer: GitHubAnalyzer,
        intelligence: JobIntelligence,
        ranker: JobRanker,
        guidance: CareerGuidanceEngine,
    ) -> None:
        self._analyzer = analyzer
        self._intelligence = intelligence
        self._ranker = ranker
        self._guidance = guidance

    def analyze_github_username(self, username: str) -> GitHubAnalysisReport:
        """Analyze a GitHub profile via the GitHub intelligence service."""
        return self._analyzer.analyze_username(validate_github_username(username))

    def run_analysis(
        self,
        github_username: str,
        job_preferences: dict[str, Any] | None = None,
    ) -> AnalysisResponse:
        """Run the LangGraph pipeline and return the structured result.

        When the pipeline records a fatal error, raises
        :class:`PipelineRateLimitError` (429) for retryable failures or
        :class:`PipelineFailedError` (422) otherwise, instead of returning a
        partial result.
        """
        github_username = validate_github_username(github_username)
        state = run_pipeline(github_username, job_preferences)

        if state.get("developer_profile") is None and state.get("errors"):
            error = state["errors"][0]
            if error.retryable:
                raise PipelineRateLimitError(error.message)
            raise PipelineFailedError(error.message)

        return AnalysisResponse(
            github_username=github_username,
            github_report=state.get("github_report"),
            developer_profile=state.get("developer_profile"),
            errors=list(state.get("errors", [])),
        )

    def search_jobs(self, query: JobQuery) -> list[Job]:
        """Fetch, normalize, enrich, and embed job postings for ``query``."""
        return self._intelligence.fetch_and_prepare(query)

    def generate_recommendations(
        self,
        github_username: str,
        job_preferences: dict[str, Any] | None,
        keywords: str,
        location: str | None,
        count: int,
    ) -> CareerGuidance:
        """Build a profile, match jobs, and generate a grounded career roadmap.

        Raises :class:`PipelineFailedError` (422) when the pipeline produces no
        developer profile.
        """
        state = run_pipeline(github_username, job_preferences)
        profile = state.get("developer_profile")
        if profile is None:
            message = (
                state["errors"][0].message
                if state.get("errors")
                else "Pipeline produced no developer profile."
            )
            raise PipelineFailedError(message)

        query = JobQuery(keywords=keywords, location=location, count=count)
        jobs = self._intelligence.fetch_and_prepare(query)
        ranked: list[MatchResult] = self._ranker.rank(profile, jobs)
        return self._guidance.generate(profile, ranked)

    def generate_dashboard(
        self,
        github_username: str,
        keywords: str,
        location: str | None = None,
        count: int = 20,
        job_preferences: dict[str, Any] | None = None,
    ) -> DashboardResult:
        """Orchestrate the full dashboard payload for the Streamlit frontend.

        Runs the pipeline once to get the report/profile, then fetches, ranks,
        and guides. Raises :class:`PipelineFailedError` when the pipeline yields
        no profile, mirroring the HTTP endpoint contract. If the job API fails
        but the profile was built, returns a profile-only result with a warning
        (the Streamlit App Flow's "showing cached recommendations" path).
        """
        github_username = validate_github_username(github_username)
        state = run_pipeline(github_username, job_preferences)
        profile = state.get("developer_profile")
        if profile is None:
            message = (
                state["errors"][0].message
                if state.get("errors")
                else "Pipeline produced no developer profile."
            )
            raise PipelineFailedError(message)

        query = JobQuery(keywords=keywords, location=location, count=count)
        try:
            jobs = self._intelligence.fetch_and_prepare(query)
        except JobAPIError:
            return DashboardResult(
                profile=profile,
                report=state.get("github_report"),
                warnings=["Unable to fetch live jobs. Showing cached recommendations."],
            )

        ranked: list[MatchResult] = self._ranker.rank(profile, jobs)
        return DashboardResult(
            profile=profile,
            report=state.get("github_report"),
            ranked_jobs=ranked,
            guidance=self._guidance.generate(profile, ranked),
        )

    def close(self) -> None:
        """Release process-wide resources held by this facade's services."""
        self._intelligence.close()
