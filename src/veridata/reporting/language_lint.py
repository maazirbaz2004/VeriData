"""Language linter: association not causation, no overclaiming, consistent direction words (Phase 5, Section 7).

A banned causal word is allowed only in a negated sentence part ("this is not evidence of cause
and effect", "does not show that X causes Y"): a negator within the 8 preceding words.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from veridata.contracts.findings import Finding
from veridata.contracts.hypothesis import Direction, RelationshipType

CAUSAL = [
    r"caus(?:e|es|ed|ing|al|ally|ation)",
    r"caused by",
    r"leads? to",
    r"led to",
    r"results? in",
    r"resulted in",
    r"due to",
    r"because of",
    r"driv(?:e|es|en|ing)",
    r"driven by",
    r"affect(?:s|ed|ing)?",
    r"impact(?:s|ed|ing)?",
    r"influenc(?:e|es|ed|ing)",
    r"makes",
    r"responsible for",
    r"determin(?:es|ed by)",
    r"effect of",
    r"increases",
    r"decreases",
    r"raises",
    r"reduces",
    r"boosts",
    r"produces",
    r"triggers",
]
OVERCLAIM = [
    r"prov(?:e|es|ed|en)",
    r"confirm(?:s|ed)?",
    r"definitive(?:ly)?",
    r"definitely",
    r"certain(?:ly)?",
    r"undeniabl[ey]",
    r"guarantee(?:s|d)?",
    r"conclusive(?:ly)?",
]
NEGATORS = {"not", "no", "never", "cannot", "without", "nor", "neither"}
_CAUSAL_RE = re.compile(r"\b(" + "|".join(CAUSAL) + r")\b", re.IGNORECASE)
_OVER_RE = re.compile(r"\b(" + "|".join(OVERCLAIM) + r")\b", re.IGNORECASE)
_SIG_RE = re.compile(r"\bsignificant(?:ly)?\b", re.IGNORECASE)
_SIG_OK_RE = re.compile(r"statistically significant after correction", re.IGNORECASE)


@dataclass
class LintIssue:
    code: str
    message: str
    match: str = ""
    span: tuple[int, int] = (0, 0)

    def as_dict(self) -> dict[str, object]:
        return {
            "code": self.code,
            "message": self.message,
            "match": self.match,
            "span": list(self.span),
        }


class LintResult(list[LintIssue]):
    """List of LintIssue objects that also exposes `.ok` and `.violations` for Phase 6 callers."""

    @property
    def ok(self) -> bool:
        return len(self) == 0

    @property
    def violations(self) -> list[str]:
        return [issue.message for issue in self]


def _negated(text: str, start: int) -> bool:
    sent_start = (
        max(
            text.rfind(".", 0, start),
            text.rfind("!", 0, start),
            text.rfind("?", 0, start),
            text.rfind("\n", 0, start),
        )
        + 1
    )
    words = re.findall(r"[A-Za-z']+", text[sent_start:start].lower())[-8:]
    return any(w in NEGATORS or w.endswith("n't") for w in words)


def lint_text(text: str, finding: Finding | None = None, *, kind: str = "finding") -> LintResult:
    """kind: 'finding' (accepted-finding explanation), 'rejected', 'report', 'chat'."""
    issues: list[LintIssue] = []
    for m in _CAUSAL_RE.finditer(text):
        if not _negated(text, m.start()):
            issues.append(
                LintIssue(
                    "causal_language",
                    "Causal language detected: use 'associated with', not causal wording.",
                    m.group(0),
                    m.span(),
                )
            )
    for m in _OVER_RE.finditer(text):
        if not _negated(text, m.start()):
            issues.append(LintIssue("overclaim", "Overclaiming word.", m.group(0), m.span()))
    ok_spans = [mm.span() for mm in _SIG_OK_RE.finditer(text)]
    for m in _SIG_RE.finditer(text):
        if not any(a <= m.start() < b for a, b in ok_spans):
            issues.append(
                LintIssue(
                    "bare_significant",
                    "Say 'statistically supported' (or 'statistically significant after correction').",
                    m.group(0),
                    m.span(),
                )
            )
    if finding is None:
        return LintResult(issues)
    low = text.lower()
    if kind == "finding":
        if not any(q in low for q in ("associated", "tend to", "tended to", "on average")):
            issues.append(
                LintIssue(
                    "missing_qualifier",
                    "Accepted-finding text must say 'associated with', 'tend to' or 'on average'.",
                )
            )
        if "after correcting" not in low and "adjusted p" not in low:
            issues.append(
                LintIssue(
                    "missing_correction",
                    "Accepted-finding text must state the multiple-testing correction.",
                )
            )
    t, h = finding.test, finding.hypothesis
    if h.relationship in {RelationshipType.NUM_NUM, RelationshipType.NUM_NUM_NONLINEAR}:
        if t.direction_observed == Direction.POSITIVE and re.search(r"\bnegative(ly)?\b", low):
            issues.append(
                LintIssue(
                    "direction_mismatch",
                    "Text says negative but the observed direction is positive.",
                )
            )
        if t.direction_observed == Direction.NEGATIVE and re.search(r"\bpositive(ly)?\b", low):
            issues.append(
                LintIssue(
                    "direction_mismatch",
                    "Text says positive but the observed direction is negative.",
                )
            )
    if h.relationship == RelationshipType.NUM_BINARY:
        hg = str(t.descriptives.get("higher_group", ""))
        order = [str(x) for x in t.descriptives.get("group_order", [])]
        for m in re.finditer(
            r"higher for (?:" + re.escape(h.column_b) + r" = )?(.+?)(?= than|[.,;(]|$)", text
        ):
            said = m.group(1).strip()
            if hg and said in order and said != hg:
                issues.append(
                    LintIssue(
                        "direction_mismatch",
                        f"Text says higher for {said} but the data show higher for {hg}.",
                        m.group(0),
                        m.span(),
                    )
                )
    if t.test_name == "mann_whitney_u" and re.search(r"\bmeans?\b", low):
        issues.append(
            LintIssue("mwu_means", "A Mann-Whitney result must not be described with means.")
        )
    return LintResult(issues)
