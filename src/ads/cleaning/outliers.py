"""Outlier detection and configurable handling (Step 10, Section 9.10)."""

from __future__ import annotations

import numpy as np
import pandas as pd

from ads.cleaning.log import CleaningLog
from ads.config import PipelineConfig
from ads.schemas import OutlierColumnReport, SemanticType


def detect_outliers_pre_imputation(
    df: pd.DataFrame,
    semantic_types: dict[str, SemanticType],
    config: PipelineConfig,
) -> tuple[dict[str, OutlierColumnReport], dict[str, pd.Series]]:
    """Detect outliers on type-converted data after validity rules and before imputation (Section 9.10).

    Returns:
        (outlier_reports_by_col, flagged_boolean_masks_by_col)
    """
    prof_cfg = config.profiling
    action = config.cleaning.outlier_action
    n_rows = len(df)

    reports: dict[str, OutlierColumnReport] = {}
    masks: dict[str, pd.Series] = {}

    if n_rows == 0:
        return reports, masks

    for col in df.columns:
        sem = semantic_types.get(col, SemanticType.UNKNOWN)
        if sem not in {SemanticType.NUMERIC_CONTINUOUS, SemanticType.NUMERIC_DISCRETE}:
            continue

        s = pd.to_numeric(df[col], errors="coerce")
        valid = s.dropna().astype("float64")
        if len(valid) < 4:
            continue

        q1 = float(np.percentile(valid, 25))
        q3 = float(np.percentile(valid, 75))
        iqr = q3 - q1

        if iqr > 0:
            low_1_5 = q1 - prof_cfg.outlier_iqr_mild * iqr
            high_1_5 = q3 + prof_cfg.outlier_iqr_mild * iqr
            low_3_0 = q1 - prof_cfg.outlier_iqr_extreme * iqr
            high_3_0 = q3 + prof_cfg.outlier_iqr_extreme * iqr
            iqr_1_5_mask = s.notna() & ((s < low_1_5) | (s > high_1_5))
            iqr_3_0_mask = s.notna() & ((s < low_3_0) | (s > high_3_0))
        else:
            low_1_5 = high_1_5 = low_3_0 = high_3_0 = None
            iqr_1_5_mask = pd.Series(False, index=df.index)
            iqr_3_0_mask = pd.Series(False, index=df.index)

        med = float(np.median(valid))
        abs_dev = np.abs(s - med)
        mad = float(np.median( np.abs(valid - med) ))

        if mad > 1e-12:
            mod_z = 0.6745 * abs_dev / mad
            modz_mask = s.notna() & (mod_z > prof_cfg.outlier_modz_threshold)
        else:
            mean_ad = float(np.mean(np.abs(valid - med)))
            if mean_ad > 1e-12:
                mod_z = abs_dev / (1.253314 * mean_ad)
                modz_mask = s.notna() & (mod_z > prof_cfg.outlier_modz_threshold)
            else:
                modz_mask = pd.Series(False, index=df.index)

        flagged_mask = iqr_1_5_mask | modz_mask
        extreme_mask = iqr_3_0_mask

        n_flagged = int(flagged_mask.sum())
        n_extreme = int(extreme_mask.sum())
        pct_flagged = round(n_flagged / len(valid), 6) if len(valid) > 0 else 0.0

        if n_flagged > 0:
            flagged_vals = s[flagged_mask].astype(float)
            min_f = round(float(flagged_vals.min()), 6)
            max_f = round(float(flagged_vals.max()), 6)
            sample_idx = [int(i) for i in df.index[flagged_mask].tolist()[:5]]
        else:
            min_f = None
            max_f = None
            sample_idx = []

        reports[col] = OutlierColumnReport(
            column=col,
            method="iqr_and_modz",
            n_flagged=n_flagged,
            n_extreme=n_extreme,
            pct_flagged=pct_flagged,
            iqr_1_5_lower=round(low_1_5, 6) if low_1_5 is not None else None,
            iqr_1_5_upper=round(high_1_5, 6) if high_1_5 is not None else None,
            iqr_3_0_lower=round(low_3_0, 6) if low_3_0 is not None else None,
            iqr_3_0_upper=round(high_3_0, 6) if high_3_0 is not None else None,
            min_flagged_value=min_f,
            max_flagged_value=max_f,
            indices_flagged_sample=sample_idx,
            action_taken=action,
        )
        masks[col] = flagged_mask

    return reports, masks


