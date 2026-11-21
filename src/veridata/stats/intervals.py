"""Analytic and seeded bootstrap confidence intervals for Phase 3 (Section 6)."""

from __future__ import annotations

from typing import Callable

import numpy as np
from scipy import stats as sp_stats


def hedges_g_ci(
    g: float,
    n1: int,
    n2: int,
    alpha: float = 0.05,
) -> tuple[float | None, float | None, str]:
    """Analytic Hedges & Olkin SE confidence interval for Hedges' g."""
    df = n1 + n2 - 2
    if n1 < 2 or n2 < 2 or df <= 0 or not np.isfinite(g):
        return None, None, "analytic_hedges_olkin"
    se = float(np.sqrt((n1 + n2) / (n1 * n2) + (g**2) / (2.0 * df)))
    z = float(sp_stats.norm.ppf(1.0 - alpha / 2.0))
    return float(g - z * se), float(g + z * se), "analytic_hedges_olkin"


def welch_mean_diff_ci(
    g1: np.ndarray,
    g2: np.ndarray,
    alpha: float = 0.05,
) -> tuple[float | None, float | None, float | None]:
    """Welch-Satterthwaite confidence interval for the raw difference in means (g1 - g2)."""
    x1 = np.asarray(g1, dtype=float)
    x2 = np.asarray(g2, dtype=float)
    n1, n2 = len(x1), len(x2)
    if n1 < 2 or n2 < 2:
        return None, None, None
    v1 = float(np.var(x1, ddof=1))
    v2 = float(np.var(x2, ddof=1))
    se_sq = v1 / n1 + v2 / n2
    if se_sq <= 0.0:
        diff = float(np.mean(x1) - np.mean(x2))
        return diff, diff, float(n1 + n2 - 2)
    num = se_sq**2
    den = (v1 / n1) ** 2 / (n1 - 1) + (v2 / n2) ** 2 / (n2 - 1)
    df = float(num / den) if den > 0 else float(n1 + n2 - 2)
    diff = float(np.mean(x1) - np.mean(x2))
    t_crit = float(sp_stats.t.ppf(1.0 - alpha / 2.0, df))
    se = float(np.sqrt(se_sq))
    return float(diff - t_crit * se), float(diff + t_crit * se), df


def pearson_r_ci(
    r: float,
    n: int,
    alpha: float = 0.05,
) -> tuple[float | None, float | None, str]:
    """Fisher z-transform confidence interval for Pearson r."""
    if n <= 3 or not np.isfinite(r):
        return None, None, "fisher_z"
    if abs(r) >= 1.0 - 1e-12:
        return float(r), float(r), "fisher_z"
    z_r = float(np.arctanh(r))
    se = float(1.0 / np.sqrt(n - 3.0))
    z_crit = float(sp_stats.norm.ppf(1.0 - alpha / 2.0))
    lo = float(np.tanh(z_r - z_crit * se))
    hi = float(np.tanh(z_r + z_crit * se))
    return lo, hi, "fisher_z"


def spearman_rho_ci_fisher(
    rho: float,
    n: int,
    alpha: float = 0.05,
) -> tuple[float | None, float | None, str]:
    """Fieller et al. Fisher-z approximation CI for Spearman rho."""
    if n <= 3 or not np.isfinite(rho):
        return None, None, "fisher_z_fieller"
    if abs(rho) >= 1.0 - 1e-12:
        return float(rho), float(rho), "fisher_z_fieller"
    z_r = float(np.arctanh(rho))
    se = float(np.sqrt((1.0 + (rho**2) / 2.0) / (n - 3.0)))
    z_crit = float(sp_stats.norm.ppf(1.0 - alpha / 2.0))
    lo = float(np.tanh(z_r - z_crit * se))
    hi = float(np.tanh(z_r + z_crit * se))
    return lo, hi, "fisher_z_fieller"


