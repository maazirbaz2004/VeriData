"""End-to-end Phase 2 -> Phase 3, pure-noise FWER smoke test, and calibration tests."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from veridata.config import PipelineConfig, load_config
from veridata.contracts.hypothesis import FeasibilityReport, Hypothesis, RelationshipType
from veridata.hypotheses.generator import generate_hypotheses
from veridata.schemas import ColumnRole, ColumnSchemaEntry, SemanticType
from veridata.stats.runner import run_all, run_hypothesis


def test_end_to_end_insurance_and_noise_rejection(tmp_path: Path) -> None:
    cfg = load_config(dataset_config_path=Path("configs/datasets/insurance.yaml"))
    df = pd.read_csv("data/cleaned/insurance_cleaned.csv")
    raw_schema = json.loads(Path("outputs/insurance/column_schema.json").read_text(encoding="utf-8"))
    schema = {k: ColumnSchemaEntry.model_validate(v) for k, v in raw_schema.items()}

    # Inject a pure-noise column to verify it is not accepted
    rng = np.random.default_rng(2026)
    df["pure_noise"] = rng.normal(0.0, 1.0, size=len(df))
    schema["pure_noise"] = ColumnSchemaEntry(
        semantic_type=SemanticType.NUMERIC_CONTINUOUS,
        role=ColumnRole.FEATURE,
        n_unique=len(df),
        pct_missing=0.0,
    )

    hset = generate_hypotheses(df, schema, None, cfg, llm=None, target="charges", dataset_name="insurance")
    out = run_all(hset, df, cfg, n_jobs=1, stage_b=True, out_dir=tmp_path / "insurance_p3")

    assert out.summary["m_tested"] == hset.manifest.n_in_family_planned
    assert (tmp_path / "insurance_p3" / "findings.json").exists()
    assert (tmp_path / "insurance_p3" / "validation_summary.md").exists()

    # Every accepted has 0 reasons; every rejected has >= 1 reason
    for dec in out.decisions:
        if dec.accepted:
            assert dec.reasons == []
        else:
            assert len(dec.reasons) >= 1

    accepted_pairs = {
        frozenset([f.hypothesis.column_a, f.hypothesis.column_b]): f
        for f in out.findings
        if f.decision.accepted
    }
    assert frozenset(["charges", "smoker"]) in accepted_pairs
    assert accepted_pairs[frozenset(["charges", "smoker"])].test.effect.magnitude == "large"
    assert frozenset(["age", "charges"]) in accepted_pairs
    # Pure noise should not be accepted with charges
    assert frozenset(["charges", "pure_noise"]) not in accepted_pairs


def test_shuffled_insurance_pure_noise_fwer_smoke() -> None:
    """Acceptance criterion: independently shuffled insurance columns yield 0 accepted findings in >= 95% of seeds."""
    cfg = load_config(dataset_config_path=Path("configs/datasets/insurance.yaml"))
    cfg.stats.benchmark_fast_mode = True
    df_orig = pd.read_csv("data/cleaned/insurance_cleaned.csv")
    raw_schema = json.loads(Path("outputs/insurance/column_schema.json").read_text(encoding="utf-8"))
    schema = {k: ColumnSchemaEntry.model_validate(v) for k, v in raw_schema.items()}
    hset = generate_hypotheses(df_orig, schema, None, cfg, llm=None, target="charges", dataset_name="insurance")

    n_seeds = 30
    zero_count = 0
    for seed in range(n_seeds):
        rng = np.random.default_rng(10_000 + seed)
        df_perm = pd.DataFrame({c: rng.permutation(df_orig[c].to_numpy()) for c in df_orig.columns})
        out = run_all(hset, df_perm, cfg, n_jobs=1, stage_b=False)
        if out.summary["n_accepted"] == 0:
            zero_count += 1

    assert (zero_count / n_seeds) >= 0.95, f"Zero-discovery rate {zero_count}/{n_seeds} < 95%"


def test_null_calibration_smoke_selected_tests() -> None:
    """Smoke Type-I error calibration under null for normal & lognormal at alpha=0.05."""
    cfg = PipelineConfig()
    rng = np.random.default_rng(555)
    h_nb = Hypothesis(
        id="cal_nb",
        column_a="y",
        column_b="g",
        relationship=RelationshipType.NUM_BINARY,
        source="enumerated",
        feasibility=FeasibilityReport(feasible=True, reasons=[], n_pairwise_complete=60),
    )

    n_trials = 400
    for dist_name in ("normal", "lognormal"):
        rejects = 0
        for _ in range(n_trials):
            if dist_name == "normal":
                y = rng.normal(0.0, 1.0, size=60)
            else:
                y = rng.lognormal(0.0, 1.5, size=60)
            df = pd.DataFrame({"y": y, "g": ["A"] * 30 + ["B"] * 30})
            res = run_hypothesis(h_nb, df, cfg, stage="A")
            if res.p_value is not None and res.p_value < 0.05:
                rejects += 1
        rate = rejects / n_trials
        # Binomial 99% interval for p=0.05, N=400 is ~[0.022, 0.082]
        assert 0.02 <= rate <= 0.085, f"Null rejection rate for {dist_name} out of bounds: {rate:.3f}"


@pytest.mark.slow
def test_analytic_ci_coverage_slow() -> None:
    """Section 10.5: 95% analytic CI coverage for Hedges' g & Pearson r within [0.92, 0.98]."""
    from veridata.stats.effect_sizes import hedges_g
    from veridata.stats.intervals import hedges_g_ci, pearson_r_ci

    rng = np.random.default_rng(12345)
    n_sim = 1000
    true_d = 0.5
    covered_g = 0
    for _ in range(n_sim):
        g1 = rng.normal(true_d, 1.0, size=50)
        g2 = rng.normal(0.0, 1.0, size=50)
        g, _, _ = hedges_g(g1, g2)
        lo, hi, _ = hedges_g_ci(g, 50, 50)
        if lo is not None and hi is not None and lo <= true_d <= hi:
            covered_g += 1
    assert 0.92 <= (covered_g / n_sim) <= 0.98

    true_r = 0.4
    covered_r = 0
    for _ in range(n_sim):
        x = rng.normal(0.0, 1.0, size=80)
        y = true_r * x + np.sqrt(1 - true_r**2) * rng.normal(0.0, 1.0, size=80)
        r = float(np.corrcoef(x, y)[0, 1])
        lo, hi, _ = pearson_r_ci(r, 80)
        if lo is not None and hi is not None and lo <= true_r <= hi:
            covered_r += 1
    assert 0.92 <= (covered_r / n_sim) <= 0.98

