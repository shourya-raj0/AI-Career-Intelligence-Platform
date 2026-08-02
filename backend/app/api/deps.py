"""Dependency injection providers.

Service instances are built lazily and memoized so expensive collaborators
(embedding models, HTTP clients) are constructed once per process and shared
across requests. Routes declare typed ``Annotated`` aliases from this module
instead of constructing services themselves. The application service facade
(:class:`~app.services.career_intelligence.CareerIntelligenceService`) is the
only dependency routes consume; it owns the composition of the domain services.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.database.session import get_db
from app.services.career_intelligence import CareerIntelligenceService
from app.services.github.analyzer import GitHubAnalyzer, build_github_client
from app.services.jobs.pipeline import JobIntelligence
from app.services.matching.ranking import JobRanker
from app.services.recommendations.guidance import CareerGuidanceEngine

SettingsDep = Annotated[Settings, Depends(get_settings)]
DbSession = Annotated[Session, Depends(get_db)]


@lru_cache(maxsize=1)
def get_github_analyzer() -> GitHubAnalyzer:
    """Return a shared GitHub analyzer with an authenticated client."""
    return GitHubAnalyzer(github=build_github_client())


@lru_cache(maxsize=1)
def get_job_intelligence() -> JobIntelligence:
    """Return a shared job intelligence pipeline."""
    return JobIntelligence()


@lru_cache(maxsize=1)
def get_job_ranker() -> JobRanker:
    """Return a shared job ranking engine."""
    return JobRanker()


@lru_cache(maxsize=1)
def get_career_guidance_engine() -> CareerGuidanceEngine:
    """Return a shared career guidance engine."""
    return CareerGuidanceEngine()


@lru_cache(maxsize=1)
def get_career_intelligence_service() -> CareerIntelligenceService:
    """Return a shared application service facade over the domain services."""
    return CareerIntelligenceService(
        analyzer=get_github_analyzer(),
        intelligence=get_job_intelligence(),
        ranker=get_job_ranker(),
        guidance=get_career_guidance_engine(),
    )


def close_application_services() -> None:
    """Release process-wide resources held by shared services (shutdown hook)."""
    if get_job_intelligence.cache_info().currsize:
        get_job_intelligence().close()
    for getter in (
        get_github_analyzer,
        get_job_intelligence,
        get_job_ranker,
        get_career_guidance_engine,
        get_career_intelligence_service,
    ):
        getter.cache_clear()


CareerIntelligenceServiceDep = Annotated[
    CareerIntelligenceService, Depends(get_career_intelligence_service)
]
