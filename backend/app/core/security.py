"""Security utilities.

Provides optional API-key authentication (``X-API-Key`` header) backed by
:class:`app.core.config.Settings`. Authentication is enforced only when the
deployment enables ``REQUIRE_API_KEY`` *and* configures an ``API_KEY``, so
local/MVP deployments work without secrets while production can opt in by
setting two environment variables.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header, HTTPException, status

from app.core.config import Settings, get_settings

API_KEY_HEADER = "X-API-Key"


def _unauthorized() -> HTTPException:
    """Return a 401 response that asks the client for an API key."""
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"code": "unauthorized", "message": "Invalid or missing API key."},
        headers={"WWW-Authenticate": "API-Key"},
    )


def require_api_key(
    settings: Annotated[Settings, Depends(get_settings)],
    x_api_key: Annotated[str | None, Header(alias=API_KEY_HEADER)] = None,
) -> None:
    """Reject the request when API-key auth is enabled and the key is wrong.

    Returns ``None`` (allow) when auth is disabled or no key is configured.
    """
    if not settings.require_api_key or not settings.api_key:
        return
    if not x_api_key or x_api_key != settings.api_key:
        raise _unauthorized()
