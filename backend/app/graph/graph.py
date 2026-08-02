"""LangGraph pipeline orchestration.

This module contains only graph wiring — nodes, edges, and conditional
routing. All business logic lives in the services layer that the nodes call.
Nodes for future stages (jobs, matching, recommendations, explanations) are
added here as their services land; the state contract already carries their
outputs.
"""

from __future__ import annotations

from typing import Any

from langgraph.graph import END, START, StateGraph

from app.graph.nodes import make_nodes
from app.graph.router import route_after_analysis
from app.graph.state import PipelineState

GRAPH_NODES: dict[str, dict[str, Any]] = {
    "analyze_github": {"retry": "analyze_github", "build_profile": "build_profile", "fail": END},
}


def build_pipeline_graph(
    analyzer: Any = None,
    profile_builder: Any = None,
) -> StateGraph:
    """Build the pipeline :class:`StateGraph`.

    ``analyzer`` and ``profile_builder`` allow injecting service instances for
    testing; when omitted, nodes construct production defaults at call time.
    """
    nodes = make_nodes(analyzer=analyzer, profile_builder=profile_builder)

    graph = StateGraph(PipelineState)
    for name, node_fn in nodes.items():
        graph.add_node(name, node_fn)

    graph.add_edge(START, "analyze_github")
    graph.add_conditional_edges(
        "analyze_github",
        route_after_analysis,
        GRAPH_NODES["analyze_github"],
    )
    graph.add_edge("build_profile", END)
    return graph


def compile_pipeline(analyzer: Any = None, profile_builder: Any = None):
    """Compile a runnable pipeline from :func:`build_pipeline_graph`."""
    return build_pipeline_graph(analyzer=analyzer, profile_builder=profile_builder).compile()


def run_pipeline(
    github_username: str,
    job_preferences: dict | None = None,
    app: Any = None,
) -> dict:
    """Run the pipeline for ``github_username`` and return the final state.

    ``app`` may be an already-compiled graph; when omitted, the module-level
    :data:`pipeline_app` is used.
    """
    pipeline = app if app is not None else pipeline_app
    initial: dict[str, Any] = {"github_username": github_username}
    if job_preferences is not None:
        initial["job_preferences"] = job_preferences
    return pipeline.invoke(initial)


pipeline_app = compile_pipeline()
