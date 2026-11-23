"""Context memory, coreference/pronoun resolution, and conversation history summarization (Section 8)."""

from __future__ import annotations

import re
from typing import Any

from veridata.agent.state import FocusState
from veridata.contracts.findings import Finding


def update_focus(
    current_focus: FocusState | dict[str, Any],
    finding: Finding | None = None,
    column: str | None = None,
    chart_path: str | None = None,
) -> FocusState:
    """Update active focus state following a successful tool execution."""
    if isinstance(current_focus, dict):
        focus = FocusState(**current_focus)
    else:
        focus = current_focus

    if finding is not None:
        focus.columns = [finding.hypothesis.column_a, finding.hypothesis.column_b]
        focus.hypothesis_id = finding.hypothesis.id
        focus.finding_id = finding.hypothesis.id
        focus.relationship = finding.hypothesis.relationship.value
    elif column is not None:
        if column not in focus.columns:
            focus.columns = [column] + focus.columns[:1]

    if chart_path is not None:
        focus.last_chart_path = chart_path

    return focus


def resolve_coreference(
    text: str,
    focus: FocusState | dict[str, Any],
    all_columns: list[str],
) -> tuple[str, list[str]]:
    """Resolve pronouns and short follow-up phrases ('it', 'that variable', 'now by region')."""
    f = focus if isinstance(focus, FocusState) else FocusState(**focus)
    resolved_text = text
    resolved_cols: list[str] = []

    lower = text.lower().strip()

    # Match 'it', 'this', 'that'
    if re.search(r"\b(it|this|that\s+variable|that\s+column)\b", lower):
        if f.columns:
            primary_col = f.columns[0]
            resolved_text = re.sub(
                r"\b(it|this|that\s+variable|that\s+column)\b",
                primary_col,
                resolved_text,
                flags=re.IGNORECASE,
            )
            resolved_cols.append(primary_col)

    # Match 'the other one' / 'the second variable'
    if re.search(r"\b(the\s+other\s+one|the\s+second\s+variable)\b", lower):
        if len(f.columns) >= 2:
            second_col = f.columns[1]
            resolved_text = re.sub(
                r"\b(the\s+other\s+one|the\s+second\s+variable)\b",
                second_col,
                resolved_text,
                flags=re.IGNORECASE,
            )
            resolved_cols.append(second_col)

    # Match "now by <col>" or "what about by <col>"
    by_match = re.search(r"\b(?:now\s+by|what\s+about\s+by|and\s+by)\s+([a-zA-Z0-9_]+)\b", lower)
    if by_match:
        target_col = by_match.group(1)
        for c in all_columns:
            if c.lower() == target_col.lower():
                resolved_cols.append(c)
                if f.columns:
                    resolved_cols.append(f.columns[0])
                break

    return resolved_text, resolved_cols


def summarize_history(messages: list[dict[str, Any]], max_turns_kept: int = 10) -> list[dict[str, Any]]:
    """Trim conversation history and replace older turns with a reference summary without invented digits."""
    if len(messages) <= max_turns_kept:
        return messages

    older = messages[:-max_turns_kept]
    kept = messages[-max_turns_kept:]

    # Build reference-only summary without inventing statistics
    tools_used = [m.get("tool") for m in older if m.get("tool")]
    intents = [m.get("intent") for m in older if m.get("intent")]

    summary_note = (
        f"[Summary of previous {len(older)} turns: user explored intents {set(intents)} "
        f"and executed tools {set(tools_used)}.]"
    )

    summary_msg = {
        "role": "system",
        "content": summary_note,
        "is_summary": True,
    }
    return [summary_msg] + kept
