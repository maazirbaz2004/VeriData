"""Core cleaning pipeline steps: Steps 1, 2, 5, 6, 7, 8, and 11 (Section 9)."""

from __future__ import annotations

import re
import warnings
from datetime import date

import numpy as np
import pandas as pd

from ads.cleaning.log import CleaningLog
from ads.config import PipelineConfig
from ads.schemas import DroppedColumnRecord, SemanticType
from ads.type_inference import (
    _EXPLICIT_DATE_FORMATS,
    clean_numeric_token,
    try_parse_numeric_series,
)

_UNICODE_SPACE_RE = re.compile(r"\u00a0")
_ZERO_WIDTH_RE = re.compile(r"[\u200b\u200c\u200d\ufeff]")
_MULTI_WS_RE = re.compile(r"[ \t]{2,}|\t")
_UNNAMED_INDEX_RE = re.compile(r"^unnamed:\s*\d+$", re.IGNORECASE)
_NON_NEG_NAME_RE = re.compile(
    r"(?:^|_)(?:age|count|price|charges|amount|tenure|tenure_months|income|spend|monthly_spend|balance)(?:$|_)",
    re.IGNORECASE,
)
_PCT_NAME_RE = re.compile(r"(?:%|pct|percent)", re.IGNORECASE)


class CleaningInvariantError(RuntimeError):
    """Raised when Step 11 post-cleaning invariant validation fails (Section 9.11)."""


def _to_snake_case(name: str) -> str:
    s = re.sub(r"[\s\-]+", "_", name.strip())
    s = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s)
    return re.sub(r"_+", "_", s).lower().strip("_")


def step1_normalize_column_names(
    df: pd.DataFrame,
    log: CleaningLog,
    config: PipelineConfig,
    ingestion_name_changes: dict[str, str] | None = None,
) -> tuple[pd.DataFrame, dict[str, str]]:
    """Step 1: Strip and collapse whitespace in column names; optionally snake_case (Section 9.1)."""
    out = df.copy()
    n_rows = len(out)
    name_map: dict[str, str] = {}

    if ingestion_name_changes:
        for orig_k, new_v in ingestion_name_changes.items():
            # Record header normalizations performed at load time
            if not orig_k.startswith("<empty_"):
                name_map[orig_k] = new_v

    new_cols: list[str] = []
    seen: dict[str, int] = {}

    for col in out.columns:
        cleaned = _ZERO_WIDTH_RE.sub("", str(col))
        cleaned = _UNICODE_SPACE_RE.sub(" ", cleaned)
        cleaned = _MULTI_WS_RE.sub(" ", cleaned).strip()
        if config.cleaning.snake_case_columns:
            cleaned = _to_snake_case(cleaned)
        if not cleaned:
            cleaned = "unnamed_col"

        if cleaned in seen:
            seen[cleaned] += 1
            final_name = f"{cleaned}.{seen[cleaned]}"
        else:
            seen[cleaned] = 0
            final_name = cleaned

        new_cols.append(final_name)
        if final_name != col:
            name_map[str(col)] = final_name

    out.columns = new_cols

    if name_map:
        before_ex = list(name_map.keys())[:5]
        after_ex = [name_map[k] for k in before_ex]
        log.add(
            step="normalize_column_names",
            column=None,
            action="normalized_headers",
            n_cells_affected=len(name_map),
            n_rows_affected=0,
            rows_before=n_rows,
            rows_after=n_rows,
            reason=f"Normalized {len(name_map)} column name(s) (stripped whitespace/BOM).",
            before_examples=before_ex,
            after_examples=after_ex,
            parameters={"name_map": name_map, "snake_case": config.cleaning.snake_case_columns},
            severity="info",
        )

    return out, name_map


