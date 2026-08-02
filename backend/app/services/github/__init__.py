"""GitHub Intelligence services.

Exposes the orchestrator entry points used by the GitHub agent:
:class:`GitHubAnalyzer`, its result models, and the client factory.
"""

from app.services.github.analyzer import (
    GitHubAnalysisError,
    GitHubAnalysisReport,
    GitHubAnalyzer,
    GitHubProfileInsufficientError,
    GitHubRateLimitError,
    GitHubUserNotFoundError,
    RepositoryAnalysis,
    build_github_client,
)
from app.services.github.framework_detector import (
    DependencyFile,
    DetectedDependency,
    FrameworkCategory,
    FrameworkDetectionResult,
    FrameworkDetector,
)
from app.services.github.quality_analyzer import (
    QualityAnalyzer,
    RepositoryMetadata,
    RepositoryQuality,
)
from app.services.github.evidence_builder import (
    EvidenceBuilder,
    EvidenceItem,
    EvidenceReport,
    RepoEvidenceInput,
)

__all__ = [
    "DependencyFile",
    "DetectedDependency",
    "EvidenceBuilder",
    "EvidenceItem",
    "EvidenceReport",
    "FrameworkCategory",
    "FrameworkDetectionResult",
    "FrameworkDetector",
    "GitHubAnalysisError",
    "GitHubAnalysisReport",
    "GitHubAnalyzer",
    "GitHubProfileInsufficientError",
    "GitHubRateLimitError",
    "GitHubUserNotFoundError",
    "QualityAnalyzer",
    "RepoEvidenceInput",
    "RepositoryAnalysis",
    "RepositoryMetadata",
    "RepositoryQuality",
    "build_github_client",
]
