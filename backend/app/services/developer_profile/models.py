"""Structured developer profile models.

The :class:`DeveloperProfile` is the single source of truth consumed by every
downstream module (matching, gap analysis, recommendations, explainability).
It is derived deterministically from a :class:`GitHubAnalysisReport` and is
never mutated after construction.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.services.github.evidence_builder import EvidenceItem, EvidenceReport


class ProfileLanguage(BaseModel):
    """A programming language and its share across analyzed repositories."""

    name: str
    repository_count: int
    share: float


class ProfileSkill(BaseModel):
    """A framework or library and how strongly it appears across repositories."""

    name: str
    category: str
    repository_count: int
    average_confidence: float
    evidence_repositories: list[str] = Field(default_factory=list)


class ProfileDomain(BaseModel):
    """A specialization (backend, AI/ML, etc.) and its derived profile strength."""

    name: str
    strength: float
    repository_count: int
    primary_skills: list[str] = Field(default_factory=list)


class ProfilePractice(BaseModel):
    """An engineering practice and how many repositories demonstrate it."""

    name: str
    repository_count: int
    repositories: list[str] = Field(default_factory=list)


class ProfileProject(BaseModel):
    """A summarized repository with its detected skills and practices."""

    name: str
    full_name: str
    url: str
    description: str | None = None
    primary_language: str | None = None
    stars: int = 0
    quality_score: float = 0.0
    frameworks: list[str] = Field(default_factory=list)
    domains: list[str] = Field(default_factory=list)
    engineering_practices: list[str] = Field(default_factory=list)
    evidence: list[EvidenceItem] = Field(default_factory=list)


class ProfileConfidence(BaseModel):
    """Deterministic confidence in the derived developer profile."""

    level: str = "Low"
    score: float = 0.0
    reason: str = "No analysis performed."


class DeveloperProfile(BaseModel):
    """The structured developer profile; the single source of truth downstream."""

    github_username: str
    languages: list[ProfileLanguage] = Field(default_factory=list)
    frameworks: list[ProfileSkill] = Field(default_factory=list)
    libraries: list[ProfileSkill] = Field(default_factory=list)
    domains: list[ProfileDomain] = Field(default_factory=list)
    projects: list[ProfileProject] = Field(default_factory=list)
    engineering_practices: list[ProfilePractice] = Field(default_factory=list)
    quality_score: float = 0.0
    confidence: ProfileConfidence = Field(default_factory=ProfileConfidence)
    evidence: EvidenceReport = Field(default_factory=EvidenceReport)

    def skill_names(self) -> set[str]:
        """Return the normalized (lowercased) skill names in this profile.

        Covers languages, frameworks, and libraries; used by matching and gap
        analysis to test whether a required job skill is already present.
        """
        names: set[str] = set()
        for skills in (self.languages, self.frameworks, self.libraries):
            for item in skills:
                names.add(item.name.lower())
        return names
