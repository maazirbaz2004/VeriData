"""Tests for Phase 2 natural-language hypothesis parser (FakeLLM + offline fuzzy + gold set)."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from veridata.agent.fake_llm import FakeLLM
from veridata.config import PipelineConfig, load_config
from veridata.contracts.hypothesis import Direction, RelationshipType
from veridata.hypotheses.nl_parser import parse_nl_hypothesis
from veridata.schemas import ColumnRole, ColumnSchemaEntry, SemanticType


def _tiny_insurance() -> tuple[pd.DataFrame, dict[str, ColumnSchemaEntry]]:
    rng = np.random.default_rng(42)
    n = 60
    df = pd.DataFrame(
        {
            "age": rng.integers(18, 65, size=n).astype(float),
            "bmi": rng.normal(28.0, 5.0, size=n),
            "charges": rng.normal(12000.0, 4000.0, size=n),
            "smoker": rng.choice(["yes", "no"], size=n, p=[0.4, 0.6]),
            "region": rng.choice(["northeast", "southeast", "southwest"], size=n),
        }
    )
    schema = {
        "age": ColumnSchemaEntry(
            semantic_type=SemanticType.NUMERIC_CONTINUOUS, role=ColumnRole.FEATURE, n_unique=40, pct_missing=0.0
        ),
        "bmi": ColumnSchemaEntry(
            semantic_type=SemanticType.NUMERIC_CONTINUOUS, role=ColumnRole.FEATURE, n_unique=60, pct_missing=0.0
        ),
        "charges": ColumnSchemaEntry(
            semantic_type=SemanticType.NUMERIC_CONTINUOUS, role=ColumnRole.TARGET_CANDIDATE, n_unique=60, pct_missing=0.0
        ),
        "smoker": ColumnSchemaEntry(
            semantic_type=SemanticType.BINARY, role=ColumnRole.FEATURE, n_unique=2, pct_missing=0.0, binary_labels=["no", "yes"]
        ),
        "region": ColumnSchemaEntry(
            semantic_type=SemanticType.CATEGORICAL_NOMINAL, role=ColumnRole.FEATURE, n_unique=3, pct_missing=0.0
        ),
    }
    return df, schema


def test_nl_parser_offline_paths() -> None:
    df, schema = _tiny_insurance()
    cfg = PipelineConfig()

    # OK path
    res_ok = parse_nl_hypothesis("Do smokers have higher charges?", df, schema, llm=None, config=cfg)
    assert res_ok.status == "ok"
    assert res_ok.hypothesis is not None
    assert res_ok.hypothesis.column_a == "charges"
    assert res_ok.hypothesis.column_b == "smoker"
    assert res_ok.hypothesis.relationship == RelationshipType.NUM_BINARY
    assert res_ok.hypothesis.expected_direction == Direction.A_GREATER
    assert res_ok.hypothesis.source == "user"

    # Unsupported causal path
    res_causal = parse_nl_hypothesis(
        "Does smoking cause higher charges?", df, schema, llm=None, config=cfg
    )
    assert res_causal.status == "unsupported"

    # No columns found path
    res_none = parse_nl_hypothesis(
        "How does credit score relate to salary?", df, schema, llm=None, config=cfg
    )
    assert res_none.status == "no_columns_found"


def test_nl_parser_with_fake_llm() -> None:
    df, schema = _tiny_insurance()
    cfg = PipelineConfig()
    # Sorted eligible: age=c01, bmi=c02, charges=c03, region=c04, smoker=c05
    fake_llm = FakeLLM(
        {
            "NLHypothesisParse": {
                "status": "ok",
                "column_a_alias": "c05",
                "column_b_alias": "c03",
                "level_of_interest": "yes",
                "expected_direction_phrase": "greater",
                "clarification_question": None,
                "candidates": [],
                "unsupported_reason": None,
            }
        }
    )
    res = parse_nl_hypothesis("Do smokers pay more?", df, schema, llm=fake_llm, config=cfg)
    assert res.status == "ok"
    assert res.used_llm is True
    assert res.hypothesis is not None
    assert res.hypothesis.column_a == "charges"
    assert res.hypothesis.column_b == "smoker"
    assert res.hypothesis.relationship == RelationshipType.NUM_BINARY
    assert res.hypothesis.expected_direction == Direction.A_GREATER


def test_nl_parser_gold_set_accuracy_meets_acceptance_criterion() -> None:
    """Acceptance criterion: >= 85% column identification accuracy on tests/gold/nl_hypotheses.jsonl."""
    gold_path = Path("tests/gold/nl_hypotheses.jsonl")
    records = [
        json.loads(line)
        for line in gold_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(records) >= 40

    cache_df: dict[str, pd.DataFrame] = {}
    cache_schema: dict[str, dict[str, ColumnSchemaEntry]] = {}
    cache_cfg: dict[str, PipelineConfig] = {}

    ok_total = 0
    cols_correct = 0
    status_correct = 0

    for rec in records:
        ds = rec["dataset"]
        if ds not in cache_df:
            cfg_path = Path("configs/datasets") / f"{ds}.yaml"
            cache_cfg[ds] = load_config(dataset_config_path=cfg_path if cfg_path.exists() else None)
            cache_df[ds] = pd.read_csv(Path("data/cleaned") / f"{ds}_cleaned.csv")
            raw_schema = json.loads(
                (Path("outputs") / ds / "column_schema.json").read_text(encoding="utf-8")
            )
            cache_schema[ds] = {
                k: ColumnSchemaEntry.model_validate(v) for k, v in raw_schema.items()
            }

        outcome = parse_nl_hypothesis(
            text=rec["text"],
            df=cache_df[ds],
            schema=cache_schema[ds],
            llm=None,
            config=cache_cfg[ds],
        )
        if outcome.status == rec["expected_status"]:
            status_correct += 1
        if rec["expected_status"] == "ok":
            ok_total += 1
            if outcome.hypothesis is not None:
                got = sorted([outcome.hypothesis.column_a, outcome.hypothesis.column_b])
                if got == sorted(rec["expected_columns"]):
                    cols_correct += 1

    col_acc = cols_correct / ok_total
    status_acc = status_correct / len(records)
    assert col_acc >= 0.85, f"Column accuracy {col_acc:.2%} < 85%"
    assert status_acc >= 0.85, f"Status accuracy {status_acc:.2%} < 85%"

