"""Pure predicates used for conditional routing.

These functions are side-effect free and inspect only the current
:class:`PipelineState`. They contain no business logic and never call a
service.
"""

from __future__ import annotations

from app.graph.state import PipelineState


def has_retryable_error(state: PipelineState) -> bool:
    """Return whether the latest errors include a transient failure."""
    return any(error.retryable for error in state.get("errors", []))


def has_fatal_error(state: PipelineState) -> bool:
    """Return whether the latest errors include a non-retryable failure."""
    return any(not error.retryable for error in state.get("errors", []))


def retries_remaining(state: PipelineState, max_attempts: int) -> bool:
    """Return whether the analysis retry budget has not been exhausted."""
    return state.get("retries", 0) < max_attempts
