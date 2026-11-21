"""NUM_BINARY statistical tests: Welch's t-test and Mann-Whitney U (Phase 3 Section 4.1)."""

from __future__ import annotations

from typing import Any

import numpy as np
from scipy import stats as sp_stats

from veridata.config import PipelineConfig
from veridata.contracts.hypothesis import Direction
from veridata.contracts.results import EffectSize
from veridata.stats.assumptions import check_ties_rate
from veridata.stats.effect_sizes import hedges_g, hodges_lehmann_shift, rank_biserial_and_ps
from veridata.stats.intervals import hedges_g_ci, welch_mean_diff_ci
from veridata.stats.types import PreparedData, RawTestOutput


def _group_descriptives(groups: list[np.ndarray], labels: list[str]) -> dict[str, dict[str, float]]:
    out: dict[str, dict[str, float]] = {}
    for lbl, arr in zip(labels, groups):
        q1, med, q3 = np.percentile(arr, [25.0, 50.0, 75.0])
        out[lbl] = {
            "n": int(len(arr)),
            "mean": float(np.mean(arr)),
            "sd": float(np.std(arr, ddof=1)) if len(arr) > 1 else 0.0,
            "median": float(med),
            "iqr": float(q3 - q1),
            "min": float(np.min(arr)),
            "max": float(np.max(arr)),
        }
    return out


def run_welch_t(
    prepared: PreparedData,
    config: PipelineConfig,
    rng: np.random.Generator,
) -> RawTestOutput:
    """Two-sided Welch's t-test with Hedges' g and analytic CIs."""
    _ = rng
    assert prepared.groups is not None and prepared.group_labels is not None
    g1, g2 = prepared.groups[0], prepared.groups[1]
    lbl1, lbl2 = prepared.group_labels[0], prepared.group_labels[1]

    res = sp_stats.ttest_ind(g1, g2, equal_var=False, alternative="two-sided")
    stat = float(res.statistic)
    p_val = float(np.clip(res.pvalue, 0.0, 1.0))

    g_val, mean_diff, mag = hedges_g(g1, g2)
    g_lo, g_hi, g_ci_method = hedges_g_ci(g_val, len(g1), len(g2))
    md_lo, md_hi, df_welch = welch_mean_diff_ci(g1, g2)

    grp_desc = _group_descriptives([g1, g2], [lbl1, lbl2])
    higher_group = lbl1 if mean_diff > 0 else (lbl2 if mean_diff < 0 else None)
    direction = (
        Direction.A_GREATER
        if mean_diff > 0
        else (Direction.B_GREATER if mean_diff < 0 else Direction.ANY)
    )

    effect = EffectSize(
        name="hedges_g",
        value=g_val,
        ci_low=g_lo,
        ci_high=g_hi,
        ci_method=g_ci_method,
        magnitude=mag,
        comparable_value=abs(g_val),
    )

    descriptives: dict[str, Any] = {
        "group_order": [lbl1, lbl2],
        "groups": grp_desc,
        "mean_diff": mean_diff,
        "mean_diff_ci_low": md_lo,
        "mean_diff_ci_high": md_hi,
        "higher_group": higher_group,
        "dropped_levels": list(prepared.dropped_levels),
    }
    return RawTestOutput(
        test_name="welch_t",
        statistic=stat,
        df=df_welch,
        p_value=p_val,
        effect=effect,
        descriptives=descriptives,
        direction_observed=direction,
    )


def run_mann_whitney_u(
    prepared: PreparedData,
    config: PipelineConfig,
    rng: np.random.Generator,
) -> RawTestOutput:
    """Two-sided Mann-Whitney U test with rank-biserial correlation and Hodges-Lehmann shift."""
    assert prepared.groups is not None and prepared.group_labels is not None
    g1, g2 = prepared.groups[0], prepared.groups[1]
    lbl1, lbl2 = prepared.group_labels[0], prepared.group_labels[1]
    n1, n2 = len(g1), len(g2)

    combined = np.concatenate([g1, g2])
    ties_rate = check_ties_rate(combined)
    if n1 + n2 > 200_000:
        method = "asymptotic"
    elif ties_rate == 0.0 and (n1 + n2) <= 50:
        method = "exact"
    else:
        method = "auto"

    res = sp_stats.mannwhitneyu(g1, g2, alternative="two-sided", method=method)
    u_stat = float(res.statistic)
    p_val = float(np.clip(res.pvalue, 0.0, 1.0))

    r_rb, prob_sup, mag = rank_biserial_and_ps(u_stat, n1, n2)
    hl_shift, hl_subsampled = hodges_lehmann_shift(g1, g2, rng)

    grp_desc = _group_descriptives([g1, g2], [lbl1, lbl2])
    higher_group = lbl1 if r_rb > 0 else (lbl2 if r_rb < 0 else None)
    direction = (
        Direction.A_GREATER
        if r_rb > 0
        else (Direction.B_GREATER if r_rb < 0 else Direction.ANY)
    )

    effect = EffectSize(
        name="rank_biserial",
        value=r_rb,
        ci_low=None,
        ci_high=None,
        ci_method=None,
        magnitude=mag,
        comparable_value=abs(r_rb),
    )

    descriptives: dict[str, Any] = {
        "group_order": [lbl1, lbl2],
        "groups": grp_desc,
        "u_statistic": u_stat,
        "probability_of_superiority": prob_sup,
        "hodges_lehmann_shift": hl_shift,
        "hodges_lehmann_subsampled": hl_subsampled,
        "ties_rate": round(ties_rate, 4),
        "mwu_method": method,
        "higher_group": higher_group,
        "dropped_levels": list(prepared.dropped_levels),
    }
    return RawTestOutput(
        test_name="mann_whitney_u",
        statistic=u_stat,
        df=None,
        p_value=p_val,
        effect=effect,
        descriptives=descriptives,
        direction_observed=direction,
    )