def bootstrap_ci_two_group(
    g1: np.ndarray,
    g2: np.ndarray,
    stat_fn: Callable[[np.ndarray, np.ndarray], float],
    rng: np.random.Generator,
    *,
    n_resamples: int = 2000,
    alpha: float = 0.05,
    max_n_subsample: int = 50_000,
    huge_n_threshold: int = 200_000,
) -> tuple[float | None, float | None, str, str | None]:
    """Stratified within-group bootstrap CI for two-group statistics (e.g., rank-biserial)."""
    x1 = np.asarray(g1, dtype=float)
    x2 = np.asarray(g2, dtype=float)
    warning: str | None = None
    if len(x1) + len(x2) > huge_n_threshold:
        n1_sub = max(10, int(max_n_subsample * len(x1) / (len(x1) + len(x2))))
        n2_sub = max(10, max_n_subsample - n1_sub)
        x1 = rng.choice(x1, size=min(len(x1), n1_sub), replace=False)
        x2 = rng.choice(x2, size=min(len(x2), n2_sub), replace=False)
        warning = "Bootstrap CI computed on seeded 50k subsample (subsampled=true)."

    n1, n2 = len(x1), len(x2)
    vals = np.empty(n_resamples, dtype=float)
    for b in range(n_resamples):
        s1 = x1[rng.integers(0, n1, size=n1)]
        s2 = x2[rng.integers(0, n2, size=n2)]
        vals[b] = stat_fn(s1, s2)
    finite = vals[np.isfinite(vals)]
    if len(finite) < max(20, int(0.5 * n_resamples)):
        return None, None, "bootstrap_percentile", "Bootstrap CI failed due to degenerate resamples."
    lo, hi = np.percentile(finite, [100.0 * (alpha / 2.0), 100.0 * (1.0 - alpha / 2.0)])
    return float(lo), float(hi), "bootstrap_percentile", warning


def bootstrap_ci_multi_group(
    groups: list[np.ndarray],
    stat_fn: Callable[[list[np.ndarray]], float],
    rng: np.random.Generator,
    *,
    n_resamples: int = 2000,
    alpha: float = 0.05,
    max_n_subsample: int = 50_000,
    huge_n_threshold: int = 200_000,
) -> tuple[float | None, float | None, str, str | None]:
    """Stratified within-group percentile bootstrap CI for k-group statistics (eta^2, epsilon^2)."""
    arrs = [np.asarray(g, dtype=float) for g in groups]
    total_n = sum(len(g) for g in arrs)
    warning: str | None = None
    if total_n > huge_n_threshold:
        arrs = [
            rng.choice(g, size=min(len(g), max(8, int(max_n_subsample * len(g) / total_n))), replace=False)
            for g in arrs
        ]
        warning = "Bootstrap CI computed on seeded 50k subsample (subsampled=true)."

    vals = np.empty(n_resamples, dtype=float)
    for b in range(n_resamples):
        sample_groups = [g[rng.integers(0, len(g), size=len(g))] for g in arrs]
        vals[b] = stat_fn(sample_groups)
    finite = vals[np.isfinite(vals)]
    if len(finite) < max(20, int(0.5 * n_resamples)):
        return None, None, "bootstrap_percentile", "Bootstrap CI failed due to degenerate resamples."
    lo, hi = np.percentile(finite, [100.0 * (alpha / 2.0), 100.0 * (1.0 - alpha / 2.0)])
    return float(lo), float(hi), "bootstrap_percentile", warning


def bootstrap_ci_paired(
    a: np.ndarray,
    b: np.ndarray,
    stat_fn: Callable[[np.ndarray, np.ndarray], float],
    rng: np.random.Generator,
    *,
    n_resamples: int = 2000,
    alpha: float = 0.05,
    max_n_subsample: int = 50_000,
    huge_n_threshold: int = 200_000,
) -> tuple[float | None, float | None, str, str | None]:
    """Paired row-resampling percentile bootstrap CI (Spearman rho, Cramér's V)."""
    arr_a = np.asarray(a)
    arr_b = np.asarray(b)
    n = len(arr_a)
    warning: str | None = None
    if n > huge_n_threshold:
        idx_sub = rng.choice(n, size=max_n_subsample, replace=False)
        arr_a = arr_a[idx_sub]
        arr_b = arr_b[idx_sub]
        n = len(arr_a)
        warning = "Bootstrap CI computed on seeded 50k subsample (subsampled=true)."

    vals = np.empty(n_resamples, dtype=float)
    for i in range(n_resamples):
        idx = rng.integers(0, n, size=n)
        vals[i] = stat_fn(arr_a[idx], arr_b[idx])
    finite = vals[np.isfinite(vals)]
    if len(finite) < max(20, int(0.5 * n_resamples)):
        return None, None, "bootstrap_percentile", "Bootstrap CI failed due to degenerate resamples."
    lo, hi = np.percentile(finite, [100.0 * (alpha / 2.0), 100.0 * (1.0 - alpha / 2.0)])
    return float(lo), float(hi), "bootstrap_percentile", warning

