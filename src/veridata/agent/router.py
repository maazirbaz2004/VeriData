"""Intent classification, rule fallback, argument extraction, and schema validation (Phase 6 Section 6)."""

from __future__ import annotations

import difflib
import json
import logging
import re
from typing import Any, Literal

from pydantic import BaseModel, Field

from veridata.agent.guardrails import alias_columns, is_out_of_scope
from veridata.agent.llm import LLMClient
from veridata.agent.memory import FocusState, resolve_coreference
from veridata.agent.state import ChatState
from veridata.errors import LLMUnavailable
from veridata.schemas import ColumnSchemaEntry

logger = logging.getLogger("veridata.agent.router")

IntentType = Literal[
    "describe_dataset",
    "describe_column",
    "compare_groups",
    "test_correlation",
    "test_association",
    "test_relationship",
    "show_distribution",
    "list_findings",
    "explain_finding",
    "explain_rejection",
    "get_ledger_status",
    "suggest_next",
    "run_batch_analysis",
    "followup_choice",
    "clarification_answer",
    "smalltalk",
    "out_of_scope",
]


class RouterDecision(BaseModel):
    """Structured decision returned by the intent router."""

    intent: IntentType
    confidence: float = 1.0
    reasoning_brief: str = Field(default="", max_length=200)


class ArgExtraction(BaseModel):
    """Extracted arguments for a selected tool."""

    column_a: str | None = None
    column_b: str | None = None
    numeric_column: str | None = None
    group_column: str | None = None
    column: str | None = None
    finding_ref: str | None = None
    top_k: int | None = None


def find_column_mentions(text: str, columns: list[str]) -> list[str]:
    """Identify dataset columns referenced in text, ordered by occurrence."""
    text_lower = text.lower()
    found: list[tuple[int, str]] = []

    # Sort columns by length descending so longer column names match first (e.g. TotalCharges before charges)
    for col in sorted(columns, key=len, reverse=True):
        pattern = rf"\b{re.escape(col.lower())}\b"
        match = re.search(pattern, text_lower)
        if match:
            found.append((match.start(), col))

    found.sort(key=lambda x: x[0])
    return [col for _, col in found]


