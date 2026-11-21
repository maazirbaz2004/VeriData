"""Deterministic assumption-aware statistical test selection (Phase 3 Sections 4.1–4.4)."""

from __future__ import annotations

from typing import Any

import numpy as np

from veridata.config import PipelineConfig
from veridata.contracts.hypothesis import RelationshipType
from veridata.contracts.results import AssumptionCheck
from veridata.errors import StatsError
from veridata.stats.assumptions import (
    check_equal_variance,
    check_expected_counts,
    check_normality,
    check_ties_rate,
    independence_note,
)
from veridata.stats.registry import REGISTRY
from veridata.stats.types import PreparedData, ToolSpec


def select_test(
    prepared: PreparedData,
    config: PipelineConfig,
) -> tuple[ToolSpec, list[AssumptionCheck], list[dict[str, Any]], bool, str]:
    """Select an appropriate statistical test using assumption diagnostics ONLY (never p-values).

    Returns ``(tool_spec, assumption_checks, selection_trace, fallback_used, reason_text)``.
    """
    assumptions: list[AssumptionCheck] = [independence_note()]
    trace: list[dict[str, Any]] = []
    rel = prepared.relationship
    aware = config.stats.assumption_aware_selection

    # Handle NUM_CATEGORICAL collapsed to 2 groups after rare-level filtering
    effective_rel = rel
    if rel == RelationshipType.NUM_CATEGORICAL and prepared.collapsed_to_two_groups:
        effective_rel = RelationshipType.NUM_BINARY
        trace.append(
            {
                "rule": "collapsed_to_two_groups",
                "input": {"k_groups": len(prepared.groups or [])},
                "outcome": "use two-group test selection",
            }
        )

    # ------------------------------------------------------------------
    # 1. NUM_BINARY: Welch's t vs Mann-Whitney U
    # ------------------------------------------------------------------
    if effective_rel == RelationshipType.NUM_BINARY:
        assert prepared.groups is not None and prepared.group_labels is not None
        g1, g2 = prepared.groups[0], prepared.groups[1]
        lbl1, lbl2 = prepared.group_labels[0], prepared.group_labels[1]

        if not aware:
            trace.append(
                {
                    "rule": "ablation_no_assumption_selection",
                    "input": {"assumption_aware_selection": False},
                    "outcome": "welch_t",
                }
            )
            return REGISTRY["welch_t"], assumptions, trace, False, "Naive ablation: Welch's t selected without assumption checks."

        # Zero variance check
        zero_var_1 = float(np.std(g1)) == 0.0
        zero_var_2 = float(np.std(g2)) == 0.0
        if zero_var_1 or zero_var_2:
            trace.append(
                {
                    "rule": "zero_variance_group",
                    "input": {"zero_var_g1": zero_var_1, "zero_var_g2": zero_var_2},
                    "outcome": "mann_whitney_u",
                }
            )
            assumptions.append(check_equal_variance([g1, g2], for_mwu=True))
            return (
                REGISTRY["mann_whitney_u"],
                assumptions,
                trace,
                True,
                "At least one group has zero variance; Welch's t is undefined, using Mann-Whitney U.",
            )

        norm1, meta1 = check_normality(g1, lbl1, config)
        norm2, meta2 = check_normality(g2, lbl2, config)
        assumptions.extend([norm1, norm2])

        both_normal = norm1.passed and norm2.passed
        max_skew = max(abs(meta1["skew"]), abs(meta2["skew"]))
        max_out = max(meta1["outlier_rate_3iqr"], meta2["outlier_rate_3iqr"])
        both_large_clt = (
            len(g1) >= config.stats.large_n_clt
            and len(g2) >= config.stats.large_n_clt
            and max_skew <= config.stats.extreme_skew
        )

        trace.append(
            {
                "rule": "normality_and_clt",
                "input": {
                    "n1": len(g1),
                    "n2": len(g2),
                    "both_normal": both_normal,
                    "max_abs_skew": round(max_skew, 3),
                    "max_outlier_rate_3iqr": round(max_out, 4),
                    "both_large_clt": both_large_clt,
                },
                "outcome": "welch_t" if (both_normal or both_large_clt) else "mann_whitney_u",
            }
        )

        if both_normal:
            assumptions.append(check_equal_variance([g1, g2], for_mwu=False))
            return (
                REGISTRY["welch_t"],
                assumptions,
                trace,
                False,
                "Both groups pass approximate normality; selected Welch's t-test.",
            )
        if both_large_clt:
            assumptions.append(check_equal_variance([g1, g2], for_mwu=False))
            return (
                REGISTRY["welch_t"],
                assumptions,
                trace,
                False,
                f"Both groups have n >= {config.stats.large_n_clt} with |skew| <= {config.stats.extreme_skew} (CLT); selected Welch's t-test.",
            )

        assumptions.append(check_equal_variance([g1, g2], for_mwu=True))
        return (
            REGISTRY["mann_whitney_u"],
            assumptions,
            trace,
            True,
            "Normality and CLT conditions not met; fell back to non-parametric Mann-Whitney U.",
        )

    # ------------------------------------------------------------------
    # 2. NUM_CATEGORICAL: Welch's ANOVA vs Kruskal-Wallis
    # ------------------------------------------------------------------
    if effective_rel == RelationshipType.NUM_CATEGORICAL:
        assert prepared.groups is not None and prepared.group_labels is not None
        groups = prepared.groups
        labels = prepared.group_labels

        if not aware:
            trace.append(
                {
                    "rule": "ablation_no_assumption_selection",
                    "input": {"assumption_aware_selection": False},
                    "outcome": "welch_anova",
                }
            )
            return REGISTRY["welch_anova"], assumptions, trace, False, "Naive ablation: Welch's ANOVA selected."

        if any(float(np.std(g)) == 0.0 for g in groups):
            trace.append(
                {
                    "rule": "zero_variance_group",
                    "input": {"n_groups": len(groups)},
                    "outcome": "kruskal_wallis",
                }
            )
            assumptions.append(check_equal_variance(groups, for_mwu=False))
            return (
                REGISTRY["kruskal_wallis"],
                assumptions,
                trace,
                True,
                "At least one group has zero variance; fell back to Kruskal-Wallis.",
            )

        norm_checks = []
        metas = []
        for lbl, grp in zip(labels, groups):
            nc, meta = check_normality(grp, lbl, config)
            norm_checks.append(nc)
            metas.append(meta)
        assumptions.extend(norm_checks)
        assumptions.append(check_equal_variance(groups, for_mwu=False))

        all_normal = all(c.passed for c in norm_checks)
        max_skew = max(abs(m["skew"]) for m in metas)
        all_large_clt = (
            all(len(g) >= config.stats.large_n_clt for g in groups)
            and max_skew <= config.stats.extreme_skew
        )

        trace.append(
            {
                "rule": "multi_group_normality_and_clt",
                "input": {
                    "k_groups": len(groups),
                    "min_group_n": min(len(g) for g in groups),
                    "all_normal": all_normal,
                    "max_abs_skew": round(max_skew, 3),
                    "all_large_clt": all_large_clt,
                },
                "outcome": "welch_anova" if (all_normal or all_large_clt) else "kruskal_wallis",
            }
        )

        if all_normal or all_large_clt:
            reason = (
                "All groups pass approximate normality; selected Welch's ANOVA."
                if all_normal
                else f"All groups have n >= {config.stats.large_n_clt} with |skew| <= {config.stats.extreme_skew} (CLT); selected Welch's ANOVA."
            )
            return REGISTRY["welch_anova"], assumptions, trace, False, reason

        return (
            REGISTRY["kruskal_wallis"],
            assumptions,
            trace,
            True,
            "Multi-group normality/CLT criteria not met; fell back to Kruskal-Wallis.",
        )

    # ------------------------------------------------------------------
    # 3. NUM_NUM: Pearson r vs Spearman rho
    # ------------------------------------------------------------------
    if effective_rel == RelationshipType.NUM_NUM:
        assert prepared.x is not None and prepared.y is not None
        x, y = prepared.x, prepared.y
        n = len(x)

        if not aware:
            trace.append(
                {
                    "rule": "ablation_no_assumption_selection",
                    "input": {"assumption_aware_selection": False},
                    "outcome": "pearson",
                }
            )
            return REGISTRY["pearson"], assumptions, trace, False, "Naive ablation: Pearson selected."

        ties_a = check_ties_rate(x)
        ties_b = check_ties_rate(y)
        max_ties = max(ties_a, ties_b)
        if max_ties > 0.50:
            assumptions.append(
                AssumptionCheck(
                    name="ties",
                    method="tie_rate",
                    statistic=round(max_ties, 4),
                    p_value=None,
                    passed=False,
                    severity="info",
                    detail=f"High tie rate ({max_ties:.1%} > 50%); Spearman rank correlation preferred.",
                )
            )
            trace.append(
                {
                    "rule": "high_ties",
                    "input": {"max_ties_rate": round(max_ties, 4)},
                    "outcome": "spearman",
                }
            )
            return (
                REGISTRY["spearman"],
                assumptions,
                trace,
                True,
                "Variables have >50% tied values; selected Spearman rank correlation.",
            )

        if n < 30:
            trace.append({"rule": "small_n", "input": {"n": n}, "outcome": "spearman"})
            return (
                REGISTRY["spearman"],
                assumptions,
                trace,
                True,
                f"Small sample size (n={n} < 30); selected Spearman for robustness.",
            )

        norm_a, meta_a = check_normality(x, prepared.hypothesis.column_a, config)
        norm_b, meta_b = check_normality(y, prepared.hypothesis.column_b, config)
        assumptions.extend([norm_a, norm_b])

        both_normal = norm_a.passed and norm_b.passed
        max_out = max(meta_a["outlier_rate_3iqr"], meta_b["outlier_rate_3iqr"])
        max_skew = max(abs(meta_a["skew"]), abs(meta_b["skew"]))

        pearson_normal_ok = both_normal and (max_out < 0.02)
        pearson_large_n_ok = (
            (n >= 200) and (max_skew <= config.stats.extreme_skew) and (max_out < 0.05)
        )

        trace.append(
            {
                "rule": "normality_outliers_large_n",
                "input": {
                    "n": n,
                    "both_normal": both_normal,
                    "max_abs_skew": round(max_skew, 3),
                    "max_outlier_rate_3iqr": round(max_out, 4),
                },
                "outcome": "pearson" if (pearson_normal_ok or pearson_large_n_ok) else "spearman",
            }
        )

        if pearson_normal_ok:
            return (
                REGISTRY["pearson"],
                assumptions,
                trace,
                False,
                "Both variables pass approximate normality with <2% extreme outliers; selected Pearson r.",
            )
        if pearson_large_n_ok:
            return (
                REGISTRY["pearson"],
                assumptions,
                trace,
                False,
                f"Large sample (n={n} >= 200) with moderate skew and <5% extreme outliers; selected Pearson r.",
            )

        return (
            REGISTRY["spearman"],
            assumptions,
            trace,
            True,
            "Skewness or extreme outliers exceed Pearson thresholds; fell back to Spearman rho.",
        )

    # ------------------------------------------------------------------
    # 4. CAT_CAT: Chi-square vs Fisher's exact vs Monte Carlo Chi-square
    # ------------------------------------------------------------------
    if effective_rel == RelationshipType.CAT_CAT:
        assert prepared.contingency is not None
        exp_check, exp_meta = check_expected_counts(prepared.contingency, config)
        assumptions.append(exp_check)

        if not aware:
            trace.append(
                {
                    "rule": "ablation_no_assumption_selection",
                    "input": {"assumption_aware_selection": False},
                    "outcome": "chi_square",
                }
            )
            return REGISTRY["chi_square"], assumptions, trace, False, "Naive ablation: Chi-square selected."

        if exp_meta["n_cells"] > 100 and exp_meta["n_total"] < 5 * exp_meta["n_cells"]:
            assumptions.append(
                AssumptionCheck(
                    name="sparse_wide_table",
                    method="cell_density",
                    statistic=float(exp_meta["n_cells"]),
                    p_value=None,
                    passed=False,
                    severity="warning",
                    detail=f"Sparse wide table ({exp_meta['n_cells']} cells, n={exp_meta['n_total']}).",
                )
            )

        if exp_meta["is_2x2"]:
            if not exp_meta["chi2_eligible"]:
                trace.append(
                    {
                        "rule": "2x2_expected_counts",
                        "input": exp_meta,
                        "outcome": "fisher_exact",
                    }
                )
                return (
                    REGISTRY["fisher_exact"],
                    assumptions,
                    trace,
                    True,
                    "2x2 table has expected count < 5 or n < 40; selected Fisher's exact test.",
                )
            trace.append(
                {"rule": "2x2_expected_counts", "input": exp_meta, "outcome": "chi_square"}
            )
            return (
                REGISTRY["chi_square"],
                assumptions,
                trace,
                False,
                "2x2 table satisfies expected count >= 5 and n >= 40; selected Pearson chi-square.",
            )

        if exp_meta["chi2_eligible"]:
            trace.append(
                {"rule": "rxc_cochran_rule", "input": exp_meta, "outcome": "chi_square"}
            )
            return (
                REGISTRY["chi_square"],
                assumptions,
                trace,
                False,
                "r x c table satisfies Cochran expected-count rule (>=80% >= 5, min >= 1); selected Pearson chi-square.",
            )

        trace.append(
            {
                "rule": "rxc_cochran_rule",
                "input": exp_meta,
                "outcome": "monte_carlo_chi_square",
            }
        )
        return (
            REGISTRY["monte_carlo_chi_square"],
            assumptions,
            trace,
            True,
            "Sparse r x c table violates Cochran rule; fell back to Monte Carlo permutation chi-square.",
        )

    raise StatsError(f"Unsupported relationship type for test selection: {effective_rel.value}")

