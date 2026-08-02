"""Job Intelligence services.

Exposes the :class:`JobIntelligence` entry point, the :class:`Job` result
model, and the individual fetcher/normalizer/parser/embedder/cache services.
"""

from app.services.jobs.cache import JobCache
from app.services.jobs.embedding import JobEmbedder
from app.services.jobs.fetcher import (
    JobAPIError,
    JobFetcher,
    JobRateLimitError,
    JobicyFetcher,
    get_job_fetcher,
    resolve_geo,
    resolve_tags,
)
from app.services.jobs.models import Job, JobQuery, RequiredSkill
from app.services.jobs.normalizer import JobNormalizer
from app.services.jobs.parser import SkillCategory, SkillParser
from app.services.jobs.pipeline import JobIntelligence

__all__ = [
    "Job",
    "JobAPIError",
    "JobCache",
    "JobEmbedder",
    "JobFetcher",
    "JobIntelligence",
    "JobNormalizer",
    "JobQuery",
    "JobRateLimitError",
    "JobicyFetcher",
    "RequiredSkill",
    "SkillCategory",
    "SkillParser",
    "get_job_fetcher",
    "resolve_geo",
    "resolve_tags",
]
