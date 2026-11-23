"""Tests for the fixed tool registry, schema validations, and deduplication."""

from pathlib import Path
import pandas as pd
import pytest

from veridata.agent.tools import ToolRegistry
from veridata.config import PipelineConfig
from veridata.profiling import build_column_schema, profile_dataset
from veridata.validation.ledger import SessionLedger


@pytest.fixture
def test_setup(tmp_path):
    df = pd.DataFrame({
        "age": [25, 30, 45, 50, 22, 60, 35, 40],
        "charges": [1200.0, 1500.0, 4000.0, 4500.0, 1100.0, 5200.0, 2100.0, 3000.0],
        "smoker": ["no", "no", "yes", "yes", "no", "yes", "no", "no"],
        "region": ["north", "south", "north", "south", "east", "west", "east", "west"],
    })
    cfg = PipelineConfig(name="test_dataset")
    prof = profile_dataset(df, dataset_name="test_dataset")
    schema = build_column_schema(prof, cfg)
    ledger = SessionLedger(dataset_sha256="test_sha", alpha=0.05)
    tools = ToolRegistry(df, schema, cfg, ledger, session_dir=tmp_path)
    return tools, df, ledger


def test_describe_dataset(test_setup):
    tools, df, _ = test_setup
    res = tools.describe_dataset()
    assert res.ok
    assert res.tool == "describe_dataset"
    fact_keys = {f.key for f in res.facts}
    assert "n_rows" in fact_keys
    assert "n_cols" in fact_keys


def test_describe_column(test_setup):
    tools, _, _ = test_setup
    res = tools.describe_column("charges")
    assert res.ok
    assert len(res.charts) == 1
    assert Path(res.charts[0]).exists()

    # Invalid column
    res_bad = tools.describe_column("non_existent")
    assert not res_bad.ok
    assert "does not exist" in res_bad.error


def test_compare_groups_and_deduplication(test_setup):
    tools, _, ledger = test_setup
    res1 = tools.compare_groups("charges", "smoker")
    assert res1.ok
    assert res1.finding is not None
    assert len(ledger.entries) == 1
    assert res1.meta.get("is_new") is True

    # Call again with same pair: must deduplicate and not re-inflate family
    res2 = tools.compare_groups("charges", "smoker")
    assert res2.ok
    assert len(ledger.entries) == 1
    assert res2.meta.get("is_new") is False


def test_test_correlation(test_setup):
    tools, _, ledger = test_setup
    res = tools.test_correlation("age", "charges")
    assert res.ok
    assert res.finding is not None
    assert len(ledger.entries) == 1


def test_test_relationship_auto_dispatch(test_setup):
    tools, _, _ = test_setup
    # numeric vs numeric -> correlation
    res_corr = tools.test_relationship("age", "charges")
    assert res_corr.ok
    assert res_corr.tool == "test_correlation"

    # numeric vs binary -> compare_groups
    res_comp = tools.test_relationship("charges", "smoker")
    assert res_comp.ok
    assert res_comp.tool == "compare_groups"

    # categorical vs categorical -> association
    res_assoc = tools.test_relationship("smoker", "region")
    assert res_assoc.ok
    assert res_assoc.tool == "test_association"


def test_list_and_explain_findings(test_setup):
    tools, _, _ = test_setup
    tools.compare_groups("charges", "smoker")
    tools.test_correlation("age", "charges")

    list_res = tools.list_findings()
    assert list_res.ok
    assert len(list_res.table) == 2

    exp_res = tools.explain_finding("1")
    assert exp_res.ok
    assert "charges" in exp_res.meta["explanation"]


def test_ledger_status(test_setup):
    tools, _, _ = test_setup
    tools.compare_groups("charges", "smoker")
    status = tools.get_ledger_status()
    assert status.ok
    assert status.meta["total_tests"] == 1
