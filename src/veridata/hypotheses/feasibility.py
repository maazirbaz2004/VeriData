"""Outcome-independent feasibility screening for hypotheses (Phase 2 Section 4)."""

from __future__ import annotations

from typing import Sequence

import numpy as np
import pandas as pd

from veridata.config import PipelineConfig
from veridata.contracts.hypothesis import FeasibilityReport, Hypothesis, RelationshipType
from veridata.schemas import ColumnSchemaEntry


def _normalize_group_series(series: pd.Series) -> pd.Series:
    """Convert non-null categorical/binary values to clean string labels."""
    return series.astype(str)


def _apply_rare_level_lumping(
    series: pd.Series,
    min_fraction: float,
) -> tuple[pd.Series, list[str]]:
    """Optionally lump rare levels (< min_fraction) into 'Other'."""
    n = len(series)
    if n == 0:
        return series, []
    counts = series.value_counts()
    rare = sorted([str(k) for k, v in counts.items() if (v / n) < min_fraction])
    if len(rare) >= 2:
        lumped = series.where(~series.isin(rare), other="Other")
        return lumped, rare
    return series, []


def assess_feasibility(
    hypothesis: Hypothesis,
    df: pd.DataFrame,
    schema: dict[str, ColumnSchemaEntry],
    config: PipelineConfig,
) -> FeasibilityReport:
    """Assess whether a hypothesis has sufficient sample size and non-degenerate data.

    Uses ONLY counts and univariate marginals — NEVER effect sizes, correlations,
    or group-mean differences (Principle P2).
    """
    col_a = hypothesis.column_a
    col_b = hypothesis.column_b
    min_n = config.stats.min_n_pairwise
    min_group_n = config.stats.min_group_n

    if col_a not in df.columns or col_b not in df.columns:
        missing_cols = [c for c in (col_a, col_b) if c not in df.columns]
        return FeasibilityReport(
            feasible=False,
            reasons=[f"missing column(s) in dataframe: {', '.join(missing_cols)}"],
            n_pairwise_complete=0,
        )

    sub = df[[col_a, col_b]].dropna()
    n_pairwise = int(len(sub))
    if n_pairwise < min_n:
        return FeasibilityReport(
            feasible=False,
            reasons=[f"n_pairwise_complete={n_pairwise} < min_n_pairwise ({min_n})"],
            n_pairwise_complete=n_pairwise,
        )

    rel = hypothesis.relationship

    if rel in {RelationshipType.NUM_NUM, RelationshipType.NUM_NUM_NONLINEAR}:
        num_a = pd.to_numeric(sub[col_a], errors="coerce")
        num_b = pd.to_numeric(sub[col_b], errors="coerce")
        valid_mask = np.isfinite(num_a) & np.isfinite(num_b)
        n_valid = int(valid_mask.sum())
        if n_valid < min_n:
            return FeasibilityReport(
                feasible=False,
                reasons=[f"numeric finite pairwise count={n_valid} < min_n_pairwise ({min_n})"],
                n_pairwise_complete=n_valid,
            )
        if num_a[valid_mask].nunique() < 2 or num_b[valid_mask].nunique() < 2:
            return FeasibilityReport(
                feasible=False,
                reasons=["degenerate: at least one column is constant after NA removal"],
                n_pairwise_complete=n_valid,
            )
        return FeasibilityReport(
            feasible=True,
            reasons=[],
            n_pairwise_complete=n_valid,
        )

    if rel == RelationshipType.NUM_BINARY:
        num_a = pd.to_numeric(sub[col_a], errors="coerce")
        valid_mask = np.isfinite(num_a)
        sub_valid = sub.loc[valid_mask]
        num_valid = num_a.loc[valid_mask]
        n_valid = int(len(sub_valid))

        if n_valid < min_n:
            return FeasibilityReport(
                feasible=False,
                reasons=[f"n_pairwise_complete={n_valid} < min_n_pairwise ({min_n})"],
                n_pairwise_complete=n_valid,
            )
        if num_valid.nunique() < 2:
            return FeasibilityReport(
                feasible=False,
                reasons=["degenerate: numeric outcome is constant after NA removal"],
                n_pairwise_complete=n_valid,
            )

        grp = _normalize_group_series(sub_valid[col_b])
        counts = grp.value_counts().to_dict()
        group_sizes = {str(k): int(counts[k]) for k in sorted(counts.keys())}

        if len(group_sizes) < 2:
            return FeasibilityReport(
                feasible=False,
                reasons=["degenerate: grouping column has < 2 distinct levels after NA removal"],
                n_pairwise_complete=n_valid,
                group_sizes=group_sizes,
            )

        reasons: list[str] = []
        for g_label, g_cnt in group_sizes.items():
            if g_cnt < min_group_n:
                reasons.append(f"group '{g_label}' has n={g_cnt} < min_group_n ({min_group_n})")
        if reasons:
            return FeasibilityReport(
                feasible=False,
                reasons=reasons,
                n_pairwise_complete=n_valid,
                group_sizes=group_sizes,
            )

        return FeasibilityReport(
            feasible=True,
            reasons=[],
            n_pairwise_complete=n_valid,
            group_sizes=group_sizes,
        )

    if rel == RelationshipType.NUM_CATEGORICAL:
        num_a = pd.to_numeric(sub[col_a], errors="coerce")
        valid_mask = np.isfinite(num_a)
        sub_valid = sub.loc[valid_mask]
        num_valid = num_a.loc[valid_mask]
        n_valid = int(len(sub_valid))

        if n_valid < min_n:
            return FeasibilityReport(
                feasible=False,
                reasons=[f"n_pairwise_complete={n_valid} < min_n_pairwise ({min_n})"],
                n_pairwise_complete=n_valid,
            )

        grp = _normalize_group_series(sub_valid[col_b])
        reasons = []
        if config.hypotheses.lump_rare_levels:
            grp, lumped = _apply_rare_level_lumping(grp, config.hypotheses.rare_level_min_fraction)
            if lumped:
                reasons.append(f"lumped_rare_levels: {', '.join(lumped)} -> Other")

        counts = grp.value_counts().to_dict()
        dropped_levels = sorted([str(k) for k, v in counts.items() if int(v) < min_group_n])
        kept_sizes = {
            str(k): int(counts[k]) for k in sorted(counts.keys()) if int(counts[k]) >= min_group_n
        }

        if dropped_levels:
            dropped_desc = ", ".join(f"'{lvl}' (n={int(counts[lvl])})" for lvl in dropped_levels)
            reasons.append(f"dropped_levels (< min_group_n={min_group_n}): {dropped_desc}")

        if len(kept_sizes) < 2:
            reasons.append(
                f"fewer than 2 levels remain with n >= min_group_n ({min_group_n})"
            )
            return FeasibilityReport(
                feasible=False,
                reasons=reasons,
                n_pairwise_complete=n_valid,
                group_sizes=kept_sizes,
                dropped_levels=dropped_levels,
            )

        kept_mask = grp.isin(kept_sizes.keys())
        n_remaining = int(kept_mask.sum())
        if n_remaining < min_n:
            reasons.append(
                f"remaining n={n_remaining} after rare-level filter < min_n_pairwise ({min_n})"
            )
            return FeasibilityReport(
                feasible=False,
                reasons=reasons,
                n_pairwise_complete=n_remaining,
                group_sizes=kept_sizes,
                dropped_levels=dropped_levels,
            )

        if num_valid.loc[kept_mask].nunique() < 2:
            reasons.append("degenerate: numeric outcome is constant on remaining levels")
            return FeasibilityReport(
                feasible=False,
                reasons=reasons,
                n_pairwise_complete=n_remaining,
                group_sizes=kept_sizes,
                dropped_levels=dropped_levels,
            )

        return FeasibilityReport(
            feasible=True,
            reasons=reasons,
            n_pairwise_complete=n_remaining,
            group_sizes=kept_sizes,
            dropped_levels=dropped_levels,
        )

    if rel == RelationshipType.CAT_CAT:
        ser_a = _normalize_group_series(sub[col_a])
        ser_b = _normalize_group_series(sub[col_b])
        reasons = []

        if config.hypotheses.lump_rare_levels:
            ser_a, lumped_a = _apply_rare_level_lumping(
                ser_a, config.hypotheses.rare_level_min_fraction
            )
            ser_b, lumped_b = _apply_rare_level_lumping(
                ser_b, config.hypotheses.rare_level_min_fraction
            )
            if lumped_a:
                reasons.append(f"lumped_rare_levels({col_a}): {', '.join(lumped_a)} -> Other")
            if lumped_b:
                reasons.append(f"lumped_rare_levels({col_b}): {', '.join(lumped_b)} -> Other")

        counts_a = ser_a.value_counts().to_dict()
        counts_b = ser_b.value_counts().to_dict()

        dropped_a = sorted([str(k) for k, v in counts_a.items() if int(v) < min_group_n])
        dropped_b = sorted([str(k) for k, v in counts_b.items() if int(v) < min_group_n])
        kept_a = {str(k) for k, v in counts_a.items() if int(v) >= min_group_n}
        kept_b = {str(k) for k, v in counts_b.items() if int(v) >= min_group_n}

        dropped_levels = [f"{col_a}:{lvl}" for lvl in dropped_a] + [
            f"{col_b}:{lvl}" for lvl in dropped_b
        ]
        if dropped_levels:
            reasons.append(
                f"dropped_levels (< min_group_n={min_group_n}): {', '.join(dropped_levels)}"
            )

        mask = ser_a.isin(kept_a) & ser_b.isin(kept_b)
        ser_a_kept = ser_a.loc[mask]
        ser_b_kept = ser_b.loc[mask]
        n_remaining = int(mask.sum())

        marg_a = ser_a_kept.value_counts().to_dict()
        marg_b = ser_b_kept.value_counts().to_dict()

        if len(marg_a) < 2 or len(marg_b) < 2:
            reasons.append("degenerate: contingency table has < 2 rows or < 2 columns after filter")
            return FeasibilityReport(
                feasible=False,
                reasons=reasons,
                n_pairwise_complete=n_remaining,
                dropped_levels=dropped_levels,
            )

        if n_remaining < min_n:
            reasons.append(
                f"remaining n={n_remaining} after rare-level filter < min_n_pairwise ({min_n})"
            )
            return FeasibilityReport(
                feasible=False,
                reasons=reasons,
                n_pairwise_complete=n_remaining,
                dropped_levels=dropped_levels,
            )

        # Expected count under independence computed strictly from univariate marginals
        min_expected = float((min(marg_a.values()) * min(marg_b.values())) / n_remaining)
        return FeasibilityReport(
            feasible=True,
            reasons=reasons,
            n_pairwise_complete=n_remaining,
            min_expected_count=round(min_expected, 4),
            dropped_levels=dropped_levels,
        )

    return FeasibilityReport(
        feasible=False,
        reasons=[f"unsupported relationship type: {rel.value}"],
        n_pairwise_complete=n_pairwise,
    )


def screen_hypotheses(
    hypotheses: Sequence[Hypothesis],
    df: pd.DataFrame,
    schema: dict[str, ColumnSchemaEntry],
    config: PipelineConfig,
) -> list[Hypothesis]:
    """Attach FeasibilityReports to every hypothesis and mark infeasible ones."""
    screened: list[Hypothesis] = []
    for hyp in hypotheses:
        report = assess_feasibility(hyp, df, schema, config)
        status = "proposed" if report.feasible else "skipped_infeasible"
        screened.append(hyp.model_copy(update={"feasibility": report, "status": status}))
    return screened

