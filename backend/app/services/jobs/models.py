"""Job Intelligence data models.

``Job`` is the structured object returned to downstream modules (matching,
recommendations, explainability). It is fully self-contained: normalized
description, extracted required skills, and the job embedding.
"""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field


class RequiredSkill(BaseModel):
    """A skill required by a job posting."""

    name: str
    category: str
    confidence: float


class Job(BaseModel):
    """A normalized job posting ready for matching."""

    id: str
    external_id: str
    source: str
    title: str
    company: str | None = None
    location: str | None = None
    description: str = ""
    description_excerpt: str | None = None
    url: str = ""
    salary_min: int | None = None
    salary_max: int | None = None
    salary_currency: str | None = None
    employment_type: str | None = None
    tags: list[str] = Field(default_factory=list)
    required_skills: list[RequiredSkill] = Field(default_factory=list)
    embedding: list[float] = Field(default_factory=list)
    posted_at: datetime | None = None
    fetched_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def search_text(self) -> str:
        """The text used for embedding and matching."""
        return f"{self.title}. {self.company or ''} {self.description}"


class JobQuery(BaseModel):
    """Parameters for a job fetch request.

    ``tags`` are provider tag names (e.g. Jobicy tags). When empty, they are
    derived from ``keywords``. ``location`` maps to the provider geo filter.
    """

    keywords: str = "ai ml"
    tags: list[str] = Field(default_factory=list)
    location: str | None = None
    count: int = 20
