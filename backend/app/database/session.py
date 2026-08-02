"""SQLAlchemy database session management.

Initializes a SQLite engine, a session factory, and a declarative base. ORM
models are intentionally not defined yet; :func:`init_db` creates any tables
future models register on :class:`Base`, so adding models later requires no
wiring changes here.
"""

from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings


class Base(DeclarativeBase):
    """Declarative base for every ORM model in the application."""


def _resolve_database_url(url: str) -> str:
    """Resolve relative SQLite paths against the backend root.

    ``sqlite:///./data/career.db`` (from ``backend/``) becomes an absolute URL
    pointing at ``backend/data/career.db`` regardless of the CWD. Absolute
    paths, drive letters, and ``:memory:`` are passed through unchanged.
    """
    if not url.startswith("sqlite:///"):
        return url
    path_part = url.replace("sqlite:///", "", 1)
    if path_part == ":memory:" or path_part.startswith("/") or ":" in path_part[:2]:
        return url
    backend_root = Path(__file__).resolve().parents[2]
    resolved = (backend_root / path_part).resolve()
    resolved.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{resolved.as_posix()}"


_settings = get_settings()

engine = create_engine(
    _resolve_database_url(_settings.database_url),
    connect_args={"check_same_thread": False},
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


def init_db() -> None:
    """Create all tables registered on :class:`Base` (idempotent)."""
    Base.metadata.create_all(bind=engine)


def ping_db() -> bool:
    """Return whether the database is reachable by executing ``SELECT 1``."""
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    return True


def dispose_db() -> None:
    """Dispose the engine connection pool (call on shutdown)."""
    engine.dispose()


def get_db() -> Generator[Session, None, None]:
    """Yield a database session, rolling back and closing on exit.

    Any exception raised inside the request handler rolls the transaction back
    before the session is closed, so partial writes never leak.
    """
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
