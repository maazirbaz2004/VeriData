"""LangGraph StateGraph for batch automated profiling, cleaning, testing, validation, and reporting."""

from __future__ import annotations

import logging
from typing import Any, Literal

from langgraph.graph import END, START, StateGraph

from veridata.agent.nodes.batch import (
    clean_node,
    handle_error_node,
    hypothesize_node,
    ingest_profile_node,
    report_node,
    test_node,
    validate_node,
)
from veridata.agent.state import BatchState

logger = logging.getLogger("veridata.agent.graph_batch")


def route_after_ingest(state: BatchState) -> Literal["clean", "handle_error"]:
    if state.get("status") == "failed" or state.get("errors"):
        return "handle_error"
    return "clean"


def route_after_hypothesize(state: BatchState) -> Literal["test", "report", "handle_error"]:
    if state.get("errors"):
        return "handle_error"
    hyp_set = state.get("hypothesis_set", {})
    hypotheses = hyp_set.get("hypotheses", [])
    if not hypotheses:
        # Nothing testable, skip directly to report
        return "report"
    return "test"


def route_after_test(state: BatchState) -> Literal["validate", "handle_error"]:
    if state.get("status") == "failed":
        return "handle_error"
    return "validate"


def build_batch_graph(checkpointer: Any = None) -> Any:
    """Build and compile the batch analysis StateGraph workflow."""
    workflow = StateGraph(BatchState)

    # Register nodes
    workflow.add_node("ingest_profile", ingest_profile_node)
    workflow.add_node("clean", clean_node)
    workflow.add_node("hypothesize", hypothesize_node)
    workflow.add_node("test", test_node)
    workflow.add_node("validate", validate_node)
    workflow.add_node("report", report_node)
    workflow.add_node("handle_error", handle_error_node)

    # Add edges
    workflow.add_edge(START, "ingest_profile")
    workflow.add_conditional_edges("ingest_profile", route_after_ingest)
    workflow.add_edge("clean", "hypothesize")
    workflow.add_conditional_edges("hypothesize", route_after_hypothesize)
    workflow.add_conditional_edges("test", route_after_test)
    workflow.add_edge("validate", "report")
    workflow.add_edge("report", END)
    workflow.add_edge("handle_error", END)

    return workflow.compile(checkpointer=checkpointer)
