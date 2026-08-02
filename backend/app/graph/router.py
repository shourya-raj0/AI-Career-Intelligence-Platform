"""Conditional routing decisions for the pipeline graph.

Router functions decide which node executes next based on the current
:class:`PipelineState`. They combine the pure predicates from
:mod:`app.graph.conditions` and return a node name; the edge mapping lives in
:mod:`app.graph.graph`.
"""

from __future__ import annotations

from typing import Literal

from app.graph.conditions import has_fatal_error, has_retryable_error, retries_remaining
from app.graph.state import MAX_ANALYSIS_ATTEMPTS, PipelineState

AnalysisRoute = Literal["retry", "build_profile", "fail"]


def route_after_analysis(state: PipelineState) -> AnalysisRoute:
    """Choose the next hop after the GitHub analysis node."""
    if has_fatal_error(state):
        return "fail"
    if has_retryable_error(state):
        return "retry" if retries_remaining(state, MAX_ANALYSIS_ATTEMPTS) else "fail"
    return "build_profile"
