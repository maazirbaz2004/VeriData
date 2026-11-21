"""Matching reported findings to ground truth (Phase 4, Section 6). Freeze before Phase 8.

Unit of evaluation: an unordered column pair. Rules, in order:
1. Duplicate reports of the same pair collapse to the first one.
2. A pair with a column that is not in the dataset is a false discovery (``unknown_column``).
3. Gray pair (weak induced dependence) -> ignored (neither true nor false).
4. Null pair -> false discovery (``null_pair``).
5. True pair -> true discovery, unless direction is checked and disagrees (``wrong_direction``).

Direction modes: ``"if_reported"`` (primary): direction is checked when the system reports one
and the truth has a comparable one (numeric-numeric sign; numeric-vs-binary higher group).
Categorical shifts with 3+ levels and categorical-categorical pairs are never direction-checked.
``"ignore"`` (pair-only): direction is never checked.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from veridata.benchmark.truth import GroundTruth, ReportedFinding, TruthPair, pair_key

DirectionMode = Literal["if_reported", "ignore"]


class FindingMatch(BaseModel):
    col_a: str
    col_b: str
    label: Literal["true", "false", "ignored"]
    reason: str  # true_pair | null_pair | wrong_direction | unknown_column | gray_pair
    q_value: float | None = None
    truth_form: str | None = None


class PairOutcome(BaseModel):
    col_a: str
    col_b: str
    form: str
    type: str
    bin: str
    detectable: bool
    testable: bool
    found: bool


class MatchResult(BaseModel):
    dataset_id: str
    direction_mode: str
    findings: list[FindingMatch] = Field(default_factory=list)
    truths: list[PairOutcome] = Field(default_factory=list)
    n_duplicates: int = 0

    @property
    def tp(self) -> int:
        return sum(1 for f in self.findings if f.label == "true")

    @property
    def fp(self) -> int:
        return sum(1 for f in self.findings if f.label == "false")


def _norm_level(v: Any) -> str:
    s = str(v).strip()
    try:
        f = float(s)
        if f.is_integer():
            return str(int(f))
    except ValueError:
        pass
    return s


def direction_agrees(reported: dict[str, Any] | None, truth: TruthPair) -> bool | None:
    """True/False when comparable; None when direction is not checked for this pair."""
    t = truth.direction
    if not reported or not t:
        return None
    if t.get("kind") == "sign" and reported.get("kind") == "sign":
        return reported.get("value") == t.get("value")
    if t.get("kind") == "group_diff" and reported.get("kind") == "group_diff":
        if t.get("n_levels") != 2 or reported.get("group_col") != t.get("group_col"):
            return None
        return _norm_level(reported.get("higher_level")) == _norm_level(t.get("higher_level"))
    return None


def match_findings(findings: list[ReportedFinding], truth: GroundTruth, direction_mode: DirectionMode = "if_reported") -> MatchResult:
    true_by_key = {p.key: p for p in truth.true_pairs}
    gray_keys = truth.gray_keys()
    all_keys = truth.all_keys()
    # completeness: every possible pair is in exactly one class
    assert not (set(true_by_key) & gray_keys), "a pair is both true and gray"
    assert set(true_by_key) | gray_keys <= all_keys, "truth lists a pair outside the dataset"

    seen: set[tuple[str, str]] = set()
    credited: set[tuple[str, str]] = set()
    out = MatchResult(dataset_id=truth.dataset_id, direction_mode=direction_mode)
    for f in findings:
        k = pair_key(f.col_a, f.col_b)
        if k in seen:
            out.n_duplicates += 1
            continue
        seen.add(k)
        if k not in all_keys:
            out.findings.append(FindingMatch(col_a=k[0], col_b=k[1], label="false", reason="unknown_column", q_value=f.q_value))
        elif k in gray_keys:
            out.findings.append(FindingMatch(col_a=k[0], col_b=k[1], label="ignored", reason="gray_pair", q_value=f.q_value))
        elif k in true_by_key:
            tp = true_by_key[k]
            agree = None if direction_mode == "ignore" else direction_agrees(f.direction, tp)
            if agree is False:
                out.findings.append(FindingMatch(col_a=k[0], col_b=k[1], label="false", reason="wrong_direction", q_value=f.q_value, truth_form=tp.form))
            else:
                credited.add(k)
                out.findings.append(FindingMatch(col_a=k[0], col_b=k[1], label="true", reason="true_pair", q_value=f.q_value, truth_form=tp.form))
        else:
            out.findings.append(FindingMatch(col_a=k[0], col_b=k[1], label="false", reason="null_pair", q_value=f.q_value))
    for p in truth.true_pairs:
        out.truths.append(
            PairOutcome(
                col_a=p.col_a, col_b=p.col_b, form=p.form, type=p.type, bin=str(p.population_effect.get("bin", "n/a")),
                detectable=p.detectable_by_default_tests, testable=p.testable, found=p.key in credited,
            )
        )
    return out
