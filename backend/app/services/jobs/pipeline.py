"""Job Intelligence orchestration.

Ties together fetching, normalization, required-skill extraction, embedding,
and caching into one entry point that returns ready-to-match :class:`Job`
objects. Individual collaborators are injectable for testing; defaults are
production-ready.
"""

from __future__ import annotations

import os

from app.services.jobs.cache import JobCache
from app.services.jobs.embedding import JobEmbedder
from app.services.jobs.fetcher import JobFetcher, get_job_fetcher, resolve_tags
from app.services.jobs.models import Job, JobQuery
from app.services.jobs.normalizer import JobNormalizer
from app.services.jobs.parser import SkillParser


class JobIntelligence:
    """Fetches, normalizes, enriches, embeds, and caches job postings."""

    def __init__(
        self,
        fetcher: JobFetcher | None = None,
        normalizer: JobNormalizer | None = None,
        parser: SkillParser | None = None,
        embedder: JobEmbedder | None = None,
        cache: JobCache | None = None,
        ttl_hours: float | None = None,
    ) -> None:
        self._fetcher = fetcher or get_job_fetcher()
        self._normalizer = normalizer or JobNormalizer()
        self._parser = parser or SkillParser()
        self._embedder = embedder or JobEmbedder()
        self._cache = cache or JobCache()
        self._ttl_hours = ttl_hours if ttl_hours is not None else float(
            os.getenv("JOB_CACHE_TTL_HOURS", "6")
        )

    def fetch_and_prepare(self, query: JobQuery) -> list[Job]:
        """Return fresh or cached, normalized, enriched Job objects for ``query``."""
        tags = resolve_tags(query)
        query_key = f"{','.join(tags)}:{query.location or ''}:{query.count}"

        cached = self._cache.get_fresh(query_key, self._ttl_hours)
        if cached is not None:
            return cached

        raw_jobs = self._fetcher.fetch(query)
        jobs = self._normalizer.normalize(raw_jobs)

        for job in jobs:
            job.required_skills = self._parser.extract_skills(job.title, job.description)

        texts = [job.search_text() for job in jobs]
        embeddings = self._embedder.embed_documents(texts)
        for job, embedding in zip(jobs, embeddings):
            job.embedding = embedding

        self._cache.store(query_key, jobs)
        return jobs

    def close(self) -> None:
        """Release process-wide resources (job cache DB, fetcher client)."""
        self._cache.close()
        self._fetcher.close()
