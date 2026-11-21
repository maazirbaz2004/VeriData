"""Reference-implementation, hand-computed micro cases, and invariance tests for Phase 3 stats."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest
from scipy import stats as sp_stats
from statsmodels.stats.oneway import anova_oneway

from veridata.config import PipelineConfig
from veridata.contracts.hypothesis import FeasibilityReport, Hypothesis, RelationshipType
from veridata.stats.effect_sizes import (
    cramers_v_bias_corrected,
    epsilon_squared_kruskal,
    eta_and_omega_squared,
    hedges_g,
    rank_biserial_and_ps,
    table_2x2_metrics,
)
from veridata.stats.registry import REGISTRY
from veridata.stats.runner import prepare_inputs, run_hypothesis


def _make_hyp(col_a: str, col_b: str, rel: RelationshipType) -> Hypothesis:
    return Hypothesis(
        id=f"test_{col_a}_{col_b}",
        column_a=col_a,
        column_b=col_b,
        relationship=rel,
        source="enumerated",
        feasibility=FeasibilityReport(feasible=True, reasons=[], n_pairwise_complete=100),
    )


def test_reference_scipy_and_statsmodels_exact_match() -> None:
    """Every test function must match scipy/statsmodels within 1e-10 (Section 10.1)."""
    rng = np.random.default_rng(2026)
    cfg = PipelineConfig()

    # 1. NUM_BINARY: Welch t & Mann-Whitney U
    g1 = rng.normal(10.0, 2.0, size=60)
    g2 = rng.normal(12.0, 3.5, size=50)
    df_nb = pd.DataFrame(
        {"y": np.concatenate([g1, g2]), "grp": ["A"] * 60 + ["B"] * 50}
    )
    prep_nb = prepare_inputs(_make_hyp("y", "grp", RelationshipType.NUM_BINARY), df_nb, cfg)

    out_wt = REGISTRY["welch_t"].run(prep_nb, cfg, np.random.default_rng(1))
    ref_wt = sp_stats.ttest_ind(g1, g2, equal_var=False, alternative="two-sided")
    assert out_wt.statistic == pytest.approx(ref_wt.statistic, abs=1e-10)
    assert out_wt.p_value == pytest.approx(ref_wt.pvalue, abs=1e-10)

    out_mwu = REGISTRY["mann_whitney_u"].run(prep_nb, cfg, np.random.default_rng(1))
    ref_mwu = sp_stats.mannwhitneyu(g1, g2, alternative="two-sided", method="auto")
    assert out_mwu.statistic == pytest.approx(ref_mwu.statistic, abs=1e-10)
    assert out_mwu.p_value == pytest.approx(ref_mwu.pvalue, abs=1e-10)

    # 2. NUM_CATEGORICAL: Welch ANOVA & Kruskal-Wallis
    c1 = rng.normal(5.0, 1.0, size=40)
    c2 = rng.normal(6.5, 2.0, size=45)
    c3 = rng.normal(8.0, 1.5, size=35)
    df_nc = pd.DataFrame(
        {"y": np.concatenate([c1, c2, c3]), "cat": ["G1"] * 40 + ["G2"] * 45 + ["G3"] * 35}
    )
    prep_nc = prepare_inputs(_make_hyp("y", "cat", RelationshipType.NUM_CATEGORICAL), df_nc, cfg)

    out_wa = REGISTRY["welch_anova"].run(prep_nc, cfg, np.random.default_rng(1))
    ref_wa = anova_oneway(
        np.concatenate([c1, c2, c3]),
        np.array([0] * 40 + [1] * 45 + [2] * 35),
        use_var="unequal",
        welch_correction=True,
    )
    assert out_wa.statistic == pytest.approx(ref_wa.statistic, abs=1e-10)
    assert out_wa.p_value == pytest.approx(ref_wa.pvalue, abs=1e-10)

    out_kw = REGISTRY["kruskal_wallis"].run(prep_nc, cfg, np.random.default_rng(1))
    ref_kw = sp_stats.kruskal(c1, c2, c3)
    assert out_kw.statistic == pytest.approx(ref_kw.statistic, abs=1e-10)
    assert out_kw.p_value == pytest.approx(ref_kw.pvalue, abs=1e-10)

    # 3. NUM_NUM: Pearson & Spearman
    x = rng.normal(0.0, 1.0, size=80)
    y = 0.6 * x + rng.normal(0.0, 0.8, size=80)
    df_nn = pd.DataFrame({"x": x, "y": y})
    prep_nn = prepare_inputs(_make_hyp("x", "y", RelationshipType.NUM_NUM), df_nn, cfg)

    out_p = REGISTRY["pearson"].run(prep_nn, cfg, np.random.default_rng(1))
    ref_p = sp_stats.pearsonr(x, y)
    assert out_p.statistic == pytest.approx(ref_p.statistic, abs=1e-10)
    assert out_p.p_value == pytest.approx(ref_p.pvalue, abs=1e-10)

    out_s = REGISTRY["spearman"].run(prep_nn, cfg, np.random.default_rng(1))
    ref_s = sp_stats.spearmanr(x, y)
    assert out_s.statistic == pytest.approx(ref_s.statistic, abs=1e-10)
    assert out_s.p_value == pytest.approx(ref_s.pvalue, abs=1e-10)

    # 4. CAT_CAT: Chi-square & Fisher exact
    obs_2x2 = np.array([[30, 10], [15, 25]])
    rows_cc, cols_cc = [], []
    for i, rl in enumerate(["R0", "R1"]):
        for j, cl in enumerate(["C0", "C1"]):
            rows_cc.extend([rl] * int(obs_2x2[i, j]))
            cols_cc.extend([cl] * int(obs_2x2[i, j]))
    df_cc = pd.DataFrame({"a": rows_cc, "b": cols_cc})
    prep_cc = prepare_inputs(_make_hyp("a", "b", RelationshipType.CAT_CAT), df_cc, cfg)

    out_chi = REGISTRY["chi_square"].run(prep_cc, cfg, np.random.default_rng(1))
    ref_chi = sp_stats.chi2_contingency(obs_2x2, correction=False)
    assert out_chi.statistic == pytest.approx(ref_chi[0], abs=1e-10)
    assert out_chi.p_value == pytest.approx(ref_chi[1], abs=1e-10)

    out_f = REGISTRY["fisher_exact"].run(prep_cc, cfg, np.random.default_rng(1))
    ref_f = sp_stats.fisher_exact(obs_2x2, alternative="two-sided")
    assert out_f.statistic == pytest.approx(ref_f.statistic, abs=1e-10)
    assert out_f.p_value == pytest.approx(ref_f.pvalue, abs=1e-10)


def test_hand_computed_micro_cases() -> None:
    """Hand-computed analytical verification (Section 10.2)."""
    # 1. Hedges' g on [4,5,6,7,8] vs [1,2,3,4,5]:
    #    mean1=6, mean2=3, diff=3; s1^2 = s2^2 = 2.5 -> s_pooled = sqrt(2.5)
    #    d = 3 / sqrt(2.5) = 1.8973665961; df = 8 -> J = 1 - 3/(4*8 - 1) = 28/31 = 0.9032258065
    #    g = 1.8973665961 * (28/31) = 1.7137504739
    g_val, diff, mag = hedges_g(np.array([4, 5, 6, 7, 8]), np.array([1, 2, 3, 4, 5]))
    expected_g = (3.0 / math.sqrt(2.5)) * (1.0 - 3.0 / 31.0)
    assert diff == pytest.approx(3.0, abs=1e-12)
    assert g_val == pytest.approx(expected_g, abs=1e-10)
    assert mag == "large"

    # 2. Rank-biserial from known U1 = 18 with n1=4, n2=5 (n1*n2 = 20):
    #    ps = 18/20 = 0.90; r_rb = 2*0.90 - 1 = 0.80
    r_rb, ps, mag_rb = rank_biserial_and_ps(18.0, 4, 5)
    assert ps == pytest.approx(0.90, abs=1e-12)
    assert r_rb == pytest.approx(0.80, abs=1e-12)
    assert mag_rb == "large"

    # 3. 2x2 Odds Ratio and Woolf 95% CI on [[20, 10], [10, 30]]:
    #    OR = (20*30)/(10*10) = 6.0
    #    se(log OR) = sqrt(1/20 + 1/10 + 1/10 + 1/30) = sqrt(17/60) = 0.5322906474
    m2x2 = table_2x2_metrics(np.array([[20, 10], [10, 30]]))
    z = float(sp_stats.norm.ppf(0.975))
    se_lor = math.sqrt(1 / 20 + 1 / 10 + 1 / 10 + 1 / 30)
    assert m2x2["odds_ratio"] == pytest.approx(6.0, abs=1e-6)
    assert m2x2["odds_ratio_ci_low"] == pytest.approx(math.exp(math.log(6.0) - z * se_lor), abs=1e-5)
    assert m2x2["odds_ratio_ci_high"] == pytest.approx(math.exp(math.log(6.0) + z * se_lor), abs=1e-5)

    # 4. Bergsma (2013) bias-corrected Cramér's V on 3x3 table [[30, 5, 5], [5, 30, 5], [5, 5, 30]]:
    #    n = 120, chi2 = 93.75, phi2 = 93.75/120 = 0.78125
    #    phi2_tilde = 0.78125 - (2*2)/119 = 0.7476365546
    #    r_tilde = k_tilde = 3 - 4/119 = 2.9663865546 -> denom = 1.9663865546
    #    V_bc = sqrt(0.7476365546 / 1.9663865546) = 0.6166097367
    obs_3x3 = np.array([[30, 5, 5], [5, 30, 5], [5, 5, 30]])
    v_bc, comp_w, df_star, _ = cramers_v_bias_corrected(obs_3x3)
    chi2_hand = 93.75
    phi2_t = chi2_hand / 120.0 - 4.0 / 119.0
    r_t = 3.0 - 4.0 / 119.0
    expected_v = math.sqrt(phi2_t / (r_t - 1.0))
    assert df_star == 2
    assert v_bc == pytest.approx(expected_v, abs=1e-6)
    assert comp_w == pytest.approx(expected_v * math.sqrt(2.0), abs=1e-6)

    # 5. Epsilon-squared from known H = 12.0, n = 41 -> 12 / 40 = 0.30
    eps, mag_e = epsilon_squared_kruskal(12.0, 41)
    assert eps == pytest.approx(0.30, abs=1e-12)
    assert mag_e == "large"

    # 6. Eta-squared on identical-variance groups [0,0,0], [2,2,2] -> SS_between = SS_total -> 1.0
    eta, _, _ = eta_and_omega_squared([np.array([0.0, 0.0, 0.0]), np.array([2.0, 2.0, 2.0])])
    assert eta == pytest.approx(1.0, abs=1e-12)


def test_row_shuffle_and_positive_scaling_invariance() -> None:
    """Shuffling rows or multiplying numeric columns by a positive constant preserves p-values."""
    rng = np.random.default_rng(99)
    n = 100
    x = rng.normal(10.0, 3.0, size=n)
    y = 0.5 * x + rng.normal(0.0, 2.0, size=n)
    grp = np.array(["A"] * 50 + ["B"] * 50)
    df = pd.DataFrame({"x": x, "y": y, "grp": grp})
    cfg = PipelineConfig()

    h_nn = _make_hyp("x", "y", RelationshipType.NUM_NUM)
    h_nb = _make_hyp("y", "grp", RelationshipType.NUM_BINARY)

    r_nn = run_hypothesis(h_nn, df, cfg, stage="A")
    r_nb = run_hypothesis(h_nb, df, cfg, stage="A")

    # Row shuffle
    df_shuf = df.sample(frac=1.0, random_state=123).reset_index(drop=True)
    r_nn_shuf = run_hypothesis(h_nn, df_shuf, cfg, stage="A")
    r_nb_shuf = run_hypothesis(h_nb, df_shuf, cfg, stage="A")
    assert r_nn.p_value == pytest.approx(r_nn_shuf.p_value, abs=1e-12)
    assert r_nb.p_value == pytest.approx(r_nb_shuf.p_value, abs=1e-12)

    # Positive constant scaling (x7.5)
    df_scaled = df.copy()
    df_scaled["x"] = df_scaled["x"] * 7.5
    df_scaled["y"] = df_scaled["y"] * 7.5
    r_nn_sc = run_hypothesis(h_nn, df_scaled, cfg, stage="A")
    r_nb_sc = run_hypothesis(h_nb, df_scaled, cfg, stage="A")
    assert r_nn.p_value == pytest.approx(r_nn_sc.p_value, abs=1e-10)
    assert r_nb.p_value == pytest.approx(r_nb_sc.p_value, abs=1e-10)

