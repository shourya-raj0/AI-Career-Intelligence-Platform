"""GitHub analysis orchestration service for the GitHub Intelligence layer.

The :class:`GitHubAnalyzer` is the only module in this package that talks to
the GitHub API (via PyGithub). It fetches a user's public repositories,
READMEs, and dependency manifests, then orchestrates three pure services:

* :class:`~app.services.github.framework_detector.FrameworkDetector` — detects
  frameworks/libraries from manifests and READMEs.
* :class:`~app.services.github.quality_analyzer.QualityAnalyzer` — scores
  repository engineering health.
* :class:`~app.services.github.evidence_builder.EvidenceBuilder` — links every
  claim back to a repository and source file.

The output is a fully structured :class:`GitHubAnalysisReport` consumed by the
Developer Profile Builder. This module never calls an LLM.
"""

from __future__ import annotations

import logging
import os
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import PurePosixPath
from typing import TYPE_CHECKING

from github import Auth, Github, GithubException, RateLimitExceededException, UnknownObjectException
from github.Repository import Repository

if TYPE_CHECKING:
    from app.services.github.framework_detector import FrameworkCategory

from app.services.github.evidence_builder import (
    EvidenceBuilder,
    EvidenceItem,
    EvidenceReport,
    RepoEvidenceInput,
)
from app.services.github.framework_detector import (
    DependencyFile,
    FrameworkDetectionResult,
    FrameworkDetector,
)
from app.services.github.quality_analyzer import (
    QualityAnalyzer,
    RepositoryMetadata,
    RepositoryQuality,
)
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

_README_TRUNCATE_CHARS = 20_000
_README_EXCERPT_CHARS = 800
_MAX_MANIFESTS_PER_REPO = 6
_MAX_FILE_BYTES = 2_000_000


@dataclass
class _TechnologyBucket:
    """Mutable aggregation state for one technology across repositories."""

    category: "FrameworkCategory"
    repositories: set[str] = field(default_factory=set)
    confidence_scores: list[float] = field(default_factory=list)


class GitHubAnalysisError(Exception):
    """Base error raised by the GitHub analyzer."""


class GitHubUserNotFoundError(GitHubAnalysisError):
    """Raised when the requested GitHub user does not exist."""


class GitHubRateLimitError(GitHubAnalysisError):
    """Raised when the GitHub API rate limit is exceeded."""


class GitHubProfileInsufficientError(GitHubAnalysisError):
    """Raised when a profile has no analyzable public repositories."""


class GitHubProfile(BaseModel):
    """Public metadata about the analyzed GitHub user."""

    username: str
    name: str | None = None
    bio: str | None = None
    avatar_url: str | None = None
    html_url: str
    blog: str | None = None
    location: str | None = None
    company: str | None = None
    followers: int = 0
    following: int = 0
    public_repos: int = 0
    created_at: datetime | None = None


class RepositoryAnalysis(BaseModel):
    """Complete analysis output for a single repository."""

    name: str
    full_name: str
    url: str
    description: str | None = None
    primary_language: str | None = None
    stars: int = 0
    forks: int = 0
    open_issues: int = 0
    size_kb: int = 0
    is_fork: bool = False
    is_archived: bool = False
    commit_count: int = 0
    default_branch: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    pushed_at: datetime | None = None
    has_readme: bool = False
    readme_excerpt: str | None = None
    dependency_files: list[DependencyFile] = Field(default_factory=list)
    detection: FrameworkDetectionResult = Field(default_factory=FrameworkDetectionResult)
    quality: RepositoryQuality | None = None
    evidence: list[EvidenceItem] = Field(default_factory=list)


class LanguageStat(BaseModel):
    """Primary-language distribution across analyzed repositories."""

    language: str
    repository_count: int
    share: float


class FrameworkStat(BaseModel):
    """Aggregated framework/library usage across analyzed repositories."""

    name: str
    category: str
    repository_count: int
    average_confidence: float
    evidence_repositories: list[str] = Field(default_factory=list)


