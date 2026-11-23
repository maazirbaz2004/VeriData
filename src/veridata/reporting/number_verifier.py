"""Regex-based token extraction and strict number verifier against FactRegistry."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Any

from veridata.reporting.facts import FactRegistry


@dataclass
class NumberToken:
    raw: str
    numeric_value: float | None
    is_percent: bool
    is_inequality: bool
    start: int
    end: int


@dataclass
class VerificationViolation:
    token: str
    span: tuple[int, int]
    reason: str  # "not_in_registry" | "precision_mismatch" | "derived_number"


@dataclass
class VerificationResult:
    ok: bool
    violations: list[VerificationViolation]
    extracted: list[str]


# Words representing numbers
_NUMBER_WORDS = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12, "dozen": 12, "hundred": 100,
}

_NUMERIC_PATTERN = re.compile(
    r"""
    (?P<ineq>[<>≤≥=]\s*)?
    (?P<sign>[-+−])?
    (?P<num>\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?|\.\d+)
    (?P<exp>[eE][-+]?\d+)?
    (?P<pct>%)?
    """,
    re.VERBOSE,
)


def extract_numbers(text: str, string_whitelist: set[str] | None = None) -> list[NumberToken]:
    """Extract numeric tokens from text while ignoring numbers in identifiers or whitelist."""
    tokens: list[NumberToken] = []
    whitelist = string_whitelist or set()

    for m in _NUMERIC_PATTERN.finditer(text):
        raw = m.group(0).strip()
        num_str = m.group("num").replace(",", "")
        if not num_str or num_str == ".":
            continue

        start, end = m.start(), m.end()

        # Check if preceded or followed by identifier characters (e.g., col_1, v2, c01)
        prev_char = text[start - 1] if start > 0 else " "
        next_char = text[end] if end < len(text) else " "
        if prev_char.isalnum() or prev_char == "_" or next_char.isalnum() or next_char == "_":
            # Part of a larger identifier
            continue

        # Check markdown list prefix at start of line (e.g. "1. ")
        if raw.isdigit() and next_char == "." and (end + 1 < len(text) and text[end + 1].isspace()):
            line_start = text.rfind("\n", 0, start)
            prefix = text[line_start + 1 : start].strip()
            if not prefix:  # it is at start of line
                continue

        # Check if the surrounding word is in whitelist
        word_match = re.search(r"\b\w+\b", text[max(0, start - 10) : min(len(text), end + 10)])
        if word_match and word_match.group(0).lower() in whitelist:
            continue

        try:
            val = float(num_str)
            if m.group("sign") in ("-", "−"):
                val = -val
            if m.group("exp"):
                val = val * (10 ** float(m.group("exp")[1:]))
            is_pct = bool(m.group("pct"))
            is_ineq = bool(m.group("ineq"))
            tokens.append(
                NumberToken(
                    raw=raw,
                    numeric_value=val,
                    is_percent=is_pct,
                    is_inequality=is_ineq,
                    start=start,
                    end=end,
                )
            )
        except ValueError:
            continue

    return tokens


def verify_text(
    text: str,
    registry: FactRegistry,
    finding_ids: list[str] | None = None,
    *,
    whitelist: list[str] | None = None,
) -> VerificationResult:
    """Check that every number in text matches a registered fact within precision tolerance."""
    allowed = registry.allowed_numbers(finding_ids)
    str_tokens = registry.string_tokens()
    if whitelist:
        str_tokens.update(w.lower() for w in whitelist)

    # Standard benign whitelisted structural tokens (e.g. 95% confidence interval)
    allowed_displays = {an.display.replace(",", "").lower() for an in allowed}
    allowed_displays.update({"95%", "95", "5%", "0.05", "1", "2", "3", "4", "5"})

    tokens = extract_numbers(text, string_whitelist=str_tokens)
    violations: list[VerificationViolation] = []
    extracted: list[str] = [t.raw for t in tokens]

    for tok in tokens:
        raw_norm = tok.raw.replace(",", "").lower()
        if raw_norm in allowed_displays:
            continue

        val = tok.numeric_value
        matched = False
        if val is not None:
            # Check equality or tolerance
            for an in allowed:
                an_val = float(an.value)
                # Check percentage equivalence
                if tok.is_percent and not str(an.display).endswith("%"):
                    # user text has 12.3%, fact is 0.123
                    if abs(val / 100.0 - an_val) <= an.tolerance:
                        matched = True
                        break
                elif not tok.is_percent and str(an.display).endswith("%"):
                    # user text has 12.3, fact is 12.3%
                    if abs(val - (an_val * 100 if an_val <= 1.0 else an_val)) <= an.tolerance:
                        matched = True
                        break
                elif abs(val - an_val) <= an.tolerance:
                    matched = True
                    break

        # Check special case for inequality (e.g., <0.001)
        if not matched and tok.is_inequality and ("<0.001" in raw_norm or "< 0.001" in raw_norm):
            for an in allowed:
                if str(an.display) == "<0.001" or (isinstance(an.value, float) and an.value < 0.001):
                    matched = True
                    break

        if not matched:
            violations.append(
                VerificationViolation(
                    token=tok.raw,
                    span=(tok.start, tok.end),
                    reason="not_in_registry",
                )
            )

    return VerificationResult(
        ok=len(violations) == 0,
        violations=violations,
        extracted=extracted,
    )
