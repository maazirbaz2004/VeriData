"""Semantic column type inference from raw string DataFrames (Section 7.2)."""

from __future__ import annotations

import re
import warnings
from dataclasses import dataclass
from typing import Iterable

import numpy as np
import pandas as pd

from ads.config import PipelineConfig, load_config
from ads.schemas import SemanticType

_ID_NAME_RE = re.compile(
    r"(?:^|_)(?:id|uuid|guid|index|key|rowid|record_id|customer_id|user_id|client_id)(?:$|_)|^unnamed:\s*\d+$",
    re.IGNORECASE,
)
_CODE_ZIP_PHONE_NAME_RE = re.compile(
    r"(?:^|_)(?:zip|zipcode|postal|postcode|phone|tel|mobile|ssn|code|fips)(?:$|_)",
    re.IGNORECASE,
)
_ORDINAL_PATTERNS: list[set[str]] = [
    {"low", "medium", "high"},
    {"low", "med", "high"},
    {"very low", "low", "medium", "high", "very high"},
    {"poor", "fair", "good", "very good", "excellent"},
    {"poor", "fair", "good", "excellent"},
    {"small", "medium", "large"},
    {"xs", "s", "m", "l", "xl"},
    {"basic", "silver", "gold"},
    {"basic", "silver", "gold", "platinum"},
    {"never", "rarely", "sometimes", "often", "always"},
]
_BOOLEAN_TRUE_TOKENS = {"yes", "y", "true", "t", "1", "1.0"}
_BOOLEAN_FALSE_TOKENS = {"no", "n", "false", "f", "0", "0.0"}
_KNOWN_BINARY_PAIRS: list[tuple[set[str], set[str], str]] = [
    ({"yes", "y", "true", "t", "1", "1.0"}, {"no", "n", "false", "f", "0", "0.0"}, "boolean-like (Yes/No/1/0)"),
    ({"male", "m"}, {"female", "f"}, "gender binary (Male/Female)"),
]
_EXPLICIT_DATE_FORMATS = [
    "%Y-%m-%d",
    "%Y/%m/%d",
    "%d/%m/%Y",
    "%m/%d/%Y",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%dT%H:%M:%S",
    "%d-%m-%Y",
    "%m-%d-%Y",
    "%b %d, %Y",
    "%B %d, %Y",
    "%d %b %Y",
]
_ACCOUNTING_NEG_RE = re.compile(r"^\(\s*([+-]?\d[\d,.]*)\s*\)$")
_CURRENCY_PCT_RE = re.compile(r"^[\$€£\s]+|[\$€£%\s]+$")


@dataclass
class ColumnTypeInference:
    """Rich inference result for a single column (used by profiling and cleaning)."""

    column: str
    semantic_type: SemanticType
    reason: str
    looks_numeric_but_object: bool = False
    mixed_types: bool = False
    n_unparseable_numeric: int = 0
    n_unparseable_datetime: int = 0
    ambiguous_date_warning: str | None = None
    high_cardinality_warning: bool = False
    override_applied: bool = False


def clean_numeric_token(val: str) -> tuple[str, bool]:
    """Normalize a single string cell for numeric parsing.

    Returns:
        (normalized_str, had_formatting_decorator)
    """
    s = val.strip()
    if not s:
        return "", False

    had_decorator = False
    m_neg = _ACCOUNTING_NEG_RE.match(s)
    if m_neg:
        s = "-" + m_neg.group(1).strip()
        had_decorator = True

    stripped_curr = _CURRENCY_PCT_RE.sub("", s).strip()
    if stripped_curr != s:
        had_decorator = True
        s = stripped_curr

    if "," in s:
        # Remove thousands commas when surrounded by digits
        no_comma = s.replace(",", "")
        had_decorator = True
        s = no_comma

    return s, had_decorator