def step2_clean_whitespace_and_unicode(
    df: pd.DataFrame,
    log: CleaningLog,
) -> pd.DataFrame:
    """Step 2: Strip leading/trailing whitespace, collapse internal spaces, remove unicode oddities (Section 9.2)."""
    out = df.copy()
    n_rows = len(out)
    if n_rows == 0:
        return out

    for col in out.columns:
        s = out[col]
        if not (pd.api.types.is_object_dtype(s) or pd.api.types.is_string_dtype(s)):
            continue

        not_na = s.notna()
        if not not_na.any():
            continue

        raw_vals = s[not_na].astype(str)
        cleaned_vals = (
            raw_vals.str.replace(_ZERO_WIDTH_RE, "", regex=True)
            .str.replace(_UNICODE_SPACE_RE, " ", regex=True)
            .str.strip()
            .str.replace(_MULTI_WS_RE, " ", regex=True)
        )

        # Ignore whitespace-only strings that become empty '' here ONLY if we still record them;
        # Wait: changing ' ' -> '' is also a whitespace cleanup or missing token cleanup.
        changed_mask = raw_vals != cleaned_vals
        n_changed = int(changed_mask.sum())

        if n_changed > 0:
            changed_idx = raw_vals.index[changed_mask]
            before_ex = [repr(v) for v in raw_vals.loc[changed_idx].head(5).tolist()]
            after_ex = [repr(v) for v in cleaned_vals.loc[changed_idx].head(5).tolist()]
            out.loc[not_na, col] = cleaned_vals

            log.add(
                step="clean_whitespace_unicode",
                column=col,
                action="stripped_and_normalized_ws",
                n_cells_affected=n_changed,
                n_rows_affected=n_changed,
                rows_before=n_rows,
                rows_after=n_rows,
                reason="Stripped leading/trailing whitespace, collapsed internal spaces, and cleaned unicode chars.",
                before_examples=before_ex,
                after_examples=after_ex,
                severity="info",
            )

    return out


