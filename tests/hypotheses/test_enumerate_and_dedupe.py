"""Tests for Phase 2 enumeration, type mapping, orientation, and deduplication."""

from __future__ import annotations

import pytest

from veridata.config import PipelineConfig
from veridata.contracts.hypothesis import (
    Direction,
    FeasibilityReport,
    Hypothesis,
    RelationshipType,
)
from veridata.errors import HypothesisError
from veridata.hypotheses.dedupe import deduplicate_hypotheses, make_hypothesis_id
from veridata.hypotheses.enumerate import (
    enumerate_hypotheses,
    filter_eligible_columns,
    map_pair_to_relationship,
)
from veridata.schemas import ColumnRole, ColumnSchemaEntry, SemanticType


def _entry(
    stype: SemanticType,
    n_unique: int = 10,
    role: ColumnRole = ColumnRole.FEATURE,
    pct_missing: float = 0.0,
) -> ColumnSchemaEntry:
    return ColumnSchemaEntry(
        semantic_type=stype,
        role=role,
        n_unique=n_unique,
        pct_missing=pct_missing,
    )


@pytest.mark.parametrize(
    ("type_a", "n_a", "type_b", "n_b", "expected_rel", "expected_a", "expected_b"),
    [
        (
            SemanticType.NUMERIC_CONTINUOUS,
            100,
            SemanticType.NUMERIC_CONTINUOUS,
            80,
            RelationshipType.NUM_NUM,
            "col_a",
            "col_b",
        ),
        (
            SemanticType.NUMERIC_CONTINUOUS,
            100,
            SemanticType.BINARY,
            2,
            RelationshipType.NUM_BINARY,
            "col_a",
            "col_b",
        ),
        # Reversed order must still orient numeric -> column_a, binary -> column_b
        (
            SemanticType.BINARY,
            2,
            SemanticType.NUMERIC_CONTINUOUS,
            100,
            RelationshipType.NUM_BINARY,
            "col_b",
            "col_a",
        ),
        (
            SemanticType.CATEGORICAL_NOMINAL,
            4,
            SemanticType.NUMERIC_CONTINUOUS,
            100,
            RelationshipType.NUM_CATEGORICAL,
            "col_b",
            "col_a",
        ),
        (
            SemanticType.CATEGORICAL_ORDINAL,
            4,
            SemanticType.NUMERIC_CONTINUOUS,
            100,
            RelationshipType.NUM_CATEGORICAL,
            "col_b",
            "col_a",
        ),
        (
            SemanticType.BINARY,
            2,
            SemanticType.BINARY,
            2,
            RelationshipType.CAT_CAT,
            "col_a",
            "col_b",
        ),
        (
            SemanticType.BINARY,
            2,
            SemanticType.CATEGORICAL_NOMINAL,
            5,
            RelationshipType.CAT_CAT,
            "col_a",
            "col_b",
        ),
        # Small discrete (<= 10 unique) defaults to categorical when paired with numeric
        (
            SemanticType.NUMERIC_CONTINUOUS,
            100,
            SemanticType.NUMERIC_DISCRETE,
            5,
            RelationshipType.NUM_CATEGORICAL,
            "col_a",
            "col_b",
        ),
        # Large discrete (> 10 unique) behaves as numeric
        (
            SemanticType.NUMERIC_CONTINUOUS,
            100,
            SemanticType.NUMERIC_DISCRETE,
            15,
            RelationshipType.NUM_NUM,
            "col_a",
            "col_b",
        ),
        # Datetime is unsupported
        (
            SemanticType.DATETIME,
            100,
            SemanticType.NUMERIC_CONTINUOUS,
            100,
            None,
            None,
            None,
        ),
        (
            SemanticType.FREE_TEXT,
            100,
            SemanticType.BINARY,
            2,
            None,
            None,
            None,
        ),
    ],
)
def test_type_mapping_table(
    type_a: SemanticType,
    n_a: int,
    type_b: SemanticType,
    n_b: int,
    expected_rel: RelationshipType | None,
    expected_a: str | None,
    expected_b: str | None,
) -> None:
    cfg = PipelineConfig()
    res = map_pair_to_relationship(
        "col_a", _entry(type_a, n_a), "col_b", _entry(type_b, n_b), cfg
    )
    if expected_rel is None:
        assert res is None
    else:
        assert res == (expected_a, expected_b, expected_rel)


def test_small_discrete_as_numeric_override() -> None:
    cfg = PipelineConfig()
    cfg.hypotheses.treat_small_discrete_as_numeric = True
    res = map_pair_to_relationship(
        "charges",
        _entry(SemanticType.NUMERIC_CONTINUOUS, 500),
        "children",
        _entry(SemanticType.NUMERIC_DISCRETE, 6),
        cfg,
    )
    assert res == ("charges", "children", RelationshipType.NUM_NUM)


