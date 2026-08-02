"""Matching Engine result models.

``MatchResult`` is the structured, deterministic output of job matching. It
carries component scores (semantic similarity, skill overlap, repository
quality) so callers can inspect exactly why a score was produced — but no
human explanation text is generated here.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.services.jobs.models import Job


class SkillOverlapResult(BaseModel):
    """Comparison of a job's required skills against the developer profile."""

    overlap_score: float
    matched_skills: list[str] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)


class MatchBreakdown(BaseModel):
    """Component scores and weights behind a :class:`MatchResult`."""

    semantic_similarity: float
    skill_overlap: float
    quality_score: float
    weight_semantic: float
    weight_overlap: float
    weight_quality: float


class MatchResult(BaseModel):
    """A ranked job match for a developer profile."""

    job: Job
    match_score: float
    confidence: str
    matched_skills: list[str] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)
    breakdown: MatchBreakdown
