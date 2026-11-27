"""Tests for independent_recompute (AST import isolation, scipy agreement, corruption catch)."""

from __future__ import annotations

import ast
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from scipy import stats as sp_stats

from veridata.evaluation import independent_recompute as ir


def test_independent_recompute_has_zero_circular_imports() -> None:
    path = Path("src/veridata/evaluation/independent_recompute.py")
    tree = ast.parse(path.read_text(encoding="utf-8"))
    forbidden_prefixes = ("veridata.stats", "veridata.validation", "veridata.reporting", "veridata.agent")
    imported: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.append(node.module)
    for mod in imported:
        assert not mod.startswith(forbidden_prefixes), f"Circular import forbidden in E4: {mod}"


def test_recompute_matches_scipy_and_hand_computed() -> None:
    rng = np.random.default_rng(123)
    x = rng.normal(10.0, 2.0, size=80)
    y = 2.0 * x + rng.normal(0.0, 1.0, size=80)
    grp = np.array(["A"] * 40 + ["B"] * 40)
    val = np.concatenate([rng.normal(5.0, 1.0, 40), rng.normal(6.5, 1.2, 40)])
    df = pd.DataFrame({"x": x, "y": y, "grp": grp, "val": val})

    res_num = ir.recompute_pair_stats(df, "x", "y", test_name="pearson", relationship="numeric_vs_numeric")
    ref_r, ref_p = sp_stats.pearsonr(x, y)
    assert res_num["ok"]
    assert res_num["n_used"] == 80
    assert res_num["pearson_r"] == pytest.approx(float(ref_r))
    assert res_num["p_value"] == pytest.approx(float(ref_p))

    res_grp = ir.recompute_pair_stats(df, "val", "grp", test_name="welch_t", relationship="numeric_vs_binary")
    ref_t, ref_tp = sp_stats.ttest_ind(val[:40], val[40:], equal_var=False)
    assert res_grp["ok"]
    assert res_grp["p_value"] == pytest.approx(float(ref_tp))
    assert res_grp["statistic"] == pytest.approx(float(ref_t))

    # Hand-computed Hedges' g check on tiny arrays: [1, 2, 3] vs [4, 5, 6]
    # means: 2 vs 5 (diff = -3), vars: 1 vs 1, sp = 1, df = 4, J = 1 - 3/15 = 0.8 => g = -2.4
    g_hand = ir._hedges_g_plain(np.array([1.0, 2.0, 3.0]), np.array([4.0, 5.0, 6.0]))
    assert g_hand == pytest.approx(-2.4)


def test_verify_veridata_finding_and_catch_corruption() -> None:
    df = pd.DataFrame({"a": np.arange(50, dtype=float), "b": np.arange(50, dtype=float) * 2.0 + 1.0})
    r_val, p_val = sp_stats.pearsonr(df["a"], df["b"])
    finding = {
        "hypothesis": {"column_a": "a", "column_b": "b", "relationship": "numeric_vs_numeric"},
        "test": {
            "status": "ok",
            "test_name": "pearson",
            "n_used": 50,
            "p_value": float(p_val),
            "effect": {"name": "pearson_r", "value": float(r_val)},
        },
    }
    ok_res = ir.verify_veridata_finding_independently(finding, df)
    assert ok_res["ok"] is True

    corrupted = {
        "hypothesis": {"column_a": "a", "column_b": "b", "relationship": "numeric_vs_numeric"},
        "test": {
            "status": "ok",
            "test_name": "pearson",
            "n_used": 50,
            "p_value": 0.42,
            "effect": {"name": "pearson_r", "value": 0.12},
        },
    }
    bad_res = ir.verify_veridata_finding_independently(corrupted, df)
    assert bad_res["ok"] is False
    assert len(bad_res["mismatches"]) == 2
