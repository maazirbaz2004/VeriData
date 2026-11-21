"""Pydantic v2 contracts for Phase 2: Hypothesis Generation (Master Plan Section 5.2)."""

from __future__ import annotations

import re
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from veridata.contracts.common import SCHEMA_VERSION

_DIGIT_RE = re.compile(r"\d")


class RelationshipType(str, Enum):
    """Statistical relationship families supported by VeriData."""

    NUM_BINARY = "numeric_vs_binary"
    NUM_CATEGORICAL = "numeric_vs_categorical"
    NUM_NUM = "numeric_vs_numeric"
    CAT_CAT = "categorical_vs_categorical"
    NUM_NUM_NONLINEAR = "numeric_vs_numeric_nonlinear"


class Direction(str, Enum):
    """Expected or observed direction of association (tests are always two-sided)."""

    ANY = "any"
    POSITIVE = "positive"
    NEGATIVE = "negative"
    A_GREATER = "a_greater"
    B_GREATER = "b_greater"


class FeasibilityReport(BaseModel):
    """Outcome-independent sample-size and degeneracy screening report."""

    feasible: bool
    reasons: list[str] = Field(default_factory=list)
    n_pairwise_complete: int
    group_sizes: dict[str, int] | None = None
    min_expected_count: float | None = None
    dropped_levels: list[str] = Field(default_factory=list)


class Hypothesis(BaseModel):
    """Structured statistical hypothesis consumed by Phase 3."""

    schema_version: str = SCHEMA_VERSION
    id: str
    column_a: str
    column_b: str
    relationship: RelationshipType
    expected_direction: Direction = Direction.ANY
    covariates: list[str] = Field(default_factory=list)
    source: Literal["enumerated", "llm", "user", "followup"]
    rationale: str = ""
    feasibility: FeasibilityReport
    priority_score: float = 0.0
    priority_components: dict[str, float] = Field(default_factory=dict)
    created_stage: Literal["batch", "chat"] = "batch"
    status: Literal["proposed", "queued", "tested", "skipped_infeasible", "error"] = "proposed"


class HypothesisManifest(BaseModel):
    """Audit manifest fixing the multiple-testing family before any test runs (Section 9)."""

    schema_version: str = SCHEMA_VERSION
    dataset_name: str = ""
    mode: Literal["exhaustive", "target_focused", "llm_prioritized"]
    effective_mode: Literal["exhaustive", "target_focused", "llm_prioritized"]
    target: str | None = None
    n_columns_total: int
    n_columns_eligible: int
    excluded_columns: list[dict[str, str]] = Field(default_factory=list)
    n_candidate_hypotheses: int
    n_infeasible: int
    n_pruned: int = 0
    pruning_steps: list[dict[str, Any]] = Field(default_factory=list)
    n_in_family_planned: int
    n_total_eligible_before_selection: int | None = None
    counts_by_relationship: dict[str, int] = Field(default_factory=dict)
    treat_small_discrete_as_numeric: bool = False
    lump_rare_levels: bool = False
    llm_used: bool = False
    llm_model: str | None = None
    llm_prompt_version: str | None = None
    llm_unknown_aliases_dropped: int = 0
    llm_invalid_rationales_dropped: int = 0
    llm_topped_up_count: int = 0
    selection_inputs_hash: str = ""
    notes: list[str] = Field(default_factory=list)


class HypothesisSet(BaseModel):
    """Complete output of Phase 2 hypothesis generation."""

    schema_version: str = SCHEMA_VERSION
    hypotheses: list[Hypothesis] = Field(default_factory=list)
    manifest: HypothesisManifest


class LLMHypothesisProposal(BaseModel):
    """Single structured hypothesis proposal returned by the LLM using safe aliases."""

    column_a_alias: str
    column_b_alias: str
    expected_direction: Direction = Direction.ANY
    rationale: str = Field(..., max_length=240)
    relevance: float = Field(..., ge=0.0, le=1.0)

    @field_validator("rationale")
    @classmethod
    def _reject_digits_in_rationale(cls, v: str) -> str:
        if _DIGIT_RE.search(v):
            raise ValueError("Rationale must not contain digits or numeric claims.")
        return v.strip()


class LLMProposalBatch(BaseModel):
    """Batch of LLM hypothesis proposals."""

    proposals: list[LLMHypothesisProposal] = Field(default_factory=list)


class NLHypothesisParse(BaseModel):
    """Structured output schema for the LLM natural-language hypothesis parser."""

    status: Literal["ok", "ambiguous", "unsupported", "no_columns_found"]
    column_a_alias: str | None = None
    column_b_alias: str | None = None
    level_of_interest: str | None = None
    expected_direction_phrase: Literal[
        "greater", "less", "associated", "different", "unspecified"
    ] = "unspecified"
    clarification_question: str | None = None
    candidates: list[str] = Field(default_factory=list, max_length=4)
    unsupported_reason: str | None = None


class NLParseOutcome(BaseModel):
    """Deterministic post-processed outcome of parse_nl_hypothesis."""

    status: Literal["ok", "ambiguous", "unsupported", "no_columns_found"]
    hypothesis: Hypothesis | None = None
    clarification_question: str | None = None
    candidates: list[str] = Field(default_factory=list)
    reason: str | None = None
    used_llm: bool = False

