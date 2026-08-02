"""Job intelligence endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Query

from app.api.deps import CareerIntelligenceServiceDep
from app.services.jobs.models import Job, JobQuery

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post(
    "/search",
    response_model=list[Job],
    summary="Search and prepare jobs",
)
def search_jobs(query: JobQuery, service: CareerIntelligenceServiceDep) -> list[Job]:
    """Fetch, normalize, enrich, and embed job postings for ``query``.

    Cached results are returned within the configured TTL; otherwise jobs are
    fetched from the job API. Provider failures map to 502 and rate limits to
    429 (handled globally).
    """
    return service.search_jobs(query)


@router.get(
    "",
    response_model=list[Job],
    summary="Search jobs via query parameters",
)
def list_jobs(
    service: CareerIntelligenceServiceDep,
    keywords: str = Query("ai ml", description="Role keywords used to derive provider tags"),
    location: str | None = Query(None, description="Free-form location filter"),
    count: int = Query(20, ge=1, le=50, description="Maximum number of jobs to return"),
) -> list[Job]:
    """Convenience GET variant of :func:`search_jobs`."""
    query = JobQuery(keywords=keywords, location=location, count=count)
    return service.search_jobs(query)
