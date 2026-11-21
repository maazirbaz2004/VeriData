"""Tests for Phase 2 feasibility screening, rare-level policy, ranking, and pruning."""

from __future__ import annotations

import numpy as np
import pandas as pd

from veridata.config import PipelineConfig
from veridata.contracts.hypothesis import FeasibilityReport, Hypothesis, RelationshipType
from veridata.hypotheses.dedupe import make_hypothesis_id
from veridata.hypotheses.feasibility import assess_feasibility
from veridata.hypotheses.ranking import prune_hypotheses_outcome_independent, rank_hypotheses
from veridata.schemas import ColumnRole, ColumnSchemaEntry, SemanticType


def _schema_entry(stype: SemanticType, n_unique: int, pct_missing: float = 0.0) -> ColumnSchemaEntry:
    return ColumnSchemaEntry(
        semantic_type=stype,
        role=ColumnRole.FEATURE,
        n_unique=n_unique,
        pct_missing=pct_missing,
    )


def _hyp(col_a: str, col_b: str, rel: RelationshipType) -> Hypothesis:
    return Hypothesis(
        id=make_hypothesis_id(rel, col_a, col_b),
        column_a=col_a,
        column_b=col_b,
        relationship=rel,
        source="enumerated",
        feasibility=FeasibilityReport(feasible=True, reasons=[], n_pairwise_complete=0),
    )


def test_feasibility_small_n_and_constant_degenerate() -> None:
    cfg = PipelineConfig()
    df = pd.DataFrame(
        {
            "x": [1.0, 2.0, 3.0] + [np.nan] * 25,
            "y": [10.0, 20.0, 30.0] + [1.0] * 25,
            "const": [5.0] * 28,
            "ok": np.arange(28, dtype=float),
        }
    )
    schema = {
        c: _schema_entry(SemanticType.NUMERIC_CONTINUOUS, 20) for c in df.columns
    }

    rep_small = assess_feasibility(_hyp("x", "y", RelationshipType.NUM_NUM), df, schema, cfg)
    assert not rep_small.feasible
    assert rep_small.n_pairwise_complete == 3

    rep_const = assess_feasibility(_hyp("const", "ok", RelationshipType.NUM_NUM), df, schema, cfg)
    assert not rep_const.feasible
    assert any("degenerate" in r for r in rep_const.reasons)


def test_feasibility_num_binary_small_group_rejected() -> None:
    cfg = PipelineConfig()
    df = pd.DataFrame(
        {
            "val": np.arange(30, dtype=float),
            "grp": ["A"] * 26 + ["B"] * 4,
        }
    )
    schema = {
        "val": _schema_entry(SemanticType.NUMERIC_CONTINUOUS, 30),
        "grp": _schema_entry(SemanticType.BINARY, 2),
    }
    rep = assess_feasibility(_hyp("val", "grp", RelationshipType.NUM_BINARY), df, schema, cfg)
    assert not rep.feasible
    assert any("group 'B'" in r for r in rep.reasons)


def test_feasibility_num_categorical_rare_level_dropped_remains_feasible() -> None:
    cfg = PipelineConfig()
    df = pd.DataFrame(
        {
            "val": np.arange(45, dtype=float),
            "cat": ["North"] * 20 + ["South"] * 20 + ["Tiny"] * 5,
        }
    )
    schema = {
        "val": _schema_entry(SemanticType.NUMERIC_CONTINUOUS, 45),
        "cat": _schema_entry(SemanticType.CATEGORICAL_NOMINAL, 3),
    }
    rep = assess_feasibility(_hyp("val", "cat", RelationshipType.NUM_CATEGORICAL), df, schema, cfg)
    assert rep.feasible
    assert rep.dropped_levels == ["Tiny"]
    assert rep.group_sizes == {"North": 20, "South": 20}
    assert rep.n_pairwise_complete == 40


def test_feasibility_cat_cat_min_expected_count_computed_from_marginals() -> None:
    cfg = PipelineConfig()
    df = pd.DataFrame(
        {
            "c1": ["A"] * 10 + ["B"] * 30,
            "c2": ["X"] * 10 + ["Y"] * 30,
        }
    )
    schema = {
        "c1": _schema_entry(SemanticType.BINARY, 2),
        "c2": _schema_entry(SemanticType.BINARY, 2),
    }
    rep = assess_feasibility(_hyp("c1", "c2", RelationshipType.CAT_CAT), df, schema, cfg)
    assert rep.feasible
    # min marginal A=10, X=10, n=40 -> expected = 10*10/40 = 2.5 (still feasible!)
    assert rep.min_expected_count == 2.5


def test_ranking_and_outcome_independent_pruning_order() -> None:
    cfg = PipelineConfig()
    cfg.hypotheses.max_tests = 2

    schema = {
        "target": _schema_entry(SemanticType.NUMERIC_CONTINUOUS, 100),
        "x1": _schema_entry(SemanticType.NUMERIC_CONTINUOUS, 100),
        "x2": _schema_entry(SemanticType.BINARY, 2),
        "high_cat": _schema_entry(SemanticType.CATEGORICAL_NOMINAL, 12),
    }
    feas_ok = FeasibilityReport(feasible=True, reasons=[], n_pairwise_complete=200)

    hyps = [
        _hyp("target", "x1", RelationshipType.NUM_NUM).model_copy(update={"feasibility": feas_ok}),
        _hyp("target", "x2", RelationshipType.NUM_BINARY).model_copy(update={"feasibility": feas_ok}),
        _hyp("x1", "x2", RelationshipType.NUM_BINARY).model_copy(update={"feasibility": feas_ok}),
        _hyp("x1", "high_cat", RelationshipType.NUM_CATEGORICAL).model_copy(
            update={"feasibility": feas_ok}
        ),
    ]

    ranked_with_target = rank_hypotheses(hyps, schema, cfg, target="target")
    # Target pairs should rank above non-target pairs
    assert "target" in (ranked_with_target[0].column_a, ranked_with_target[0].column_b)

    # Pruning with target -> step 1 switches to target_focused, leaving 2 pairs
    kept_t, steps_t, pruned_t, mode_t = prune_hypotheses_outcome_independent(
        ranked_with_target, schema, cfg, target="target"
    )
    assert pruned_t == 2
    assert mode_t == "target_focused"
    assert steps_t[0]["rule"] == "switch_to_target_focused"
    assert len(kept_t) == 2

    # Pruning without target -> step 2 drops high-cardinality NUM_CATEGORICAL first, then step 3 priority
    ranked_no_target = rank_hypotheses(hyps, schema, cfg, target=None)
    kept_nt, steps_nt, pruned_nt, mode_nt = prune_hypotheses_outcome_independent(
        ranked_no_target, schema, cfg, target=None
    )
    assert pruned_nt == 2
    assert mode_nt is None
    assert steps_nt[0]["rule"] == "drop_high_cardinality_categorical_pairs"
    assert all(h.column_b != "high_cat" for h in kept_nt)

