"""Dataset profiling and Phase 2 column schema generation (Section 8, Section 6.6)."""

from __future__ import annotations

import difflib
import json
import re
import warnings
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy import stats

import ads
from ads.config import PipelineConfig, load_config
from ads.schemas import (
    ColumnProfile,
    ColumnRole,
    ColumnSchemaEntry,
    DataProfile,
    IngestionMetadata,
    MissingMatrixSummary,
    NearDuplicatePair,
    SemanticType,
    TopValueEntry,
)
from ads.type_inference import (
    ColumnTypeInference,
    infer_column_types_detailed,
    try_parse_numeric_series,
)

_UNICODE_ODDITIES_RE = re.compile(r"[\u00a0\u200b\u200c\u200d\ufeff]")
_INTERNAL_MULTI_WS_RE = re.compile(r" {2,}|\t")
_LEAKAGE_NAME_RE = re.compile(
    r"(?:^|_)(?:target|label|outcome|class|y|response)(?:$|_)",
    re.IGNORECASE,
)


def compute_outlier_counts(
    numeric_series: pd.Series,
    iqr_mild: float = 1.5,
    iqr_extreme: float = 3.0,
    modz_threshold: float = 3.5,
) -> tuple[int, int, int, float, float, float]:
    """Compute IQR (1.5x, 3.0x) and Modified Z-Score outlier counts with MAD=0 guard.

    Returns:
        (n_iqr_1_5, n_iqr_3_0, n_modz, q1, q3, iqr)
    """
    valid = numeric_series.dropna().astype("float64")
    if len(valid) == 0:
        return 0, 0, 0, 0.0, 0.0, 0.0

    q1 = float(np.percentile(valid, 25))
    q3 = float(np.percentile(valid, 75))
    iqr = q3 - q1

    if iqr > 0:
        low_1_5 = q1 - iqr_mild * iqr
        high_1_5 = q3 + iqr_mild * iqr
        low_3_0 = q1 - iqr_extreme * iqr
        high_3_0 = q3 + iqr_extreme * iqr
        n_iqr_1_5 = int(((valid < low_1_5) | (valid > high_1_5)).sum())
        n_iqr_3_0 = int(((valid < low_3_0) | (valid > high_3_0)).sum())
    else:
        n_iqr_1_5 = 0
        n_iqr_3_0 = 0

    med = float(np.median(valid))
    abs_dev = np.abs(valid - med)
    mad = float(np.median(abs_dev))

    if mad > 1e-12:
        mod_z = 0.6745 * abs_dev / mad
        n_modz = int((mod_z > modz_threshold).sum())
    else:
        # Guard MAD = 0: fallback to mean absolute deviation (Section 8)
        mean_ad = float(np.mean(abs_dev))
        if mean_ad > 1e-12:
            mod_z = abs_dev / (1.253314 * mean_ad)
            n_modz = int((mod_z > modz_threshold).sum())
        else:
            n_modz = 0

    return n_iqr_1_5, n_iqr_3_0, n_modz, q1, q3, iqr


def _find_near_duplicate_labels(
    non_null_stripped: pd.Series,
    similarity_threshold: float = 0.90,
    max_unique: int = 50,
) -> list[NearDuplicatePair]:
    """Find fuzzy near-duplicate categorical label pairs (excluding case-only variants)."""
    vc = non_null_stripped.value_counts()
    if len(vc) <= 1 or len(vc) > max_unique:
        return []

    # Group by casefold first so we only compare distinct case-insensitive spellings
    canonical_rep: dict[str, tuple[str, int]] = {}
    for label, count in vc.items():
        cf = str(label).casefold()
        if cf not in canonical_rep:
            canonical_rep[cf] = (str(label), int(count))
        else:
            prev_label, prev_count = canonical_rep[cf]
            canonical_rep[cf] = (prev_label, prev_count + int(count))

    items = list(canonical_rep.items())
    if len(items) <= 1 or len(items) > max_unique:
        return []

    pairs: list[NearDuplicatePair] = []
    for i in range(len(items)):
        cf_a, (label_a, count_a) = items[i]
        for j in range(i + 1, len(items)):
            cf_b, (label_b, count_b) = items[j]
            # Section 8: skip pairs of short strings < 4 chars unless case-only differences
            if min(len(cf_a), len(cf_b)) < 4:
                continue
            sim = difflib.SequenceMatcher(None, cf_a, cf_b).ratio()
            if sim >= similarity_threshold:
                pairs.append(
                    NearDuplicatePair(
                        label_a=label_a,
                        label_b=label_b,
                        count_a=count_a,
                        count_b=count_b,
                        similarity=round(float(sim), 4),
                    )
                )
    return pairs


