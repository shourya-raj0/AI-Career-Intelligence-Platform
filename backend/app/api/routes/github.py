"""GitHub intelligence endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Path

from app.api.deps import CareerIntelligenceServiceDep
from app.core.validation import validate_github_username
from app.services.github.analyzer import GitHubAnalysisReport

router = APIRouter(prefix="/github", tags=["github"])


@router.get(
    "/{username}",
    response_model=GitHubAnalysisReport,
    summary="Analyze a GitHub profile",
)
def analyze_github(
    service: CareerIntelligenceServiceDep,
    username: str = Path(..., description="GitHub username to analyze"),
) -> GitHubAnalysisReport:
    """Fetch and analyze the public repositories of ``username``.

    Returns the full structured :class:`GitHubAnalysisReport`. Invalid
    usernames map to 422, unknown users to 404, API rate limits to 429, and
    profiles with no analyzable repositories to 422 (handled globally).
    """
    return service.analyze_github_username(validate_github_username(username))