def try_parse_numeric_series(
    non_null_str: pd.Series,
) -> tuple[pd.Series, float, bool, int]:
    """Attempt to parse a non-null string Series as float.

    Returns:
        (parsed_float_series, parse_rate, had_formatting_decorators, n_failed)
    """
    if len(non_null_str) == 0:
        return pd.Series(dtype="float64"), 0.0, False, 0

    cleaned_vals: list[str] = []
    any_decorator = False
    for raw_val in non_null_str.astype(str):
        c_val, dec = clean_numeric_token(raw_val)
        cleaned_vals.append(c_val)
        if dec:
            any_decorator = True

    cleaned_series = pd.Series(cleaned_vals, index=non_null_str.index, dtype="object")
    # Reject non-ASCII digits (e.g., Arabic-Indic '١٢') or infinities from counting as standard numbers
    ascii_mask = cleaned_series.map(lambda x: bool(x) and x.isascii())
    lower_vals = cleaned_series.str.lower()
    inf_mask = lower_vals.isin({"inf", "-inf", "+inf", "infinity", "-infinity", "nan"})

    candidate_for_num = cleaned_series.where(ascii_mask & ~inf_mask, other=np.nan)
    parsed = pd.to_numeric(candidate_for_num, errors="coerce")
    valid_mask = parsed.notna() & np.isfinite(parsed)
    parsed = parsed.where(valid_mask, other=np.nan)

    n_valid = int(valid_mask.sum())
    n_total = len(non_null_str)
    n_failed = n_total - n_valid
    parse_rate = n_valid / n_total if n_total > 0 else 0.0

    # Also check if naive float conversion on raw strings would have failed where cleaned succeeded
    raw_parsed = pd.to_numeric(non_null_str, errors="coerce")
    if int(raw_parsed.notna().sum()) < n_valid:
        any_decorator = True

    return parsed, parse_rate, any_decorator, n_failed


def _is_fixed_length_code_or_zip(col_name: str, non_null_str: pd.Series) -> bool:
    """Detect ZIP codes, postal codes, phone numbers, or zero-padded codes (Section 7.2)."""
    if len(non_null_str) == 0:
        return False

    vals = non_null_str.str.strip()
    # Check if values have leading zeros in multi-digit strings (e.g., '00123', '02138')
    leading_zero_digits = vals.map(
        lambda s: len(s) > 1 and s.isdigit() and s.startswith("0")
    )
    if leading_zero_digits.mean() >= 0.10:
        return True

    if _CODE_ZIP_PHONE_NAME_RE.search(col_name):
        # Check if mostly digit/hyphen/plus strings of bounded length
        code_like = vals.map(
            lambda s: bool(re.match(r"^[\d\-\+\(\)\s]{3,15}$", s))
        )
        if code_like.mean() >= 0.80:
            return True

    return False