def route_intent_rules(
    text: str,
    columns: list[str],
    focus: FocusState | dict[str, Any] | None = None,
    pending_clarification: dict[str, Any] | None = None,
) -> RouterDecision:
    """Deterministic, rule-based fallback router matching regex and keywords."""
    clean = text.strip().lower()

    # 1. Pending clarification
    if pending_clarification is not None:
        return RouterDecision(
            intent="clarification_answer",
            confidence=0.95,
            reasoning_brief="Pending clarification exists.",
        )

    # 2. Out of scope and injection
    if is_out_of_scope(clean) or any(k in clean for k in ("ignore previous instructions", "system prompt", "system:")):
        return RouterDecision(
            intent="out_of_scope",
            confidence=1.0,
            reasoning_brief="Request involves forbidden capabilities (code/prediction/causality) or injection.",
        )

    # 3. Smalltalk
    if clean in ("hi", "hello", "hey", "help", "who are you", "what can you do") or clean.startswith("hello!"):
        return RouterDecision(
            intent="smalltalk",
            confidence=0.9,
            reasoning_brief="Greeting or help request.",
        )

    # 4. Dataset overview / description
    if any(k in clean for k in ("describe dataset", "dataset summary", "overview", "data shape", "shape and missingness", "kind of data", "rows and columns", "profile dataset")):
        return RouterDecision(
            intent="describe_dataset",
            confidence=0.9,
            reasoning_brief="User asked to describe the dataset.",
        )

    # 5. Ledger status / family size
    if any(k in clean for k in ("ledger status", "how many tests", "family size", "testing family", "multiple testing", "multiple-testing", "fdr alpha")):
        return RouterDecision(
            intent="get_ledger_status",
            confidence=0.9,
            reasoning_brief="User asked for ledger status.",
        )

    # 6. Next suggestions
    if any(k in clean for k in ("suggest next", "what next", "what should i test", "what should we test", "recommend", "next steps")):
        return RouterDecision(
            intent="suggest_next",
            confidence=0.9,
            reasoning_brief="User asked for suggestions.",
        )

    # 7. List findings
    if any(k in clean for k in ("list findings", "show findings", "what are the findings", "validated findings", "what did we find", "summary of findings", "survived benjamini", "findings table", "findings for")):
        return RouterDecision(
            intent="list_findings",
            confidence=0.9,
            reasoning_brief="User requested findings list.",
        )

    # 8. Rejection explanation
    if any(k in clean for k in ("why was", "why were", "explain rejection", "why rejected")):
        return RouterDecision(
            intent="explain_rejection",
            confidence=0.85,
            reasoning_brief="User asked about rejected findings.",
        )

    # 9. Explain finding
    if any(k in clean for k in ("explain finding", "explain the finding", "tell me more about finding", "explain the first", "explain the second", "tell me more about the")):
        return RouterDecision(
            intent="explain_finding",
            confidence=0.85,
            reasoning_brief="User asked to explain a finding.",
        )

    # 10. Distribution
    if any(k in clean for k in ("distribution of", "show distribution", "histogram of", "plot distribution", "show its distribution", "distribution for")):
        return RouterDecision(
            intent="show_distribution",
            confidence=0.85,
            reasoning_brief="User requested distribution plot.",
        )

    # 11. Statistical questions mentioning columns
    cols_found = find_column_mentions(text, columns)
    if not cols_found and focus is not None:
        _, resolved_cols = resolve_coreference(text, focus, columns)
        cols_found = resolved_cols

    if any(k in clean for k in ("association", "associated")):
        return RouterDecision(
            intent="test_association",
            confidence=0.85,
            reasoning_brief="Association keyword detected.",
        )

    if any(k in clean for k in ("correlat", "relation between", "differ across", "compare", "higher", "lower", "more than", "less than")):
        if any(k in clean for k in ("compare", "differ across", "differ by", "by ", "higher", "lower", "more than", "less than")):
            return RouterDecision(
                intent="compare_groups",
                confidence=0.8,
                reasoning_brief="Comparison phrasing detected.",
            )
        if "correlat" in clean:
            return RouterDecision(
                intent="test_correlation",
                confidence=0.8,
                reasoning_brief="Correlation keyword detected.",
            )
        return RouterDecision(
            intent="test_relationship",
            confidence=0.75,
            reasoning_brief="General relationship question.",
        )

    if len(cols_found) == 1:
        return RouterDecision(
            intent="describe_column",
            confidence=0.7,
            reasoning_brief="Single column mentioned.",
        )
    elif len(cols_found) >= 2:
        return RouterDecision(
            intent="test_relationship",
            confidence=0.75,
            reasoning_brief="Two columns mentioned.",
        )

    return RouterDecision(
        intent="smalltalk",
        confidence=0.5,
        reasoning_brief="Unrecognized intent; defaulting to help/smalltalk.",
    )


def route_intent(
    text: str,
    columns: list[str],
    llm: LLMClient | None = None,
    focus: FocusState | dict[str, Any] | None = None,
    pending_clarification: dict[str, Any] | None = None,
) -> RouterDecision:
    """Route user message to IntentType via LLM or rule-based fallback."""
    # Always check guardrails first
    if is_out_of_scope(text):
        return RouterDecision(intent="out_of_scope", confidence=1.0, reasoning_brief="Out of scope request.")

    if pending_clarification is not None:
        return RouterDecision(intent="clarification_answer", confidence=1.0, reasoning_brief="Clarification response.")

    rule_decision = route_intent_rules(text, columns, focus=focus)
    if llm is None or rule_decision.confidence >= 0.85:
        return rule_decision

    # LLM classification
    system_prompt = (
        "You are an intent classification router for VeriData. "
        "Classify the user message into one of the allowed intents:\n"
        "describe_dataset, describe_column, compare_groups, test_correlation, "
        "test_association, test_relationship, show_distribution, list_findings, "
        "explain_finding, explain_rejection, get_ledger_status, suggest_next, "
        "run_batch_analysis, followup_choice, clarification_answer, smalltalk, out_of_scope."
    )
    user_prompt = f"User message: {text}\nAvailable columns: {columns[:20]}"
    try:
        decision = llm.structured(
            system=system_prompt,
            user=user_prompt,
            schema=RouterDecision,
            temperature=0.0,
        )
        return decision
    except (LLMUnavailable, Exception) as exc:
        logger.debug("LLM router failed (%s); using rule fallback.", exc)
        return rule_decision


