"""Application exception types and HTTP handlers.

:class:`AppError` and its subclasses are the application's own error types.
:func:`register_exception_handlers` wires generic handlers (validation, HTTP,
unhandled) plus an optional mapping of ``service exception -> (status, code)``
so the API always returns a consistent error envelope::

    {"error": {"code": "...", "message": "...", "details": ...}}

The service mapping is supplied by the composition root (:mod:`app.main`) so
this core module stays independent of the service layer.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


class AppError(Exception):
    """Base class for all application errors.

    Subclasses set ``status_code`` and ``code``; ``details`` carries optional
    structured context for the client.
    """

    status_code: int = 500
    code: str = "internal_error"

    def __init__(self, message: str, *, details: Any = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details


class NotFoundError(AppError):
    """The requested resource does not exist."""

    status_code = 404
    code = "not_found"


class ConflictError(AppError):
    """The request conflicts with the current server state."""

    status_code = 409
    code = "conflict"


class InvalidRequestError(AppError):
    """The request payload is semantically invalid."""

    status_code = 422
    code = "invalid_request"


class RateLimitError(AppError):
    """A downstream API rate limit was exceeded."""

    status_code = 429
    code = "rate_limited"


class ExternalServiceError(AppError):
    """A downstream dependency failed."""

    status_code = 502
    code = "external_service"


class PipelineFailedError(AppError):
    """The analysis pipeline could not produce a developer profile."""

    status_code = 422
    code = "pipeline_failed"


class PipelineRateLimitError(PipelineFailedError):
    """The pipeline failed because of a retryable (rate-limit) condition."""

    status_code = 429


ServiceErrorMap = dict[type[Exception], tuple[int, str]]


def _error_body(code: str, message: str, details: Any = None) -> dict:
    """Return the canonical error envelope."""
    body: dict = {"error": {"code": code, "message": message}}
    if details is not None:
        body["error"]["details"] = details
    return body


async def _app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    """Serialize a :class:`AppError` to the canonical envelope."""
    return JSONResponse(
        status_code=exc.status_code,
        content=_error_body(exc.code, exc.message, exc.details),
    )


def _make_service_error_handler(status_code: int, code: str):
    """Build a handler that maps a service exception to an HTTP response."""

    async def handler(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(status_code=status_code, content=_error_body(code, str(exc)))

    return handler


async def _validation_error_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Serialize pydantic request-validation failures."""
    return JSONResponse(
        status_code=422,
        content=_error_body("validation_error", "Request validation failed.", exc.errors()),
    )


async def _http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    """Normalize Starlette HTTP exceptions into the canonical envelope."""
    detail = exc.detail
    if isinstance(detail, dict):
        if "error" in detail:
            return JSONResponse(status_code=exc.status_code, content=detail)
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_body(
                str(detail.get("code", "http_error")),
                str(detail.get("message", detail)),
            ),
        )
    return JSONResponse(
        status_code=exc.status_code,
        content=_error_body("http_error", str(detail)),
    )


async def _unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Log unexpected failures and return a generic 500."""
    logger.exception(
        "Unhandled exception while serving %s %s", request.method, request.url.path
    )
    return JSONResponse(
        status_code=500,
        content=_error_body("internal_error", "An unexpected error occurred."),
    )


def register_exception_handlers(
    app: FastAPI, service_errors: ServiceErrorMap | None = None
) -> None:
    """Register every exception handler on ``app``.

    ``service_errors`` optionally maps service exception classes to
    ``(status_code, error code)``. Starlette resolves the most specific handler
    via the exception MRO, so subclasses win over their bases automatically.
    """
    app.add_exception_handler(AppError, _app_error_handler)
    if service_errors:
        for exc_type, (status_code, code) in service_errors.items():
            app.add_exception_handler(exc_type, _make_service_error_handler(status_code, code))
    app.add_exception_handler(RequestValidationError, _validation_error_handler)
    app.add_exception_handler(StarletteHTTPException, _http_exception_handler)
    app.add_exception_handler(Exception, _unhandled_exception_handler)
