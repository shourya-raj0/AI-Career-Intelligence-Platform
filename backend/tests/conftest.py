"""Shared fixtures, factories, and deterministic stand-ins for tests.

The backend services default to production collaborators (PyGithub, the real
sentence-transformers model, the live job API). Unit tests use the small
deterministic fakes below so they run fast and offline — no torch download,
no network calls.

Run.
    cd backend
    python -m pytest

Layout:
    tests/unit         pure business-logic tests (offline).
    tests/integration  FastAPI + dependency-injection wiring tests.
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.developer_profile.models import DeveloperProfile  # noqa: E402
from app.services.github.analyzer import (  # noqa: E402
    GitHubAnalysisReport,
    GitHubProfile,
    RepositoryAnalysis,
)
from app.services.github.framework_detector import (  # noqa: E402
    DetectedDependency,
    DependencyKind,
    FrameworkCategory,
    FrameworkDetectionResult,
)
from app.services.github.quality_analyzer import QualitySignal, RepositoryQuality  # noqa: E402
from app.services.jobs.models import Job, RequiredSkill  # noqa: E402


class FakeEmbedder:
    """Deterministic embedding stand-in (no torch).

    Produces a fixed bag-of-characters feature vector so the same text always
    maps to the same vector, distinct texts to distinct vectors. Enough to
    exercise ranking, similarity, and retrieval deterministically.
    """

    dim = 8

    def __init__(self) -> None:
        self._call_count = 0

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        self._call_count += 1
        return [self._vector(text) for text in texts]

    def embed_profile(self, profile: DeveloperProfile) -> list[float]:
        return self._vector(profile.github_username)

    def _embed_into_embedding(self, value: list[float]) -> None:  # placeholder
        pass

    @classmethod
    def _vector(cls, text: str) -> list[float]:
        seed = sum((i + 1) * ord(ch) for i, ch in enumerate(text)) % 97
        vector = [0.0] * cls.dim
        vector[seed % cls.dim] = 1.0 + (seed % 40) / 40.0
        return vector


@pytest.fixture
def embedder() -> FakeEmbedder:
    return FakeEmbedder()


def make_quality(
    has_readme: bool = True,
    has_tests: bool = True,
    has_ci_cfg: bool = True,
    score: float = 70.0,
) -> RepositoryQuality:
    """Build a canned :class:`RepositoryQuality` for fixtures."""
    return RepositoryQuality(
        overall_score=score,
        readme_score=60.0 if has_readme else 0.0,
        testing_score=60.0 if has_tests else 0.0,
        ci_score=70.0 if has_ci_cfg else 0.0,
        documentation_score=60.0,
        structure_score=60.0,
        activity_score=60.0,
        community_score=40.0,
        signals=[
            _signal("readme", has_readme),
            _signal("testing", has_tests),
            _signal("ci_cd", has_ci_cfg),
        ],
    )


def _signal(name: str, value: bool):
    from app.services.github.quality_analyzer import QualitySignal

    return QualitySignal(name=name, value=value, detail=f"{name}={value}")


def make_dependency(
    name: str = "FastAPI",
    category: FrameworkCategory = FrameworkCategory.BACKEND,
    kind: DependencyKind = DependencyKind.FRAMEWORK,
    source_file: str = "requirements.txt",
    confidence: float = 0.9,
) -> DetectedDependency:
    return DetectedDependency(
        name=name,
        category=category,
        kind=kind,
        source_file=source_file,
        confidence=confidence,
        aliases=[name.lower()],
    )


def make_analysis(
    name: str,
    primary_language: str,
    detection: FrameworkDetectionResult | None = None,
    quality: RepositoryQuality | None = None,
    stars: int = 1,
    is_fork: bool = False,
) -> RepositoryAnalysis:
    return RepositoryAnalysis(
        name=name,
        full_name=f"dev/{name}",
        url=f"https://github.com/dev/{name}",
        description=f"description of {name}",
        primary_language=primary_language,
        stars=stars,
        forks=0,
        open_issues=0,
        size_kb=100,
        is_fork=is_fork,
        is_archived=False,
        commit_count=40,
        default_branch="main",
        created_at=None,
        updated_at=None,
        pushed_at=None,
        has_readme=True,
        readme_excerpt=f"readme {name}",
        dependency_files=[],
        detection=detection or FrameworkDetectionResult(ecosystem="python"),
        quality=quality or make_quality(),
        evidence=[],
    )


def make_job(
    title: str,
    required: list[tuple[str, float]] | None = None,
    description: str = "desc",
    location: str | None = None,
    company: str = "Acme",
) -> Job:
    skills = [
        RequiredSkill(name=name, category="category", confidence=conf)
        for name, conf in (required or [])
    ]
    job = Job(
        id=f"jobicy:{title}",
        external_id=title,
        source="jobicy",
        title=title,
        company=company,
        location=location,
        description=description,
        url=f"https://example.com/{title}",
        employment_type="Full-time",
        required_skills=skills,
        fetched_at=datetime.now(timezone.utc),
    )
    job.embedding = FakeEmbedder._vector(f"{title}. {description}")
    return job


def make_profile(languages: list[str] | None = None) -> DeveloperProfile:
    return DeveloperProfile(
        github_username="dev",
        languages=[
            {
                "name": lang,
                "repository_count": 1,
                "share": 0.5,
            }
            for lang in (languages or ["Python"])
        ],
        frameworks=[
            {
                "name": "FastAPI",
                "category": "backend",
                "repository_count": 1,
                "average_confidence": 0.9,
            }
        ],
        quality_score=70.0,
    )


def make_github_report(username: str = "dev") -> GitHubAnalysisReport:
    """Build a minimal, valid :class:`GitHubAnalysisReport` for test wiring."""
    from datetime import datetime, timezone

    return GitHubAnalysisReport(
        username=username,
        profile=GitHubProfile(username=username, html_url=f"https://github.com/{username}"),
        repositories=[make_analysis(f"{username}-repo", "Python")],
        confidence="Medium",
        confidence_reason="minimal report",
        analyzed_at=datetime.now(timezone.utc),
        analyzed_repositories=1,
        total_repositories=1,
    )