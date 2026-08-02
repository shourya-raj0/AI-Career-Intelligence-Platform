"""LangGraph pipeline orchestration.

Exposes the compiled pipeline, the graph factory, the runner, and the shared
state contract. Importing this package compiles the default pipeline.
"""

from app.graph.graph import (
    build_pipeline_graph,
    compile_pipeline,
    pipeline_app,
    run_pipeline,
)
from app.graph.state import MAX_ANALYSIS_ATTEMPTS, PipelineError, PipelineState

__all__ = [
    "MAX_ANALYSIS_ATTEMPTS",
    "PipelineError",
    "PipelineState",
    "build_pipeline_graph",
    "compile_pipeline",
    "pipeline_app",
    "run_pipeline",
]
