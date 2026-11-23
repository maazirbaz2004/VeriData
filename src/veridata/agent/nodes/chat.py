"""Chat graph node functions for multi-turn conversational interface (Phase 6 Section 6)."""

from __future__ import annotations

import difflib
import logging
from typing import Any

from veridata.agent.datastore import GLOBAL_DATASTORE
from veridata.agent.followups import generate_followups
from veridata.agent.guardrails import detect_injection, is_out_of_scope, sanitize_input, sanitize_output
from veridata.agent.memory import FocusState, update_focus
from veridata.agent.router import (
    extract_arguments,
    route_intent,
    validate_arguments,
)
from veridata.agent.state import ChatState
from veridata.agent.tools import ToolRegistry, ToolResult
from veridata.reporting.facts import FactRegistry, build_facts
from veridata.reporting.language_lint import lint_text
from veridata.reporting.narration import explain_finding
from veridata.reporting.number_verifier import verify_text
from veridata.validation.ledger import SessionLedger

logger = logging.getLogger("veridata.agent.nodes.chat")


def guard_input_node(state: ChatState) -> dict[str, Any]:
    """Sanitize user input and enforce safety guardrails."""
    raw_input = state.get("user_input", "")
    sanitized = sanitize_input(raw_input)

    if detect_injection(sanitized):
        return {
            "user_input": sanitized,
            "intent": "out_of_scope",
            "answer": {
                "text": "I am an objective data science assistant and cannot process system-override instructions.",
                "charts": [],
                "verified": True,
                "source": "guardrail",
            },
        }

    if is_out_of_scope(sanitized):
        return {
            "user_input": sanitized,
            "intent": "out_of_scope",
            "answer": {
                "text": "I can explore distributions, compare groups, test correlations, and validate statistical findings in your data. I do not write arbitrary code or make causal claims.",
                "charts": [],
                "verified": True,
                "source": "guardrail",
            },
        }

    return {"user_input": sanitized}


def resolve_clarification_node(state: ChatState) -> dict[str, Any]:
    """Resolve a pending clarification using the user's answer."""
    pending = state.get("pending_clarification")
    if not pending:
        return {}

    user_text = state.get("user_input", "").strip()
    candidates: list[str] = pending.get("candidates", [])
    resume_intent = pending.get("resume_intent", "describe_column")
    partial_args = dict(pending.get("partial_args", {}))

    matched_candidate = None
    for cand in candidates:
        if cand.lower() in user_text.lower():
            matched_candidate = cand
            break

    if not matched_candidate:
        close = difflib.get_close_matches(user_text, candidates, n=1)
        if close:
            matched_candidate = close[0]

    if matched_candidate:
        if "column" in partial_args or resume_intent in ("describe_column", "show_distribution"):
            partial_args["column"] = matched_candidate
        elif not partial_args.get("column_a"):
            partial_args["column_a"] = matched_candidate
        else:
            partial_args["column_b"] = matched_candidate

        return {
            "intent": resume_intent,
            "parsed_args": partial_args,
            "pending_clarification": None,
        }

    return {}


def route_intent_node(state: ChatState) -> dict[str, Any]:
    """Classify the user message into a registered intent."""
    if state.get("intent") is not None:
        return {}

    cols = list(state.get("schema", {}).keys())
    decision = route_intent(
        text=state.get("user_input", ""),
        columns=cols,
        focus=state.get("focus"),
        pending_clarification=state.get("pending_clarification"),
    )
    return {"intent": decision.intent}


def extract_args_node(state: ChatState) -> dict[str, Any]:
    """Extract tool arguments from the user message and focus."""
    if state.get("parsed_args") is not None:
        return {}

    cols = list(state.get("schema", {}).keys())
    args = extract_arguments(
        text=state.get("user_input", ""),
        intent=state.get("intent", "smalltalk"),
        columns=cols,
        focus=state.get("focus"),
        schema=state.get("schema"),
    )
    return {"parsed_args": args}