def step5_convert_types(
    df: pd.DataFrame,
    semantic_types: dict[str, SemanticType],
    log: CleaningLog,
    config: PipelineConfig,
) -> pd.DataFrame:
    """Step 5: Convert columns to their inferred semantic dtypes and log coercions (Section 9.5)."""
    out = df.copy()
    n_rows = len(out)
    if n_rows == 0:
        return out

    for col in out.columns:
        sem = semantic_types.get(col, SemanticType.UNKNOWN)
        s = out[col]

        # Numeric columns (including numeric 0/1 binaries)
        if sem in {SemanticType.NUMERIC_CONTINUOUS, SemanticType.NUMERIC_DISCRETE, SemanticType.BINARY}:
            if pd.api.types.is_numeric_dtype(s) and not pd.api.types.is_bool_dtype(s):
                # Already numeric (e.g. re-run for idempotence)
                valid_nums = s.dropna()
                if sem == SemanticType.NUMERIC_DISCRETE and len(valid_nums) > 0:
                    if bool(np.all(np.isclose(valid_nums % 1, 0.0, atol=1e-9))):
                        out[col] = s.round().astype("Int64")
                elif sem == SemanticType.NUMERIC_CONTINUOUS:
                    out[col] = s.astype("float64")
                continue

            not_na = s.notna()
            if not not_na.any():
                if sem in {SemanticType.NUMERIC_CONTINUOUS, SemanticType.NUMERIC_DISCRETE}:
                    out[col] = pd.Series([np.nan] * n_rows, index=out.index, dtype="float64")
                continue

            non_null_str = s[not_na].astype(str)
            parsed_num, parse_rate, _, n_failed = try_parse_numeric_series(non_null_str)

            # For BINARY, only convert to numeric if >= numeric_parse_threshold are numbers (0/1)
            if sem == SemanticType.BINARY and parse_rate < config.type_inference.numeric_parse_threshold:
                continue

            # Count how many valid cells had formatting decorators ($, commas, %, parentheses, sci notation)
            n_decorated = 0
            dec_before: list[str] = []
            dec_after: list[str] = []
            has_pct_symbol = False

            valid_mask = parsed_num.notna()
            for idx_k, raw_v in non_null_str[valid_mask].items():
                if "%" in raw_v:
                    has_pct_symbol = True
                cleaned_tok, had_dec = clean_numeric_token(raw_v)
                if had_dec or ("e" in cleaned_tok.lower()):
                    n_decorated += 1
                    if len(dec_before) < 5:
                        dec_before.append(raw_v)
                        dec_after.append(f"{parsed_num.loc[idx_k]:g}")

            # Log coerced_to_NaN if any non-null cells failed to parse (Section 9.5)
            if n_failed > 0:
                failed_mask = ~valid_mask
                failed_vals = non_null_str[failed_mask]
                f_before = failed_vals.head(5).tolist()
                f_after = ["NaN"] * len(f_before)
                log.add(
                    step="convert_types",
                    column=col,
                    action="coerced_to_NaN",
                    n_cells_affected=n_failed,
                    n_rows_affected=n_failed,
                    rows_before=n_rows,
                    rows_after=n_rows,
                    reason=f"Coerced {n_failed} unparseable numeric token(s) in '{col}' to NaN.",
                    before_examples=f_before,
                    after_examples=f_after,
                    severity="warning",
                )

            # Build full numeric series
            full_num = pd.Series(np.nan, index=out.index, dtype="float64")
            full_num.loc[parsed_num.index] = parsed_num.astype("float64")

            valid_vals = full_num.dropna()
            all_int = len(valid_vals) > 0 and bool(
                np.all(np.isclose(valid_vals % 1, 0.0, atol=1e-9))
            )

            if sem == SemanticType.NUMERIC_DISCRETE and all_int:
                out[col] = full_num.round().astype("Int64")
                target_dtype = "Int64"
            elif sem == SemanticType.BINARY and all_int:
                out[col] = full_num.round().astype("Int64")
                target_dtype = "Int64"
            else:
                out[col] = full_num.astype("float64")
                target_dtype = "float64"

            pct_note = " (percentage symbol stripped without dividing by 100)" if has_pct_symbol else ""
            if n_decorated > 0:
                log.add(
                    step="convert_types",
                    column=col,
                    action="cast_dtype",
                    n_cells_affected=n_decorated,
                    n_rows_affected=n_decorated,
                    rows_before=n_rows,
                    rows_after=n_rows,
                    reason=(
                        f"Converted '{col}' to {target_dtype}, stripping numeric formatting "
                        f"on {n_decorated} cell(s){pct_note}."
                    ),
                    before_examples=dec_before,
                    after_examples=dec_after,
                    parameters={"target_dtype": target_dtype, "has_percent": has_pct_symbol},
                    severity="info",
                )

        elif sem == SemanticType.DATETIME:
            not_na = s.notna()
            if not not_na.any():
                continue

            non_null_str = s[not_na].astype(str).str.strip()
            parsed_dt = pd.Series(pd.NaT, index=non_null_str.index, dtype="datetime64[ns]")
            unparsed_mask = pd.Series(True, index=non_null_str.index)

            for fmt in _EXPLICIT_DATE_FORMATS:
                if not unparsed_mask.any():
                    break
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    dt_try = pd.to_datetime(
                        non_null_str[unparsed_mask], format=fmt, errors="coerce"
                    )
                hit_idx = dt_try[dt_try.notna()].index
                parsed_dt.loc[hit_idx] = dt_try.loc[hit_idx]
                unparsed_mask.loc[hit_idx] = False

            if unparsed_mask.any():
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    dt_flex = pd.to_datetime(
                        non_null_str[unparsed_mask],
                        dayfirst=not config.type_inference.month_first_default,
                        errors="coerce",
                    )
                hit_idx = dt_flex[dt_flex.notna()].index
                parsed_dt.loc[hit_idx] = dt_flex.loc[hit_idx]
                unparsed_mask.loc[hit_idx] = False

            n_dt_failed = int(unparsed_mask.sum())
            if n_dt_failed > 0:
                failed_dt_vals = non_null_str[unparsed_mask]
                f_before = failed_dt_vals.head(5).tolist()
                f_after = ["NaN"] * len(f_before)
                log.add(
                    step="convert_types",
                    column=col,
                    action="coerced_to_NaN",
                    n_cells_affected=n_dt_failed,
                    n_rows_affected=n_dt_failed,
                    rows_before=n_rows,
                    rows_after=n_rows,
                    reason=f"Coerced {n_dt_failed} unparseable datetime string(s) in '{col}' to NaN.",
                    before_examples=f_before,
                    after_examples=f_after,
                    severity="warning",
                )

            valid_dt = parsed_dt.dropna()
            # Format as ISO YYYY-MM-DD (or YYYY-MM-DDTHH:MM:SS if non-midnight times exist)
            has_time = len(valid_dt) > 0 and bool(
                ((valid_dt.dt.hour != 0) | (valid_dt.dt.minute != 0) | (valid_dt.dt.second != 0)).any()
            )
            iso_fmt = "%Y-%m-%dT%H:%M:%S" if has_time else "%Y-%m-%d"
            iso_strings = valid_dt.dt.strftime(iso_fmt)

            # Count how many date strings actually changed format (e.g. DD/MM/YYYY -> YYYY-MM-DD)
            orig_valid = non_null_str.loc[valid_dt.index]
            changed_dt_mask = orig_valid != iso_strings
            n_reformatted = int(changed_dt_mask.sum())

            new_col_series = pd.Series(np.nan, index=out.index, dtype="object")
            new_col_series.loc[iso_strings.index] = iso_strings
            out[col] = new_col_series

            if n_reformatted > 0:
                c_idx = orig_valid.index[changed_dt_mask]
                dt_before = orig_valid.loc[c_idx].head(5).tolist()
                dt_after = iso_strings.loc[c_idx].head(5).tolist()
                log.add(
                    step="convert_types",
                    column=col,
                    action="standardized_datetime",
                    n_cells_affected=n_reformatted,
                    n_rows_affected=n_reformatted,
                    rows_before=n_rows,
                    rows_after=n_rows,
                    reason=f"Standardized {n_reformatted} date cell(s) in '{col}' to ISO format ({iso_fmt}).",
                    before_examples=dt_before,
                    after_examples=dt_after,
                    parameters={"iso_format": iso_fmt},
                    severity="info",
                )

    return out