def test_enumeration_counts_on_three_fixtures() -> None:
    cfg = PipelineConfig()

    # Fixture 1: 3 numeric + 2 binary + 1 categorical = 6 eligible -> C(6,2) = 15
    schema1 = {
        "n1": _entry(SemanticType.NUMERIC_CONTINUOUS, 100),
        "n2": _entry(SemanticType.NUMERIC_CONTINUOUS, 100),
        "n3": _entry(SemanticType.NUMERIC_CONTINUOUS, 100),
        "b1": _entry(SemanticType.BINARY, 2),
        "b2": _entry(SemanticType.BINARY, 2),
        "c1": _entry(SemanticType.CATEGORICAL_NOMINAL, 4),
        "id_col": _entry(SemanticType.ID_LIKE, 100, role=ColumnRole.ID),
        "const_col": _entry(SemanticType.CONSTANT, 1, role=ColumnRole.EXCLUDED),
        "dt_col": _entry(SemanticType.DATETIME, 50),
        "n1__log1p": _entry(SemanticType.NUMERIC_CONTINUOUS, 100),
    }
    hyps1, excluded1, notes1, n_elig1 = enumerate_hypotheses(schema1, cfg)
    assert n_elig1 == 6
    assert len(hyps1) == 15
    assert len(excluded1) == 4
    assert any("datetime" in n for n in notes1)

    # Fixture 2: target_focused on n1 -> 5 pairs
    hyps2, _, _, _ = enumerate_hypotheses(schema1, cfg, target="n1", mode="target_focused")
    assert len(hyps2) == 5
    assert all("n1" in (h.column_a, h.column_b) for h in hyps2)

    # Fixture 3: enable_nonlinear=True adds 3 NUM_NUM_NONLINEAR pairs (C(3,2)=3) -> 18 total
    cfg_nl = PipelineConfig()
    cfg_nl.hypotheses.enable_nonlinear = True
    hyps3, _, _, _ = enumerate_hypotheses(schema1, cfg_nl)
    assert len(hyps3) == 18
    assert sum(1 for h in hyps3 if h.relationship == RelationshipType.NUM_NUM_NONLINEAR) == 3


def test_high_cardinality_categorical_excluded() -> None:
    cfg = PipelineConfig()
    cfg.hypotheses.max_levels_categorical = 10
    schema = {
        "num": _entry(SemanticType.NUMERIC_CONTINUOUS, 100),
        "high_card": _entry(SemanticType.CATEGORICAL_NOMINAL, 25),
    }
    eligible, excluded, _ = filter_eligible_columns(schema, cfg)
    assert eligible == ["num"]
    assert len(excluded) == 1
    assert "high_cardinality" in excluded[0]["reason"]


def test_target_focused_missing_target_raises() -> None:
    cfg = PipelineConfig()
    schema = {
        "a": _entry(SemanticType.NUMERIC_CONTINUOUS, 50),
        "b": _entry(SemanticType.BINARY, 2),
    }
    with pytest.raises(HypothesisError):
        enumerate_hypotheses(schema, cfg, target=None, mode="target_focused")


def test_symmetry_and_dedupe_merge_priority() -> None:
    id1 = make_hypothesis_id(RelationshipType.NUM_NUM, "age", "charges")
    id2 = make_hypothesis_id(RelationshipType.NUM_NUM, "charges", "age")
    assert id1 == id2

    feas = FeasibilityReport(feasible=True, reasons=[], n_pairwise_complete=100)
    h_enum = Hypothesis(
        id=id1,
        column_a="age",
        column_b="charges",
        relationship=RelationshipType.NUM_NUM,
        source="enumerated",
        rationale="",
        feasibility=feas,
    )
    h_llm = Hypothesis(
        id=id1,
        column_a="age",
        column_b="charges",
        relationship=RelationshipType.NUM_NUM,
        expected_direction=Direction.POSITIVE,
        source="llm",
        rationale="Older individuals may be associated with higher medical charges.",
        feasibility=feas,
    )
    h_user = Hypothesis(
        id=id1,
        column_a="age",
        column_b="charges",
        relationship=RelationshipType.NUM_NUM,
        expected_direction=Direction.ANY,
        source="user",
        rationale="",
        feasibility=feas,
        created_stage="chat",
    )

    merged = deduplicate_hypotheses([h_enum, h_llm, h_user])
    assert len(merged) == 1
    assert merged[0].source == "user"
    assert merged[0].expected_direction == Direction.POSITIVE
    assert "Older individuals" in merged[0].rationale
    assert merged[0].created_stage == "chat"

