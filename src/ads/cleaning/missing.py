"""Missing-token normalization (Step 3) and missing-value handling (Step 9) (Sections 9.3, 9.9)."""

from __future__ import annotations

import numpy as np
import pandas as pd

from ads.cleaning.log import CleaningLog
from ads.config import PipelineConfig
from ads.schemas import DroppedColumnRecord, SemanticType


def step3_normalize_missing_tokens(
    df: pd.DataFrame,
    log: CleaningLog,
    config: PipelineConfig,
) -> pd.DataFrame:
    """Step 3: Replace configured placeholder tokens and empty strings with NaN (Section 9.3)."""
    out = df.copy()
    n_rows = len(out)
    if n_rows == 0:
        return out

    effective_tokens = config.effective_missing_tokens()
    # Map lowercase token -> canonical token display name (excluding empty string)
    token_lookup = {
        t.strip().lower(): t.strip() for t in effective_tokens if t.strip() != ""
    }
    warn_ratio = config.cleaning.missing_token_warning_ratio

    for col in out.columns:
        s = out[col]
        # Only inspect object / string columns or columns that still contain strings
        if not (pd.api.types.is_object_dtype(s) or pd.api.types.is_string_dtype(s)):
            continue

        not_na = s.notna()
        if not not_na.any():
            continue

        str_vals = s[not_na].astype(str).str.strip()
        lower_vals = str_vals.str.lower()

        empty_mask = str_vals == ""
        token_mask = (~empty_mask) & lower_vals.isin(token_lookup)
        replace_mask = empty_mask | token_mask

        n_empty = int(empty_mask.sum())
        n_tokens = int(token_mask.sum())

        # Replace empty strings with np.nan silently or log if non-empty placeholder tokens were found
        if n_empty > 0:
            empty_indices = str_vals.index[empty_mask]
            out.loc[empty_indices, col] = np.nan

        if n_tokens > 0:
            token_indices = str_vals.index[token_mask]
            matched_raw = str_vals.loc[token_indices]
            token_counts = matched_raw.value_counts().to_dict()
            before_ex = matched_raw.head(5).tolist()
            after_ex = ["NaN"] * len(before_ex)

            out.loc[token_indices, col] = np.nan

            max_single_token_count = max(token_counts.values()) if token_counts else 0
            ratio = n_tokens / n_rows if n_rows > 0 else 0.0
            max_tok_ratio = max_single_token_count / n_rows if n_rows > 0 else 0.0
            severity = (
                "warning"
                if (ratio > warn_ratio or max_tok_ratio > warn_ratio)
                else "info"
            )

            tok_summary = ", ".join(f"{k!r}: {v}" for k, v in token_counts.items())
            log.add(
                step="normalize_missing_tokens",
                column=col,
                action="converted_to_NaN",
                n_cells_affected=n_tokens,
                n_rows_affected=n_tokens,
                rows_before=n_rows,
                rows_after=n_rows,
                reason=f"Replaced placeholder missing token(s) ({tok_summary}) with NaN.",
                before_examples=before_ex,
                after_examples=after_ex,
                parameters={"token_counts": token_counts, "ratio": round(ratio, 4)},
                severity=severity,
            )

    return out