def step6_apply_validity_rules(
    df: pd.DataFrame,
    semantic_types: dict[str, SemanticType],
    log: CleaningLog,
    config: PipelineConfig,
) -> pd.DataFrame:
    """Step 6: Apply domain validity rules (set violations to NaN) + generic sanity checks (Section 9.6)."""
    out = df.copy()
    n_rows = len(out)
    if n_rows == 0:
        return out

    # 1. Configured validity_rules
    for col, rule in config.validity_rules.items():
        if col not in out.columns:
            continue
        s = out[col]
        not_na = s.notna()
        if not not_na.any():
            continue

        viol_mask = pd.Series(False, index=out.index)
        if rule.min is not None or rule.max is not None:
            num_s = pd.to_numeric(s, errors="coerce")
            if rule.min is not None:
                viol_mask = viol_mask | (not_na & (num_s < rule.min))
            if rule.max is not None:
                viol_mask = viol_mask | (not_na & (num_s > rule.max))

        if rule.allowed_values is not None:
            allowed_set = {str(v) for v in rule.allowed_values}
            viol_mask = viol_mask | (not_na & (~s.astype(str).isin(allowed_set)))

        n_viol = int(viol_mask.sum())
        if n_viol > 0:
            v_before = [str(v) for v in s.loc[viol_mask].head(5).tolist()]
            v_after = ["NaN"] * len(v_before)
            if pd.api.types.is_integer_dtype(out[col].dtype):
                out.loc[viol_mask, col] = pd.NA
            else:
                out.loc[viol_mask, col] = np.nan

            log.add(
                step="apply_validity_rules",
                column=col,
                action="invalid_to_NaN",
                n_cells_affected=n_viol,
                n_rows_affected=n_viol,
                rows_before=n_rows,
                rows_after=n_rows,
                reason=(
                    f"Set {n_viol} out-of-range cell(s) in '{col}' to NaN "
                    f"(rule: min={rule.min}, max={rule.max}, allowed={rule.allowed_values})."
                ),
                before_examples=v_before,
                after_examples=v_after,
                parameters=rule.model_dump(exclude_none=True),
                severity="warning",
            )

    # 2. Generic sanity checks (flag only, do not mutate data) (Section 9.6)
    today_iso = date.today().isoformat()
    for col in out.columns:
        sem = semantic_types.get(col, SemanticType.UNKNOWN)
        s = out[col].dropna()
        if len(s) == 0:
            continue

        if sem in {SemanticType.NUMERIC_CONTINUOUS, SemanticType.NUMERIC_DISCRETE}:
            num_s = pd.to_numeric(s, errors="coerce").dropna()
            if _NON_NEG_NAME_RE.search(col):
                neg_vals = num_s[num_s < 0]
                if len(neg_vals) > 0:
                    log.add(
                        step="apply_validity_rules",
                        column=col,
                        action="sanity_check_flag",
                        n_cells_affected=0,
                        n_rows_affected=int(len(neg_vals)),
                        rows_before=n_rows,
                        rows_after=n_rows,
                        reason=f"Generic sanity check: '{col}' has {len(neg_vals)} negative value(s) (flagged only).",
                        before_examples=[f"{v:g}" for v in neg_vals.head(5).tolist()],
                        after_examples=[f"{v:g}" for v in neg_vals.head(5).tolist()],
                        severity="warning",
                    )
            if _PCT_NAME_RE.search(col):
                gt100 = num_s[num_s > 100]
                if len(gt100) > 0:
                    log.add(
                        step="apply_validity_rules",
                        column=col,
                        action="sanity_check_flag",
                        n_cells_affected=0,
                        n_rows_affected=int(len(gt100)),
                        rows_before=n_rows,
                        rows_after=n_rows,
                        reason=f"Generic sanity check: percentage column '{col}' has {len(gt100)} value(s) > 100 (flagged only).",
                        before_examples=[f"{v:g}" for v in gt100.head(5).tolist()],
                        after_examples=[f"{v:g}" for v in gt100.head(5).tolist()],
                        severity="warning",
                    )
        elif sem == SemanticType.DATETIME:
            str_dates = s.astype(str)
            future_dates = str_dates[str_dates > today_iso]
            if len(future_dates) > 0:
                log.add(
                    step="apply_validity_rules",
                    column=col,
                    action="sanity_check_flag",
                    n_cells_affected=0,
                    n_rows_affected=int(len(future_dates)),
                    rows_before=n_rows,
                    rows_after=n_rows,
                    reason=f"Generic sanity check: datetime column '{col}' has {len(future_dates)} future date(s) > {today_iso} (flagged only).",
                    before_examples=future_dates.head(5).tolist(),
                    after_examples=future_dates.head(5).tolist(),
                    severity="warning",
                )

    return out


