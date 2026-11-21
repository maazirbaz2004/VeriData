"""CAT_CAT statistical tests: Chi-square, Fisher's exact, and Monte Carlo Chi-square (Section 4.4)."""

from __future__ import annotations

from typing import Any

import numpy as np
from scipy import stats as sp_stats

from veridata.config import PipelineConfig
from veridata.contracts.hypothesis import Direction
from veridata.contracts.results import EffectSize
from veridata.stats.effect_sizes import cramers_v_bias_corrected, table_2x2_metrics
from veridata.stats.types import PreparedData, RawTestOutput


def _contingency_descriptives(
    observed: np.ndarray,
    row_labels: list[str],
    col_labels: list[str],
    dropped_levels: list[str],
) -> dict[str, Any]:
    obs = np.asarray(observed, dtype=float)
    n = float(obs.sum())
    row_sums = obs.sum(axis=1, keepdims=True)
    col_sums = obs.sum(axis=0, keepdims=True)
    expected = (row_sums @ col_sums) / max(1.0, n)

    row_pcts = (obs / np.maximum(1.0, row_sums)) * 100.0
    # Adjusted standardized residuals: (O - E) / sqrt(E * (1 - p_r) * (1 - p_c))
    p_r = row_sums / max(1.0, n)
    p_c = col_sums / max(1.0, n)
    denom = np.sqrt(np.maximum(1e-12, expected * (1.0 - p_r) * (1.0 - p_c)))
    adj_resid = (obs - expected) / denom

    cells: list[dict[str, Any]] = []
    for i, r_lbl in enumerate(row_labels):
        for j, c_lbl in enumerate(col_labels):
            cells.append(
                {
                    "row": r_lbl,
                    "col": c_lbl,
                    "observed": int(obs[i, j]),
                    "expected": round(float(expected[i, j]), 2),
                    "row_pct": round(float(row_pcts[i, j]), 2),
                    "adj_residual": round(float(adj_resid[i, j]), 3),
                }
            )
    cells.sort(key=lambda c: (-abs(c["adj_residual"]), c["row"], c["col"]))

    desc: dict[str, Any] = {
        "row_labels": list(row_labels),
        "col_labels": list(col_labels),
        "observed": obs.astype(int).tolist(),
        "row_percentages": np.round(row_pcts, 2).tolist(),
        "min_expected_count": round(float(expected.min()), 4),
        "top_residual_cells": cells[:3],
        "dropped_levels": list(dropped_levels),
    }
    if obs.shape == (2, 2):
        desc.update(table_2x2_metrics(obs))
    return desc


def run_chi_square(
    prepared: PreparedData,
    config: PipelineConfig,
    rng: np.random.Generator,
) -> RawTestOutput:
    """Pearson chi-square test of independence with Bergsma bias-corrected Cramér's V."""
    _ = rng
    assert prepared.contingency is not None
    assert prepared.row_labels is not None and prepared.col_labels is not None
    obs = prepared.contingency

    chi2, p_val, dof, _ = sp_stats.chi2_contingency(obs, correction=config.stats.yates)
    v_bc, comp_w, df_star, mag = cramers_v_bias_corrected(obs)

    effect = EffectSize(
        name="cramers_v_bc",
        value=v_bc,
        ci_low=None,
        ci_high=None,
        ci_method=None,
        magnitude=mag,
        comparable_value=comp_w,
    )
    desc = _contingency_descriptives(
        obs, prepared.row_labels, prepared.col_labels, prepared.dropped_levels
    )
    desc["df_star"] = df_star

    return RawTestOutput(
        test_name="chi_square",
        statistic=float(chi2),
        df=float(dof),
        p_value=float(np.clip(p_val, 0.0, 1.0)),
        effect=effect,
        descriptives=desc,
        direction_observed=Direction.ANY,
    )


def run_fisher_exact(
    prepared: PreparedData,
    config: PipelineConfig,
    rng: np.random.Generator,
) -> RawTestOutput:
    """Two-sided Fisher's exact test for 2x2 tables."""
    _ = config, rng
    assert prepared.contingency is not None
    assert prepared.row_labels is not None and prepared.col_labels is not None
    obs = prepared.contingency

    res = sp_stats.fisher_exact(obs, alternative="two-sided")
    odds_ratio = float(res.statistic)
    p_val = float(np.clip(res.pvalue, 0.0, 1.0))

    v_bc, comp_w, df_star, mag = cramers_v_bias_corrected(obs)
    effect = EffectSize(
        name="cramers_v_bc",
        value=v_bc,
        ci_low=None,
        ci_high=None,
        ci_method=None,
        magnitude=mag,
        comparable_value=comp_w,
    )
    desc = _contingency_descriptives(
        obs, prepared.row_labels, prepared.col_labels, prepared.dropped_levels
    )
    desc["df_star"] = df_star
    desc["fisher_odds_ratio"] = odds_ratio

    return RawTestOutput(
        test_name="fisher_exact",
        statistic=odds_ratio,
        df=None,
        p_value=p_val,
        effect=effect,
        descriptives=desc,
        direction_observed=Direction.ANY,
    )


def run_monte_carlo_chi_square(
    prepared: PreparedData,
    config: PipelineConfig,
    rng: np.random.Generator,
) -> RawTestOutput:
    """Seeded permutation (Monte Carlo) chi-square test for sparse r x c tables."""
    assert prepared.contingency is not None
    assert prepared.row_labels is not None and prepared.col_labels is not None
    obs = prepared.contingency
    r, c = obs.shape
    n = int(obs.sum())
    chi2_obs, _, dof, expected = sp_stats.chi2_contingency(obs, correction=False)
    chi2_obs = float(chi2_obs)

    # Expand to integer codes for fast vectorized-friendly permutation
    row_codes = np.repeat(np.arange(r, dtype=np.int32), obs.sum(axis=1).astype(int))
    col_codes = np.concatenate(
        [np.repeat(np.arange(c, dtype=np.int32), obs[i].astype(int)) for i in range(r)]
    )

    n_perm = (
        min(999, config.stats.permutation_resamples)
        if config.stats.benchmark_fast_mode
        else config.stats.permutation_resamples
    )
    expected_safe = np.maximum(expected, 1e-12)
    exceed = 0
    for _ in range(n_perm):
        perm_c = rng.permutation(col_codes)
        idx = row_codes * c + perm_c
        counts = np.bincount(idx, minlength=r * c).reshape(r, c)
        chi2_sim = float(np.sum((counts - expected) ** 2 / expected_safe))
        if chi2_sim >= chi2_obs - 1e-12:
            exceed += 1

    p_val = float((1 + exceed) / (1 + n_perm))
    v_bc, comp_w, df_star, mag = cramers_v_bias_corrected(obs)

    effect = EffectSize(
        name="cramers_v_bc",
        value=v_bc,
        ci_low=None,
        ci_high=None,
        ci_method=None,
        magnitude=mag,
        comparable_value=comp_w,
    )
    desc = _contingency_descriptives(
        obs, prepared.row_labels, prepared.col_labels, prepared.dropped_levels
    )
    desc["df_star"] = df_star
    desc["permutation_resamples"] = n_perm

    return RawTestOutput(
        test_name="monte_carlo_chi_square",
        statistic=chi2_obs,
        df=float(dof),
        p_value=float(np.clip(p_val, 0.0, 1.0)),
        effect=effect,
        descriptives=desc,
        direction_observed=Direction.ANY,
    )

