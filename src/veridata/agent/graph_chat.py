"""LangGraph StateGraph for multi-turn conversational interface with guardrails and validation."""

from __future__ import annotations

import logging
from typing import Any, Literal

from langgraph.graph import END, START, StateGraph

from veridata.agent.nodes.chat import (
    ask_clarification_node,
    execute_tool_node,
    explain_node,
    extract_args_node,
    guard_input_node,
    handle_tool_error_node,
    resolve_clarification_node,
    route_intent_node,
    suggest_followups_node,
    update_ledger_node,
    update_memory_node,
    validate_args_node,
)
from veridata.agent.state import ChatState

logger = logging.getLogger("veridata.agent.graph_chat")


def route_after_guard(state: ChatState) -> Literal["resolve_clarification", "route_intent", "update_memory"]:
    if state.get("intent") == "out_of_scope":
        return "update_memory"
    if state.get("pending_clarification") is not None:
        return "resolve_clarification"
    return "route_intent"


def route_after_clarification(state: ChatState) -> Literal["validate_args", "route_intent"]:
    if state.get("parsed_args") is not None:
        return "validate_args"
    return "route_intent"


def route_after_intent(state: ChatState) -> Literal["extract_args", "execute_tool"]:
    intent = state.get("intent")
    if intent in ("smalltalk", "describe_dataset", "get_ledger_status", "suggest_next"):
        return "execute_tool"
    return "extract_args"


def route_after_validate(state: ChatState) -> Literal["execute_tool", "ask_clarification"]:
    if state.get("pending_clarification") is not None:
        return "ask_clarification"
    return "execute_tool"


def route_after_execute(state: ChatState) -> Literal["update_ledger", "handle_tool_error"]:
    res = state.get("last_tool_result", {})
    if not res.get("ok", True):
        return "handle_tool_error"
    return "update_ledger"


def build_chat_graph(checkpointer: Any = None) -> Any:
    """Build and compile the multi-turn conversational StateGraph workflow."""
    workflow = StateGraph(ChatState)

    # Register nodes
    workflow.add_node("guard_input", guard_input_node)
    workflow.add_node("resolve_clarification", resolve_clarification_node)
    workflow.add_node("route_intent", route_intent_node)
    workflow.add_node("extract_args", extract_args_node)
    workflow.add_node("validate_args", validate_args_node)
    workflow.add_node("ask_clarification", ask_clarification_node)
    workflow.add_node("execute_tool", execute_tool_node)
    workflow.add_node("update_ledger", update_ledger_node)
    workflow.add_node("explain", explain_node)
    workflow.add_node("suggest_followups", suggest_followups_node)
    workflow.add_node("update_memory", update_memory_node)
    workflow.add_node("handle_tool_error", handle_tool_error_node)

    # Add edges
    workflow.add_edge(START, "guard_input")
    workflow.add_conditional_edges("guard_input", route_after_guard)
    workflow.add_conditional_edges("resolve_clarification", route_after_clarification)
    workflow.add_conditional_edges("route_intent", route_after_intent)
    workflow.add_edge("extract_args", "validate_args")
    workflow.add_conditional_edges("validate_args", route_after_validate)
    workflow.add_edge("ask_clarification", "update_memory")
    workflow.add_conditional_edges("execute_tool", route_after_execute)
    workflow.add_edge("update_ledger", "explain")
    workflow.add_edge("explain", "suggest_followups")
    workflow.add_edge("suggest_followups", "update_memory")
    workflow.add_edge("handle_tool_error", "update_memory")
    workflow.add_edge("update_memory", END)

    return workflow.compile(checkpointer=checkpointer)
