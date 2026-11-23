"""Language linter enforcing association-not-causation phrasing and qualification (Phase 5 Section 7)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from veridata.contracts.findings import Finding


@dataclass
class LintResult:
    ok: bool
    violations: list[str]


_BANNED_CAUSAL_PATTERNS = [
    r"\bcauses\b",
    r"\bcaused\s+by\b",
    r"\bleads\s+to\b",
    r"\bresults\s+in\b",
    r"\bdue\s+to\b",
    r"\bbecause\s+of\b",
    r"\bdrives\b",
    r"\bimpacts\b",
    r"\bdetermines\b",
    r"\bresponsible\s+for\b",
]

_BANNED_OVERCLAIMS = [
    r"\bproves\b",
    r"\bproven\b",
    r"\bdefinitively\b",
    r"\bcertainly\b",
    r"\bundeniable\b",
    r"\bguarantee\b",
    r"\bguarantees\b",
]

_BARE_SIGNIFICANT = re.compile(
    r"(?<!statistically\s)(?<!practically\s)\bsignificant\b(?!\safter)",
    re.IGNORECASE,
)


def lint_text(text: str, finding: Finding | None = None) -> LintResult:
    """Scan text for causal verbs, bare significance overclaims, and missing qualifiers."""
    violations: list[str] = []
    text_lower = text.lower()

    # Strip explicit negation disclaimers (e.g. "does not show that X causes Y") so caveats aren't flagged
    eval_text = re.sub(
        r"\bdoes\s+not\s+(?:show|imply|mean|prove|establish)\s+that\s+[^.]*",
        "",
        text_lower,
    )

    # 1. Banned causal patterns
    for pat in _BANNED_CAUSAL_PATTERNS:
        if re.search(pat, eval_text):
            violations.append(f"Causal language detected matching pattern: {pat}")

    # 2. Banned overclaims
    for pat in _BANNED_OVERCLAIMS:
        if re.search(pat, text_lower):
            violations.append(f"Overclaim detected matching pattern: {pat}")

    # 3. Bare 'significant' without 'statistically' or correction qualification
    # (Allow "statistically supported" or "statistically significant")
    # For user-facing robustness, check if 'significant' appears without 'statistically'
    if "statistically significant" not in text_lower and "statistically supported" not in text_lower:
        if re.search(r"\bsignificant\b", text_lower):
            violations.append("Bare 'significant' used without 'statistically supported' or 'statistically significant'.")

    return LintResult(ok=len(violations) == 0, violations=violations)
