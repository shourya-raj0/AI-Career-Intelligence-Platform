"""Career guidance (recommendations) endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.api.deps import CareerIntelligenceServiceDep
from app.services.recommendations.models import CareerGuidance

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


class RecommendationRequest(BaseModel):
    """Request body for generating career guidance."""

    github_username: str = Field(..., min_length=1, description="GitHub username to analyze")
    job_preferences: dict[str, Any] | None = Field(
        default=None,
        description="Optional job preferences threaded through the pipeline",
    )
    keywords: str = Field("ai ml", description="Role keywords used to fetch jobs")
    location: str | None = Field(default=None, description="Free-form location filter")
    count: int = Field(20, ge=1, le=50, description="Number of jobs to match against")


@router.post(
    "",
    response_model=CareerGuidance,
    summary="Generate career guidance for a developer",
)
def generate_recommendations(
    payload: RecommendationRequest,
    service: CareerIntelligenceServiceDep,
) -> CareerGuidance:
    """Build a profile, match jobs, and generate a grounded career roadmap.

    Orchestration lives in the application service facade; this endpoint only
    validates the request and returns the produced :class:`CareerGuidance`.
    """
    return service.generate_recommendations(
        github_username=payload.github_username,
        job_preferences=payload.job_preferences,
        keywords=payload.keywords,
        location=payload.location,
        count=payload.count,
    )
