"""Internal data structures for the Phase 3 statistical tool library."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any, Callable

import numpy as np
import pandas as pd

from veridata.config import PipelineConfig
from veridata.contracts.hypothesis import Direction, Hypothesis, RelationshipType
from veridata.contracts.results import AssumptionCheck, EffectSize


def derive_seed(base_seed: int, hypothesis_id: str) -> int:
    """Derive a deterministic 32-bit RNG seed from config seed + hypothesis ID."""
    digest = hashlib.sha256(f"{base_seed}:{hypothesis_id}".encode("utf-8")).digest()
    return int.from_bytes(digest[:4], byteorder="big")


@dataclass
class PreparedData:
    """Validated, pairwise-complete inputs ready for a statistical test."""

    hypothesis: Hypothesis
    relationship: RelationshipType
    n_used: int
    # NUM_NUM / NUM_NUM_NONLINEAR
    x: np.ndarray | None = None
    y: np.ndarray | None = None
    # NUM_BINARY / NUM_CATEGORICAL
    groups: list[np.ndarray] | None = None
    group_labels: list[str] | None = None
    group_sizes: dict[str, int] | None = None
    collapsed_to_two_groups: bool = False
    # CAT_CAT
    contingency: np.ndarray | None = None
    row_labels: list[str] | None = None
    col_labels: list[str] | None = None
    cat_a_values: np.ndarray | None = None
    cat_b_values: np.ndarray | None = None
    # Status / diagnostics
    status: str = "ok"  # "ok" | "skipped_infeasible" | "degenerate" | "error"
    status_reason: str = ""
    dropped_levels: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass
class RawTestOutput:
    """Output returned by an individual statistical test tool function."""

    test_name: str
    statistic: float
    df: float | list[float] | None
    p_value: float
    effect: EffectSize
    descriptives: dict[str, Any]
    direction_observed: Direction | None
    extra_assumptions: list[AssumptionCheck] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ToolSpec:
    """Fixed registry entry describing a callable statistical test tool (Section 4.5)."""

    name: str
    relationship: RelationshipType
    run: Callable[[PreparedData, PipelineConfig, np.random.Generator], RawTestOutput]
    effect_name: str
    description: str

