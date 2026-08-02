"""Repository quality analysis service for the GitHub Intelligence layer.

Computes a deterministic engineering-health score for a repository from
metadata signals (README presence/length, tests, CI/CD configuration,
documentation, project structure, commit activity, and community traction).

The analyzer is pure business logic over :class:`RepositoryMetadata`; it
never touches PyGithub or any network resource, which keeps it unit-testable
and decoupled from the data source.
"""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field


class RepositoryMetadata(BaseModel):
    """Immutable input snapshot describing one repository for scoring."""

    full_name: str
    stars: int = 0
    forks: int = 0
    commit_count: int = 0
    created_at: datetime | None = None
    pushed_at: datetime | None = None
    is_fork: bool = False
    is_archived: bool = False
    has_license: bool = False
    has_description: bool = False
    has_readme: bool = False
    readme_chars: int = 0
    readme_sections: int = 0
    readme_mentions_setup: bool = False
    has_tests: bool = False
    test_file_count: int = 0
    has_test_config: bool = False
    has_ci_github_actions: bool = False
    has_ci_other: bool = False
    has_docs_dir: bool = False
    has_src_layout: bool = False
    has_package_layout: bool = False
    has_root_config: bool = False
    tree_file_count: int = 0


class QualitySignal(BaseModel):
    """A single boolean engineering-health signal for dashboards."""

    name: str
    value: bool
    detail: str


class RepositoryQuality(BaseModel):
    """Deterministic quality assessment for one repository."""

    overall_score: float
    readme_score: float
    testing_score: float
    ci_score: float
    documentation_score: float
    structure_score: float
    activity_score: float
    community_score: float
    signals: list[QualitySignal] = Field(default_factory=list)


_README_WEIGHT = 0.20
_TESTING_WEIGHT = 0.20
_CI_WEIGHT = 0.15
_DOCUMENTATION_WEIGHT = 0.10
_STRUCTURE_WEIGHT = 0.10
_ACTIVITY_WEIGHT = 0.15
_COMMUNITY_WEIGHT = 0.10

_SETUP_MARKERS = ("install", "usage", "getting started", "quickstart", "run")


def _clamp(value: float, minimum: float = 0.0, maximum: float = 100.0) -> float:
    """Clamp ``value`` into the inclusive range ``[minimum, maximum]``."""
    return max(minimum, min(maximum, value))


def _days_since(moment: datetime | None) -> int | None:
    """Return whole days elapsed between ``moment`` and now (UTC)."""
    if moment is None:
        return None
    delta = datetime.now(timezone.utc) - moment
    return max(0, int(delta.days))


