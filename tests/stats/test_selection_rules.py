"""Selection-rule tests and no-LLM import lint for Phase 3 stats/ and validation/."""

from __future__ import annotations

import ast
from pathlib import Path

import numpy as np
import pandas as pd

from veridata.config import PipelineConfig
from veridata.contracts.hypothesis import FeasibilityReport, Hypothesis, RelationshipType
from veridata.stats.runner import run_hypothesis


def _hyp(col_a: str, col_b: str, rel: RelationshipType) -> Hypothesis:
    return Hypothesis(
        id=f"sel_{col_a}_{col_b}",
        column_a=col_a,
        column_b=col_b,
        relationship=rel,
        source="enumerated",
        feasibility=FeasibilityReport(feasible=True, reasons=[], n_pairwise_complete=100),
    )


def test_selection_rules_all_branches() -> None:
    rng = np.random.default_rng(7)
    cfg = PipelineConfig()

    # 1. Normal NUM_BINARY -> welch_t
    df_norm = pd.DataFrame(
        {"y": np.concatenate([rng.normal(0, 1, 35), rng.normal(1, 1, 35)]), "g": ["A"] * 35 + ["B"] * 35}
    )
    r1 = run_hypothesis(_hyp("y", "g", RelationshipType.NUM_BINARY), df_norm, cfg)
    assert r1.test_name == "welch_t"
    assert r1.fallback_used is False
    assert len(r1.selection_trace) >= 1

    # 2. Skewed small-n NUM_BINARY -> mann_whitney_u
    df_skew_small = pd.DataFrame(
        {
            "y": np.concatenate([rng.lognormal(0, 2.0, 20), rng.lognormal(1, 2.0, 20)]),
            "g": ["A"] * 20 + ["B"] * 20,
        }
    )
    r2 = run_hypothesis(_hyp("y", "g", RelationshipType.NUM_BINARY), df_skew_small, cfg)
    assert r2.test_name == "mann_whitney_u"
    assert r2.fallback_used is True

    # 3. Zero-variance group NUM_BINARY -> mann_whitney_u
    df_zvar = pd.DataFrame(
        {"y": np.concatenate([np.zeros(20), rng.normal(1, 1, 20)]), "g": ["A"] * 20 + ["B"] * 20}
    )
    r3 = run_hypothesis(_hyp("y", "g", RelationshipType.NUM_BINARY), df_zvar, cfg)
    assert r3.test_name == "mann_whitney_u"
    assert r3.fallback_used is True

    # 4. Normal NUM_CATEGORICAL -> welch_anova; skewed small-n -> kruskal_wallis
    df_nc_norm = pd.DataFrame(
        {
            "y": np.concatenate([rng.normal(0, 1, 30), rng.normal(1, 1, 30), rng.normal(2, 1, 30)]),
            "c": ["A"] * 30 + ["B"] * 30 + ["C"] * 30,
        }
    )
    r4 = run_hypothesis(_hyp("y", "c", RelationshipType.NUM_CATEGORICAL), df_nc_norm, cfg)
    assert r4.test_name == "welch_anova"

    df_nc_skew = pd.DataFrame(
        {
            "y": np.concatenate([rng.lognormal(0, 2.2, 20), rng.lognormal(0, 2.2, 20), rng.lognormal(1, 2.2, 20)]),
            "c": ["A"] * 20 + ["B"] * 20 + ["C"] * 20,
        }
    )
    r5 = run_hypothesis(_hyp("y", "c", RelationshipType.NUM_CATEGORICAL), df_nc_skew, cfg)
    assert r5.test_name == "kruskal_wallis"
    assert r5.fallback_used is True

    # 5. NUM_NUM: normal -> pearson; small n (<30) -> spearman; heavy outliers -> spearman
    df_nn_norm = pd.DataFrame({"x": rng.normal(0, 1, 80), "y": rng.normal(0, 1, 80)})
    r6 = run_hypothesis(_hyp("x", "y", RelationshipType.NUM_NUM), df_nn_norm, cfg)
    assert r6.test_name == "pearson"

    df_nn_small = pd.DataFrame({"x": rng.normal(0, 1, 25), "y": rng.normal(0, 1, 25)})
    r7 = run_hypothesis(_hyp("x", "y", RelationshipType.NUM_NUM), df_nn_small, cfg)
    assert r7.test_name == "spearman"

    x_out = np.concatenate([rng.normal(0, 1, 70), np.full(10, 100.0)])
    y_out = rng.normal(0, 1, 80)
    r8 = run_hypothesis(_hyp("x", "y", RelationshipType.NUM_NUM), pd.DataFrame({"x": x_out, "y": y_out}), cfg)
    assert r8.test_name == "spearman"

    # 6. CAT_CAT: sparse 2x2 -> fisher_exact; sparse 4x4 -> monte_carlo_chi_square
    df_f = pd.DataFrame({"a": ["A"] * 12 + ["B"] * 12, "b": ["X"] * 10 + ["Y"] * 14})
    r9 = run_hypothesis(_hyp("a", "b", RelationshipType.CAT_CAT), df_f, cfg)
    assert r9.test_name == "fisher_exact"

    # Sparse 4x4 where >= 80% of cells have expected < 5 (n=40 across 16 cells -> mean expected 2.5)
    df_mc = pd.DataFrame(
        {
            "a": ["R1"] * 10 + ["R2"] * 10 + ["R3"] * 10 + ["R4"] * 10,
            "b": (["C1"] * 10 + ["C2"] * 10 + ["C3"] * 10 + ["C4"] * 10),
        }
    )
    cfg_fast = PipelineConfig()
    cfg_fast.stats.benchmark_fast_mode = True
    r10 = run_hypothesis(_hyp("a", "b", RelationshipType.CAT_CAT), df_mc, cfg_fast)
    assert r10.test_name == "monte_carlo_chi_square"
    assert r10.fallback_used is True


def test_no_llm_imports_in_stats_or_validation() -> None:
    """Acceptance criterion: zero imports of LLM clients anywhere under stats/ or validation/."""
    src_root = Path(__file__).resolve().parents[2] / "src" / "veridata"
    forbidden = ("anthropic", "veridata.agent")
    for sub in ("stats", "validation"):
        for py_file in (src_root / sub).rglob("*.py"):
            tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        assert not alias.name.startswith(forbidden), f"Forbidden import {alias.name} in {py_file}"
                elif isinstance(node, ast.ImportFrom) and node.module:
                    assert not node.module.startswith(forbidden), f"Forbidden import {node.module} in {py_file}"