def extract_arguments(
    text: str,
    intent: str,
    columns: list[str],
    focus: FocusState | dict[str, Any] | None = None,
    schema: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Extract and bind concrete tool arguments from text and conversation focus."""
    args: dict[str, Any] = {}

    # Handle pronouns/coreference
    f = focus if isinstance(focus, FocusState) else (FocusState(**focus) if focus else None)
    resolved_text, coref_cols = resolve_coreference(text, f or FocusState(), columns)

    cols_found = find_column_mentions(resolved_text, columns)
    for c in coref_cols:
        if c not in cols_found:
            cols_found.append(c)

    if intent == "describe_column" or intent == "show_distribution":
        if cols_found:
            args["column"] = cols_found[0]
        elif f and f.columns:
            args["column"] = f.columns[0]

    elif intent in ("compare_groups", "test_correlation", "test_association", "test_relationship"):
        if len(cols_found) >= 2:
            args["column_a"] = cols_found[0]
            args["column_b"] = cols_found[1]
            args["numeric_column"] = cols_found[0]
            args["group_column"] = cols_found[1]
        elif len(cols_found) == 1 and f and f.columns:
            args["column_a"] = f.columns[0]
            args["column_b"] = cols_found[0]
            args["numeric_column"] = f.columns[0]
            args["group_column"] = cols_found[0]

    elif intent in ("explain_finding", "explain_rejection"):
        # Check for finding reference numbers ("first", "second", "1", "2")
        ord_match = re.search(r"\b(first|second|third|fourth|1|2|3|4)\b", text.lower())
        ord_map = {"first": "1", "second": "2", "third": "3", "fourth": "4"}
        if ord_match:
            raw_ord = ord_match.group(1)
            args["finding_ref"] = ord_map.get(raw_ord, raw_ord)
        elif cols_found:
            args["finding_ref"] = cols_found[0]
        elif f and f.finding_id:
            args["finding_ref"] = f.finding_id
        else:
            args["finding_ref"] = "last"

    elif intent == "list_findings":
        args["top_k"] = 10

    return args


def validate_arguments(
    intent: str,
    args: dict[str, Any],
    columns: list[str],
) -> tuple[bool, dict[str, Any] | None, dict[str, Any] | None]:
    """Validate extracted arguments against dataset schema; detects ambiguity or missing required args."""
    if intent in ("describe_dataset", "get_ledger_status", "suggest_next", "smalltalk", "out_of_scope", "list_findings"):
        return True, args, None

    if intent in ("describe_column", "show_distribution"):
        col = args.get("column")
        if not col or col not in columns:
            return False, None, {
                "question": f"Which column would you like to inspect? Available options: {columns[:5]}",
                "candidates": columns[:5],
                "resume_intent": intent,
                "partial_args": args,
            }

    if intent in ("compare_groups", "test_correlation", "test_association", "test_relationship"):
        col_a = args.get("column_a") or args.get("numeric_column")
        col_b = args.get("column_b") or args.get("group_column")

        if not col_a or not col_b:
            return False, None, {
                "question": "Which two variables would you like to test? Please specify the columns.",
                "candidates": columns[:6],
                "resume_intent": intent,
                "partial_args": args,
            }

        if col_a not in columns or col_b not in columns:
            missing = [c for c in (col_a, col_b) if c not in columns]
            return False, None, {
                "question": f"Could not find column(s) {missing}. Did you mean one of these?",
                "candidates": difflib.get_close_matches(missing[0], columns, n=3) or columns[:4],
                "resume_intent": intent,
                "partial_args": args,
            }

    return True, args, None