def validate_args_node(state: ChatState) -> dict[str, Any]:
    """Validate extracted arguments against the schema."""
    cols = list(state.get("schema", {}).keys())
    intent = state.get("intent", "smalltalk")
    args = state.get("parsed_args", {})

    valid, clean_args, pending = validate_arguments(intent, args, cols)
    if not valid:
        return {
            "pending_clarification": pending,
            "parsed_args": None,
        }

    return {"parsed_args": clean_args}


def ask_clarification_node(state: ChatState) -> dict[str, Any]:
    """Render a clarification request to the user."""
    pending = state.get("pending_clarification", {})
    q = pending.get("question", "Could you please clarify your question?")
    return {
        "answer": {
            "text": q,
            "charts": [],
            "verified": True,
            "source": "clarification",
        }
    }


def execute_tool_node(state: ChatState) -> dict[str, Any]:
    """Execute the selected tool via ToolRegistry."""
    intent = state.get("intent")
    args = state.get("parsed_args") or {}

    # Look up tool registry from datastore
    tool_reg: ToolRegistry = GLOBAL_DATASTORE.get_artifact(f"tools_{state.get('session_id')}")
    if tool_reg is None:
        return {
            "errors": [{"stage": "execute_tool", "error": "Tool registry not initialized."}],
            "last_tool_result": {"tool": intent, "ok": False, "error": "Tool registry not initialized."},
        }

    result: ToolResult
    try:
        if intent == "describe_dataset":
            result = tool_reg.describe_dataset()
        elif intent == "describe_column":
            result = tool_reg.describe_column(args.get("column", ""))
        elif intent == "compare_groups":
            result = tool_reg.compare_groups(
                args.get("numeric_column") or args.get("column_a", ""),
                args.get("group_column") or args.get("column_b", ""),
            )
        elif intent == "test_correlation":
            result = tool_reg.test_correlation(args.get("column_a", ""), args.get("column_b", ""))
        elif intent == "test_association":
            result = tool_reg.test_association(args.get("column_a", ""), args.get("column_b", ""))
        elif intent == "test_relationship":
            result = tool_reg.test_relationship(args.get("column_a", ""), args.get("column_b", ""))
        elif intent == "show_distribution":
            result = tool_reg.show_distribution(args.get("column", ""))
        elif intent == "list_findings":
            result = tool_reg.list_findings(args.get("top_k", 10))
        elif intent == "explain_finding":
            result = tool_reg.explain_finding(args.get("finding_ref", "last"))
        elif intent == "explain_rejection":
            result = tool_reg.explain_rejection(args.get("finding_ref", "last"))
        elif intent == "get_ledger_status":
            result = tool_reg.get_ledger_status()
        elif intent == "suggest_next":
            result = tool_reg.suggest_next()
        else:
            result = ToolResult(tool=str(intent), ok=True, meta={"message": "No tool needed for intent."})
    except Exception as exc:
        logger.exception("Tool execution error: %s", exc)
        result = ToolResult(tool=str(intent), ok=False, error=str(exc))

    return {
        "last_tool_result": result.model_dump(),
        "tool_calls_this_turn": state.get("tool_calls_this_turn", 0) + 1,
    }


def update_ledger_node(state: ChatState) -> dict[str, Any]:
    """Check for multiple-testing diffs caused by this turn."""
    tool_res_dict = state.get("last_tool_result", {})
    diffs = tool_res_dict.get("ledger_diff", [])
    return {"ledger_diff": diffs}


