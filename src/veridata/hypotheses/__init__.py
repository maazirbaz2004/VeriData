"""Phase 2: Intelligent Hypothesis Generation package."""

from __future__ import annotations

from veridata.hypotheses.dedupe import deduplicate_hypotheses, make_hypothesis_id
from veridata.hypotheses.enumerate import (
    effective_column_kind,
    enumerate_hypotheses,
    filter_eligible_columns,
    map_pair_to_relationship,
)
from veridata.hypotheses.feasibility import assess_feasibility, screen_hypotheses
from veridata.hypotheses.generator import (
    generate_hypotheses,
    render_hypotheses_markdown,
    save_hypothesis_outputs,
)
from veridata.hypotheses.llm_proposer import propose_hypotheses_with_llm, validate_rationale
from veridata.hypotheses.nl_parser import parse_nl_hypothesis
from veridata.hypotheses.ranking import (
    prune_hypotheses_outcome_independent,
    rank_hypotheses,
    score_hypothesis,
)
from veridata.hypotheses.safe_profile import (
    FORBIDDEN_SAFE_PROFILE_KEYS,
    SafeProfile,
    build_safe_profile,
    contains_forbidden_keys,
    sanitize_text,
)

__all__ = [
    "FORBIDDEN_SAFE_PROFILE_KEYS",
    "SafeProfile",
    "assess_feasibility",
    "build_safe_profile",
    "contains_forbidden_keys",
    "deduplicate_hypotheses",
    "effective_column_kind",
    "enumerate_hypotheses",
    "filter_eligible_columns",
    "generate_hypotheses",
    "make_hypothesis_id",
    "map_pair_to_relationship",
    "parse_nl_hypothesis",
    "propose_hypotheses_with_llm",
    "prune_hypotheses_outcome_independent",
    "rank_hypotheses",
    "render_hypotheses_markdown",
    "sanitize_text",
    "save_hypothesis_outputs",
    "score_hypothesis",
    "screen_hypotheses",
    "validate_rationale",
]

