"""Application logging configuration.

Provides a single :func:`setup_logging` entry point used at import time and on
startup. Logs go to stderr in a structured, human-readable format and honor the
configured level. Noisy third-party loggers are pinned to ``WARNING`` so the
console stays readable in production.
"""

from __future__ import annotations

import logging
import sys
from logging.config import dictConfig

DEFAULT_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"


def _config(level: str) -> dict:
    """Return the ``dictConfig`` payload for ``level``."""
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": DEFAULT_LOG_FORMAT,
                "datefmt": "%Y-%m-%dT%H:%M:%S%z",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "stream": sys.stderr,
                "formatter": "default",
                "level": level,
            },
        },
        "root": {
            "handlers": ["console"],
            "level": level,
        },
        "loggers": {
            "uvicorn": {"level": level, "handlers": ["console"], "propagate": False},
            "uvicorn.access": {"level": "WARNING", "handlers": ["console"], "propagate": False},
            "sqlalchemy.engine": {"level": "WARNING", "handlers": ["console"], "propagate": False},
            "httpx": {"level": "WARNING", "handlers": ["console"], "propagate": False},
        },
    }


def setup_logging(level: str | None = None) -> None:
    """Configure the root logger with a console handler at ``level``."""
    dictConfig(_config((level or "INFO").upper()))


def get_logger(name: str) -> logging.Logger:
    """Return a module-level logger."""
    return logging.getLogger(name)