def step10_apply_outlier_action(
    df_conservative: pd.DataFrame,
    df_imputed: pd.DataFrame,
    outlier_reports: dict[str, OutlierColumnReport],
    outlier_masks: dict[str, pd.Series],
    log: CleaningLog,
    config: PipelineConfig,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Step 10: Log flagged outliers and optionally cap or remove in imputed output only (Section 9.10)."""
    df_cons = df_conservative
    df_imp = df_imputed.copy()
    action = config.cleaning.outlier_action
    n_rows_cons = len(df_cons)

    # 1. Always log flagged outliers for columns where n_flagged > 0
    for col, rep in outlier_reports.items():
        if rep.n_flagged == 0:
            continue

        mask = outlier_masks[col]
        ex_vals = [f"{float(v):g}" for v in df_cons.loc[mask, col].dropna().head(5).tolist()]

        if action == "flag":
            log.add(
                step="handle_outliers",
                column=col,
                action="flagged_outliers",
                n_cells_affected=0,
                n_rows_affected=rep.n_flagged,
                rows_before=n_rows_cons,
                rows_after=n_rows_cons,
                reason=(
                    f"Flagged {rep.n_flagged} outlier(s) ({rep.pct_flagged:.1%}) and "
                    f"{rep.n_extreme} extreme outlier(s) in '{col}' (action=flag; values untouched)."
                ),
                before_examples=ex_vals,
                after_examples=ex_vals,
                parameters={
                    "iqr_1_5_bounds": [rep.iqr_1_5_lower, rep.iqr_1_5_upper],
                    "iqr_3_0_bounds": [rep.iqr_3_0_lower, rep.iqr_3_0_upper],
                    "sample_indices": rep.indices_flagged_sample,
                },
                severity="info",
            )
        elif action == "cap":
            if (
                col in df_imp.columns
                and rep.iqr_1_5_lower is not None
                and rep.iqr_1_5_upper is not None
            ):
                s_imp = pd.to_numeric(df_imp[col], errors="coerce")
                cap_mask = s_imp.notna() & (
                    (s_imp < rep.iqr_1_5_lower) | (s_imp > rep.iqr_1_5_upper)
                )
                n_capped = int(cap_mask.sum())
                if n_capped > 0:
                    c_before = [f"{float(v):g}" for v in s_imp[cap_mask].head(5).tolist()]
                    clipped = s_imp.clip(lower=rep.iqr_1_5_lower, upper=rep.iqr_1_5_upper)
                    if pd.api.types.is_integer_dtype(df_imp[col].dtype):
                        df_imp[col] = clipped.round().astype("Int64")
                    else:
                        df_imp[col] = clipped.astype("float64")
                    c_after = [
                        f"{float(v):g}" for v in df_imp.loc[cap_mask, col].head(5).tolist()
                    ]
                    log.add(
                        step="handle_outliers",
                        column=col,
                        action="capped_outliers_imputed",
                        n_cells_affected=n_capped,
                        n_rows_affected=n_capped,
                        rows_before=len(df_imp),
                        rows_after=len(df_imp),
                        reason=(
                            f"Winsorized {n_capped} outlier(s) in '{col}' to 1.5xIQR fences "
                            f"[{rep.iqr_1_5_lower}, {rep.iqr_1_5_upper}] in imputed output only."
                        ),
                        before_examples=c_before,
                        after_examples=c_after,
                        parameters={
                            "lower": rep.iqr_1_5_lower,
                            "upper": rep.iqr_1_5_upper,
                        },
                        severity="warning",
                    )

    if action == "remove" and len(df_imp) > 0:
        # Combine outlier masks aligned to df_imp rows (only if df_imp has same index prior to target drop)
        combined_remove = pd.Series(False, index=df_imp.index)
        for col, rep in outlier_reports.items():
            if col not in df_imp.columns or rep.n_flagged == 0:
                continue
            s_imp = pd.to_numeric(df_imp[col], errors="coerce")
            if rep.iqr_1_5_lower is not None and rep.iqr_1_5_upper is not None:
                col_out = s_imp.notna() & (
                    (s_imp < rep.iqr_1_5_lower) | (s_imp > rep.iqr_1_5_upper)
                )
                combined_remove = combined_remove | col_out

        n_to_remove = int(combined_remove.sum())
        max_frac = config.cleaning.outlier_remove_max_row_fraction
        if n_to_remove > 0:
            frac = n_to_remove / len(df_imp)
            if frac > max_frac:
                log.add(
                    step="handle_outliers",
                    column=None,
                    action="refused_outlier_removal",
                    n_cells_affected=0,
                    n_rows_affected=n_to_remove,
                    rows_before=len(df_imp),
                    rows_after=len(df_imp),
                    reason=(
                        f"Refused outlier row removal in imputed output: would drop {n_to_remove} rows "
                        f"({frac:.1%} > max allowed {max_frac:.1%})."
                    ),
                    severity="warning",
                )
            else:
                rows_before = len(df_imp)
                df_imp = df_imp.loc[~combined_remove].reset_index(drop=True)
                rows_after = len(df_imp)
                log.add(
                    step="handle_outliers",
                    column=None,
                    action="removed_outlier_rows_imputed",
                    n_cells_affected=n_to_remove * len(df_imp.columns),
                    n_rows_affected=n_to_remove,
                    rows_before=rows_before,
                    rows_after=rows_after,
                    reason=f"Removed {n_to_remove} outlier row(s) ({frac:.1%}) in imputed output only.",
                    severity="warning",
                )

    return df_cons, df_imp

