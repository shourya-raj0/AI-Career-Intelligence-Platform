"""Frontend data-access layer.

This module is the single seam between the Streamlit UI and the backend. The
Streamlit MVP imports the backend Python APIs directly (there is no HTTP hop in
the deployed single unit), but it does **not** re-implement business logic: the
shared :class:`CareerIntelligenceService` facade owns the pipeline, job
fetching, ranking, and guidance orchestration, and this module is a thin client
over it.

If the backend is later served as a separate FastAPI service, only this file
needs to be swapped for an HTTP client.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Callable

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.exceptions import AppError  # noqa: E402
from app.services.career_intelligence import CareerIntelligenceService  # noqa: E402

ANALYSIS_STEPS = [
    "Fetching repositories",
    "Analyzing repositories",
    "Building developer profile",
    "Fetching jobs",
    "Matching jobs",
    "Generating recommendations",
    "Preparing dashboard",
]

ROLE_KEYWORDS: dict[str, str] = {
    "AI/ML": "machine learning",
    "Backend": "backend",
    "Frontend": "frontend",
    "Data": "data",
    "Full-Stack": "fullstack",
    "Software Engineering": "software",
}

#: One shared facade for the whole process, mirroring `app.api.deps` so the
#: embedding model, job cache, and HTTP clients are constructed once.
_service: CareerIntelligenceService | None = None


def _get_service() -> CareerIntelligenceService:
    global _service
    if _service is None:
        from app.api.deps import get_career_intelligence_service

        _service = get_career_intelligence_service()
    return _service


def analyze(
    username: str,
    role: str = "AI/ML",
    location: str | None = None,
    count: int = 20,
    on_step: Callable[[int, str], None] | None = None,
) -> dict:
    """Run the full analysis for ``username`` and return dashboard data.

    The result dict carries ``profile``, ``report``, ``ranked_jobs``,
    ``guidance``, ``errors``, and ``warnings`` so the UI can render every
    App Flow screen (or an error message) from one payload.
    """
    result: dict = {
        "profile": None,
        "report": None,
        "ranked_jobs": [],
        "guidance": None,
        "errors": [],
        "warnings": [],
    }

    keywords = ROLE_KEYWORDS.get(role, "machine learning")
    _step(on_step, 0, "Fetching repositories")

    try:
        dashboard = _get_service().generate_dashboard(
            username,
            keywords=keywords,
            location=location,
            count=count,
        )
    except AppError as exc:
        result["errors"] = [str(exc)]
        _step(on_step, 6, "Preparing dashboard")
        return result

    if dashboard.profile is None:
        result["errors"] = ["No developer profile was produced."]
        _step(on_step, 6, "Preparing dashboard")
        return result

    result["profile"] = dashboard.profile
    result["report"] = dashboard.report
    result["ranked_jobs"] = dashboard.ranked_jobs
    result["guidance"] = dashboard.guidance
    result["warnings"] = dashboard.warnings

    _step(on_step, 6, "Preparing dashboard")
    return result


def _step(on_step: Callable[[int, str], None] | None, index: int, label: str) -> None:
    if on_step is not None:
        on_step(index, label)