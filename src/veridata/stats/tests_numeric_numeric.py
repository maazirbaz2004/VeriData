"""NUM_NUM statistical tests: Pearson r and Spearman rho (Phase 3 Section 4.3)."""

from __future__ import annotations

from typing import Any

import numpy as np
from scipy import stats as sp_stats

from veridata.config import PipelineConfig
from veridata.contracts.hypothesis import Direction
from veridata.contracts.results import EffectSize
from veridata.stats.assumptions import check_linearity_advisory, check_ties_rate
from veridata.stats.effect_sizes import classify_correlation
from veridata.stats.intervals import pearson_r_ci, spearman_rho_ci_fisher
from veridata.stats.types import PreparedData, RawTestOutput


def _ols_slope_intercept(x: np.ndarray, y: np.ndarray) -> tuple[float | None, float | None]:
    vx = float(np.var(x))
    if vx <= 0.0:
        return None, None
    slope = float(np.cov(x, y, ddof=0)[0, 1] / vx)
    intercept = float(np.mean(y) - slope * np.mean(x))
    return slope, intercept


def run_pearson(
    prepared: PreparedData,
    config: PipelineConfig,
    rng: np.random.Generator,
) -> RawTestOutput:
    """Two-sided Pearson correlation with Fisher-z CI and advisory linearity check."""
    _ = config, rng
    assert prepared.x is not None and prepared.y is not None
    x, y = prepared.x, prepared.y
    n = len(x)

    res = sp_stats.pearsonr(x, y)
    r_val = float(np.clip(res.statistic, -1.0, 1.0))
    p_val = float(np.clip(res.pvalue, 0.0, 1.0))

    ci_lo, ci_hi, ci_method = pearson_r_ci(r_val, n)
    lin_check = check_linearity_advisory(x, y)
    slope, intercept = _ols_slope_intercept(x, y)

    direction = (
        Direction.POSITIVE
        if r_val > 0
        else (Direction.NEGATIVE if r_val < 0 else Direction.ANY)
    )
    effect = EffectSize(
        name="pearson_r",
        value=r_val,
        ci_low=ci_lo,
        ci_high=ci_hi,
        ci_method=ci_method,
        magnitude=classify_correlation(abs(r_val)),
        comparable_value=abs(r_val),
    )

    descriptives: dict[str, Any] = {
        "n": n,
        "mean_a": float(np.mean(x)),
        "sd_a": float(np.std(x, ddof=1)),
        "mean_b": float(np.mean(y)),
        "sd_b": float(np.std(y, ddof=1)),
        "pearson_r": r_val,
        "ols_slope": slope,
        "ols_intercept": intercept,
    }
    return RawTestOutput(
        test_name="pearson",
        statistic=r_val,
        df=float(n - 2),
        p_value=p_val,
        effect=effect,
        descriptives=descriptives,
        direction_observed=direction,
        extra_assumptions=[lin_check],
    )


def run_spearman(
    prepared: PreparedData,
    config: PipelineConfig,
    rng: np.random.Generator,
) -> RawTestOutput:
    """Two-sided Spearman rank correlation with tie diagnostics."""
    _ = rng
    assert prepared.x is not None and prepared.y is not None
    x, y = prepared.x, prepared.y
    n = len(x)

    res = sp_stats.spearmanr(x, y)
    rho = float(np.clip(res.statistic, -1.0, 1.0))
    p_val = float(np.clip(res.pvalue, 0.0, 1.0))

    ci_lo: float | None = None
    ci_hi: float | None = None
    ci_method: str | None = None
    if config.stats.benchmark_fast_mode:
        ci_lo, ci_hi, ci_method = spearman_rho_ci_fisher(rho, n)

    slope, intercept = _ols_slope_intercept(x, y)
    ties_a = check_ties_rate(x)
    ties_b = check_ties_rate(y)

    direction = (
        Direction.POSITIVE
        if rho > 0
        else (Direction.NEGATIVE if rho < 0 else Direction.ANY)
    )
    effect = EffectSize(
        name="spearman_rho",
        value=rho,
        ci_low=ci_lo,
        ci_high=ci_hi,
        ci_method=ci_method,
        magnitude=classify_correlation(abs(rho)),
        comparable_value=abs(rho),
    )

    descriptives: dict[str, Any] = {
        "n": n,
        "median_a": float(np.median(x)),
        "median_b": float(np.median(y)),
        "spearman_rho": rho,
        "ties_rate_a": round(ties_a, 4),
        "ties_rate_b": round(ties_b, 4),
        "ols_slope": slope,
        "ols_intercept": intercept,
    }
    return RawTestOutput(
        test_name="spearman",
        statistic=rho,
        df=float(n - 2),
        p_value=p_val,
        effect=effect,
        descriptives=descriptives,
        direction_observed=direction,
    )