class GitHubAnalysisReport(BaseModel):
    """Structured analysis report for one GitHub username."""

    username: str
    profile: GitHubProfile
    repositories: list[RepositoryAnalysis] = Field(default_factory=list)
    languages: list[LanguageStat] = Field(default_factory=list)
    frameworks: list[FrameworkStat] = Field(default_factory=list)
    libraries: list[FrameworkStat] = Field(default_factory=list)
    overall_quality_score: float = 0.0
    confidence: str
    confidence_reason: str
    evidence: EvidenceReport = Field(default_factory=EvidenceReport)
    rate_limit_remaining: int | None = None
    analyzed_at: datetime
    analyzed_repositories: int
    total_repositories: int


def build_github_client(token: str | None = None) -> Github:
    """Build an authenticated Github client."""

    from app.core.config import get_settings
    import app.core.config as config_module
    import os

    settings = get_settings()

    print("=" * 60)
    print("CONFIG FILE:", config_module.__file__)
    print("CURRENT WORKING DIRECTORY:", os.getcwd())
    print("GITHUB TOKEN:", settings.github_token)
    print("=" * 60)

    resolved_token = token or settings.github_token

    if resolved_token:
        return Github(auth=Auth.Token(resolved_token))

    print("WARNING: Using unauthenticated GitHub client")
    return Github()


