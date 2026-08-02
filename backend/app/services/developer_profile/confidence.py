"""Deterministic profile confidence computation.

Produces a stable, reproducible confidence score for a derived
:class:`DeveloperProfile` from the underlying analysis signals. The report
type is imported only for type checking so this module stays light at runtime.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable

from app.services.developer_profile.models import ProfileConfidence

if TYPE_CHECKING:
    from app.services.github.analyzer import GitHubAnalysisReport, RepositoryAnalysis

_WEIGHT_REPOS = 0.30
_WEIGHT_README = 0.20
_WEIGHT_EVIDENCE = 0.20
_WEIGHT_DETECTION = 0.30

_REPO_CAP = 10
_EVIDENCE_CAP = 40

_HIGH_THRESHOLD = 0.70
_MEDIUM_THRESHOLD = 0.45


def compute_profile_confidence(report: "GitHubAnalysisReport") -> ProfileConfidence:
    """Compute the confidence level, numeric score, and reason for a report."""
    repo_count = len(report.repositories)
    if repo_count == 0:
        return ProfileConfidence(
            level="Low", score=0.0, reason="No repositories were analyzed."
        )

    readme_coverage = _coverage(report, lambda analysis: analysis.has_readme)
    detection_rate = _coverage(
        report, lambda analysis: bool(analysis.detection.all_dependencies())
    )
    evidence_items = len(report.evidence.items)

    score = (
        _WEIGHT_REPOS * min(repo_count / _REPO_CAP, 1.0)
        + _WEIGHT_README * readme_coverage
        + _WEIGHT_EVIDENCE * min(evidence_items / _EVIDENCE_CAP, 1.0)
        + _WEIGHT_DETECTION * detection_rate
    )
    score = round(min(1.0, max(0.0, score)), 3)

    if score >= _HIGH_THRESHOLD:
        level = "High"
    elif score >= _MEDIUM_THRESHOLD:
        level = "Medium"
    else:
        level = "Low"

    reason = (
        f"Analyzed {repo_count} repositories, {int(readme_coverage * 100)}% with READMEs, "
        f"{int(detection_rate * 100)}% with detected frameworks, and {evidence_items} evidence items."
    )
    return ProfileConfidence(level=level, score=score, reason=reason)


def _coverage(
    report: "GitHubAnalysisReport", predicate: Callable[["RepositoryAnalysis"], bool]
) -> float:
    """Return the fraction of analyzed repositories matching ``predicate``."""
    hits = sum(1 for analysis in report.repositories if predicate(analysis))
    return hits / len(report.repositories)