def _profile_single_column(
    col_name: str,
    raw_series: pd.Series,
    raw_dtype_str: str,
    type_info: ColumnTypeInference,
    missing_tokens_map: dict[str, str],
    candidate_unknown_tokens: set[str],
    config: PipelineConfig,
) -> tuple[ColumnProfile, pd.Series, list[str]]:
    """Compute ColumnProfile, missingness mask, and column warnings without mutating input."""
    prof_cfg = config.profiling
    n_total = len(raw_series)
    col_warnings: list[str] = []

    # Convert to string representation while tracking true NaNs (convert to nullable string first for Int64/category safety)
    isna_mask = raw_series.isna()
    str_series = raw_series.astype("string").fillna("").astype(str)
    stripped = str_series.str.strip()
    lower_stripped = stripped.str.lower()

    # Missing token accounting
    is_empty_or_na = isna_mask | (stripped == "")
    is_placeholder_token = (~is_empty_or_na) & lower_stripped.isin(missing_tokens_map)
    is_missing_mask = is_empty_or_na | is_placeholder_token

    n_missing = int(is_missing_mask.sum())
    pct_missing = round(n_missing / n_total, 6) if n_total > 0 else 0.0
    n_nonnull = n_total - n_missing

    # Breakdown of non-empty placeholder tokens found
    token_counts: dict[str, int] = {}
    if is_placeholder_token.any():
        vc_tokens = stripped[is_placeholder_token].value_counts()
        token_counts = {str(k): int(v) for k, v in vc_tokens.items()}
    n_missing_token_cells = int(is_placeholder_token.sum())

    # Check candidate 'unknown' tokens when not configured as missing (Section 8 DECISION)
    if not prof_cfg.treat_unknown_as_missing:
        unk_mask = (~is_missing_mask) & lower_stripped.isin(candidate_unknown_tokens)
        n_unk = int(unk_mask.sum())
        if n_unk > 0:
            pct_unk = n_unk / n_total if n_total > 0 else 0.0
            col_warnings.append(
                f"Column '{col_name}' has {n_unk} cell(s) ({pct_unk:.1%}) with candidate missing token 'unknown'."
            )

    non_null_raw = str_series[~is_missing_mask]
    non_null_stripped = stripped[~is_missing_mask]

    # String quality flags (computed on non-missing cells)
    if len(non_null_raw) > 0:
        # Unicode oddities (\u00a0, zero-width chars)
        unicode_mask = non_null_raw.str.contains(_UNICODE_ODDITIES_RE, regex=True)
        n_unicode = int(unicode_mask.sum())
        has_unicode = n_unicode > 0

        # Leading/trailing whitespace (including \u00a0)
        ws_mask = non_null_raw.map(lambda s: s != s.strip(" \t\n\r\u00a0"))
        n_ws = int(ws_mask.sum())
        has_ws = n_ws > 0

        # Internal multiple whitespace
        multi_ws_mask = non_null_stripped.str.contains(_INTERNAL_MULTI_WS_RE, regex=True)
        n_multi_ws = int(multi_ws_mask.sum())
        has_multi_ws = n_multi_ws > 0

        # Case variants (group stripped values by casefold)
        norm_space = non_null_stripped.str.replace(_INTERNAL_MULTI_WS_RE, " ", regex=True)
        case_groups: dict[str, list[str]] = {}
        df_case = pd.DataFrame({"raw": norm_space, "cf": norm_space.str.casefold()})
        for cf_val, grp in df_case.groupby("cf", sort=True):
            unique_spellings = sorted(grp["raw"].unique().tolist())
            if len(unique_spellings) > 1:
                case_groups[str(cf_val)] = unique_spellings
        has_mixed_case = len(case_groups) > 0
    else:
        n_unicode, has_unicode = 0, False
        n_ws, has_ws = 0, False
        n_multi_ws, has_multi_ws = 0, False
        case_groups, has_mixed_case = {}, False

    sem_type = type_info.semantic_type

    # Default fields
    n_unique = int(non_null_stripped.nunique(dropna=True))
    pct_unique = round(n_unique / n_nonnull, 6) if n_nonnull > 0 else 0.0
    mode_val: Any | None = None
    top_values: list[TopValueEntry] = []

    # Numeric stats placeholders
    min_v = max_v = mean_v = median_v = std_v = q1_v = q3_v = iqr_v = skew_v = kurt_v = None
    n_zeros = n_negative = None
    n_out_1_5 = n_out_3_0 = n_out_modz = None

    # Datetime stats placeholders
    min_date = max_date = None
    n_unparseable: int | None = None

    # Compute type-specific statistics on a temporary view
    parsed_num, num_rate, _, _ = try_parse_numeric_series(non_null_stripped)
    is_numeric_binary = (
        sem_type == SemanticType.BINARY and num_rate >= config.type_inference.numeric_parse_threshold
    )

    if sem_type in {SemanticType.NUMERIC_CONTINUOUS, SemanticType.NUMERIC_DISCRETE} or is_numeric_binary:
        valid_nums = parsed_num.dropna().astype("float64")
        n_unique = int(valid_nums.nunique())
        pct_unique = round(n_unique / len(valid_nums), 6) if len(valid_nums) > 0 else 0.0

        if len(valid_nums) > 0:
            min_v = round(float(valid_nums.min()), 6)
            max_v = round(float(valid_nums.max()), 6)
            mean_v = round(float(valid_nums.mean()), 6)
            median_v = round(float(valid_nums.median()), 6)
            std_v = round(float(valid_nums.std(ddof=1)), 6) if len(valid_nums) > 1 else 0.0
            n_zeros = int((valid_nums == 0).sum())
            n_negative = int((valid_nums < 0).sum())

            n_out_1_5, n_out_3_0, n_out_modz, q1_raw, q3_raw, iqr_raw = compute_outlier_counts(
                valid_nums,
                iqr_mild=prof_cfg.outlier_iqr_mild,
                iqr_extreme=prof_cfg.outlier_iqr_extreme,
                modz_threshold=prof_cfg.outlier_modz_threshold,
            )
            q1_v = round(q1_raw, 6)
            q3_v = round(q3_raw, 6)
            iqr_v = round(iqr_raw, 6)

            if len(valid_nums) >= 3 and std_v > 1e-12:
                skew_v = round(float(stats.skew(valid_nums, bias=False)), 6)
            else:
                skew_v = 0.0

            if len(valid_nums) >= 4 and std_v > 1e-12:
                kurt_v = round(float(stats.kurtosis(valid_nums, bias=False)), 6)
            else:
                kurt_v = 0.0

            vc_num = valid_nums.value_counts()
            sorted_num_items = sorted(
                vc_num.items(), key=lambda kv: (-int(kv[1]), float(kv[0]))
            )
            mode_val = float(sorted_num_items[0][0])
            if sem_type in {SemanticType.NUMERIC_DISCRETE, SemanticType.BINARY}:
                for val_k, cnt_v in sorted_num_items[:10]:
                    label_str = f"{val_k:g}"
                    top_values.append(
                        TopValueEntry(
                            value=label_str,
                            count=int(cnt_v),
                            pct=round(int(cnt_v) / n_total, 6),
                        )
                    )

            if (
                sem_type in {SemanticType.NUMERIC_CONTINUOUS, SemanticType.NUMERIC_DISCRETE}
                and skew_v is not None
                and abs(skew_v) > prof_cfg.extreme_skew_warning_threshold
            ):
                col_warnings.append(
                    f"Column '{col_name}' has extreme skewness (skew={skew_v:.2f})."
                )

    elif sem_type == SemanticType.DATETIME:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            dt_series = pd.to_datetime(
                non_null_stripped,
                format="mixed",
                dayfirst=not config.type_inference.month_first_default,
                errors="coerce",
            )
        valid_dt = dt_series.dropna()
        n_unparseable = int(len(non_null_stripped) - len(valid_dt))
        n_unique = int(valid_dt.nunique())
        pct_unique = round(n_unique / len(valid_dt), 6) if len(valid_dt) > 0 else 0.0
        if len(valid_dt) > 0:
            min_date = valid_dt.min().isoformat()
            max_date = valid_dt.max().isoformat()
            mode_val = valid_dt.mode().iloc[0].isoformat()
        if type_info.ambiguous_date_warning:
            col_warnings.append(f"Column '{col_name}': {type_info.ambiguous_date_warning}.")

    else:
        # Categorical, binary string, constant, id_like, free_text, unknown
        if len(non_null_stripped) > 0:
            vc = non_null_stripped.value_counts()
            sorted_str_items = sorted(
                vc.items(), key=lambda kv: (-int(kv[1]), str(kv[0]))
            )
            mode_val = str(sorted_str_items[0][0])
            for val_k, cnt_v in sorted_str_items[:10]:
                top_values.append(
                    TopValueEntry(
                        value=str(val_k),
                        count=int(cnt_v),
                        pct=round(int(cnt_v) / n_total, 6),
                    )
                )

    # Near-duplicate fuzzy labels for categorical/binary columns
    near_dups: list[NearDuplicatePair] = []
    if sem_type in {
        SemanticType.CATEGORICAL_NOMINAL,
        SemanticType.CATEGORICAL_ORDINAL,
        SemanticType.BINARY,
    }:
        near_dups = _find_near_duplicate_labels(
            non_null_stripped,
            similarity_threshold=prof_cfg.label_similarity_threshold,
            max_unique=config.type_inference.max_categorical_unique,
        )
        if near_dups:
            pair_strs = [f"({p.label_a!r} vs {p.label_b!r}, sim={p.similarity:.2f})" for p in near_dups[:3]]
            col_warnings.append(
                f"Column '{col_name}' has near-duplicate label candidate(s): {', '.join(pair_strs)}."
            )

    # Additional column-level warnings (Section 8)
    if sem_type == SemanticType.CONSTANT:
        col_warnings.append(f"Column '{col_name}' is constant ({type_info.reason}).")
    elif sem_type == SemanticType.ID_LIKE:
        col_warnings.append(f"Column '{col_name}' looks like an ID ({type_info.reason}).")

    if pct_missing > prof_cfg.high_missing_warning_threshold:
        col_warnings.append(
            f"Column '{col_name}' has high missingness ({pct_missing:.1%}, n={n_missing})."
        )

    if type_info.high_cardinality_warning:
        col_warnings.append(
            f"Column '{col_name}' has high cardinality ({n_unique} unique values)."
        )

    if type_info.mixed_types:
        col_warnings.append(
            f"Column '{col_name}' mixes numeric/datetime values with unparseable strings."
        )

    # Imbalance check for binary / low-cardinality categorical
    if sem_type == SemanticType.BINARY and len(non_null_stripped) > 0:
        vc_ci = non_null_stripped.str.casefold().value_counts(normalize=True)
        if len(vc_ci) >= 2:
            minority_pct = float(vc_ci.iloc[-1])
            if minority_pct < prof_cfg.minority_imbalance_threshold:
                col_warnings.append(
                    f"Binary column '{col_name}' is highly imbalanced (minority class = {minority_pct:.1%})."
                )

    # Suspected leakage / target-like column name note
    if _LEAKAGE_NAME_RE.search(col_name):
        col_warnings.append(
            f"Info: Column '{col_name}' has a target/outcome-like name."
        )

    col_profile = ColumnProfile(
        name=col_name,
        raw_dtype=raw_dtype_str,
        semantic_type=sem_type,
        semantic_type_reason=type_info.reason,
        n_total=n_total,
        n_missing=n_missing,
        pct_missing=pct_missing,
        n_unique=n_unique,
        pct_unique=pct_unique,
        mode=mode_val,
        top_values=top_values,
        min=min_v,
        max=max_v,
        mean=mean_v,
        median=median_v,
        std=std_v,
        q1=q1_v,
        q3=q3_v,
        iqr=iqr_v,
        skewness=skew_v,
        kurtosis=kurt_v,
        n_zeros=n_zeros,
        n_negative=n_negative,
        n_outliers_iqr_1_5=n_out_1_5,
        n_outliers_iqr_3_0=n_out_3_0,
        n_outliers_modz=n_out_modz,
        has_leading_trailing_ws=has_ws,
        n_leading_trailing_ws=n_ws,
        has_internal_multi_ws=has_multi_ws,
        n_internal_multi_ws=n_multi_ws,
        has_unicode_oddities=has_unicode,
        n_unicode_oddities=n_unicode,
        has_mixed_case_variants=has_mixed_case,
        case_variant_groups=case_groups,
        near_duplicate_labels=near_dups,
        n_missing_token_cells=n_missing_token_cells,
        missing_tokens_found=token_counts,
        looks_numeric_but_object=type_info.looks_numeric_but_object,
        mixed_types=type_info.mixed_types,
        min_date=min_date,
        max_date=max_date,
        n_unparseable=n_unparseable,
    )

    return col_profile, is_missing_mask, col_warnings


