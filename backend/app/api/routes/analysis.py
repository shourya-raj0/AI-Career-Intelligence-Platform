"""Pipeline analysis endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field, field_validator

from app.api.deps import CareerIntelligenceServiceDep
from app.core.validation import validate_github_username
from app.services.career_intelligence import AnalysisResponse

router = APIRouter(prefix="/analysis", tags=["analysis"])


class AnalysisRequest(BaseModel):
    """Request body for running the full analysis pipeline."""

    github_username: str = Field(..., min_length=1, description="GitHub username to analyze")
    job_preferences: dict[str, Any] | None = Field(
        default=None,
        description="Optional job preferences threaded through the pipeline",
    )

    @field_validator("github_username")
    @classmethod
    def _validate_username(cls, value: str) -> str:
        return validate_github_username(value)


@router.post(
    "",
    response_model=AnalysisResponse,
    summary="Run the full analysis pipeline",
)
def run_full_analysis(
    payload: AnalysisRequest,
    service: CareerIntelligenceServiceDep,
) -> AnalysisResponse:
    """Run the LangGraph pipeline for ``payload.github_username``.

    The pipeline analyzes the GitHub profile and builds the structured
    :class:`DeveloperProfile`. Pipeline failures surface as typed errors
    handled globally (422, or 429 for a retryable rate limit).
    """
    return service.run_analysis(
        github_username=payload.github_username,
        job_preferences=payload.job_preferences,
    )
