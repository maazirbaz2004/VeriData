"""Statistical assumption checks for Phase 3 (Section 5)."""

from __future__ import annotations

from typing import Any

import numpy as np
from scipy import stats as sp_stats

from veridata.config import PipelineConfig
from veridata.contracts.results import AssumptionCheck


def check_outlier_rate(values: np.ndarray) -> float:
    """Return fraction of finite observations outside 3.0 x IQR fences."""
    arr = np.asarray(values, dtype=float)
    arr = arr[np.isfinite(arr)]
    if len(arr) < 4:
        return 0.0
    q1, q3 = np.percentile(arr, [25.0, 75.0])
    iqr = float(q3 - q1)
    if iqr <= 0.0:
        return 0.0
    lo = q1 - 3.0 * iqr
    hi = q3 + 3.0 * iqr
    return float(np.mean((arr < lo) | (arr > hi)))


def check_ties_rate(values: np.ndarray) -> float:
    """Return proportion of tied values: 1 - n_unique / n."""
    arr = np.asarray(values, dtype=float)
    arr = arr[np.isfinite(arr)]
    if len(arr) <= 1:
        return 0.0
    return float(1.0 - (len(np.unique(arr)) / len(arr)))


def check_normality(
    values: np.ndarray,
    label: str,
    config: PipelineConfig,
) -> tuple[AssumptionCheck, dict[str, float]]:
    """Assess approximate normality via Shapiro-Wilk (n <= normality_n_max) and skew/kurtosis."""
    arr = np.asarray(values, dtype=float)
    arr = arr[np.isfinite(arr)]
    n = len(arr)

    if n < 3 or float(np.std(arr)) == 0.0:
        meta = {"n": float(n), "skew": 0.0, "kurtosis": 0.0, "outlier_rate_3iqr": 0.0}
        return (
            AssumptionCheck(
                name=f"normality_{label}",
                method="variance_check",
                statistic=None,
                p_value=None,
                passed=False,
                severity="info",
                detail=f"Group/variable '{label}' has zero variance or n < 3 (n={n}).",
            ),
            meta,
        )

    skew = float(sp_stats.skew(arr, bias=False)) if n >= 3 else 0.0
    kurt = float(sp_stats.kurtosis(arr, fisher=True, bias=False)) if n >= 4 else 0.0
    if not np.isfinite(skew):
        skew = 0.0
    if not np.isfinite(kurt):
        kurt = 0.0
    out_rate = check_outlier_rate(arr)
    rule_pass = (abs(skew) < 1.0) and (abs(kurt) < 3.0)

    stat_val: float | None = None
    p_val: float | None = None
    method = "skew_kurtosis_rule"
    shapiro_pass = False

    if n <= config.stats.normality_n_max:
        try:
            res = sp_stats.shapiro(arr)
            stat_val = float(res.statistic)
            p_val = float(np.clip(res.pvalue, 0.0, 1.0))
            shapiro_pass = p_val > 0.01
            method = "shapiro"
        except Exception:  # noqa: BLE001
            method = "skew_kurtosis_rule"

    passed = bool(shapiro_pass or rule_pass)
    detail = (
        f"n={n}, skew={skew:.2f}, excess_kurtosis={kurt:.2f}, 3xIQR_outlier_rate={out_rate:.3f}"
        + (f", shapiro_p={p_val:.4g}" if p_val is not None else " (Shapiro skipped for large n)")
    )
    meta = {
        "n": float(n),
        "skew": skew,
        "kurtosis": kurt,
        "outlier_rate_3iqr": out_rate,
    }
    return (
        AssumptionCheck(
            name=f"normality_{label}",
            method=method,
            statistic=stat_val,
            p_value=p_val,
            passed=passed,
            severity="info",
            detail=detail,
        ),
        meta,
    )


def check_equal_variance(
    groups: list[np.ndarray],
    *,
    for_mwu: bool = False,
) -> AssumptionCheck:
    """Brown-Forsythe (median-centered Levene) test for equality of variances."""
    valid = [g for g in groups if len(g) >= 2]
    if len(valid) < 2:
        return AssumptionCheck(
            name="equal_variance",
            method="levene_median",
            statistic=None,
            p_value=None,
            passed=True,
            severity="info",
            detail="Skipped: fewer than 2 groups with n >= 2.",
        )
    if all(float(np.std(g)) == 0.0 for g in valid):
        return AssumptionCheck(
            name="equal_variance",
            method="levene_median",
            statistic=0.0,
            p_value=1.0,
            passed=True,
            severity="info",
            detail="All groups have zero within-group variance.",
        )

    res = sp_stats.levene(*valid, center="median")
    stat_val = float(res.statistic) if np.isfinite(res.statistic) else None
    p_val = float(np.clip(res.pvalue, 0.0, 1.0)) if np.isfinite(res.pvalue) else None
    passed = True if p_val is None else bool(p_val > 0.05)

    severity: Any = "info"
    detail = f"Brown-Forsythe Levene p={p_val:.4g}." if p_val is not None else "Levene non-finite."
    if not passed and for_mwu:
        severity = "warning"
        detail += " Unequal spreads detected; interpret Mann-Whitney as stochastic dominance rather than pure location shift."

    return AssumptionCheck(
        name="equal_variance",
        method="levene_median",
        statistic=stat_val,
        p_value=p_val,
        passed=passed,
        severity=severity,
        detail=detail,
    )


