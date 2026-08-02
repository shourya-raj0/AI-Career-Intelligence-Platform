"""Application configuration.

Settings are loaded from environment variables and an optional ``.env`` file
via pydantic-settings. The application layer reads its knobs from
:class:`Settings`; the existing services layer keeps reading plain env vars
(``GITHUB_TOKEN``, ``JOB_CACHE_DB``, ...) directly, so the two never disagree.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed, environment-driven application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Application metadata -------------------------------------------
    app_name: str = "AI Career Intelligence Platform"
    app_version: str = "1.0.0"
    environment: str = "development"
    debug: bool = False
    log_level: str = "INFO"

    # --- API surface -----------------------------------------------------
    api_v1_prefix: str = "/api/v1"
    host: str = "127.0.0.1"
    port: int = 8000

    # --- CORS -------------------------------------------------------------
    cors_origins: list[str] = ["*"]
    # Credentials-bearing CORS requests require explicit origins; setting this
    # True alongside a "*" origin is rejected at startup (see app.main).
    cors_allow_credentials: bool = False

    # --- Database ---------------------------------------------------------
    # Relative SQLite paths are resolved against the backend root.
    database_url: str = "sqlite:///./data/career.db"

    # --- Security ---------------------------------------------------------
    # Authentication is optional: enforced only when BOTH require_api_key is
    # true AND an api_key is configured (see app.core.security).
    require_api_key: bool = False
    api_key: str | None = None
    github_token: str | None = None

    # --- Runtime ----------------------------------------------------------
    request_timeout_seconds: float = 60.0


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached :class:`Settings` instance."""
    return Settings()