def step7_handle_duplicates(
    df: pd.DataFrame,
    semantic_types: dict[str, SemanticType],
    log: CleaningLog,
    config: PipelineConfig,
) -> pd.DataFrame:
    """Step 7: Drop exact duplicate rows after normalization, obeying auto/always/never policy (Section 9.7)."""
    out = df.copy()
    n_rows_before = len(out)
    if n_rows_before == 0:
        return out

    policy = config.cleaning.drop_duplicates
    if policy == "never":
        return out

    # Exclude synthetic exported index column ('Unnamed: 0') when comparing rows for duplication
    data_cols = [c for c in out.columns if not _UNNAMED_INDEX_RE.match(c)]
    if not data_cols:
        data_cols = list(out.columns)

    # Identify completely empty rows so they are handled by Step 8 (structural_drops) rather than Step 7
    non_empty_row_mask = out[data_cols].notna().any(axis=1)
    dup_mask = pd.Series(False, index=out.index)
    if non_empty_row_mask.any():
        dup_mask.loc[non_empty_row_mask] = out.loc[non_empty_row_mask, data_cols].duplicated(
            keep="first"
        )

    n_dups = int(dup_mask.sum())
    if n_dups == 0:
        return out

    dup_indices = [int(i) for i in out.index[dup_mask].tolist()]
    dup_rate = n_dups / n_rows_before

    # Check if dataset has an ID column (excluding 'Unnamed: 0')
    has_id_col = any(
        (semantic_types.get(c) == SemanticType.ID_LIKE or c in config.id_columns)
        and not _UNNAMED_INDEX_RE.match(c)
        for c in data_cols
    )

    if policy == "auto" and not has_id_col:
        if (
            len(data_cols) <= config.cleaning.duplicate_auto_max_cols
            or dup_rate > config.cleaning.duplicate_auto_max_rate
        ):
            log.add(
                step="handle_duplicates",
                column=None,
                action="kept_duplicates_warning",
                n_cells_affected=0,
                n_rows_affected=n_dups,
                rows_before=n_rows_before,
                rows_after=n_rows_before,
                reason=(
                    f"Possible legitimate duplicates, kept ({n_dups} duplicate rows = {dup_rate:.1%}, "
                    f"n_cols={len(data_cols)}, no ID column)."
                ),
                parameters={
                    "duplicate_count": n_dups,
                    "duplicate_rate": round(dup_rate, 4),
                    "sample_indices": dup_indices[:20],
                },
                severity="warning",
            )
            return out

    out = out.loc[~dup_mask].reset_index(drop=True)
    n_rows_after = len(out)
    log.add(
        step="handle_duplicates",
        column=None,
        action="dropped_duplicate_rows",
        n_cells_affected=n_dups * len(out.columns),
        n_rows_affected=n_dups,
        rows_before=n_rows_before,
        rows_after=n_rows_after,
        reason=f"Dropped {n_dups} exact duplicate row(s) (kept first occurrence).",
        parameters={"dropped_row_indices_sample": dup_indices[:20]},
        severity="info",
    )
    return out