def step9_handle_missing_values(
    df_conservative: pd.DataFrame,
    semantic_types: dict[str, SemanticType],
    high_missing_cols_to_drop: list[str],
    dropped_columns: list[DroppedColumnRecord],
    log: CleaningLog,
    config: PipelineConfig,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Step 9: Produce Output A (df_clean_conservative) and Output B (df_clean_imputed) (Section 9.9).

    - Output A (conservative): No imputation; remaining NaNs stay NaN.
    - Output B (imputed):
        * Drops columns with pct_missing > column_drop_threshold (0.80).
        * Drops rows with missing target if config.cleaning.target_missing == 'drop'.
        * Adds `<col>__was_missing` boolean indicator for columns with pct_missing >= 5%.
        * Imputes numeric columns with median.
        * Imputes categorical/binary columns with mode, or level 'Missing' if pct_missing >= 5%.
        * Leaves datetime NaT/NaN untouched.
    """
    df_cons = df_conservative.copy()
    df_imp = df_conservative.copy()
    n_rows_start = len(df_imp)

    # 1. Drop >80% missing columns in imputed output only (Section 9.8 DECISION)
    cols_to_drop_imp = [c for c in high_missing_cols_to_drop if c in df_imp.columns]
    if cols_to_drop_imp:
        df_imp = df_imp.drop(columns=cols_to_drop_imp)
        for col in cols_to_drop_imp:
            dropped_columns.append(
                DroppedColumnRecord(
                    name=col,
                    reason=f"pct_missing > {config.cleaning.column_drop_threshold:.0%}",
                    output_target="imputed_only",
                )
            )
            log.add(
                step="handle_missing_values",
                column=col,
                action="dropped_column_imputed_only",
                n_cells_affected=n_rows_start,
                n_rows_affected=0,
                rows_before=n_rows_start,
                rows_after=n_rows_start,
                reason=(
                    f"Dropped column '{col}' in imputed output only "
                    f"(pct_missing > {config.cleaning.column_drop_threshold:.0%}); kept as excluded in conservative."
                ),
                severity="warning",
            )

    # 2. Target missing policy in imputed output (never impute target; drop rows if target_missing == 'drop')
    target_col = config.target
    if target_col and target_col in df_imp.columns:
        target_na_mask = df_imp[target_col].isna()
        n_target_na = int(target_na_mask.sum())
        if n_target_na > 0 and config.cleaning.target_missing == "drop":
            rows_before = len(df_imp)
            df_imp = df_imp.loc[~target_na_mask].reset_index(drop=True)
            rows_after = len(df_imp)
            log.add(
                step="handle_missing_values",
                column=target_col,
                action="dropped_missing_target_rows_imputed",
                n_cells_affected=n_target_na,
                n_rows_affected=n_target_na,
                rows_before=rows_before,
                rows_after=rows_after,
                reason=f"Dropped {n_target_na} row(s) with missing target '{target_col}' in imputed output.",
                severity="warning",
            )

    n_rows_imp = len(df_imp)
    if n_rows_imp == 0:
        return df_cons, df_imp

    ind_thresh = config.cleaning.missing_indicator_threshold
    cat_level_thresh = config.cleaning.categorical_missing_as_level_threshold

    # Iterate over original columns present in df_imp
    orig_cols = list(df_imp.columns)
    indicator_cols: dict[str, pd.Series] = {}

    for col in orig_cols:
        if target_col and col == target_col:
            continue

        na_mask = df_imp[col].isna()
        n_miss = int(na_mask.sum())
        if n_miss == 0:
            continue

        pct_miss = n_miss / n_rows_imp
        sem = semantic_types.get(col, SemanticType.UNKNOWN)

        # Add `<col>__was_missing` indicator if pct_missing >= 5% (Section 9.9)
        if pct_miss >= ind_thresh:
            ind_col_name = f"{col}__was_missing"
            indicator_cols[ind_col_name] = na_mask.astype(bool)

        if sem == SemanticType.DATETIME:
            log.add(
                step="handle_missing_values",
                column=col,
                action="left_datetime_missing",
                n_cells_affected=0,
                n_rows_affected=0,
                rows_before=n_rows_imp,
                rows_after=n_rows_imp,
                reason=f"Datetime column '{col}' has {n_miss} missing value(s); left un-imputed per policy.",
                severity="info",
            )
            continue

        if sem in {SemanticType.ID_LIKE, SemanticType.FREE_TEXT, SemanticType.CONSTANT}:
            continue

        is_num_dtype = pd.api.types.is_numeric_dtype(df_imp[col])
        if sem in {SemanticType.NUMERIC_CONTINUOUS, SemanticType.NUMERIC_DISCRETE} or is_num_dtype:
            valid_nums = pd.to_numeric(df_imp[col].dropna(), errors="coerce").dropna()
            if len(valid_nums) == 0:
                continue
            med_val = float(valid_nums.median())
            if pd.api.types.is_integer_dtype(df_imp[col].dtype):
                fill_val: float | int = int(round(med_val))
            else:
                fill_val = round(med_val, 6)

            df_imp.loc[na_mask, col] = fill_val
            log.add(
                step="handle_missing_values",
                column=col,
                action="imputed_median",
                n_cells_affected=n_miss,
                n_rows_affected=n_miss,
                rows_before=n_rows_imp,
                rows_after=n_rows_imp,
                reason=f"Imputed {n_miss} missing cell(s) ({pct_miss:.1%}) in '{col}' with median={fill_val} (imputed output only).",
                before_examples=["NaN"] * min(5, n_miss),
                after_examples=[str(fill_val)] * min(5, n_miss),
                parameters={"strategy": "median", "fill_value": fill_val, "pct_missing": round(pct_miss, 4)},
                severity="info",
            )
        else:
            # Categorical / binary string imputation
            if pct_miss >= cat_level_thresh:
                fill_str = "Missing"
                strategy = "missing_level"
            else:
                non_na = df_imp[col].dropna().astype(str)
                if len(non_na) == 0:
                    continue
                vc = non_na.value_counts()
                sorted_vc = sorted(vc.items(), key=lambda kv: (-int(kv[1]), str(kv[0])))
                fill_str = str(sorted_vc[0][0])
                strategy = "mode"

            df_imp.loc[na_mask, col] = fill_str
            log.add(
                step="handle_missing_values",
                column=col,
                action=f"imputed_{strategy}",
                n_cells_affected=n_miss,
                n_rows_affected=n_miss,
                rows_before=n_rows_imp,
                rows_after=n_rows_imp,
                reason=(
                    f"Imputed {n_miss} missing cell(s) ({pct_miss:.1%}) in '{col}' "
                    f"with {strategy}={fill_str!r} (imputed output only)."
                ),
                before_examples=["NaN"] * min(5, n_miss),
                after_examples=[fill_str] * min(5, n_miss),
                parameters={"strategy": strategy, "fill_value": fill_str, "pct_missing": round(pct_miss, 4)},
                severity="info",
            )

    # Append indicator columns to df_imp
    for ind_name, ind_series in indicator_cols.items():
        df_imp[ind_name] = ind_series

    return df_cons, df_imp