class GitHubAnalyzer:
    """Orchestrates repository fetching and analysis for a GitHub user.

    Dependencies are injected via the constructor to keep the orchestrator
    testable; each collaborator defaults to a real, production-ready instance.
    """

    def __init__(
        self,
        github: Github,
        framework_detector: FrameworkDetector | None = None,
        quality_analyzer: QualityAnalyzer | None = None,
        evidence_builder: EvidenceBuilder | None = None,
        max_repositories: int = 20,
        include_forks: bool = False,
    ) -> None:
        self._github = github
        self._framework_detector = framework_detector or FrameworkDetector()
        self._quality_analyzer = quality_analyzer or QualityAnalyzer()
        self._evidence_builder = evidence_builder or EvidenceBuilder()
        self._max_repositories = max_repositories
        self._include_forks = include_forks

    def analyze_username(self, username: str) -> GitHubAnalysisReport:
        """Fetch and analyze the GitHub profile for ``username``.

        Raises :class:`GitHubUserNotFoundError` for unknown users,
        :class:`GitHubRateLimitError` on API rate limiting, and
        :class:`GitHubProfileInsufficientError` when no analyzable
        repositories exist.
        """
        user = self._get_user(username)
        repositories = self._fetch_repositories(user.login)
        analyzable = self._filter_analyzable(repositories)

        if not analyzable:
            raise GitHubProfileInsufficientError(
                f"Profile {user.login!r} has no public repositories to analyze."
            )

        analyses = [self._analyze_repository(repo) for repo in analyzable]
        report = self._assemble_report(user, analyses, total_repositories=user.public_repos)
        logger.info(
            "Analyzed %d repositories for GitHub user %r", len(analyses), user.login
        )
        return report

    def _get_user(self, username: str) -> "object":
        try:
            return self._github.get_user(username)
        except UnknownObjectException as exc:
            raise GitHubUserNotFoundError(f"GitHub user {username!r} was not found.") from exc
        except RateLimitExceededException as exc:
            raise GitHubRateLimitError(
                "GitHub rate limit exceeded. Please try again later."
            ) from exc
        except GithubException as exc:
            if exc.status == 404:
                raise GitHubUserNotFoundError(
                    f"GitHub user {username!r} was not found."
                ) from exc
            raise GitHubAnalysisError(
                f"Failed to fetch GitHub user {username!r}: {exc}"
            ) from exc

    def _fetch_repositories(self, username: str) -> list[Repository]:
        try:
            page = self._github.get_user(username).get_repos(
                sort="updated", direction="desc"
            )
        except RateLimitExceededException as exc:
            raise GitHubRateLimitError(
                "GitHub rate limit exceeded. Please try again later."
            ) from exc
        except GithubException as exc:
            raise GitHubAnalysisError(
                f"Failed to list repositories for {username!r}: {exc}"
            ) from exc

        repositories: list[Repository] = []
        for repo in page:
            if repo.fork and not self._include_forks:
                continue
            repositories.append(repo)
            if len(repositories) >= self._max_repositories:
                break
        return repositories

    @staticmethod
    def _filter_analyzable(repositories: list[Repository]) -> list[Repository]:
        """Drop archived and empty repositories from the analysis set."""
        analyzable: list[Repository] = []
        for repo in repositories:
            if repo.archived:
                continue
            if not repo.default_branch and repo.size == 0:
                continue
            analyzable.append(repo)
        return analyzable

    def _analyze_repository(self, repo: Repository) -> RepositoryAnalysis:
        tree_paths, file_sizes = self._fetch_tree(repo)
        readme_text = self._fetch_readme(repo)
        manifest_files = self._fetch_manifests(repo, tree_paths, file_sizes)
        commit_count = self._fetch_commit_count(repo)

        detection = self._framework_detector.detect(manifest_files)
        readme_matches = self._framework_detector.detect_from_readme(readme_text or "")
        detection = detection.model_copy(update={"readme_matches": readme_matches})

        metadata = self._build_metadata(repo, tree_paths, readme_text, commit_count)
        quality = self._quality_analyzer.analyze(metadata)

        evidence_input = RepoEvidenceInput(
            full_name=repo.full_name,
            primary_language=repo.language,
            detection=detection,
            readme_text=readme_text,
            quality=quality,
        )
        evidence = self._evidence_builder.build_repo_evidence(evidence_input)

        return RepositoryAnalysis(
            name=repo.name,
            full_name=repo.full_name,
            url=repo.html_url,
            description=repo.description,
            primary_language=repo.language,
            stars=repo.stargazers_count,
            forks=repo.forks_count,
            open_issues=repo.open_issues_count,
            size_kb=repo.size,
            is_fork=repo.fork,
            is_archived=repo.archived,
            commit_count=commit_count,
            default_branch=repo.default_branch,
            created_at=repo.created_at,
            updated_at=repo.updated_at,
            pushed_at=repo.pushed_at,
            has_readme=readme_text is not None,
            readme_excerpt=(readme_text or "")[:_README_EXCERPT_CHARS],
            dependency_files=manifest_files,
            detection=detection,
            quality=quality,
            evidence=evidence,
        )

    def _fetch_tree(self, repo: Repository) -> tuple[list[str], dict[str, int]]:
        if not repo.default_branch:
            return [], {}
        try:
            tree = repo.get_git_tree(repo.default_branch, recursive=True)
        except (GithubException, RateLimitExceededException):
            logger.warning("Could not fetch git tree for %s", repo.full_name)
            return [], {}
        paths: list[str] = []
        sizes: dict[str, int] = {}
        for element in tree.tree:
            if getattr(element, "type", None) == "blob":
                paths.append(element.path)
                sizes[element.path] = getattr(element, "size", 0) or 0
        return paths, sizes

    def _fetch_readme(self, repo: Repository) -> str | None:
        try:
            content = repo.get_readme()
            decoded = content.decoded_content.decode("utf-8", errors="replace")
        except UnknownObjectException:
            return None
        except (GithubException, RateLimitExceededException) as exc:
            logger.warning("Failed to read README for %s: %s", repo.full_name, exc)
            return None
        return decoded[:_README_TRUNCATE_CHARS]

    def _fetch_manifests(
        self,
        repo: Repository,
        tree_paths: list[str],
        file_sizes: dict[str, int],
    ) -> list[DependencyFile]:
        manifest_paths = [
            path for path in tree_paths if self._framework_detector.is_manifest(path)
        ]
        manifest_paths.sort(key=lambda path: path.count("/"))
        manifest_paths = manifest_paths[: _MAX_MANIFESTS_PER_REPO]

        dependency_files: list[DependencyFile] = []
        for path in manifest_paths:
            if file_sizes.get(path, 0) > _MAX_FILE_BYTES:
                continue
            try:
                content_file = repo.get_contents(path)
                if isinstance(content_file, list):
                    continue
                content = content_file.decoded_content.decode("utf-8", errors="replace")
            except (GithubException, RateLimitExceededException) as exc:
                logger.warning("Failed to fetch manifest %s from %s: %s", path, repo.full_name, exc)
                continue
            parsed = self._framework_detector.parse_manifest(path, content)
            if parsed is not None:
                dependency_files.append(parsed)
        return dependency_files

    @staticmethod
    def _fetch_commit_count(repo: Repository) -> int:
        try:
            return repo.get_commits().totalCount or 0
        except (GithubException, RateLimitExceededException):
            return 0

    @staticmethod
    def _build_metadata(
        repo: Repository,
        tree_paths: list[str],
        readme_text: str | None,
        commit_count: int,
    ) -> RepositoryMetadata:
        lowered_paths = [path.lower() for path in tree_paths]
        lowered_readme = (readme_text or "").lower()

        test_file_count = sum(
            1
            for path in lowered_paths
            if (
                path.startswith(("tests/", "test/", "__tests__/"))
                or PurePosixPath(path).name.startswith("test_")
                or PurePosixPath(path).name.endswith(("_test.py", ".test.js", ".test.ts", "_test.go"))
            )
        )

        return RepositoryMetadata(
            full_name=repo.full_name,
            stars=repo.stargazers_count,
            forks=repo.forks_count,
            commit_count=commit_count,
            created_at=repo.created_at,
            pushed_at=repo.pushed_at,
            is_fork=repo.fork,
            is_archived=repo.archived,
            has_license=repo.license is not None,
            has_description=bool(repo.description),
            has_readme=readme_text is not None,
            readme_chars=len(readme_text or ""),
            readme_sections=sum(1 for line in (readme_text or "").splitlines() if line.strip().startswith("##")),
            readme_mentions_setup=any(marker in lowered_readme for marker in ("install", "usage", "getting started", "quickstart", "run")),
            has_tests=test_file_count > 0,
            test_file_count=test_file_count,
            has_test_config=any(
                PurePosixPath(path).name
                in {
                    "pytest.ini",
                    "tox.ini",
                    "jest.config.js",
                    "jest.config.ts",
                    "jest.config.mjs",
                    "jest.config.cjs",
                    "vitest.config.ts",
                    "vitest.config.mjs",
                    "karma.conf.js",
                    "karma.conf.ts",
                    "cypress.config.ts",
                    "cypress.config.js",
                    "playwright.config.ts",
                    "phpunit.xml",
                    ".rspec",
                }
                for path in lowered_paths
            ),
            has_ci_github_actions=any(path.startswith(".github/workflows/") for path in lowered_paths),
            has_ci_other=any(
                path in lowered_paths
                for path in (
                    ".gitlab-ci.yml",
                    ".travis.yml",
                    "circleci/config.yml",
                    ".circleci/config.yml",
                    "jenkinsfile",
                    "azure-pipelines.yml",
                    "bitbucket-pipelines.yml",
                    "appveyor.yml",
                )
            ),
            has_docs_dir=any(path.startswith(("docs/", "doc/")) for path in lowered_paths),
            has_src_layout=any(
                path.startswith(("src/", "lib/", "app/"))
                for path in lowered_paths
            ),
            has_package_layout=any(
                path.count("/") == 0 and path.endswith((".py", ".go", ".rs", ".rb"))
                for path in lowered_paths
            ),
            has_root_config=any(
                path in lowered_paths
                for path in (
                    "pyproject.toml",
                    "requirements.txt",
                    "package.json",
                    "go.mod",
                    "cargo.toml",
                    "pom.xml",
                    "build.gradle",
                    "build.gradle.kts",
                    "gemfile",
                    "composer.json",
                    "dockerfile",
                )
            ),
            tree_file_count=len(tree_paths),
        )

    def _assemble_report(
        self,
        user: "object",
        analyses: list[RepositoryAnalysis],
        total_repositories: int,
    ) -> GitHubAnalysisReport:
        all_evidence = [item for analysis in analyses for item in analysis.evidence]
        evidence_report = self._evidence_builder.build_report(all_evidence)

        language_counts: Counter[str] = Counter(
            analysis.primary_language for analysis in analyses if analysis.primary_language
        )
        languages = [
            LanguageStat(
                language=language,
                repository_count=count,
                share=round(count / len(analyses), 3),
            )
            for language, count in language_counts.most_common()
        ]

        frameworks = self._aggregate_technologies(analyses, dependency_kind="framework")
        libraries = self._aggregate_technologies(analyses, dependency_kind="library")

        overall_quality = self._overall_quality_score(analyses)
        confidence, confidence_reason = self._compute_confidence(analyses)

        return GitHubAnalysisReport(
            username=user.login,
            profile=self._build_profile(user),
            repositories=analyses,
            languages=languages,
            frameworks=frameworks,
            libraries=libraries,
            overall_quality_score=overall_quality,
            confidence=confidence,
            confidence_reason=confidence_reason,
            evidence=evidence_report,
            rate_limit_remaining=self._rate_limit_remaining(),
            analyzed_at=datetime.now(timezone.utc),
            analyzed_repositories=len(analyses),
            total_repositories=total_repositories,
        )

    @staticmethod
    def _build_profile(user: "object") -> GitHubProfile:
        return GitHubProfile(
            username=user.login,
            name=user.name,
            bio=user.bio,
            avatar_url=user.avatar_url,
            html_url=user.html_url,
            blog=user.blog,
            location=user.location,
            company=user.company,
            followers=user.followers,
            following=user.following,
            public_repos=user.public_repos,
            created_at=user.created_at,
        )

    @staticmethod
    def _aggregate_technologies(
        analyses: list[RepositoryAnalysis], dependency_kind: str
    ) -> list[FrameworkStat]:
        grouped: dict[str, _TechnologyBucket] = {}
        for analysis in analyses:
            detections = (
                analysis.detection.frameworks
                if dependency_kind == "framework"
                else analysis.detection.libraries
            )
            for detection in detections:
                bucket = grouped.setdefault(
                    detection.name,
                    _TechnologyBucket(category=detection.category),
                )
                bucket.repositories.add(analysis.full_name)
                bucket.confidence_scores.append(detection.confidence)
        return [
            FrameworkStat(
                name=name,
                category=bucket.category.value,
                repository_count=len(bucket.repositories),
                average_confidence=round(
                    sum(bucket.confidence_scores) / len(bucket.confidence_scores), 3
                ),
                evidence_repositories=sorted(bucket.repositories),
            )
            for name, bucket in sorted(
                grouped.items(),
                key=lambda item: len(item[1].repositories),
                reverse=True,
            )
        ]

    @staticmethod
    def _overall_quality_score(analyses: list[RepositoryAnalysis]) -> float:
        if not analyses:
            return 0.0
        weighted = sum(
            (1.0 + analysis.stars) * (analysis.quality.overall_score if analysis.quality else 0.0)
            for analysis in analyses
        )
        total_weight = sum(1.0 + analysis.stars for analysis in analyses)
        return round(weighted / total_weight, 1)

    @staticmethod
    def _compute_confidence(
        analyses: list[RepositoryAnalysis],
    ) -> tuple[str, str]:
        analyzed = len(analyses)
        non_forks = [a for a in analyses if not a.is_fork]
        readme_coverage = sum(1 for a in analyses if a.has_readme) / analyzed
        active_repos = sum(1 for a in analyses if a.quality and a.quality.activity_score >= 30) / analyzed

        if analyzed >= 5 and len(non_forks) >= 3 and readme_coverage >= 0.6 and active_repos >= 0.5:
            return (
                "High",
                f"{analyzed} repositories with strong README coverage and recent activity.",
            )
        if analyzed >= 2 and readme_coverage >= 0.4:
            return (
                "Medium",
                f"{analyzed} repositories analyzed; README coverage at {int(readme_coverage * 100)}%.",
            )
        return (
            "Low",
            "Profile contains few public repositories or limited documentation.",
        )

    def _rate_limit_remaining(self) -> int | None:
        try:
            return self._github.get_rate_limit().core.remaining
        except (GithubException, RateLimitExceededException, AttributeError):
            return None
