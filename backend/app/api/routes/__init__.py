"""API route aggregation.

Mounts every domain router under the configured API prefix and applies the
optional API-key dependency to the whole surface. No business logic lives here.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.routes import analysis, github, jobs, recommendations
from app.core.config import get_settings
from app.core.security import require_api_key

_settings = get_settings()

api_router = APIRouter(
    prefix=_settings.api_v1_prefix,
    dependencies=[Depends(require_api_key)],
)

api_router.include_router(github.router)
api_router.include_router(analysis.router)
api_router.include_router(jobs.router)
api_router.include_router(recommendations.router)