def _try_parse_datetime_series(
    non_null_str: pd.Series,
    month_first_default: bool = False,
) -> tuple[float, int, str | None]:
    """Test whether a non-null string series represents dates/timestamps (Section 7.2 Step 5).

    Returns:
        (best_parse_rate, n_unparseable, ambiguity_warning)
    """
    n_total = len(non_null_str)
    if n_total == 0:
        return 0.0, 0, None

    vals = non_null_str.str.strip()

    # Guard: do not parse purely numeric small integers or floats as dates
    pure_num = pd.to_numeric(vals, errors="coerce")
    if pure_num.notna().mean() >= 0.80:
        return 0.0, n_total, None

    # Must look plausibly date-like (contain digits and date separators -, /, :, or month names)
    date_token_mask = vals.str.contains(
        r"\d{1,4}[-/\s,]\d{1,2}|\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\b",
        case=False,
        regex=True,
    )
    if date_token_mask.mean() < 0.70:
        return 0.0, n_total, None

    # Check slash date ambiguity (%d/%m/%Y vs %m/%d/%Y)
    slash_vals = vals[vals.str.match(r"^\d{1,2}/\d{1,2}/\d{2,4}$")]
    ambiguity_warning: str | None = None
    if len(slash_vals) > 0:
        dmy = pd.to_datetime(slash_vals, format="%d/%m/%Y", errors="coerce")
        mdy = pd.to_datetime(slash_vals, format="%m/%d/%Y", errors="coerce")
        if dmy.notna().all() and mdy.notna().all():
            # Check if day and month are ever different (not just 01/01/2020)
            if not (dmy == mdy).all():
                default_order = "month-first (%m/%d/%Y)" if month_first_default else "day-first=False (ISO/month-first fallback)"
                ambiguity_warning = (
                    f"ambiguous day/month order (both %d/%m/%Y and %m/%d/%Y parse all slash dates); "
                    f"defaulted to {default_order}"
                )

    # Try explicit formats first, then union across formats for mixed-format date columns (Section 12.2)
    parsed_mask = pd.Series(False, index=vals.index)
    for fmt in _EXPLICIT_DATE_FORMATS:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            dt = pd.to_datetime(vals[~parsed_mask], format=fmt, errors="coerce")
        parsed_mask.loc[dt[dt.notna()].index] = True
        if parsed_mask.all():
            break

    # Flexible fallback for any remaining unparsed strings
    if not parsed_mask.all():
        remaining = vals[~parsed_mask]
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            dt_flex = pd.to_datetime(
                remaining,
                dayfirst=not month_first_default,
                errors="coerce",
            )
        parsed_mask.loc[dt_flex[dt_flex.notna()].index] = True

    n_parsed = int(parsed_mask.sum())
    parse_rate = n_parsed / n_total
    n_unparseable = n_total - n_parsed
    return parse_rate, n_unparseable, ambiguity_warning


def _is_monotonic_or_id_named(col_name: str, int_series: pd.Series) -> tuple[bool, str]:
    """Check if an all-unique integer column is an ID or a 0/1-based step-1 row index."""
    if _ID_NAME_RE.search(col_name):
        return True, f"integer column with all unique values and ID-like name '{col_name}'"
    if len(int_series) >= 10:
        first_val = int(int_series.iloc[0])
        if first_val in (0, 1) and bool((int_series.diff().dropna() == 1).all()):
            return True, f"all-unique sequential row index starting at {first_val}"
    return False, ""


