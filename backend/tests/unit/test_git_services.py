"""Unit tests for GitHub Intelligence services (pure Python, offline)."""

from __future__ import annotations

from app.services.github.analyzer import GitHubAnalyzer
from app.services.github.framework_detector import (
    FrameworkDetectionResult,
    FrameworkDetector,
)
from app.services.github.quality_analyzer import QualityAnalyzer, RepositoryMetadata

from tests.conftest import make_analysis, make_dependency, make_quality


# --- FrameworkDetector: manifest parsing ------------------------------------


def test_parse_requirements_txt():
    detector = FrameworkDetector()
    deps = detector.parse_manifest("requirements.txt", "numpy==1.24\nfastapi>=0.1\n")
    assert deps is not None
    assert "numpy" in deps.dependencies
    assert "fastapi" in deps.dependencies
    assert deps.ecosystem == "python"


def test_parse_requires_ignores_comments_and_blank_lines():
    detector = FrameworkDetector()
    deps = detector.parse_manifest("requirements.txt", "# comment\n\nnumpy\n")
    assert deps is not None
    assert deps.dependencies == ["numpy"]


def test_parse_package_json():
    detector = FrameworkDetector()
    content = '{"dependencies": {"react": "^18.0.0", "express": "^4.0.0"}}'
    deps = detector.parse_manifest("package.json", content)
    assert deps is not None
    assert "react" in deps.dependencies
    assert "express" in deps.dependencies


def test_unknown_manifest_path_returns_none():
    detector = FrameworkDetector()
    assert detector.parse_manifest("foo.txt", "anything") is None


def test_detect_classifies_frameworks_and_libraries():
    detector = FrameworkDetector()
    requirements = detector.parse_manifest("requirements.txt", "fastapi\nnumpy\n")
    result = detector.detect([requirements])
    assert "FastAPI" in {d.name for d in result.frameworks}
    assert "NumPy" in {d.name for d in result.libraries}
    assert result.ecosystem == "python"


def test_detect_from_readme():
    detector = FrameworkDetector()
    names = {m.name for m in detector.detect_from_readme("Uses FastAPI and pytest.")}
    assert "Docker" not in names  # not mentioned
    assert "pytest" in names


def test_is_manifest_matches_supported_files():
    detector = FrameworkDetector()
    assert detector.is_manifest("requirements.txt")
    assert detector.is_manifest("go.mod")
    assert not detector.is_manifest("README.md")


def test_detect_returns_no_primary_framework_for_generic_deps():
    detector = FrameworkDetector()
    deps = detector.parse_manifest("requirements.txt", "requests")
    result = detector.detect([deps])
    assert result.primary_frameworks == []


# --- QualityAnalyzer ---------------------------------------------------------


def test_quality_scores_ordered():
    analyzer = QualityAnalyzer()
    good = analyzer.analyze(
        RepositoryMetadata(
            full_name="owner/good",
            stars=60,
            forks=30,
            commit_count=200,
            has_readme=True,
            readme_chars=2000,
            readme_sections=6,
            readme_mentions_setup=True,
            has_tests=True,
            test_file_count=10,
            has_test_config=True,
            has_ci_github_actions=True,
            has_ci_other=True,
            has_docs_dir=True,
            has_src_layout=True,
            has_root_config=True,
            tree_file_count=40,
        )
    )
    poor = analyzer.analyze(RepositoryMetadata(full_name="owner/repo"))
    assert good.overall_score > poor.overall_score
    assert 0.0 <= poor.overall_score <= 100.0


def test_quality_ci_score_increases_with_ci():
    analyzer = QualityAnalyzer()
    none = analyzer.analyze(RepositoryMetadata(full_name="owner/repo")).ci_score
    gh = analyzer.analyze(
        RepositoryMetadata(full_name="owner/repo", has_ci_github_actions=True)
    ).ci_score
    both = analyzer.analyze(
        RepositoryMetadata(
            full_name="owner/repo",
            has_ci_github_actions=True,
            has_ci_other=True,
        )
    ).ci_score
    assert none < gh < both


def test_quality_no_readme_scores_zero():
    analyzer = QualityAnalyzer()
    result = analyzer.analyze(RepositoryMetadata(full_name="owner/repo"))
    assert result.readme_score == 0.0


# --- GitHubAnalyzer aggregation (static helpers) ------------------------------


def test_aggregate_technologies_groups_unique_repositories():
    dep = make_dependency(name="FastAPI")
    detection_a = FrameworkDetectionResult(
        ecosystem="python", frameworks=[dep], libraries=[]
    )
    detection_b = FrameworkDetectionResult(
        ecosystem="python", frameworks=[dep], libraries=[]
    )
    analyses = [
        make_analysis("alpha", "Python", detection=detection_a),
        make_analysis("beta", "Python", detection=detection_b),
    ]
    aggregated = GitHubAnalyzer._aggregate_technologies(analyses, "framework")
    assert len(aggregated) == 1
    assert aggregated[0].name == "FastAPI"
    assert aggregated[0].repository_count == 2


def test_overall_quality_score_is_star_weighted():
    low = make_analysis("low", "Python", stars=0, quality=make_quality(score=20.0))
    high = make_analysis("high", "Python", stars=10, quality=make_quality(score=90.0))
    score = GitHubAnalyzer._overall_quality_score([low, high])
    assert score > 20.0  # the high-star repo dominates


def test_compute_confidence_high_for_substantial_profile():
    analyses = [make_analysis(f"repo{i}", "Python") for i in range(5)]
    level, _ = GitHubAnalyzer._compute_confidence(analyses)
    assert level == "High"


def test_compute_confidence_low_for_sparse_profile():
    analyses = [make_analysis("only", "Python")]
    level, _ = GitHubAnalyzer._compute_confidence(analyses)
    assert level in {"Low", "Medium"}