"""NUM_CATEGORICAL statistical tests: Welch's ANOVA and Kruskal-Wallis (Phase 3 Section 4.2)."""

from __future__ import annotations

from typing import Any

import numpy as np
from scipy import stats as sp_stats
from statsmodels.stats.oneway import anova_oneway

from veridata.config import PipelineConfig
from veridata.contracts.hypothesis import Direction
from veridata.contracts.results import EffectSize
from veridata.stats.effect_sizes import epsilon_squared_kruskal, eta_and_omega_squared
from veridata.stats.types import PreparedData, RawTestOutput


def _multi_group_descriptives(
    groups: list[np.ndarray],
    labels: list[str],
    rank_metric: str,
) -> dict[str, Any]:
    per_group: dict[str, dict[str, float]] = {}
    for lbl, arr in zip(labels, groups):
        q1, med, q3 = np.percentile(arr, [25.0, 50.0, 75.0])
        per_group[lbl] = {
            "n": int(len(arr)),
            "mean": float(np.mean(arr)),
            "sd": float(np.std(arr, ddof=1)) if len(arr) > 1 else 0.0,
            "median": float(med),
            "iqr": float(q3 - q1),
        }
    highest = max(labels, key=lambda l: per_group[l][rank_metric])
    lowest = min(labels, key=lambda l: per_group[l][rank_metric])
    return {
        "group_order": list(labels),
        "groups": per_group,
        "highest_group": highest,
        "lowest_group": lowest,
    }


def run_welch_anova(
    prepared: PreparedData,
    config: PipelineConfig,
    rng: np.random.Generator,
) -> RawTestOutput:
    """Welch's one-way ANOVA (unequal variances) with eta-squared and omega-squared."""
    _ = config, rng
    assert prepared.groups is not None and prepared.group_labels is not None
    groups = prepared.groups
    labels = prepared.group_labels

    data = np.concatenate(groups)
    grp_codes = np.concatenate([np.full(len(g), i, dtype=int) for i, g in enumerate(groups)])

    res = anova_oneway(data, grp_codes, use_var="unequal", welch_correction=True)
    stat = float(res.statistic)
    p_val = float(np.clip(res.pvalue, 0.0, 1.0))
    df_vals = [float(res.df[0]), float(res.df[1])] if hasattr(res, "df") else None

    eta_sq, omega_sq, mag = eta_and_omega_squared(groups)
    effect = EffectSize(
        name="eta_squared",
        value=eta_sq,
        ci_low=None,
        ci_high=None,
        ci_method=None,
        magnitude=mag,
        comparable_value=eta_sq,
    )

    desc = _multi_group_descriptives(groups, labels, rank_metric="mean")
    desc["omega_squared"] = omega_sq
    desc["dropped_levels"] = list(prepared.dropped_levels)

    return RawTestOutput(
        test_name="welch_anova",
        statistic=stat,
        df=df_vals,
        p_value=p_val,
        effect=effect,
        descriptives=desc,
        direction_observed=Direction.ANY,
    )


def run_kruskal_wallis(
    prepared: PreparedData,
    config: PipelineConfig,
    rng: np.random.Generator,
) -> RawTestOutput:
    """Kruskal-Wallis H test with Tomczak & Tomczak epsilon-squared."""
    _ = config, rng
    assert prepared.groups is not None and prepared.group_labels is not None
    groups = prepared.groups
    labels = prepared.group_labels

    res = sp_stats.kruskal(*groups)
    h_stat = float(res.statistic)
    p_val = float(np.clip(res.pvalue, 0.0, 1.0))
    df_val = float(len(groups) - 1)

    eps_sq, mag = epsilon_squared_kruskal(h_stat, prepared.n_used)
    effect = EffectSize(
        name="epsilon_squared",
        value=eps_sq,
        ci_low=None,
        ci_high=None,
        ci_method=None,
        magnitude=mag,
        comparable_value=eps_sq,
    )

    desc = _multi_group_descriptives(groups, labels, rank_metric="median")
    desc["dropped_levels"] = list(prepared.dropped_levels)

    return RawTestOutput(
        test_name="kruskal_wallis",
        statistic=h_stat,
        df=df_val,
        p_value=p_val,
        effect=effect,
        descriptives=desc,
        direction_observed=Direction.ANY,
    )

