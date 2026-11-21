"""Standardized effect sizes and magnitude classifiers (Phase 3 Section 4)."""

from __future__ import annotations

from typing import Any, Literal

import numpy as np
from scipy import stats as sp_stats


Magnitude = Literal["negligible", "small", "medium", "large"]


def classify_cohens_d(abs_d: float) -> Magnitude:
    if abs_d < 0.20:
        return "negligible"
    if abs_d < 0.50:
        return "small"
    if abs_d < 0.80:
        return "medium"
    return "large"


def classify_correlation(abs_r: float) -> Magnitude:
    if abs_r < 0.10:
        return "negligible"
    if abs_r < 0.30:
        return "small"
    if abs_r < 0.50:
        return "medium"
    return "large"


def classify_eta_squared(val: float) -> Magnitude:
    if val < 0.01:
        return "negligible"
    if val < 0.06:
        return "small"
    if val < 0.14:
        return "medium"
    return "large"


def classify_cramers_w(w_val: float) -> Magnitude:
    """Classify Cohen's w = V_bc * sqrt(df*) (small=0.10, medium=0.30, large=0.50)."""
    return classify_correlation(abs(w_val))


def hedges_g(g1: np.ndarray, g2: np.ndarray) -> tuple[float, float, Magnitude]:
    """Compute bias-corrected Hedges' g (g1 - g2) using pooled SD standardizer.

    Returns ``(g, mean_diff, magnitude)``.
    """
    x1 = np.asarray(g1, dtype=float)
    x2 = np.asarray(g2, dtype=float)
    n1, n2 = len(x1), len(x2)
    mean_diff = float(np.mean(x1) - np.mean(x2))
    df = n1 + n2 - 2
    if df <= 0:
        return 0.0, mean_diff, "negligible"

    s1_sq = float(np.var(x1, ddof=1)) if n1 > 1 else 0.0
    s2_sq = float(np.var(x2, ddof=1)) if n2 > 1 else 0.0
    s_pooled = float(np.sqrt(((n1 - 1) * s1_sq + (n2 - 1) * s2_sq) / df))
    if s_pooled <= 0.0:
        return 0.0, mean_diff, "negligible"

    d = mean_diff / s_pooled
    # Exact Hedges' J correction approximation (accurate for df >= 2)
    j_corr = 1.0 - (3.0 / (4.0 * df - 1.0)) if df >= 2 else 1.0
    g = float(d * j_corr)
    return g, mean_diff, classify_cohens_d(abs(g))


def rank_biserial_and_ps(
    u_stat_g1: float,
    n1: int,
    n2: int,
) -> tuple[float, float, Magnitude]:
    """Compute rank-biserial correlation and probability of superiority from U1.

    Positive ``r_rb`` indicates group 1 tends to have larger values than group 2:
    ``ps = U1 / (n1 * n2)`` and ``r_rb = 2 * ps - 1 = 1 - 2 * U2 / (n1 * n2)``.
    """
    denom = float(n1 * n2)
    if denom <= 0.0:
        return 0.0, 0.5, "negligible"
    ps = float(np.clip(u_stat_g1 / denom, 0.0, 1.0))
    r_rb = float(np.clip(2.0 * ps - 1.0, -1.0, 1.0))
    return r_rb, ps, classify_correlation(abs(r_rb))


def hodges_lehmann_shift(
    g1: np.ndarray,
    g2: np.ndarray,
    rng: np.random.Generator,
    max_pairs: int = 2_500_000,
    subsample_pairs: int = 200_000,
) -> tuple[float, bool]:
    """Median of all pairwise differences (x1_i - x2_j), subsampling if n1*n2 > max_pairs."""
    x1 = np.asarray(g1, dtype=float)
    x2 = np.asarray(g2, dtype=float)
    if len(x1) * len(x2) <= max_pairs:
        diffs = x1[:, None] - x2[None, :]
        return float(np.median(diffs)), False
    idx1 = rng.integers(0, len(x1), size=subsample_pairs)
    idx2 = rng.integers(0, len(x2), size=subsample_pairs)
    return float(np.median(x1[idx1] - x2[idx2])), True


def eta_and_omega_squared(groups: list[np.ndarray]) -> tuple[float, float, Magnitude]:
    """Compute eta-squared (SS_between/SS_total) and bias-corrected omega-squared."""
    arrays = [np.asarray(g, dtype=float) for g in groups if len(g) > 0]
    k = len(arrays)
    all_vals = np.concatenate(arrays)
    n = len(all_vals)
    if k < 2 or n <= k:
        return 0.0, 0.0, "negligible"

    grand_mean = float(np.mean(all_vals))
    ss_total = float(np.sum((all_vals - grand_mean) ** 2))
    if ss_total <= 0.0:
        return 0.0, 0.0, "negligible"

    ss_between = float(sum(len(g) * (float(np.mean(g)) - grand_mean) ** 2 for g in arrays))
    ss_within = max(0.0, ss_total - ss_between)
    ms_within = ss_within / (n - k)

    eta_sq = float(np.clip(ss_between / ss_total, 0.0, 1.0))
    omega_sq = float(
        np.clip((ss_between - (k - 1) * ms_within) / (ss_total + ms_within), 0.0, 1.0)
    )
    return eta_sq, omega_sq, classify_eta_squared(eta_sq)


