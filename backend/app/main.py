"""FastAPI application entry point.

Wires configuration, logging, exception handlers, CORS, the API router, and the
startup/shutdown lifecycle (database init/dispose). Run locally with::

    uvicorn app.main:app --reload
"""

from __future__ import annotations

from dotenv import load_dotenv
load_dotenv()


import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.deps import close_application_services
from app.api.routes import api_router
from app.core.config import get_settings
from app.core.exceptions import ServiceErrorMap, register_exception_handlers
from app.core.logging import setup_logging
from app.database.session import dispose_db, init_db, ping_db
from app.services.github.analyzer import (
    GitHubAnalysisError,
    GitHubProfileInsufficientError,
    GitHubRateLimitError,
    GitHubUserNotFoundError,
)
from app.services.jobs.fetcher import JobAPIError, JobRateLimitError

logger = logging.getLogger(__name__)

settings = get_settings()
setup_logging(settings.log_level)

#: Map service exceptions to ``(HTTP status, error code)`` for the global
#: handlers registered in :func:`create_app`. Kept here (the composition root)
#: so the core layer stays independent of the service layer.
SERVICE_ERROR_MAP: ServiceErrorMap = {
    GitHubUserNotFoundError: (404, "github_user_not_found"),
    GitHubProfileInsufficientError: (422, "github_profile_insufficient"),
    GitHubRateLimitError: (429, "github_rate_limited"),
    GitHubAnalysisError: (502, "github_analysis_failed"),
    JobRateLimitError: (429, "job_api_rate_limited"),
    JobAPIError: (502, "job_api_error"),
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: initialize the database. Shutdown: release resources."""
    init_db()
    logger.info("%s starting (environment=%s)", settings.app_name, settings.environment)
    yield
    close_application_services()
    dispose_db()
    logger.info("%s stopped", settings.app_name)


def create_app() -> FastAPI:
    """Configure and return the FastAPI application instance."""
    application = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        debug=settings.debug,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    allow_credentials = settings.cors_allow_credentials
    if allow_credentials and "*" in settings.cors_origins:
        logger.warning(
            "CORS allow_credentials=True is incompatible with the wildcard "
            "origin; credentials will be disabled."
        )
        allow_credentials = False
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=allow_credentials,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(application, SERVICE_ERROR_MAP)
    application.include_router(api_router)

    @application.get("/health", tags=["system"], summary="Health check")
    def health() -> dict:
        """Return service liveness and database reachability."""
        try:
            ping_db()
            database_ok = True
        except Exception:
            logger.exception("Database health check failed")
            database_ok = False
        return {
            "status": "ok" if database_ok else "degraded",
            "service": settings.app_name,
            "version": settings.app_version,
            "environment": settings.environment,
            "database": "ok" if database_ok else "unavailable",
        }

    return application


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )
