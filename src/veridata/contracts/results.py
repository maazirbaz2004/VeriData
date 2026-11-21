"""Pydantic v2 contracts for Phase 3 Statistical Test Results (Master Plan Section 5.3)."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from veridata.contracts.common import SCHEMA_VERSION
from veridata.contracts.hypothesis import Direction


class AssumptionCheck(BaseModel):
    """Result of a single statistical assumption diagnostic."""

    name: str
    method: str
    statistic: float | None = None
    p_value: float | None = None
    passed: bool
    severity: Literal["info", "warning", "violation"]
    detail: str


class EffectSize(BaseModel):
    """Standardized effect size with optional confidence interval."""

    name: str
    value: float
    ci_low: float | None = None
    ci_high: float | None = None
    ci_method: str | None = None
    magnitude: Literal["negligible", "small", "medium", "large"]
    comparable_value: float | None = None


class TestResult(BaseModel):
    """Deterministic output of running a statistical test on a Hypothesis."""

    __test__ = False

    schema_version: str = SCHEMA_VERSION
    hypothesis_id: str
    status: Literal["ok", "skipped_infeasible", "error"]
    test_name: str
    test_selection_reason: str = ""
    selection_trace: list[dict[str, Any]] = Field(default_factory=list)
    fallback_used: bool = False
    n_used: int = 0
    group_sizes: dict[str, int] | None = None
    statistic: float | None = None
    df: float | list[float] | None = None
    p_value: float | None = None
    effect: EffectSize | None = None
    descriptives: dict[str, Any] = Field(default_factory=dict)
    direction_observed: Direction | None = None
    assumptions: list[AssumptionCheck] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    runtime_ms: float = 0.0
    seed: int | None = None
    error: str | None = None
