"""Job API fetching.

Integrates the Jobicy remote-jobs API by default, behind a small provider
interface so other free job APIs can be swapped in without touching callers.
The fetcher returns raw provider payloads; normalization happens in
:mod:`app.services.jobs.normalizer`.
"""

from __future__ import annotations

import os
from abc import ABC, abstractmethod

import httpx

from app.services.jobs.models import JobQuery


class JobAPIError(Exception):
    """Base error raised by a job API client."""


class JobRateLimitError(JobAPIError):
    """Raised when the job API rate limit is exceeded."""


_DEFAULT_TAGS = ["data", "software-engineering"]

_ROLE_TAGS: dict[str, list[str]] = {
    "ai": ["data", "software-engineering"],
    "ml": ["data", "software-engineering"],
    "machine learning": ["data", "software-engineering"],
    "data": ["data"],
    "backend": ["backend"],
    "frontend": ["frontend"],
    "fullstack": ["full-stack"],
    "full-stack": ["full-stack"],
    "devops": ["software-engineering"],
    "software": ["software-engineering"],
}


_GEO_ALIASES: list[tuple[tuple[str, ...], str]] = [
    (("usa", "us", "united states", "america"), "USA"),
    (("uk", "united kingdom", "england", "scotland", "wales", "london"), "UK"),
    (
        ("europe", "eu", "european union", "germany", "france", "netherlands", "spain",
         "portugal", "poland", "sweden", "denmark", "norway", "finland", "ireland",
         "belgium", "switzerland", "austria", "italy"),
        "Europe",
    ),
    (("australia",), "Australia"),
    (("canada",), "Canada"),
]

_WORLDWIDE_MARKERS = ("worldwide", "remote", "anywhere", "global")


def resolve_tags(query: JobQuery) -> list[str]:
    """Resolve the Jobicy tags to fetch, from explicit tags or keywords."""
    if query.tags:
        return list(dict.fromkeys(query.tags))
    lowered = query.keywords.lower()
    for role, tags in _ROLE_TAGS.items():
        if role in lowered:
            return list(tags)
    return list(_DEFAULT_TAGS)


def resolve_geo(location: str | None) -> str | None:
    """Map a free-form location to a valid Jobicy geo value, or ``None``."""
    if not location:
        return None
    lowered = location.strip().lower()
    if not lowered or any(marker in lowered for marker in _WORLDWIDE_MARKERS):
        return None
    for aliases, geo in _GEO_ALIASES:
        if any(alias in lowered for alias in aliases):
            return geo
    return None


class JobFetcher(ABC):
    """Fetches raw job payloads for a :class:`JobQuery`."""

    @abstractmethod
    def fetch(self, query: JobQuery) -> list[dict]:
        """Return raw job postings for ``query``."""

    def close(self) -> None:
        """Release any resources held by the fetcher.

        The base implementation is a no-op; subclasses that own clients (e.g.
        an ``httpx.Client``) should override it.
        """


class JobicyFetcher(JobFetcher):
    """Fetch remote jobs from the Jobicy public API (no key required)."""

    BASE_URL = "https://jobicy.com/api/v2/remote-jobs"

    def __init__(self, client: httpx.Client | None = None, timeout: float = 30.0) -> None:
        self._client = client or httpx.Client(timeout=timeout)

    def fetch(self, query: JobQuery) -> list[dict]:
        jobs: list[dict] = []
        seen: set[int] = set()
        geo = resolve_geo(query.location)
        for tag in resolve_tags(query):
            params: dict[str, object] = {"count": query.count, "tag": tag}
            if geo:
                params["geo"] = geo
            payload = self._get(params)
            for raw in payload.get("jobs") or []:
                raw_id = raw.get("id")
                if raw_id in seen:
                    continue
                seen.add(raw_id)
                jobs.append(raw)
                if len(jobs) >= query.count:
                    break
            if len(jobs) >= query.count:
                break
        return jobs[: query.count]

    def _get(self, params: dict[str, object]) -> dict:
        try:
            response = self._client.get(self.BASE_URL, params=params)
        except httpx.HTTPError as exc:
            raise JobAPIError(f"Job API request failed: {exc}") from exc
        if response.status_code == 429:
            raise JobRateLimitError("Job API rate limit exceeded. Try again later.")
        if response.status_code != 200:
            raise JobAPIError(f"Job API returned HTTP {response.status_code}.")
        payload = response.json()
        if not payload.get("success"):
            raise JobAPIError(payload.get("message") or "Job API reported a failure.")
        return payload

    def close(self) -> None:
        """Close the underlying ``httpx.Client`` to release sockets."""
        self._client.close()


def get_job_fetcher() -> JobFetcher:
    """Build the configured job fetcher (provider via ``JOB_API_PROVIDER``)."""
    provider = os.getenv("JOB_API_PROVIDER", "jobicy").strip().lower()
    if provider == "jobicy":
        return JobicyFetcher()
    raise ValueError(f"Unsupported JOB_API_PROVIDER: {provider!r}")
