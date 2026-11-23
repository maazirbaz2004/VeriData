"""Ground-truth and system-output models for the planted-truth benchmark (Phase 4, Sections 4.4 and 5).

These models are local to ``veridata.benchmark``; they do not change the shared ``contracts/``.
Pairs are always stored unordered, with ``col_a < col_b``.
"""

from __future__ import annotations

import json
from itertools import combinations
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

TRUTH_SCHEMA_VERSION = "1.0"

PairType = Literal["direct", "induced", "weak_induced"]


def pair_key(a: str, b: str) -> tuple[str, str]:
    """Canonical unordered pair key."""
    return (a, b) if a <= b else (b, a)


class TruthPair(BaseModel):
    """One truly dependent (or gray-zone) column pair."""

    col_a: str
    col_b: str
    type: PairType
    form: str  # linear | monotonic | binary_shift | categorical_shift | cat_cat | latent_factor | quadratic | interaction | induced
    population_effect: dict[str, Any] = Field(default_factory=dict)
    direction: dict[str, Any] | None = None  # {"kind": "sign", "value": "+"} | {"kind": "group_diff", "group_col": c, "higher_level": l}
    detectable_by_default_tests: bool = True
    testable: bool = True  # enough complete rows / group sizes in the realised dataset
    relationship: str = ""
    via: list[str] = Field(default_factory=list)
    dependence_measure: float | None = None  # large-n empirical measure used for induced/gray decisions

    @property
    def key(self) -> tuple[str, str]:
        return pair_key(self.col_a, self.col_b)


class GroundTruth(BaseModel):
    """Answer key for one generated dataset."""

    schema_version: str = TRUTH_SCHEMA_VERSION
    dataset_id: str
    scenario_id: str
    seed: int
    n_rows: int
    columns: dict[str, str]  # column -> numeric | binary | categorical
    true_pairs: list[TruthPair] = Field(default_factory=list)
    gray_pairs: list[TruthPair] = Field(default_factory=list)
    n_pairs_total: int = 0
    null_pairs_count: int = 0
    is_pure_null: bool = False
    notes: dict[str, Any] = Field(default_factory=dict)

    def true_keys(self) -> set[tuple[str, str]]:
        return {p.key for p in self.true_pairs}

    def gray_keys(self) -> set[tuple[str, str]]:
        return {p.key for p in self.gray_pairs}

    def all_keys(self) -> set[tuple[str, str]]:
        return {pair_key(a, b) for a, b in combinations(sorted(self.columns), 2)}

    def null_keys(self) -> set[tuple[str, str]]:
        return self.all_keys() - self.true_keys() - self.gray_keys()

    def testable_truths(self) -> list[TruthPair]:
        """Recall denominator (primary): detectable by default tests and feasible."""
        return [p for p in self.true_pairs if p.detectable_by_default_tests and p.testable]

    def save(self, path: Path | str) -> Path:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return p

    @classmethod
    def load(cls, path: Path | str) -> GroundTruth:
        return cls.model_validate(json.loads(Path(path).read_text(encoding="utf-8")))


class ReportedFinding(BaseModel):
    """A finding reported by any system under evaluation (Section 5)."""

    col_a: str
    col_b: str
    direction: dict[str, Any] | None = None
    effect: float | None = None
    p_value: float | None = None
    q_value: float | None = None
    claim_text: str | None = None
    source_id: str | None = None


class SystemOutput(BaseModel):
    """What a system returns for one dataset."""

    system_name: str
    dataset_id: str = ""
    findings: list[ReportedFinding] = Field(default_factory=list)
    n_tests_attempted: int | None = None
    runtime_s: float = 0.0
    cost_usd: float | None = None
    error: str | None = None
    meta: dict[str, Any] = Field(default_factory=dict)