def check_expected_counts(
    observed: np.ndarray,
    config: PipelineConfig,
) -> tuple[AssumptionCheck, dict[str, Any]]:
    """Inspect contingency table expected counts under independence (Section 4.4)."""
    obs = np.asarray(observed, dtype=float)
    r, c = obs.shape
    n = float(obs.sum())
    row_sums = obs.sum(axis=1, keepdims=True)
    col_sums = obs.sum(axis=0, keepdims=True)
    expected = (row_sums @ col_sums) / max(1.0, n)

    min_exp = float(expected.min())
    pct_ge_5 = float(np.mean(expected >= float(config.stats.min_expected_count_chi2)))
    is_2x2 = (r == 2) and (c == 2)

    if is_2x2:
        chi2_ok = (min_exp >= float(config.stats.min_expected_count_chi2)) and (n >= 40.0)
    else:
        chi2_ok = (pct_ge_5 >= 0.80) and (min_exp >= 1.0)

    detail = (
        f"Table {r}x{c} (n={int(n)}): min_expected={min_exp:.2f}, "
        f"cells>=5={pct_ge_5:.1%}; chi2_eligible={chi2_ok}."
    )
    check = AssumptionCheck(
        name="expected_counts",
        method="cochran_rule",
        statistic=min_exp,
        p_value=None,
        passed=chi2_ok,
        severity="info",
        detail=detail,
    )
    return check, {
        "min_expected": min_exp,
        "pct_ge_5": pct_ge_5,
        "is_2x2": is_2x2,
        "chi2_eligible": chi2_ok,
        "n_cells": r * c,
        "n_total": int(n),
    }


def check_linearity_advisory(x: np.ndarray, y: np.ndarray) -> AssumptionCheck:
    """Advisory-only quadratic vs linear F-test for Pearson correlation (never alters selection)."""
    x_arr = np.asarray(x, dtype=float)
    y_arr = np.asarray(y, dtype=float)
    n = len(x_arr)
    if n < 10 or float(np.std(x_arr)) == 0.0 or float(np.std(y_arr)) == 0.0:
        return AssumptionCheck(
            name="linearity",
            method="quadratic_f_test_advisory",
            statistic=None,
            p_value=None,
            passed=True,
            severity="info",
            detail="Skipped advisory linearity check (small n or zero variance).",
        )
    x_std = (x_arr - x_arr.mean()) / x_arr.std()
    X1 = np.column_stack([np.ones(n), x_std])
    X2 = np.column_stack([np.ones(n), x_std, x_std**2])
    beta1, *_ = np.linalg.lstsq(X1, y_arr, rcond=None)
    beta2, *_ = np.linalg.lstsq(X2, y_arr, rcond=None)
    rss1 = float(np.sum((y_arr - X1 @ beta1) ** 2))
    rss2 = float(np.sum((y_arr - X2 @ beta2) ** 2))
    df2 = n - 3
    if rss2 <= 1e-15 or df2 <= 0:
        return AssumptionCheck(
            name="linearity",
            method="quadratic_f_test_advisory",
            statistic=0.0,
            p_value=1.0,
            passed=True,
            severity="info",
            detail="Exact or near-exact linear fit.",
        )
    f_stat = max(0.0, ((rss1 - rss2) / 1.0) / (rss2 / df2))
    p_val = float(np.clip(sp_stats.f.sf(f_stat, 1, df2), 0.0, 1.0))
    passed = p_val > 0.01
    return AssumptionCheck(
        name="linearity",
        method="quadratic_f_test_advisory",
        statistic=round(f_stat, 4),
        p_value=p_val,
        passed=passed,
        severity="info",
        detail=(
            f"Advisory quadratic term F={f_stat:.2f}, p={p_val:.4g} "
            "(informational only; does not alter test selection)."
        ),
    )


def independence_note() -> AssumptionCheck:
    """Standard assumption note: statistical tests assume independent observations."""
    return AssumptionCheck(
        name="independence_note",
        method="design_assumption",
        statistic=None,
        p_value=None,
        passed=True,
        severity="info",
        detail="Rows are assumed independent; clustered or repeated-measures data may inflate false positives.",
    )