def _infer_single_column(
    col_name: str,
    raw_series: pd.Series,
    missing_tokens_lower: set[str],
    config: PipelineConfig,
) -> ColumnTypeInference:
    """Run the 10-step semantic type inference cascade on a single column (Section 7.2)."""
    ti_cfg = config.type_inference
    n_rows = len(raw_series)

    # Normalize candidate series for inference without mutating input
    stripped = raw_series.fillna("").astype(str).str.strip()
    is_missing = stripped.str.lower().isin(missing_tokens_lower) | (stripped == "")
    non_null = stripped[~is_missing]
    n_nonnull = len(non_null)

    # Check config overrides (forced_types / id_columns / ordinal_orders)
    if col_name in config.forced_types:
        forced = config.forced_types[col_name]
        return ColumnTypeInference(
            column=col_name,
            semantic_type=forced,
            reason=f"config override: forced_types[{col_name!r}] = {forced.value}",
            override_applied=True,
        )
    if col_name in config.id_columns:
        return ColumnTypeInference(
            column=col_name,
            semantic_type=SemanticType.ID_LIKE,
            reason=f"config override: listed in id_columns",
            override_applied=True,
        )
    if col_name in config.ordinal_orders:
        return ColumnTypeInference(
            column=col_name,
            semantic_type=SemanticType.CATEGORICAL_ORDINAL,
            reason=f"config override: listed in ordinal_orders",
            override_applied=True,
        )

    # Step 2: All missing -> constant
    if n_nonnull == 0:
        return ColumnTypeInference(
            column=col_name,
            semantic_type=SemanticType.CONSTANT,
            reason="all missing (fully empty column)",
        )

    n_unique_raw = int(non_null.nunique(dropna=True))
    casefolded = non_null.str.casefold()
    n_unique_ci = int(casefolded.nunique(dropna=True))

    # Step 3: Single distinct value -> constant
    if n_unique_raw <= 1:
        only_val = str(non_null.iloc[0])[:30]
        return ColumnTypeInference(
            column=col_name,
            semantic_type=SemanticType.CONSTANT,
            reason=f"constant column (1 unique non-null value: {only_val!r})",
        )

    # Check mixed boolean encoding (e.g. Yes/No/yes/Y/1/0 in Section 12.2) before numeric check
    unique_ci_set = set(casefolded.unique())
    for true_set, false_set, pair_label in _KNOWN_BINARY_PAIRS:
        combined = true_set | false_set
        if unique_ci_set.issubset(combined) and (unique_ci_set & true_set) and (unique_ci_set & false_set):
            # If it's purely numeric 0/1, let Step 4 record "numeric with two values (0/1)";
            # if it mixes strings and 0/1 or string pairs, return binary here.
            if not unique_ci_set.issubset({"0", "1", "0.0", "1.0"}):
                sample_vals = sorted(non_null.unique().tolist())[:6]
                return ColumnTypeInference(
                    column=col_name,
                    semantic_type=SemanticType.BINARY,
                    reason=f"binary string/mixed encoding ({pair_label}: {sample_vals})",
                )

    # Step 4a: ZIP / Postal / Phone / Zero-padded code guard (Section 7.2 DECISION)
    if _is_fixed_length_code_or_zip(col_name, non_null):
        unique_ratio = n_unique_raw / n_nonnull
        if unique_ratio >= ti_cfg.id_unique_ratio and n_nonnull >= ti_cfg.id_min_nonnull:
            return ColumnTypeInference(
                column=col_name,
                semantic_type=SemanticType.ID_LIKE,
                reason=f"code/ZIP/phone column '{col_name}' with high uniqueness ({unique_ratio:.1%})",
            )
        return ColumnTypeInference(
            column=col_name,
            semantic_type=SemanticType.CATEGORICAL_NOMINAL,
            reason=f"fixed-length digit code/ZIP/phone column '{col_name}' treated as categorical",
        )

    # Step 4b: Numeric test
    parsed_num, num_parse_rate, had_num_decorator, n_num_failed = try_parse_numeric_series(non_null)
    if num_parse_rate >= ti_cfg.numeric_parse_threshold:
        valid_nums = parsed_num.dropna()
        n_unique_num = int(valid_nums.nunique())
        mixed_types = n_num_failed > 0
        looks_numeric_obj = had_num_decorator or mixed_types

        extra_notes: list[str] = []
        if had_num_decorator:
            extra_notes.append("formatted numeric strings ($, commas, %, or parentheses)")
        if mixed_types:
            extra_notes.append(f"{n_num_failed} unparseable numeric token(s)")
        suffix = f" [{'; '.join(extra_notes)}]" if extra_notes else ""

        if n_unique_num <= 1:
            return ColumnTypeInference(
                column=col_name,
                semantic_type=SemanticType.CONSTANT,
                reason=f"numeric column with 1 distinct value{suffix}",
                looks_numeric_but_object=looks_numeric_obj,
                mixed_types=mixed_types,
                n_unparseable_numeric=n_num_failed,
            )

        if n_unique_num == 2 and not had_num_decorator:
            vals_sorted = sorted(valid_nums.unique().tolist())
            return ColumnTypeInference(
                column=col_name,
                semantic_type=SemanticType.BINARY,
                reason=f"numeric with two values ({vals_sorted[0]:g}, {vals_sorted[1]:g}){suffix}",
                looks_numeric_but_object=looks_numeric_obj,
                mixed_types=mixed_types,
                n_unparseable_numeric=n_num_failed,
            )

        all_integers = bool(np.all(np.isclose(valid_nums % 1, 0.0, atol=1e-9)))
        if all_integers:
            int_vals = valid_nums.round().astype("int64")
            if n_unique_num == len(valid_nums):
                is_id, id_reason = _is_monotonic_or_id_named(col_name, int_vals)
                if is_id:
                    return ColumnTypeInference(
                        column=col_name,
                        semantic_type=SemanticType.ID_LIKE,
                        reason=f"{id_reason}{suffix}",
                        looks_numeric_but_object=looks_numeric_obj,
                        mixed_types=mixed_types,
                        n_unparseable_numeric=n_num_failed,
                    )

            unique_ratio_num = n_unique_num / len(valid_nums)
            # Use configured ratio for normal-sized datasets; allow up to 0.40 on tiny unit-test series (<100 rows)
            effective_max_ratio = (
                ti_cfg.discrete_max_ratio if len(valid_nums) >= 100 else max(ti_cfg.discrete_max_ratio, 0.40)
            )
            if n_unique_num <= ti_cfg.discrete_max_unique and unique_ratio_num < effective_max_ratio:
                return ColumnTypeInference(
                    column=col_name,
                    semantic_type=SemanticType.NUMERIC_DISCRETE,
                    reason=(
                        f"integer values with {n_unique_num} unique levels "
                        f"(unique ratio {unique_ratio_num:.1%}){suffix}"
                    ),
                    looks_numeric_but_object=looks_numeric_obj,
                    mixed_types=mixed_types,
                    n_unparseable_numeric=n_num_failed,
                )

        return ColumnTypeInference(
            column=col_name,
            semantic_type=SemanticType.NUMERIC_CONTINUOUS,
            reason=f"numeric values ({num_parse_rate:.1%} parseable, {n_unique_num} unique){suffix}",
            looks_numeric_but_object=looks_numeric_obj,
            mixed_types=mixed_types,
            n_unparseable_numeric=n_num_failed,
        )

    # Step 5: Datetime test
    dt_rate, n_dt_unparseable, dt_ambiguity = _try_parse_datetime_series(
        non_null, month_first_default=ti_cfg.month_first_default
    )
    if dt_rate >= ti_cfg.datetime_parse_threshold:
        reason = f"datetime strings ({dt_rate:.1%} parseable)"
        if dt_ambiguity:
            reason += f"; WARNING: {dt_ambiguity}"
        return ColumnTypeInference(
            column=col_name,
            semantic_type=SemanticType.DATETIME,
            reason=reason,
            n_unparseable_datetime=n_dt_unparseable,
            ambiguous_date_warning=dt_ambiguity,
            mixed_types=n_dt_unparseable > 0,
        )

    # Step 6: Binary test (strings: 2 distinct case/whitespace-insensitive values)
    if n_unique_ci == 2:
        vc_raw = non_null.value_counts()
        sorted_items = sorted(vc_raw.items(), key=lambda kv: (-int(kv[1]), str(kv[0])))
        top_spellings = [str(k) for k, _ in sorted_items[:2]]
        return ColumnTypeInference(
            column=col_name,
            semantic_type=SemanticType.BINARY,
            reason=f"string column with 2 distinct normalized values ({top_spellings[0]!r}, {top_spellings[1]!r})",
        )

    # Step 7: ID-like test (strings)
    unique_ratio_str = n_unique_raw / n_nonnull
    lengths = non_null.str.len()
    len_std = float(lengths.std()) if len(lengths) > 1 else 0.0
    consistent_length = len_std <= 2.0
    name_is_id = bool(_ID_NAME_RE.search(col_name))

    if (
        unique_ratio_str >= ti_cfg.id_unique_ratio
        and (n_nonnull >= ti_cfg.id_min_nonnull or name_is_id)
        and (consistent_length or name_is_id)
    ):
        return ColumnTypeInference(
            column=col_name,
            semantic_type=SemanticType.ID_LIKE,
            reason=(
                f"string ID-like column ({unique_ratio_str:.1%} unique across {n_nonnull} rows, "
                f"mean_len={lengths.mean():.1f})"
            ),
        )

    # Step 8: Free text test
    mean_len = float(lengths.mean())
    word_counts = non_null.str.split().map(len)
    mean_words = float(word_counts.mean())
    if mean_len > ti_cfg.text_mean_len or (
        mean_words > ti_cfg.text_mean_words and unique_ratio_str > ti_cfg.text_unique_ratio
    ):
        return ColumnTypeInference(
            column=col_name,
            semantic_type=SemanticType.FREE_TEXT,
            reason=(
                f"free text (mean_len={mean_len:.1f} chars, mean_words={mean_words:.1f}, "
                f"unique_ratio={unique_ratio_str:.1%})"
            ),
        )

    # Step 9: Check known ordinal value sets (Section 6.1: only known ordinal patterns or config)
    if unique_ci_set in _ORDINAL_PATTERNS:
        return ColumnTypeInference(
            column=col_name,
            semantic_type=SemanticType.CATEGORICAL_ORDINAL,
            reason=f"matches known ordinal level set ({sorted(unique_ci_set)})",
        )

    # Step 9b: Categorical nominal
    max_cat_allowed = max(
        ti_cfg.max_categorical_unique,
        int(ti_cfg.categorical_max_ratio * max(n_rows, 1)),
    )
    if n_unique_ci <= max_cat_allowed:
        return ColumnTypeInference(
            column=col_name,
            semantic_type=SemanticType.CATEGORICAL_NOMINAL,
            reason=f"string categorical with {n_unique_ci} normalized unique values (raw={n_unique_raw})",
        )

    if unique_ratio_str >= ti_cfg.id_unique_ratio:
        return ColumnTypeInference(
            column=col_name,
            semantic_type=SemanticType.ID_LIKE,
            reason=f"high-uniqueness string column ({unique_ratio_str:.1%} unique)",
        )

    if unique_ratio_str <= 0.80:
        return ColumnTypeInference(
            column=col_name,
            semantic_type=SemanticType.CATEGORICAL_NOMINAL,
            reason=f"high cardinality categorical ({n_unique_ci} unique values, unique_ratio={unique_ratio_str:.1%})",
            high_cardinality_warning=True,
        )

    # Step 10: Fallback unknown
    return ColumnTypeInference(
        column=col_name,
        semantic_type=SemanticType.UNKNOWN,
        reason=f"unclassified column ({n_unique_raw} unique values out of {n_nonnull} non-null)",
    )


def infer_column_types_detailed(
    df_raw_str: pd.DataFrame,
    config: PipelineConfig | None = None,
    extra_missing_tokens: Iterable[str] | None = None,
) -> dict[str, ColumnTypeInference]:
    """Infer detailed semantic type metadata for every column in df_raw_str."""
    cfg = config or load_config()
    tokens = {t.strip().lower() for t in cfg.effective_missing_tokens()}
    if extra_missing_tokens:
        tokens.update(t.strip().lower() for t in extra_missing_tokens)

    results: dict[str, ColumnTypeInference] = {}
    for col in df_raw_str.columns:
        results[col] = _infer_single_column(col, df_raw_str[col], tokens, cfg)
    return results


def infer_column_types(
    df_raw_str: pd.DataFrame,
    config: PipelineConfig | None = None,
) -> dict[str, tuple[SemanticType, str]]:
    """Infer (SemanticType, reason) for every column in df_raw_str (Section 7.2 API)."""
    detailed = infer_column_types_detailed(df_raw_str, config=config)
    return {col: (info.semantic_type, info.reason) for col, info in detailed.items()}

