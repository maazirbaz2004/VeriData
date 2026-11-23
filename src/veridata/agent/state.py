"""Agent state definitions for LangGraph batch analysis and chat workflows (Phase 6 Section 3)."""

from __future__ import annotations

import operator
from typing import Annotated, Any, Literal
from typing_extensions import TypedDict

from pydantic import BaseModel, Field


class FocusState(BaseModel):
    """Contextual memory of the conversation's active analytical focus."""

    columns: list[str] = Field(default_factory=list)
    hypothesis_id: str | None = None
    finding_id: str | None = None
    relationship: str | None = None
    group_level: str | None = None
    last_chart_path: str | None = None


def merge_dicts(a: dict[str, Any], b: dict[str, Any]) -> dict[str, Any]:
    """Reducer that merges two dictionaries."""
    res = dict(a)
    res.update(b)
    return res


def append_list(a: list[Any], b: list[Any]) -> list[Any]:
    """Reducer that appends items to a list."""
    return list(a) + list(b)


class BatchState(TypedDict, total=False):
    """State schema for the end-to-end batch analysis LangGraph workflow."""

    run_id: str
    dataset_id: str
    dataset_name: str
    dataset_sha256: str
    config: dict[str, Any]
    profile: dict[str, Any]
    schema: dict[str, Any]
    cleaning_log: list[dict[str, Any]]
    cleaned_dataset_id: str
    hypothesis_set: dict[str, Any]
    results_path: str
    ledger_path: str
    decisions: list[dict[str, Any]]
    findings_path: str
    report_paths: dict[str, str]
    warnings: Annotated[list[str], operator.add]
    errors: Annotated[list[dict[str, Any]], operator.add]
    stage_timings: dict[str, float]
    status: Literal["pending", "running", "done", "failed"]
    progress_message: str | None


class ChatState(TypedDict, total=False):
    """State schema for multi-turn conversational question answering."""

    session_id: str
    dataset_id: str
    cleaned_dataset_id: str
    dataset_sha256: str
    dataset_name: str
    schema: dict[str, Any]
    profile_summary: dict[str, Any]
    messages: list[dict[str, Any]]
    user_input: str
    intent: str | None
    parsed_args: dict[str, Any] | None
    pending_clarification: dict[str, Any] | None
    focus: dict[str, Any]
    tool_calls_this_turn: int
    last_tool_result: dict[str, Any] | None
    ledger_path: str
    ledger_diff: list[dict[str, Any]]
    answer: dict[str, Any] | None
    followups: list[dict[str, Any]]
    budget: dict[str, Any]
    errors: Annotated[list[dict[str, Any]], operator.add]
