"""Unit tests for the DeveloperProfileBuilder and its deterministic helpers."""

from __future__ import annotations

from datetime import datetime, timezone

from app.services.developer_profile.builder import DeveloperProfileBuilder
from app.services.github.analyzer import (
    EvidenceReport,
    FrameworkStat,
    GitHubAnalysisReport,
    GitHubProfile,
    LanguageStat,
)
from app.services.github.framework_detector import FrameworkDetectionResult
from app.services.github.quality_analyzer import QualitySignal, RepositoryQuality

from tests.conftest import make_analysis, make_dependency


def _report() -> GitHubAnalysisReport:
    dep = make_dependency(name="FastAPI")
    detection = FrameworkDetectionResult(ecosystem="python", frameworks=[dep], libraries=[])
    quality = RepositoryQuality(
        overall_score=80.0,
        readme_score=80.0,
        testing_score=80.0,
        ci_score=80.0,
        documentation_score=80.0,
        structure_score=80.0,
        activity_score=80.0,
        community_score=80.0,
        signals=[
            QualitySignal(name="readme", value=True, detail="has readme"),
            QualitySignal(name="testing", value=True, detail="has tests"),
        ],
    )
    analyses = [make_analysis("core-app", "Python", detection=detection, quality=quality)]

    languages = [LanguageStat(language="Python", repository_count=1, share=1.0)]
    frameworks = [
        FrameworkStat(
            name="FastAPI",
            category="backend",
            repository_count=1,
            average_confidence=0.9,
            evidence_repositories=["dev/core-app"],
        )
    ]
    return GitHubAnalysisReport(
        username="dev",
        profile=GitHubProfile(username="dev", html_url="https://github.com/dev"),
        repositories=analyses,
        languages=languages,
        frameworks=frameworks,
        overall_quality_score=80.0,
        confidence="High",
        confidence_reason="solid profile",
        evidence=EvidenceReport(),
        rate_limit_remaining=100,
        analyzed_at=datetime.now(timezone.utc),
        analyzed_repositories=1,
        total_repositories=5,
    )


def test_builder_produces_structured_profile():
    profile = DeveloperProfileBuilder().build(_report())
    assert profile.github_username == "dev"
    assert profile.quality_score == 80.0
    assert [lang.name for lang in profile.languages] == ["Python"]
    assert [skill.name for skill in profile.frameworks] == ["FastAPI"]
    assert profile.confidence.score > 0.0


def test_skill_names_normalizes_case():
    names = DeveloperProfileBuilder().build(_report()).skill_names()
    assert "python" in names
    assert "fastapi" in names


def test_confidence_computed():
    profile = DeveloperProfileBuilder().build(_report())
    assert profile.confidence.level in {"High", "Medium"}
    assert profile.confidence.score >= 0.5


def test_projects_built_from_repositories():
    projects = DeveloperProfileBuilder().build(_report()).projects
    assert len(projects) == 1
    assert projects[0].name == "core-app"


def test_engineering_practices_populated():
    practices = DeveloperProfileBuilder().build(_report()).engineering_practices
    names = {p.name for p in practices}
    assert "readme" in names
    assert "testing" in names