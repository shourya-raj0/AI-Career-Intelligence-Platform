"""Developer Profile Builder service.

Converts a :class:`GitHubAnalysisReport` into the structured
:class:`DeveloperProfile` — the single source of truth consumed by every
downstream module (matching, gap analysis, recommendations, explainability).
This module is deterministic and performs no network I/O.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.services.developer_profile.confidence import compute_profile_confidence
from app.services.developer_profile.models import DeveloperProfile
from app.services.developer_profile.scorer import (
    build_domains,
    build_languages,
    build_practices,
    build_projects,
    build_skills,
)

if TYPE_CHECKING:
    from app.services.github.analyzer import GitHubAnalysisReport


class DeveloperProfileBuilder:
    """Builds a :class:`DeveloperProfile` from a GitHub analysis report."""

    def build(self, report: "GitHubAnalysisReport") -> DeveloperProfile:
        """Derive the structured developer profile for ``report``."""
        return DeveloperProfile(
            github_username=report.username,
            languages=build_languages(report),
            frameworks=build_skills(report.frameworks),
            libraries=build_skills(report.libraries),
            domains=build_domains(report),
            projects=build_projects(report),
            engineering_practices=build_practices(report),
            quality_score=report.overall_quality_score,
            confidence=compute_profile_confidence(report),
            evidence=report.evidence,
        )
