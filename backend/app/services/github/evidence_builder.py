"""Evidence building service for the GitHub Intelligence layer.

Converts detected skills, quality signals, and repository metadata into a
structured, machine-consumable :class:`EvidenceReport`. Every claim about a
developer (language, framework, library, or engineering-health signal) is
linked back to a concrete repository and, where applicable, a source file —
so downstream explainability can cite real proof rather than assumptions.
"""

from __future__ import annotations

from collections import Counter
from enum import Enum

from pydantic import BaseModel, Field

from app.services.github.framework_detector import (
    DetectedDependency,
    DependencyKind,
    FrameworkCategory,
    FrameworkDetectionResult,
)
from app.services.github.quality_analyzer import RepositoryQuality


class EvidenceKind(str, Enum):
    """The type of signal an evidence item proves."""

    LANGUAGE = "language"
    FRAMEWORK = "framework"
    LIBRARY = "library"
    QUALITY = "quality"


class EvidenceItem(BaseModel):
    """A single verifiable claim tied to a repository and source file."""

    skill: str
    kind: EvidenceKind
    category: FrameworkCategory | None = None
    repository: str
    file_path: str | None = None
    detail: str
    confidence: float


class EvidenceReport(BaseModel):
    """Aggregated evidence across every analyzed repository."""

    items: list[EvidenceItem] = Field(default_factory=list)
    coverage: dict[str, int] = Field(default_factory=dict)
    by_repository: dict[str, list[EvidenceItem]] = Field(default_factory=dict)


class RepoEvidenceInput(BaseModel):
    """Inputs required to build evidence for a single repository."""

    full_name: str
    primary_language: str | None = None
    detection: FrameworkDetectionResult = Field(default_factory=FrameworkDetectionResult)
    readme_text: str | None = None
    quality: RepositoryQuality | None = None


class EvidenceBuilder:
    """Builds evidence items linking skills and signals to source proof."""

    def build_repo_evidence(self, repo_input: RepoEvidenceInput) -> list[EvidenceItem]:
        """Build the evidence items for a single repository."""
        items: list[EvidenceItem] = []
        items.extend(self._language_evidence(repo_input))
        items.extend(self._dependency_evidence(repo_input.detection.frameworks, repo_input.full_name))
        items.extend(self._dependency_evidence(repo_input.detection.libraries, repo_input.full_name))
        items.extend(self._readme_evidence(repo_input))
        items.extend(self._quality_evidence(repo_input))
        return items

    def build_report(self, items: list[EvidenceItem]) -> EvidenceReport:
        """Aggregate a flat list of evidence items into a :class:`EvidenceReport`."""
        coverage: dict[str, int] = dict(Counter(item.skill for item in items))
        by_repository: dict[str, list[EvidenceItem]] = {}
        for item in items:
            by_repository.setdefault(item.repository, []).append(item)
        return EvidenceReport(items=items, coverage=coverage, by_repository=by_repository)

    @staticmethod
    def _language_evidence(repo_input: RepoEvidenceInput) -> list[EvidenceItem]:
        if not repo_input.primary_language:
            return []
        return [
            EvidenceItem(
                skill=repo_input.primary_language,
                kind=EvidenceKind.LANGUAGE,
                category=None,
                repository=repo_input.full_name,
                file_path=None,
                detail=f"Primary language of {repo_input.full_name}",
                confidence=0.8,
            )
        ]

    @staticmethod
    def _dependency_evidence(
        detections: list[DetectedDependency], full_name: str
    ) -> list[EvidenceItem]:
        items: list[EvidenceItem] = []
        for detection in detections:
            kind = (
                EvidenceKind.FRAMEWORK
                if detection.kind is DependencyKind.FRAMEWORK
                else EvidenceKind.LIBRARY
            )
            items.append(
                EvidenceItem(
                    skill=detection.name,
                    kind=kind,
                    category=detection.category,
                    repository=full_name,
                    file_path=detection.source_file,
                    detail=f"Declared in {detection.source_file}",
                    confidence=detection.confidence,
                )
            )
        return items

    @staticmethod
    def _readme_evidence(repo_input: RepoEvidenceInput) -> list[EvidenceItem]:
        if not repo_input.readme_text:
            return []
        items: list[EvidenceItem] = []
        for match in repo_input.detection.readme_matches:
            kind = (
                EvidenceKind.FRAMEWORK
                if match.kind is DependencyKind.FRAMEWORK
                else EvidenceKind.LIBRARY
            )
            items.append(
                EvidenceItem(
                    skill=match.name,
                    kind=kind,
                    category=match.category,
                    repository=repo_input.full_name,
                    file_path="README.md",
                    detail=f"Mentioned in the README of {repo_input.full_name}",
                    confidence=match.confidence,
                )
            )
        return items

    @staticmethod
    def _quality_evidence(repo_input: RepoEvidenceInput) -> list[EvidenceItem]:
        if repo_input.quality is None:
            return []
        return [
            EvidenceItem(
                skill=signal.name,
                kind=EvidenceKind.QUALITY,
                category=None,
                repository=repo_input.full_name,
                file_path=None,
                detail=signal.detail,
                confidence=0.7,
            )
            for signal in repo_input.quality.signals
            if signal.value
        ]
