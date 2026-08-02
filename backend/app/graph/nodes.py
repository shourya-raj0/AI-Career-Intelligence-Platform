"""Graph nodes: thin adapters that call services.

A node receives the current :class:`PipelineState` and returns the state
updates for the next hop. Nodes contain **no business logic** — they delegate
to services, translate service exceptions into :class:`PipelineError`, and
decide only which fields to record. Services are injected through factories
so the graph can be tested without touching the network.
"""

from __future__ import annotations

from typing import Callable

from app.graph.state import PipelineError, PipelineState
from app.services.developer_profile.builder import DeveloperProfileBuilder
from app.services.github.analyzer import (
    GitHubAnalysisError,
    GitHubAnalyzer,
    GitHubRateLimitError,
    GitHubUserNotFoundError,
    build_github_client,
)

NodeFn = Callable[[PipelineState], dict]


def make_analyze_github_node(analyzer: GitHubAnalyzer | None = None) -> NodeFn:
    """Build the GitHub analysis node, optionally with an injected analyzer."""

    def analyze_github(state: PipelineState) -> dict:
        username = state.get("github_username")
        if not username:
            return {
                "errors": [
                    PipelineError(node="analyze_github", message="Missing GitHub username.")
                ]
            }
        instance = analyzer if analyzer is not None else GitHubAnalyzer(github=build_github_client())
        try:
            report = instance.analyze_username(username)
        except GitHubRateLimitError as exc:
            return {
                "errors": [
                    PipelineError(node="analyze_github", message=str(exc), retryable=True)
                ],
                "retries": state.get("retries", 0) + 1,
            }
        except (GitHubUserNotFoundError, GitHubAnalysisError) as exc:
            return {
                "errors": [
                    PipelineError(node="analyze_github", message=str(exc), retryable=False)
                ]
            }
        return {"github_report": report, "errors": [], "retries": 0}

    return analyze_github


def make_build_profile_node(builder: DeveloperProfileBuilder | None = None) -> NodeFn:
    """Build the developer profile node, optionally with an injected builder."""

    def build_profile(state: PipelineState) -> dict:
        report = state.get("github_report")
        if report is None:
            return {
                "errors": [
                    PipelineError(node="build_profile", message="No GitHub report available.")
                ]
            }
        instance = builder if builder is not None else DeveloperProfileBuilder()
        profile = instance.build(report)
        return {"developer_profile": profile, "errors": []}

    return build_profile


def make_nodes(
    analyzer: GitHubAnalyzer | None = None,
    profile_builder: DeveloperProfileBuilder | None = None,
) -> dict[str, NodeFn]:
    """Build every node in the pipeline keyed by node name."""
    return {
        "analyze_github": make_analyze_github_node(analyzer),
        "build_profile": make_build_profile_node(profile_builder),
    }
