"""SQLite-backed caching for fetched jobs.

Caches normalized jobs (including extracted skills and embeddings) keyed by the
resolved fetch query. Repeating the same query within the TTL returns the cached
jobs without hitting the job API or recomputing embeddings. The database file
defaults to ``backend/data/jobs.db`` and can be overridden with
``JOB_CACHE_DB``.
"""

from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.services.jobs.models import Job, RequiredSkill

_SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    query_key        TEXT NOT NULL,
    id               TEXT NOT NULL,
    external_id      TEXT,
    source           TEXT,
    title            TEXT,
    company          TEXT,
    location         TEXT,
    description      TEXT,
    url              TEXT,
    salary_min       INTEGER,
    salary_max       INTEGER,
    salary_currency  TEXT,
    employment_type  TEXT,
    tags             TEXT,
    required_skills  TEXT,
    embedding        TEXT,
    posted_at        TEXT,
    fetched_at       TEXT,
    PRIMARY KEY (query_key, id)
);
"""

_JOB_COLUMNS = (
    "query_key",
    "id",
    "external_id",
    "source",
    "title",
    "company",
    "location",
    "description",
    "url",
    "salary_min",
    "salary_max",
    "salary_currency",
    "employment_type",
    "tags",
    "required_skills",
    "embedding",
    "posted_at",
    "fetched_at",
)


def _default_db_path() -> Path:
    configured = os.getenv("JOB_CACHE_DB")
    if configured:
        return Path(configured)
    backend_root = Path(__file__).resolve().parents[3]
    return backend_root / "data" / "jobs.db"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class JobCache:
    """Stores and retrieves normalized jobs for a fetch query."""

    def __init__(self, db_path: str | Path | None = None) -> None:
        self._db_path = Path(db_path) if db_path else _default_db_path()
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._get_connection() as conn:
            conn.executescript(_SCHEMA)

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self._db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def get_fresh(self, query_key: str, ttl_hours: float) -> list[Job] | None:
        """Return cached jobs for ``query_key`` if fetched within the TTL."""
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=ttl_hours)).isoformat()
        with self._get_connection() as conn:
            rows = conn.execute(
                f"SELECT {', '.join(_JOB_COLUMNS)} FROM jobs "
                "WHERE query_key = ? AND fetched_at >= ? ORDER BY id",
                (query_key, cutoff),
            ).fetchall()
        if not rows:
            return None
        return [self._row_to_job(row) for row in rows]

    def store(self, query_key: str, jobs: list[Job]) -> None:
        """Replace the cached jobs for ``query_key`` with ``jobs``."""
        fetched_at = _now_iso()
        with self._get_connection() as conn:
            conn.execute("DELETE FROM jobs WHERE query_key = ?", (query_key,))
            conn.executemany(
                f"INSERT INTO jobs ({', '.join(_JOB_COLUMNS)}) VALUES ({', '.join('?' * len(_JOB_COLUMNS))})",
                [
                    (
                        query_key,
                        job.id,
                        job.external_id,
                        job.source,
                        job.title,
                        job.company,
                        job.location,
                        job.description,
                        job.url,
                        job.salary_min,
                        job.salary_max,
                        job.salary_currency,
                        job.employment_type,
                        json.dumps(job.tags),
                        json.dumps(
                            [skill.model_dump() for skill in job.required_skills]
                        ),
                        json.dumps(job.embedding),
                        job.posted_at.isoformat() if job.posted_at else None,
                        fetched_at,
                    )
                    for job in jobs
                ],
            )
            conn.commit()

    def close(self) -> None:
        """No-op: each operation opens and closes its own connection."""

    @staticmethod
    def _row_to_job(row: sqlite3.Row) -> Job:
        return Job(
            id=row[1],
            external_id=row[2],
            source=row[3],
            title=row[4],
            company=row[5],
            location=row[6],
            description=row[7] or "",
            url=row[8] or "",
            salary_min=row[9],
            salary_max=row[10],
            salary_currency=row[11],
            employment_type=row[12],
            tags=json.loads(row[13] or "[]"),
            required_skills=[
                RequiredSkill(**item) for item in json.loads(row[14] or "[]")
            ],
            embedding=json.loads(row[15] or "[]"),
            posted_at=datetime.fromisoformat(row[16]) if row[16] else None,
            fetched_at=datetime.fromisoformat(row[17]),
        )
