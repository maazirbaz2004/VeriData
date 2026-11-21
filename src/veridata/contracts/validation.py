"""Pydantic v2 contracts for Phase 3 Statistical Validation (Master Plan Section 5.4)."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field

from veridata.contracts.common import SCHEMA_VERSION


class RejectionReason(str, Enum):
    """Machine-readable rejection reason codes (Principle P10)."""

    NOT_SIGNIFICANT_AFTER_CORRECTION = "not_significant_after_correction"
    EFFECT_BELOW_THRESHOLD = "effect_below_threshold"
    ASSUMPTION_VIOLATED = "assumption_violated_no_fallback"
    INSUFFICIENT_DATA = "insufficient_data"
    DEGENERATE_DATA = "degenerate_data"
    TEST_ERROR = "test_error"
    TRIVIAL_RELATIONSHIP = "trivial_relationship"
    UNSTABLE_CI = "ci_includes_zero"


class ValidationDecision(BaseModel):
    """Validation verdict for a single hypothesis test within a multiple-testing family."""

    schema_version: str = SCHEMA_VERSION
    hypothesis_id: str
    p_raw: float | None = None
    q_value: float | None = None
    family_id: str = "batch"
    family_size: int = 0
    rank_in_family: int | None = None
    accepted: bool
    reasons: list[RejectionReason] = Field(default_factory=list)
    reason_text: str = ""
    flags: list[str] = Field(default_factory=list)
    would_pass_without_correction: bool = False
    would_pass_without_effect_floor: bool = False