def epsilon_squared_kruskal(h_stat: float, n_total: int) -> tuple[float, Magnitude]:
    """Tomczak & Tomczak epsilon-squared = H / (n - 1) for Kruskal-Wallis."""
    if n_total <= 1:
        return 0.0, "negligible"
    eps = float(np.clip(h_stat / (n_total - 1.0), 0.0, 1.0))
    return eps, classify_eta_squared(eps)


def cramers_v_bias_corrected(
    observed: np.ndarray,
) -> tuple[float, float, int, Magnitude]:
    """Bergsma (2013) bias-corrected Cramér's V and Cohen's w-equivalent comparable value.

    Returns ``(v_bc, comparable_w, df_star, magnitude)`` where
    ``comparable_w = v_bc * sqrt(df_star)`` and ``df_star = min(r - 1, c - 1)``.
    """
    obs = np.asarray(observed, dtype=float)
    r, c = obs.shape
    n = float(obs.sum())
    df_star = min(r - 1, c - 1)
    if n <= 1.0 or df_star <= 0:
        return 0.0, 0.0, max(1, df_star), "negligible"

    chi2, _, _, _ = sp_stats.chi2_contingency(obs, correction=False)
    phi2 = float(chi2) / n
    phi2_tilde = max(0.0, phi2 - ((c - 1.0) * (r - 1.0)) / (n - 1.0))
    r_tilde = r - ((r - 1.0) ** 2) / (n - 1.0)
    k_tilde = c - ((c - 1.0) ** 2) / (n - 1.0)
    denom = min(k_tilde - 1.0, r_tilde - 1.0)
    if denom <= 0.0:
        return 0.0, 0.0, df_star, "negligible"

    v_bc = float(np.sqrt(max(0.0, phi2_tilde / denom)))
    v_bc = float(np.clip(v_bc, 0.0, 1.0))
    comparable_w = float(v_bc * np.sqrt(df_star))
    return v_bc, comparable_w, df_star, classify_cramers_w(comparable_w)


def table_2x2_metrics(observed: np.ndarray, alpha: float = 0.05) -> dict[str, Any]:
    """Compute phi, odds ratio + Woolf CI (0.5 continuity if any zero), and risk difference."""
    obs = np.asarray(observed, dtype=float)
    if obs.shape != (2, 2):
        return {}
    a, b = float(obs[0, 0]), float(obs[0, 1])
    c, d = float(obs[1, 0]), float(obs[1, 1])
    n = a + b + c + d
    denom_phi = np.sqrt((a + b) * (c + d) * (a + c) * (b + d))
    phi = float((a * d - b * c) / denom_phi) if denom_phi > 0 else 0.0

    continuity_applied = bool(np.any(obs == 0))
    a_c, b_c, c_c, d_c = (a + 0.5, b + 0.5, c + 0.5, d + 0.5) if continuity_applied else (a, b, c, d)
    odds_ratio = float((a_c * d_c) / (b_c * c_c))
    log_or = float(np.log(odds_ratio))
    se_log_or = float(np.sqrt(1.0 / a_c + 1.0 / b_c + 1.0 / c_c + 1.0 / d_c))
    z = float(sp_stats.norm.ppf(1.0 - alpha / 2.0))
    or_ci_low = float(np.exp(log_or - z * se_log_or))
    or_ci_high = float(np.exp(log_or + z * se_log_or))

    p1 = a / max(1.0, a + b)
    p2 = c / max(1.0, c + d)
    risk_diff = float(p1 - p2)
    se_rd = float(
        np.sqrt(p1 * (1.0 - p1) / max(1.0, a + b) + p2 * (1.0 - p2) / max(1.0, c + d))
    )
    rd_ci_low = float(np.clip(risk_diff - z * se_rd, -1.0, 1.0))
    rd_ci_high = float(np.clip(risk_diff + z * se_rd, -1.0, 1.0))

    return {
        "phi": round(phi, 6),
        "odds_ratio": round(odds_ratio, 6),
        "odds_ratio_ci_low": round(or_ci_low, 6),
        "odds_ratio_ci_high": round(or_ci_high, 6),
        "odds_ratio_continuity_correction": continuity_applied,
        "risk_difference": round(risk_diff, 6),
        "risk_difference_ci_low": round(rd_ci_low, 6),
        "risk_difference_ci_high": round(rd_ci_high, 6),
    }