def profile_dataset(
    df_raw_str: pd.DataFrame,
    df_naive: pd.DataFrame | None = None,
    ingestion_meta: IngestionMetadata | None = None,
    config: PipelineConfig | None = None,
    dataset_name: str | None = None,
) -> DataProfile:
    """Profile a dataset without mutating the input DataFrame (Section 8)."""
    cfg = config or load_config()
    ds_name = dataset_name or cfg.name
    n_rows, n_cols = df_raw_str.shape

    # Effective missing tokens (excluding empty string which is checked explicitly)
    effective_tokens = cfg.effective_missing_tokens()
    missing_tokens_map = {
        t.strip().lower(): t for t in effective_tokens if t.strip() != ""
    }
    candidate_unknown_tokens = {
        t.strip().lower() for t in cfg.profiling.candidate_missing_tokens if t.strip() != ""
    }

    type_inferences = infer_column_types_detailed(df_raw_str, config=cfg)

    col_profiles: list[ColumnProfile] = []
    missing_masks: dict[str, pd.Series] = {}
    all_warnings: list[str] = []

    if ingestion_meta and ingestion_meta.warnings:
        all_warnings.extend(ingestion_meta.warnings)

    for col in df_raw_str.columns:
        if df_naive is not None and col in df_naive.columns:
            raw_dtype_str = str(df_naive[col].dtype)
        else:
            raw_dtype_str = str(df_raw_str[col].dtype)

        col_prof, miss_mask, col_warns = _profile_single_column(
            col_name=col,
            raw_series=df_raw_str[col],
            raw_dtype_str=raw_dtype_str,
            type_info=type_inferences[col],
            missing_tokens_map=missing_tokens_map,
            candidate_unknown_tokens=candidate_unknown_tokens,
            config=cfg,
        )
        col_profiles.append(col_prof)
        missing_masks[col] = miss_mask
        all_warnings.extend(col_warns)

    # Missing matrix summary
    if n_rows > 0 and n_cols > 0:
        miss_df = pd.DataFrame(missing_masks, index=df_raw_str.index)
        row_missing_counts = miss_df.sum(axis=1)
        total_cells = n_rows * n_cols
        total_missing_cells = int(row_missing_counts.sum())
        pct_missing_cells = round(total_missing_cells / total_cells, 6)
        rows_any_missing = int((row_missing_counts > 0).sum())
        pct_rows_any_missing = round(rows_any_missing / n_rows, 6)
        rows_gt_half = int((row_missing_counts > (n_cols / 2.0)).sum())
        pct_rows_gt_half = round(rows_gt_half / n_rows, 6)
        n_fully_empty_rows = int((row_missing_counts == n_cols).sum())
        n_fully_empty_cols = int((miss_df.sum(axis=0) == n_rows).sum())
    else:
        total_cells = n_rows * n_cols
        total_missing_cells = 0
        pct_missing_cells = 0.0
        rows_any_missing = 0
        pct_rows_any_missing = 0.0
        rows_gt_half = 0
        pct_rows_gt_half = 0.0
        n_fully_empty_rows = 0
        n_fully_empty_cols = n_cols if n_rows == 0 and n_cols > 0 else 0

    if n_fully_empty_rows > 0:
        all_warnings.append(f"Dataset contains {n_fully_empty_rows} fully empty row(s).")
    if n_fully_empty_cols > 0:
        all_warnings.append(f"Dataset contains {n_fully_empty_cols} fully empty column(s).")

    # Duplicate rows: raw vs normalized (Section 8)
    if n_rows > 0 and n_cols > 0:
        # Exclude completely empty rows from duplicate counting so empty rows aren't double-counted as duplicates
        non_empty_row_mask = row_missing_counts < n_cols
        df_non_empty = df_raw_str[non_empty_row_mask]
        n_dup_raw = int(df_non_empty.duplicated(keep="first").sum())

        norm_cols: dict[str, pd.Series] = {}
        for col in df_non_empty.columns:
            s = df_non_empty[col].fillna("").astype(str).str.replace(_UNICODE_ODDITIES_RE, " ", regex=True).str.strip()
            s = s.str.replace(_INTERNAL_MULTI_WS_RE, " ", regex=True).str.casefold()
            s = s.where(~s.isin(missing_tokens_map), other="")
            norm_cols[col] = s
        df_norm = pd.DataFrame(norm_cols, index=df_non_empty.index)
        n_dup_norm = int(df_norm.duplicated(keep="first").sum())
        pct_dup = round(n_dup_norm / n_rows, 6)
        if n_dup_norm > n_dup_raw:
            all_warnings.append(
                f"Found {n_dup_norm - n_dup_raw} additional duplicate row(s) after whitespace/case normalization "
                f"(raw={n_dup_raw}, normalized={n_dup_norm})."
            )
    else:
        n_dup_raw = 0
        n_dup_norm = 0
        pct_dup = 0.0

    memory_mb = round(float(df_raw_str.memory_usage(deep=True).sum()) / (1024 * 1024), 6)
    source_file = ingestion_meta.source_file if ingestion_meta else (cfg.file or "")
    sha256 = ingestion_meta.sha256 if ingestion_meta else ""

    lib_versions = {
        "ads": ads.__version__,
        "pandas": pd.__version__,
        "numpy": np.__version__,
    }

    return DataProfile(
        schema_version="1.0",
        dataset_name=ds_name,
        source_file=source_file,
        sha256=sha256,
        n_rows=n_rows,
        n_cols=n_cols,
        memory_mb=memory_mb,
        n_duplicate_rows_raw=n_dup_raw,
        n_duplicate_rows=n_dup_norm,
        pct_duplicate_rows=pct_dup,
        n_fully_empty_rows=n_fully_empty_rows,
        n_fully_empty_cols=n_fully_empty_cols,
        columns=col_profiles,
        missing_matrix_summary=MissingMatrixSummary(
            total_cells=total_cells,
            total_missing_cells=total_missing_cells,
            pct_missing_cells=pct_missing_cells,
            rows_with_any_missing=rows_any_missing,
            pct_rows_with_any_missing=pct_rows_any_missing,
            rows_with_gt_half_missing=rows_gt_half,
            pct_rows_with_gt_half_missing=pct_rows_gt_half,
        ),
        warnings=all_warnings,
        generated_at="deterministic",
        library_versions=lib_versions,
    )


