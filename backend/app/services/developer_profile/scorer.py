"""Deterministic aggregation of a GitHub analysis into profile structures.

Pure business logic: these functions take a :class:`GitHubAnalysisReport` and
produce the derived views that make up a :class:`DeveloperProfile`. They never
touch the network or an LLM. The report type is imported only for type
checking, so this module does not pull PyGithub in at runtime.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.services.developer_profile.models import (
    ProfileDomain,
    ProfileLanguage,
    ProfilePractice,
    ProfileProject,
    ProfileSkill,
)

if TYPE_CHECKING:
    from app.services.github.analyzer import FrameworkStat, GitHubAnalysisReport

_GENERAL_CATEGORY = "general"
_DOMAIN_SATURATION = 4.0


def build_languages(report: "GitHubAnalysisReport") -> list[ProfileLanguage]:
    """Map the report language stats into profile languages."""
    return [
        ProfileLanguage(
            name=stat.language,
            repository_count=stat.repository_count,
            share=stat.share,
        )
        for stat in report.languages
    ]


def build_skills(stats: list["FrameworkStat"]) -> list[ProfileSkill]:
    """Map aggregated framework/library stats into profile skills."""
    return [
        ProfileSkill(
            name=stat.name,
            category=stat.category,
            repository_count=stat.repository_count,
            average_confidence=stat.average_confidence,
            evidence_repositories=list(stat.evidence_repositories),
        )
        for stat in stats
    ]


def build_domains(report: "GitHubAnalysisReport") -> list[ProfileDomain]:
    """Derive specializations from framework/library categories.

    Generic libraries are excluded so the domain list reflects meaningful
    specializations. Strength is a saturated (0-100), deterministic function
    of the total confidence-weighted footprint of each category.
    """
    weights: dict[str, float] = {}
    skills_by_category: dict[str, list[FrameworkStat]] = {}
    repos_by_category: dict[str, set[str]] = {}

    for stat in report.frameworks + report.libraries:
        if stat.category == _GENERAL_CATEGORY:
            continue
        weights[stat.category] = (
            weights.get(stat.category, 0.0) + stat.repository_count * stat.average_confidence
        )
        skills_by_category.setdefault(stat.category, []).append(stat)
        repos_by_category.setdefault(stat.category, set()).update(stat.evidence_repositories)

    domains = [
        ProfileDomain(
            name=category,
            strength=_domain_strength(weights[category]),
            repository_count=len(repos_by_category[category]),
            primary_skills=[
                skill.name
                for skill in sorted(
                    skills_by_category[category],
                    key=lambda skill: skill.repository_count,
                    reverse=True,
                )[:3]
            ],
        )
        for category in weights
    ]
    return sorted(domains, key=lambda domain: domain.strength, reverse=True)


def build_projects(report: "GitHubAnalysisReport") -> list[ProfileProject]:
    """Summarize each repository with its detected skills and practices."""
    projects: list[ProfileProject] = []
    for analysis in report.repositories:
        detections = analysis.detection.frameworks + analysis.detection.libraries
        projects.append(
            ProfileProject(
                name=analysis.name,
                full_name=analysis.full_name,
                url=analysis.url,
                description=analysis.description,
                primary_language=analysis.primary_language,
                stars=analysis.stars,
                quality_score=analysis.quality.overall_score if analysis.quality else 0.0,
                frameworks=[detection.name for detection in analysis.detection.frameworks],
                domains=sorted({detection.category.value for detection in detections} - {_GENERAL_CATEGORY}),
                engineering_practices=[
                    signal.name for signal in analysis.quality.signals if signal.value
                ]
                if analysis.quality
                else [],
                evidence=list(analysis.evidence),
            )
        )
    return sorted(projects, key=lambda project: project.quality_score, reverse=True)


def build_practices(report: "GitHubAnalysisReport") -> list[ProfilePractice]:
    """Aggregate which engineering practices appear across repositories."""
    repos_by_practice: dict[str, set[str]] = {}
    for analysis in report.repositories:
        if analysis.quality is None:
            continue
        for signal in analysis.quality.signals:
            if signal.value:
                repos_by_practice.setdefault(signal.name, set()).add(analysis.full_name)
    return [
        ProfilePractice(
            name=name,
            repository_count=len(repositories),
            repositories=sorted(repositories),
        )
        for name, repositories in sorted(
            repos_by_practice.items(), key=lambda item: len(item[1]), reverse=True
        )
    ]


def _domain_strength(weight: float) -> float:
    """Map a cumulative confidence-weighted footprint into a 0-100 score."""
    return round(100.0 * weight / (weight + _DOMAIN_SATURATION), 1)
