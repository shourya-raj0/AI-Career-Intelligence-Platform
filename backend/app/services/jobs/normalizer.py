"""Job normalization.

Converts raw provider payloads into clean, structured :class:`Job` objects.
Performs no business logic beyond normalization: HTML stripping, entity
unescaping, whitespace collapsing, and field mapping. Malformed postings are
skipped so one bad record never fails the whole fetch.
"""

from __future__ import annotations

import html
import re
from datetime import datetime

from app.services.jobs.models import Job

_MAX_DESCRIPTION_CHARS = 20_000
_MAX_EXCERPT_CHARS = 400

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


def _clean_text(value: object) -> str:
    """Strip HTML tags and collapse whitespace from a raw string."""
    if not isinstance(value, str):
        return ""
    text = html.unescape(value)
    text = _TAG_RE.sub(" ", text)
    return _WS_RE.sub(" ", text).strip()


def _to_int(value: object) -> int | None:
    try:
        return int(value) if value not in (None, "") else None
    except (TypeError, ValueError):
        return None


def _parse_datetime(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _first_list_item(value: object) -> str | None:
    if isinstance(value, list) and value:
        return _clean_text(value[0])
    if isinstance(value, str) and value:
        return _clean_text(value)
    return None


class JobNormalizer:
    """Normalizes raw job postings into :class:`Job` objects."""

    SOURCE = "jobicy"

    def normalize(self, raw_jobs: list[dict]) -> list[Job]:
        """Normalize ``raw_jobs``, skipping postings missing required fields."""
        jobs: list[Job] = []
        for raw in raw_jobs:
            job = self._normalize_one(raw)
            if job is not None:
                jobs.append(job)
        return jobs

    def _normalize_one(self, raw: dict) -> Job | None:
        title = _clean_text(raw.get("jobTitle") or raw.get("title"))
        description = _clean_text(raw.get("jobDescription") or raw.get("description"))
        external_id = str(raw.get("id") or raw.get("external_id") or "")
        url = raw.get("url") or ""
        if not title or not description or not external_id or not url:
            return None

        excerpt = _clean_text(raw.get("jobExcerpt") or raw.get("excerpt") or "")
        tags = [_clean_text(tag) for tag in (raw.get("jobIndustry") or []) if _clean_text(tag)]

        return Job(
            id=f"{self.SOURCE}:{external_id}",
            external_id=external_id,
            source=self.SOURCE,
            title=title,
            company=_clean_text(raw.get("companyName") or raw.get("company")) or None,
            location=_clean_text(raw.get("jobGeo") or raw.get("location")) or None,
            description=description[:_MAX_DESCRIPTION_CHARS],
            description_excerpt=excerpt[:_MAX_EXCERPT_CHARS] or None,
            url=url,
            salary_min=_to_int(raw.get("annualSalaryMin") or raw.get("salary_min")),
            salary_max=_to_int(raw.get("annualSalaryMax") or raw.get("salary_max")),
            salary_currency=raw.get("salaryCurrency") or raw.get("salary_currency"),
            employment_type=_first_list_item(raw.get("jobType")) or raw.get("employment_type"),
            tags=tags,
            posted_at=_parse_datetime(raw.get("pubDate") or raw.get("posted_at")),
        )