def step8_structural_drops(
    df: pd.DataFrame,
    semantic_types: dict[str, SemanticType],
    dropped_columns: list[DroppedColumnRecord],
    log: CleaningLog,
    config: PipelineConfig,
) -> tuple[pd.DataFrame, list[str]]:
    """Step 8: Drop empty rows/cols, exported Unnamed: 0 index cols, and >50% missing rows (Section 9.8).

    Returns:
        (df_after_structural_drops, high_missing_cols_for_imputed_drop)
    """
    out = df.copy()

    # 1. Drop exported index columns ('Unnamed: 0') if present
    unnamed_cols = [c for c in out.columns if _UNNAMED_INDEX_RE.match(c)]
    if unnamed_cols:
        n_rows_cur = len(out)
        out = out.drop(columns=unnamed_cols)
        for u_col in unnamed_cols:
            dropped_columns.append(
                DroppedColumnRecord(
                    name=u_col,
                    reason="exported_unnamed_index_column",
                    output_target="both",
                )
            )
            log.add(
                step="structural_drops",
                column=u_col,
                action="dropped_index_column",
                n_cells_affected=n_rows_cur,
                n_rows_affected=0,
                rows_before=n_rows_cur,
                rows_after=n_rows_cur,
                reason=f"Dropped redundant exported index column '{u_col}'.",
                severity="info",
            )

    # 2. Drop fully empty columns (100% missing)
    empty_cols = [c for c in out.columns if out[c].isna().all()]
    if empty_cols:
        n_rows_cur = len(out)
        out = out.drop(columns=empty_cols)
        for e_col in empty_cols:
            dropped_columns.append(
                DroppedColumnRecord(
                    name=e_col,
                    reason="fully_empty_column",
                    output_target="both",
                )
            )
            log.add(
                step="structural_drops",
                column=e_col,
                action="dropped_empty_column",
                n_cells_affected=n_rows_cur,
                n_rows_affected=0,
                rows_before=n_rows_cur,
                rows_after=n_rows_cur,
                reason=f"Dropped fully empty column '{e_col}'.",
                severity="info",
            )

    # 3. Drop fully empty rows (all remaining columns are NaN)
    if len(out) > 0 and len(out.columns) > 0:
        empty_row_mask = out.isna().all(axis=1)
        n_empty_rows = int(empty_row_mask.sum())
        if n_empty_rows > 0:
            rows_before = len(out)
            empty_indices = [int(i) for i in out.index[empty_row_mask].tolist()]
            out = out.loc[~empty_row_mask].reset_index(drop=True)
            rows_after = len(out)
            log.add(
                step="structural_drops",
                column=None,
                action="dropped_empty_rows",
                n_cells_affected=n_empty_rows * len(out.columns),
                n_rows_affected=n_empty_rows,
                rows_before=rows_before,
                rows_after=rows_after,
                reason=f"Dropped {n_empty_rows} fully empty row(s).",
                parameters={"dropped_row_indices_sample": empty_indices[:20]},
                severity="info",
            )

    # 4. Drop rows with pct_missing_in_row > row_drop_threshold (default 0.50) in both outputs
    if len(out) > 0 and len(out.columns) > 0:
        row_miss_pct = out.isna().mean(axis=1)
        high_miss_row_mask = row_miss_pct > config.cleaning.row_drop_threshold
        n_high_miss_rows = int(high_miss_row_mask.sum())
        if n_high_miss_rows > 0:
            rows_before = len(out)
            hm_indices = [int(i) for i in out.index[high_miss_row_mask].tolist()]
            out = out.loc[~high_miss_row_mask].reset_index(drop=True)
            rows_after = len(out)
            log.add(
                step="structural_drops",
                column=None,
                action="dropped_high_missing_rows",
                n_cells_affected=n_high_miss_rows * len(out.columns),
                n_rows_affected=n_high_miss_rows,
                rows_before=rows_before,
                rows_after=rows_after,
                reason=(
                    f"Dropped {n_high_miss_rows} row(s) with > "
                    f"{config.cleaning.row_drop_threshold:.0%} missing values."
                ),
                parameters={"dropped_row_indices_sample": hm_indices[:20]},
                severity="warning",
            )

    # 5. Mark constant, id_like, free_text, and >80% missing columns as excluded (keep in conservative)
    high_missing_cols: list[str] = []
    n_rows_now = len(out)
    for col in out.columns:
        sem = semantic_types.get(col, SemanticType.UNKNOWN)
        pct_miss = float(out[col].isna().mean()) if n_rows_now > 0 else 0.0

        if pct_miss > config.cleaning.column_drop_threshold:
            high_missing_cols.append(col)
            log.add(
                step="structural_drops",
                column=col,
                action="marked_excluded",
                n_cells_affected=0,
                n_rows_affected=0,
                rows_before=n_rows_now,
                rows_after=n_rows_now,
                reason=(
                    f"Marked '{col}' as excluded in schema (mostly missing: {pct_miss:.1%}); "
                    "kept in conservative output, scheduled for drop in imputed output."
                ),
                severity="warning",
            )
        elif sem in {SemanticType.CONSTANT, SemanticType.ID_LIKE, SemanticType.FREE_TEXT}:
            log.add(
                step="structural_drops",
                column=col,
                action="marked_excluded",
                n_cells_affected=0,
                n_rows_affected=0,
                rows_before=n_rows_now,
                rows_after=n_rows_now,
                reason=f"Kept column '{col}' in data but marked role as {'id' if sem == SemanticType.ID_LIKE else 'excluded'} ({sem.value}).",
                severity="info",
            )

    return out, high_missing_cols