def explain_node(state: ChatState) -> dict[str, Any]:
    """Format and machine-verify the turn's final answer."""
    tool_res_dict = state.get("last_tool_result", {})
    intent = state.get("intent")

    if not tool_res_dict.get("ok", True):
        return {
            "answer": {
                "text": f"I couldn't complete that test: {tool_res_dict.get('error')}",
                "charts": [],
                "verified": True,
                "source": "error_handler",
            }
        }

    finding_dict = tool_res_dict.get("finding")
    charts = tool_res_dict.get("charts", [])

    if finding_dict is not None:
        # Rehydrate Finding
        from veridata.contracts.findings import Finding
        finding = Finding.model_validate(finding_dict)
        reg = FactRegistry()
        reg.add_many(finding.facts, finding_id=finding.hypothesis.id)

        exp = explain_finding(finding, registry=reg)
        answer_text = exp.text

        # Append diff notice if any existing finding was affected
        diffs = state.get("ledger_diff", [])
        if diffs:
            answer_text += f"\n\n*Note: Adding this test updated the multiple-testing family ({len(diffs)} finding status updated).*"

        return {
            "answer": {
                "text": sanitize_output(answer_text),
                "charts": charts,
                "facts_used": exp.used_fact_keys,
                "verified": exp.verified,
                "source": exp.source,
            }
        }

    # Non-finding answers
    meta = tool_res_dict.get("meta", {})
    if intent == "describe_dataset":
        text = meta.get("summary", "Dataset profile generated.")
    elif intent == "describe_column":
        text = f"Profiled column '{args_col}'. Distribution chart generated." if (args_col := meta.get("column")) else "Column profile generated."
    elif intent == "list_findings":
        count = meta.get("count", 0)
        text = f"Found {count} validated finding(s) in the current session."
    elif intent == "get_ledger_status":
        text = f"Session testing ledger contains {meta.get('total_tests')} tests ({meta.get('accepted_count')} validated) at FDR alpha 0.05."
    elif intent == "explain_finding":
        text = meta.get("explanation", "Finding explanation generated.")
    elif intent == "explain_rejection":
        text = meta.get("rejection_explanation", "Rejection explanation generated.")
    elif intent == "smalltalk":
        text = "Hello! I am VeriData. Ask me about your dataset columns, relationships, group comparisons, or validated findings."
    else:
        text = "I've processed your request."

    return {
        "answer": {
            "text": sanitize_output(text),
            "charts": charts,
            "facts_used": [],
            "verified": True,
            "source": "template",
        }
    }


def suggest_followups_node(state: ChatState) -> dict[str, Any]:
    """Generate next executable follow-up suggestions."""
    tool_reg: ToolRegistry = GLOBAL_DATASTORE.get_artifact(f"tools_{state.get('session_id')}")
    if tool_reg is None:
        return {"followups": []}

    last_f = tool_reg.last_findings[0] if tool_reg.last_findings else None
    followups = generate_followups(
        df=tool_reg.df,
        schema=tool_reg.schema,
        ledger=tool_reg.ledger,
        last_finding=last_f,
        max_followups=3,
    )
    return {"followups": followups}


def update_memory_node(state: ChatState) -> dict[str, Any]:
    """Update conversation history and FocusState."""
    current_focus = state.get("focus") or {}
    tool_res = state.get("last_tool_result", {})
    finding_dict = tool_res.get("finding")
    charts = tool_res.get("charts", [])
    chart_path = charts[0] if charts else None

    finding = None
    if finding_dict:
        from veridata.contracts.findings import Finding
        finding = Finding.model_validate(finding_dict)

    updated_focus = update_focus(
        current_focus,
        finding=finding,
        chart_path=chart_path,
    )

    messages = list(state.get("messages", []))
    user_input = state.get("user_input")
    answer = state.get("answer")

    if user_input:
        messages.append({"role": "user", "content": user_input})
    if answer:
        messages.append({"role": "assistant", "content": answer.get("text"), "charts": answer.get("charts")})

    return {
        "focus": updated_focus.model_dump(),
        "messages": messages,
        "tool_calls_this_turn": 0,
        "user_input": "",
        "intent": None,
        "parsed_args": None,
    }


def handle_tool_error_node(state: ChatState) -> dict[str, Any]:
    """Handle runtime tool execution errors."""
    err = state.get("last_tool_result", {}).get("error", "An error occurred during tool execution.")
    return {
        "answer": {
            "text": f"Error executing tool: {err}",
            "charts": [],
            "verified": True,
            "source": "error_handler",
        }
    }