class QualityAnalyzer:
    """Scores repository engineering health from :class:`RepositoryMetadata`."""

    def analyze(self, metadata: RepositoryMetadata) -> RepositoryQuality:
        """Compute and return the quality assessment for ``metadata``."""
        readme_score = self._readme_score(metadata)
        testing_score = self._testing_score(metadata)
        ci_score = self._ci_score(metadata)
        documentation_score = self._documentation_score(metadata)
        structure_score = self._structure_score(metadata)
        activity_score = self._activity_score(metadata)
        community_score = self._community_score(metadata)

        overall = round(
            readme_score * _README_WEIGHT
            + testing_score * _TESTING_WEIGHT
            + ci_score * _CI_WEIGHT
            + documentation_score * _DOCUMENTATION_WEIGHT
            + structure_score * _STRUCTURE_WEIGHT
            + activity_score * _ACTIVITY_WEIGHT
            + community_score * _COMMUNITY_WEIGHT,
            1,
        )
        return RepositoryQuality(
            overall_score=overall,
            readme_score=readme_score,
            testing_score=testing_score,
            ci_score=ci_score,
            documentation_score=documentation_score,
            structure_score=structure_score,
            activity_score=activity_score,
            community_score=community_score,
            signals=self._build_signals(metadata),
        )

    @staticmethod
    def _readme_score(metadata: RepositoryMetadata) -> float:
        if not metadata.has_readme:
            return 0.0
        score = 30.0
        if metadata.readme_chars >= 300:
            score += 20.0
        if metadata.readme_chars >= 1500:
            score += 20.0
        if metadata.readme_mentions_setup:
            score += 20.0
        if metadata.readme_sections >= 4:
            score += 20.0
        return _clamp(score)

    @staticmethod
    def _testing_score(metadata: RepositoryMetadata) -> float:
        score = 0.0
        if metadata.has_tests:
            score += 60.0
        if metadata.test_file_count >= 5:
            score += 20.0
        elif metadata.test_file_count >= 2:
            score += 10.0
        if metadata.has_test_config:
            score += 20.0
        return _clamp(score)

    @staticmethod
    def _ci_score(metadata: RepositoryMetadata) -> float:
        if metadata.has_ci_github_actions and metadata.has_ci_other:
            return 100.0
        if metadata.has_ci_github_actions:
            return 70.0
        if metadata.has_ci_other:
            return 40.0
        return 0.0

    @staticmethod
    def _documentation_score(metadata: RepositoryMetadata) -> float:
        score = 0.0
        if metadata.has_docs_dir:
            score += 60.0
        if metadata.readme_chars >= 1000:
            score += 20.0
        if metadata.readme_sections >= 6:
            score += 20.0
        return _clamp(score)

    @staticmethod
    def _structure_score(metadata: RepositoryMetadata) -> float:
        score = 20.0
        if metadata.has_src_layout:
            score += 30.0
        elif metadata.has_package_layout:
            score += 25.0
        if metadata.has_root_config:
            score += 20.0
        if metadata.has_tests:
            score += 20.0
        if metadata.tree_file_count >= 20:
            score += 10.0
        return _clamp(score)

    @staticmethod
    def _activity_score(metadata: RepositoryMetadata) -> float:
        score = 0.0
        if metadata.commit_count >= 50:
            score += 50.0
        elif metadata.commit_count >= 20:
            score += 35.0
        elif metadata.commit_count >= 5:
            score += 20.0
        elif metadata.commit_count >= 1:
            score += 10.0
        days = _days_since(metadata.pushed_at)
        if days is not None:
            if days <= 30:
                score += 40.0
            elif days <= 90:
                score += 30.0
            elif days <= 365:
                score += 15.0
        if metadata.stars >= 10:
            score += 10.0
        return _clamp(score)

    @staticmethod
    def _community_score(metadata: RepositoryMetadata) -> float:
        score = 0.0
        if metadata.stars >= 50:
            score += 60.0
        elif metadata.stars >= 10:
            score += 40.0
        elif metadata.stars >= 1:
            score += 20.0
        if metadata.forks >= 20:
            score += 40.0
        elif metadata.forks >= 5:
            score += 25.0
        elif metadata.forks >= 1:
            score += 10.0
        return _clamp(score)

    @staticmethod
    def _build_signals(metadata: RepositoryMetadata) -> list[QualitySignal]:
        """Build the boolean dashboard signals for a repository."""
        return [
            QualitySignal(
                name="readme",
                value=metadata.has_readme,
                detail="Repository has a README file" if metadata.has_readme else "No README found",
            ),
            QualitySignal(
                name="testing",
                value=metadata.has_tests,
                detail=f"{metadata.test_file_count} test files detected"
                if metadata.has_tests
                else "No tests detected",
            ),
            QualitySignal(
                name="ci_cd",
                value=metadata.has_ci_github_actions or metadata.has_ci_other,
                detail="CI/CD configuration detected" if metadata.has_ci_github_actions else
                "Alternative CI configuration detected" if metadata.has_ci_other
                else "No CI/CD configuration found",
            ),
            QualitySignal(
                name="documentation",
                value=metadata.has_docs_dir or metadata.readme_chars >= 1000,
                detail="Docs folder or substantial README present"
                if metadata.has_docs_dir or metadata.readme_chars >= 1000
                else "Limited documentation",
            ),
            QualitySignal(
                name="project_structure",
                value=metadata.has_src_layout or metadata.has_package_layout,
                detail="Clear source layout detected"
                if metadata.has_src_layout or metadata.has_package_layout
                else "Flat or minimal project layout",
            ),
            QualitySignal(
                name="activity",
                value=metadata.commit_count > 0,
                detail=f"{metadata.commit_count} commits recorded",
            ),
            QualitySignal(
                name="community",
                value=metadata.stars > 0,
                detail=f"{metadata.stars} stars, {metadata.forks} forks",
            ),
            QualitySignal(
                name="license",
                value=metadata.has_license,
                detail="License file present" if metadata.has_license else "No license detected",
            ),
        ]