def build_column_schema(
    profile: DataProfile,
    config: PipelineConfig | None = None,
) -> dict[str, ColumnSchemaEntry]:
    """Build the Phase 2 handoff column_schema.json dictionary (Section 6.6)."""
    cfg = config or load_config()
    schema: dict[str, ColumnSchemaEntry] = {}

    for col_prof in profile.columns:
        name = col_prof.name
        sem = col_prof.semantic_type
        exclude_reason: str | None = None

        if cfg.target and name == cfg.target:
            role = ColumnRole.TARGET_CANDIDATE
        elif sem == SemanticType.ID_LIKE or name in cfg.id_columns:
            role = ColumnRole.ID
            exclude_reason = "id_like"
        elif sem in {SemanticType.CONSTANT, SemanticType.FREE_TEXT, SemanticType.UNKNOWN}:
            role = ColumnRole.EXCLUDED
            exclude_reason = sem.value
        elif col_prof.pct_missing > cfg.cleaning.column_drop_threshold:
            role = ColumnRole.EXCLUDED
            exclude_reason = f"mostly_missing ({col_prof.pct_missing:.1%} > {cfg.cleaning.column_drop_threshold:.0%})"
        else:
            role = ColumnRole.FEATURE

        bin_labels: list[str] | None = None
        if sem == SemanticType.BINARY and col_prof.top_values:
            bin_labels = [tv.value for tv in col_prof.top_values[:2]]

        schema[name] = ColumnSchemaEntry(
            semantic_type=sem,
            role=role,
            n_unique=col_prof.n_unique,
            pct_missing=col_prof.pct_missing,
            exclude_reason=exclude_reason,
            binary_labels=bin_labels,
        )

    return schema


def save_profile_json(profile: DataProfile, path: Path | str) -> Path:
    """Serialize DataProfile deterministically to profile.json."""
    out_path = Path(path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    data = profile.model_dump(mode="json")
    out_path.write_text(
        json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return out_path


def save_column_schema_json(
    schema: dict[str, ColumnSchemaEntry], path: Path | str
) -> Path:
    """Serialize Phase 2 handoff schema deterministically to column_schema.json."""
    out_path = Path(path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {k: v.model_dump(mode="json") for k, v in schema.items()}
    out_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return out_path
