"""Security guardrails, input sanitization, injection detection, and budget enforcement (Section 9)."""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from veridata.schemas import ColumnSchemaEntry

# Prompt injection patterns
_INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|prior)\s+(instructions|directives|prompts)",
    r"you\s+are\s+now\s+(an?\s+)?(unrestricted|unlocked|a\s+helpful\s+uncensored|dan)",
    r"system\s*:\s*you\s+are",
    r"\}\}\s*system\s*:",
    r"<\s*script\b",
    r"<\s*/?\s*system\b",
    r"disregard\s+(the\s+|all\s+|prior\s+)?(above|instructions|directives)",
    r"bypass\s+safety",
    r"pretend\s+you\s+are",
    r"reveal\s+your\s+(system\s+prompt|internal\s+guidelines)",
    r"print\s+(your\s+)?(system\s+prompt|instructions|secret)",
    r"drop\s+table\b",
]

# Requests outside analytical scope
_OUT_OF_SCOPE_PATTERNS = [
    r"\b(write|generate|execute|run)\s+(a\s+)?(python|bash|code|script|sql)\b",
    r"\b(delete|drop|remove)\s+(the\s+)?(file|database|table|column)\b",
    r"\b(train|fit)\s+(a\s+)?(neural|deep|xgboost|random\s+forest|classifier|regression\s+model|model|network|llm)\b",
    r"\bpredict\b",
    r"\bwhy\s+does\b.*\bcause\b",
    r"\bcause[s]?\b",
]


def sanitize_input(text: str, max_chars: int = 1000) -> str:
    """Sanitize user input: limit length, strip control characters, normalize Unicode."""
    if not text:
        return ""
    # Normalize unicode to NFKC
    text = unicodedata.normalize("NFKC", text)
    # Strip non-printable / control characters except newlines/tabs
    text = "".join(ch for ch in text if ch in "\n\r\t" or not unicodedata.category(ch).startswith("C"))
    # Truncate
    text = text[:max_chars].strip()
    return text


def detect_injection(text: str) -> bool:
    """Detect common prompt-injection attempts in user text."""
    lower = text.lower()
    for pat in _INJECTION_PATTERNS:
        if re.search(pat, lower):
            return True
    return False


def is_out_of_scope(text: str) -> bool:
    """Check if the user request asks for code generation, prediction, or causal claims."""
    lower = text.lower()
    for pat in _OUT_OF_SCOPE_PATTERNS:
        if re.search(pat, lower):
            return True
    return False


def alias_columns(schema: dict[str, ColumnSchemaEntry | dict[str, Any]]) -> tuple[dict[str, str], dict[str, str]]:
    """Map real column names to short aliases c01..cNN to prevent injection through column names."""
    col_to_alias: dict[str, str] = {}
    alias_to_col: dict[str, str] = {}
    for idx, col in enumerate(sorted(schema.keys()), 1):
        alias = f"c{idx:02d}"
        col_to_alias[col] = alias
        alias_to_col[alias] = col
    return col_to_alias, alias_to_col


def sanitize_output(text: str) -> str:
    """Clean model outputs by stripping URLs and raw markdown code blocks."""
    # Strip URLs
    text = re.sub(r"https?://\S+", "[link removed]", text)
    # Strip markdown code blocks ```python ... ```
    text = re.sub(r"```[a-zA-Z]*\n?[\s\S]*?```", "[code block removed]", text)
    return text


class TurnBudget:
    """Tracks token and tool call usage within a session."""

    def __init__(self, max_tool_calls_per_turn: int = 4, max_tokens: int = 100_000) -> None:
        self.max_tool_calls_per_turn = max_tool_calls_per_turn
        self.max_tokens = max_tokens
        self.tool_calls_made = 0
        self.tokens_used = 0

    def can_call_tool(self) -> bool:
        return self.tool_calls_made < self.max_tool_calls_per_turn

    def record_tool_call(self) -> None:
        self.tool_calls_made += 1

    def record_tokens(self, tokens: int) -> None:
        self.tokens_used += tokens