def step11_validate_invariants(
    df_conservative: pd.DataFrame,
    df_imputed: pd.DataFrame,
    n_rows_initial: int,
    semantic_types: dict[str, SemanticType],
    log: CleaningLog,
    config: PipelineConfig,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Step 11: Validate post-cleaning invariants and finalize category dtypes (Section 9.11)."""
    df_cons = df_conservative.copy()
    df_imp = df_imputed.copy()

    # 1. No duplicate column names
    if len(set(df_cons.columns)) != len(df_cons.columns):
        raise CleaningInvariantError(
            f"Duplicate column names found in df_clean_conservative: {list(df_cons.columns)}"
        )
    if len(set(df_imp.columns)) != len(df_imp.columns):
        raise CleaningInvariantError(
            f"Duplicate column names found in df_clean_imputed: {list(df_imp.columns)}"
        )

    # 2. Check no remaining placeholder tokens or leading/trailing whitespace in string columns
    missing_tokens_lower = {
        t.strip().lower() for t in config.effective_missing_tokens() if t.strip() != ""
    }
    for col in df_cons.columns:
        s = df_cons[col]
        if pd.api.types.is_object_dtype(s) or pd.api.types.is_string_dtype(s) or isinstance(s.dtype, pd.CategoricalDtype):
            non_na = s.dropna().astype(str)
            if len(non_na) == 0:
                continue
            has_ws = non_na.map(lambda v: v != v.strip(" \t\n\r\u00a0"))
            if has_ws.any():
                bad_ex = non_na[has_ws].head(3).tolist()
                raise CleaningInvariantError(
                    f"Column '{col}' still has leading/trailing whitespace after cleaning: {bad_ex}"
                )
            has_empty = non_na == ""
            if has_empty.any():
                raise CleaningInvariantError(
                    f"Column '{col}' still contains empty string '' instead of NaN after cleaning."
                )
            has_tok = non_na.str.lower().isin(missing_tokens_lower)
            if has_tok.any():
                bad_tok = non_na[has_tok].head(3).tolist()
                raise CleaningInvariantError(
                    f"Column '{col}' still contains placeholder missing token(s) after cleaning: {bad_tok}"
                )

    # 3. Check dtype matches semantic type for numeric columns
    for col in df_cons.columns:
        sem = semantic_types.get(col, SemanticType.UNKNOWN)
        if sem in {SemanticType.NUMERIC_CONTINUOUS, SemanticType.NUMERIC_DISCRETE}:
            if not pd.api.types.is_numeric_dtype(df_cons[col].dtype):
                raise CleaningInvariantError(
                    f"Numeric column '{col}' ({sem.value}) has non-numeric dtype {df_cons[col].dtype}."
                )

    # 4. Row accounting reconciliation
    cons_removed_logged = sum(
        max(0, e.rows_before - e.rows_after)
        for e in log.entries
        if e.step in {"handle_duplicates", "structural_drops"}
    )
    actual_cons_removed = n_rows_initial - len(df_cons)
    if actual_cons_removed != cons_removed_logged:
        raise CleaningInvariantError(
            f"Conservative row count mismatch: initial={n_rows_initial}, final={len(df_cons)} "
            f"(removed={actual_cons_removed}), but logged removals={cons_removed_logged}."
        )

    imp_only_removed_logged = sum(
        max(0, e.rows_before - e.rows_after)
        for e in log.entries
        if e.action in {"dropped_missing_target_rows_imputed", "removed_outlier_rows_imputed"}
    )
    actual_imp_diff = len(df_cons) - len(df_imp)
    if actual_imp_diff != imp_only_removed_logged:
        raise CleaningInvariantError(
            f"Imputed vs conservative row count mismatch: conservative={len(df_cons)}, "
            f"imputed={len(df_imp)} (diff={actual_imp_diff}), but logged imputed-only removals={imp_only_removed_logged}."
        )

    # 5. Finalize categorical columns as pandas 'category' dtype (Section 9.5)
    for col in df_cons.columns:
        sem = semantic_types.get(col, SemanticType.UNKNOWN)
        if sem in {SemanticType.CATEGORICAL_NOMINAL, SemanticType.CATEGORICAL_ORDINAL}:
            df_cons[col] = df_cons[col].astype("category")
            if col in df_imp.columns:
                df_imp[col] = df_imp[col].astype("category")

    return df_cons, df_imp


