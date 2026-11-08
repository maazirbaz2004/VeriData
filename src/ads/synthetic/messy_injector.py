"""Deterministic messy data injector and ground-truth manifest builder (Section 12.2)."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from ads.schemas import ManifestEntry, MessyManifest
from ads.synthetic.base_generator import make_clean_base, save_base_truth_json

DEFAULT_INJECTION_RATES: dict[str, float] = {
    "ws_leading_trailing": 0.05,
    "ws_internal": 0.02,
    "case_variants_auto": 0.10,
    "case_variants_fuzzy": 0.03,
    "missing_tokens_income": 0.08,
    "missing_tokens_region_unknown": 0.04,
    "real_nan_age": 0.06,
    "real_nan_satisfaction": 0.03,
    "numeric_sci_rate": 0.01,
    "mixed_types_tenure": 0.01,
    "date_garbage_rate": 0.01,
    "duplicates_exact": 0.03,
    "duplicates_formatting": 0.01,
    "outliers_numeric": 0.005,
    "impossible_values": 0.005,
    "empty_rows_count": 10,
    "binary_encoding_mix": 0.05,
}


def inject_problems(
    df_clean: pd.DataFrame,
    seed: int = 42,
    rates: dict[str, float] | None = None,
    dataset_name: str = "messy_synthetic",
) -> tuple[pd.DataFrame, MessyManifest, dict[str, Any]]:
    """Inject 18 reproducible data-quality problems into a copy of df_clean (Section 12.2).

    Returns:
        (df_messy, manifest, index_map_payload)
    """
    rng = np.random.default_rng(seed)
    cfg_rates = dict(DEFAULT_INJECTION_RATES)
    if rates:
        cfg_rates.update(rates)

    n_rows = len(df_clean)
    n_cols = len(df_clean.columns)
    all_idx = np.arange(n_rows)

    # Start with string representations of every column so injections do not fight pandas dtypes
    df = pd.DataFrame(index=df_clean.index)
    for col in df_clean.columns:
        df[col] = df_clean[col].fillna("").astype(str)

    # Track row provenance via _row_uid (removed before saving messy_dataset.csv)
    df["_row_uid"] = [int(i) for i in range(n_rows)]
    df["_row_kind"] = ["primary"] * n_rows

    entries: list[ManifestEntry] = []

    # -------------------------------------------------------------------------
    # 1. outliers_numeric: multiply ~0.5% of income and monthly_spend by 10-50x
    #    (Inject BEFORE numeric_as_string formatting so formatted strings reflect the outlier values)
    # -------------------------------------------------------------------------
    n_out = max(1, int(round(n_rows * cfg_rates["outliers_numeric"])))
    out_income_idx = sorted(rng.choice(all_idx, size=n_out, replace=False).tolist())
    out_spend_idx = sorted(rng.choice(all_idx, size=n_out, replace=False).tolist())

    income_numeric = df_clean["income"].astype(float).copy()
    spend_numeric = df_clean["monthly_spend"].astype(float).copy()

    income_factors: dict[int, float] = {}
    for r_i in out_income_idx:
        factor = round(float(rng.uniform(12.0, 45.0)), 2)
        income_numeric.iloc[r_i] = round(income_numeric.iloc[r_i] * factor, 2)
        income_factors[r_i] = factor

    spend_factors: dict[int, float] = {}
    for r_i in out_spend_idx:
        factor = round(float(rng.uniform(12.0, 45.0)), 2)
        spend_numeric.iloc[r_i] = round(spend_numeric.iloc[r_i] * factor, 2)
        spend_factors[r_i] = factor

    out_union_rows = sorted(set(out_income_idx) | set(out_spend_idx))
    entries.append(
        ManifestEntry(
            problem_id="outliers_numeric",
            problem_type="outliers",
            columns=["income", "monthly_spend"],
            n_cells=len(out_income_idx) + len(out_spend_idx),
            n_rows=len(out_union_rows),
            row_indices_sample=out_union_rows[:20],
            description="Multiplied ~0.5% of income and monthly_spend by 12-45x.",
            expected_pipeline_behavior="flagged_only",
            details={"income_rows": out_income_idx, "monthly_spend_rows": out_spend_idx},
        )
    )

    # -------------------------------------------------------------------------
    # 2. missing_tokens: ~8% of income replaced with "", "N/A", "?", "null", "-";
    #    ~4% of region replaced with "Unknown"
    # -------------------------------------------------------------------------
    avail_income_for_miss = np.setdiff1d(all_idx, np.array(out_income_idx, dtype=int))
    n_miss_inc = max(1, int(round(n_rows * cfg_rates["missing_tokens_income"])))
    miss_inc_idx = sorted(rng.choice(avail_income_for_miss, size=n_miss_inc, replace=False).tolist())
    inc_tokens_pool = ["", "N/A", "?", "null", "-"]
    inc_tokens_assigned = rng.choice(inc_tokens_pool, size=n_miss_inc).tolist()

    n_miss_reg = max(1, int(round(n_rows * cfg_rates["missing_tokens_region_unknown"])))
    miss_reg_idx = sorted(rng.choice(all_idx, size=n_miss_reg, replace=False).tolist())

    # -------------------------------------------------------------------------
    # 3. numeric_as_string: format non-missing income and all monthly_spend with $ and commas
    #    plus ~1% as scientific notation "1.23e4"
    # -------------------------------------------------------------------------
    miss_inc_set = set(miss_inc_idx)
    n_sci = max(1, int(round(n_rows * cfg_rates["numeric_sci_rate"])))
    non_miss_inc_idx = [i for i in range(n_rows) if i not in miss_inc_set]
    sci_inc_set = set(rng.choice(non_miss_inc_idx, size=min(n_sci, len(non_miss_inc_idx)), replace=False).tolist())
    sci_spend_set = set(rng.choice(all_idx, size=n_sci, replace=False).tolist())

    inc_formatted_count = 0
    for i in range(n_rows):
        if i in miss_inc_set:
            continue
        val = float(income_numeric.iloc[i])
        if i in sci_inc_set:
            df.loc[i, "income"] = f"{val:.3e}"
        else:
            df.loc[i, "income"] = f"${val:,.2f}"
        inc_formatted_count += 1

    spend_formatted_count = 0
    for i in range(n_rows):
        val = float(spend_numeric.iloc[i])
        if i in sci_spend_set:
            df.loc[i, "monthly_spend"] = f"{val:.3e}"
        else:
            df.loc[i, "monthly_spend"] = f"${val:,.2f}"
        spend_formatted_count += 1

    # Now apply missing_tokens to income and region
    for idx_pos, r_i in enumerate(miss_inc_idx):
        df.loc[r_i, "income"] = inc_tokens_assigned[idx_pos]
    for r_i in miss_reg_idx:
        df.loc[r_i, "region"] = "Unknown"

    miss_token_union_rows = sorted(set(miss_inc_idx) | set(miss_reg_idx))
    entries.append(
        ManifestEntry(
            problem_id="missing_tokens",
            problem_type="missing_token",
            columns=["income", "region"],
            n_cells=len(miss_inc_idx) + len(miss_reg_idx),
            n_rows=len(miss_token_union_rows),
            row_indices_sample=miss_token_union_rows[:20],
            description="Replaced ~8% of income with placeholder tokens ('', 'N/A', '?', 'null', '-') and ~4% of region with 'Unknown'.",
            expected_pipeline_behavior="auto_fixed",
            details={
                "income_rows": miss_inc_idx,
                "region_unknown_rows": miss_reg_idx,
            },
        )
    )

    entries.append(
        ManifestEntry(
            problem_id="numeric_as_string",
            problem_type="numeric_as_string",
            columns=["income", "monthly_spend"],
            n_cells=inc_formatted_count + spend_formatted_count,
            n_rows=n_rows,
            row_indices_sample=list(range(min(20, n_rows))),
            description="Stored income and monthly_spend with '$' and thousands commas (~1% as scientific notation).",
            expected_pipeline_behavior="auto_fixed",
            details={
                "income_formatted_cells": inc_formatted_count,
                "monthly_spend_formatted_cells": spend_formatted_count,
            },
        )
    )

    # -------------------------------------------------------------------------
    # 4. real_nan: true NaN (empty cell in CSV) in age (~6%) and satisfaction (~3%)
    # -------------------------------------------------------------------------
    n_nan_age = max(1, int(round(n_rows * cfg_rates["real_nan_age"])))
    nan_age_idx = sorted(rng.choice(all_idx, size=n_nan_age, replace=False).tolist())
    for r_i in nan_age_idx:
        df.loc[r_i, "age"] = ""

    n_nan_sat = max(1, int(round(n_rows * cfg_rates["real_nan_satisfaction"])))
    nan_sat_idx = sorted(rng.choice(all_idx, size=n_nan_sat, replace=False).tolist())
    for r_i in nan_sat_idx:
        df.loc[r_i, "satisfaction"] = ""

    nan_union_rows = sorted(set(nan_age_idx) | set(nan_sat_idx))
    entries.append(
        ManifestEntry(
            problem_id="real_nan",
            problem_type="missing_token",
            columns=["age", "satisfaction"],
            n_cells=len(nan_age_idx) + len(nan_sat_idx),
            n_rows=len(nan_union_rows),
            row_indices_sample=nan_union_rows[:20],
            description="Injected true NaN (empty cells) in ~6% of age and ~3% of satisfaction.",
            expected_pipeline_behavior="left_alone",
            details={"age_rows": nan_age_idx, "satisfaction_rows": nan_sat_idx},
        )
    )

    # -------------------------------------------------------------------------
    # 5. impossible_values: negative age, age > 120, negative tenure_months (~0.5% each)
    # -------------------------------------------------------------------------
    avail_age_imp = np.setdiff1d(all_idx, np.array(nan_age_idx, dtype=int))
    n_imp_each = max(1, int(round(n_rows * cfg_rates["impossible_values"])))
    imp_age_chosen = rng.choice(avail_age_imp, size=2 * n_imp_each, replace=False)
    imp_age_neg_idx = sorted(imp_age_chosen[:n_imp_each].tolist())
    imp_age_high_idx = sorted(imp_age_chosen[n_imp_each:].tolist())

    for r_i in imp_age_neg_idx:
        df.loc[r_i, "age"] = str(-int(rng.integers(1, 25)))
    for r_i in imp_age_high_idx:
        df.loc[r_i, "age"] = str(int(rng.integers(125, 165)))

    # -------------------------------------------------------------------------
    # 6. mixed_types: ~1% of tenure_months replaced by words ("twelve", "n/a")
    # -------------------------------------------------------------------------
    n_mixed_ten = max(1, int(round(n_rows * cfg_rates["mixed_types_tenure"])))
    mixed_ten_idx = sorted(rng.choice(all_idx, size=n_mixed_ten, replace=False).tolist())
    for k_i, r_i in enumerate(mixed_ten_idx):
        df.loc[r_i, "tenure_months"] = "twelve" if k_i % 2 == 0 else "twenty"

    avail_ten_imp = np.setdiff1d(all_idx, np.array(mixed_ten_idx, dtype=int))
    imp_ten_neg_idx = sorted(rng.choice(avail_ten_imp, size=n_imp_each, replace=False).tolist())
    for r_i in imp_ten_neg_idx:
        df.loc[r_i, "tenure_months"] = str(-int(rng.integers(1, 18)))

    imp_union_rows = sorted(set(imp_age_neg_idx) | set(imp_age_high_idx) | set(imp_ten_neg_idx))
    entries.append(
        ManifestEntry(
            problem_id="impossible_values",
            problem_type="impossible_values",
            columns=["age", "tenure_months"],
            n_cells=len(imp_age_neg_idx) + len(imp_age_high_idx) + len(imp_ten_neg_idx),
            n_rows=len(imp_union_rows),
            row_indices_sample=imp_union_rows[:20],
            description="Injected negative age, age > 120, and negative tenure_months (~0.5% each).",
            expected_pipeline_behavior="auto_fixed",
            details={
                "age_negative_rows": imp_age_neg_idx,
                "age_gt_120_rows": imp_age_high_idx,
                "tenure_negative_rows": imp_ten_neg_idx,
            },
        )
    )

    entries.append(
        ManifestEntry(
            problem_id="mixed_types",
            problem_type="mixed_types",
            columns=["tenure_months"],
            n_cells=len(mixed_ten_idx),
            n_rows=len(mixed_ten_idx),
            row_indices_sample=mixed_ten_idx[:20],
            description="Replaced ~1% of tenure_months with English words ('twelve', 'twenty').",
            expected_pipeline_behavior="auto_fixed",
            details={"tenure_word_rows": mixed_ten_idx},
        )
    )

    # -------------------------------------------------------------------------
    # 7. case_variants in gender: ~10% case-only ("male"/"MALE"/"female"/"FEMALE")
    #    and ~3% fuzzy abbreviation ("M"/"F")
    # -------------------------------------------------------------------------
    n_case_auto = max(1, int(round(n_rows * cfg_rates["case_variants_auto"])))
    n_case_fuzzy = max(1, int(round(n_rows * cfg_rates["case_variants_fuzzy"])))
    gender_chosen = rng.choice(all_idx, size=n_case_auto + n_case_fuzzy, replace=False)
    case_auto_idx = sorted(gender_chosen[:n_case_auto].tolist())
    case_fuzzy_idx = sorted(gender_chosen[n_case_auto:].tolist())

    for k_i, r_i in enumerate(case_auto_idx):
        orig = df.loc[r_i, "gender"]
        df.loc[r_i, "gender"] = orig.lower() if k_i % 2 == 0 else orig.upper()

    for r_i in case_fuzzy_idx:
        orig = df.loc[r_i, "gender"]
        df.loc[r_i, "gender"] = "M" if orig.lower().startswith("m") else "F"

    entries.append(
        ManifestEntry(
            problem_id="case_variants",
            problem_type="case_variant",
            columns=["gender"],
            n_cells=len(case_auto_idx) + len(case_fuzzy_idx),
            n_rows=len(case_auto_idx) + len(case_fuzzy_idx),
            row_indices_sample=sorted(case_auto_idx + case_fuzzy_idx)[:20],
            description="Injected ~10% case-only variants ('male', 'MALE', 'female', 'FEMALE') and ~3% 'M'/'F' abbreviations in gender.",
            expected_pipeline_behavior="auto_fixed",
            details={
                "case_only_auto_fixed_rows": case_auto_idx,
                "abbreviation_flagged_only_rows": case_fuzzy_idx,
            },
        )
    )

    # -------------------------------------------------------------------------
    # 8. ws_internal: double internal spaces in ~2% of region cells
    # -------------------------------------------------------------------------
    avail_reg_ws = np.setdiff1d(all_idx, np.array(miss_reg_idx, dtype=int))
    n_ws_int = max(1, int(round(n_rows * cfg_rates["ws_internal"])))
    ws_int_idx = sorted(rng.choice(avail_reg_ws, size=n_ws_int, replace=False).tolist())
    for r_i in ws_int_idx:
        df.loc[r_i, "region"] = df.loc[r_i, "region"].replace(" ", "  ", 1)

    entries.append(
        ManifestEntry(
            problem_id="ws_internal",
            problem_type="whitespace",
            columns=["region"],
            n_cells=len(ws_int_idx),
            n_rows=len(ws_int_idx),
            row_indices_sample=ws_int_idx[:20],
            description="Injected double internal spaces in ~2% of region cells.",
            expected_pipeline_behavior="auto_fixed",
            details={"region_rows": ws_int_idx},
        )
    )

    # -------------------------------------------------------------------------
    # 9. ws_leading_trailing: add leading/trailing spaces to ~5% of cells in 3 string columns
    #    (gender, region, membership)
    # -------------------------------------------------------------------------
    n_ws_lt = max(1, int(round(n_rows * cfg_rates["ws_leading_trailing"])))
    avail_gen_lt = np.setdiff1d(all_idx, np.array(case_fuzzy_idx, dtype=int))
    ws_gen_idx = sorted(rng.choice(avail_gen_lt, size=n_ws_lt, replace=False).tolist())
    ws_reg_idx = sorted(rng.choice(avail_reg_ws, size=n_ws_lt, replace=False).tolist())
    ws_mem_idx = sorted(rng.choice(all_idx, size=n_ws_lt, replace=False).tolist())

    for r_i in ws_gen_idx:
        df.loc[r_i, "gender"] = f" {df.loc[r_i, 'gender']} "
    for r_i in ws_reg_idx:
        df.loc[r_i, "region"] = f"{df.loc[r_i, 'region']}  "
    for r_i in ws_mem_idx:
        df.loc[r_i, "membership"] = f"  {df.loc[r_i, 'membership']}"

    ws_lt_union = sorted(set(ws_gen_idx) | set(ws_reg_idx) | set(ws_mem_idx))
    entries.append(
        ManifestEntry(
            problem_id="ws_leading_trailing",
            problem_type="whitespace",
            columns=["gender", "region", "membership"],
            n_cells=len(ws_gen_idx) + len(ws_reg_idx) + len(ws_mem_idx),
            n_rows=len(ws_lt_union),
            row_indices_sample=ws_lt_union[:20],
            description="Added leading/trailing whitespace to ~5% of cells in gender, region, and membership.",
            expected_pipeline_behavior="auto_fixed",
            details={
                "gender_rows": ws_gen_idx,
                "region_rows": ws_reg_idx,
                "membership_rows": ws_mem_idx,
            },
        )
    )

    # -------------------------------------------------------------------------
    # 10. date_formats: signup_date mixed YYYY-MM-DD, DD/MM/YYYY, Mon DD, YYYY (~33% each)
    #     + ~1% garbage strings
    # -------------------------------------------------------------------------
    n_date_garbage = max(1, int(round(n_rows * cfg_rates["date_garbage_rate"])))
    date_garbage_idx = sorted(rng.choice(all_idx, size=n_date_garbage, replace=False).tolist())
    date_garbage_set = set(date_garbage_idx)
    reformatted_date_rows: list[int] = []

    for i in range(n_rows):
        if i in date_garbage_set:
            df.loc[i, "signup_date"] = "not_a_valid_date"
            continue
        dt_obj = datetime.strptime(df.loc[i, "signup_date"], "%Y-%m-%d").date()
        bucket = i % 3
        if bucket == 1:
            df.loc[i, "signup_date"] = dt_obj.strftime("%d/%m/%Y")
            reformatted_date_rows.append(i)
        elif bucket == 2:
            df.loc[i, "signup_date"] = dt_obj.strftime("%b %d, %Y")
            reformatted_date_rows.append(i)

    date_affected_rows = sorted(set(reformatted_date_rows) | date_garbage_set)
    entries.append(
        ManifestEntry(
            problem_id="date_formats",
            problem_type="date_format",
            columns=["signup_date"],
            n_cells=len(date_affected_rows),
            n_rows=len(date_affected_rows),
            row_indices_sample=date_affected_rows[:20],
            description="Mixed signup_date formats (YYYY-MM-DD, DD/MM/YYYY, Mon DD, YYYY) plus ~1% unparseable date strings.",
            expected_pipeline_behavior="auto_fixed",
            details={
                "garbage_date_rows": date_garbage_idx,
                "non_iso_formatted_count": len(reformatted_date_rows),
            },
        )
    )

    # -------------------------------------------------------------------------
    # 11. binary_encoding_mix: churned encoded as Yes/No/yes/Y/1/0 mix (~5% variants)
    # -------------------------------------------------------------------------
    n_bin_mix = max(1, int(round(n_rows * cfg_rates["binary_encoding_mix"])))
    bin_mix_idx = sorted(rng.choice(all_idx, size=n_bin_mix, replace=False).tolist())
    for k_i, r_i in enumerate(bin_mix_idx):
        orig = df.loc[r_i, "churned"]
        if orig == "Yes":
            df.loc[r_i, "churned"] = ["yes", "Y", "1"][k_i % 3]
        else:
            df.loc[r_i, "churned"] = ["no", "0"][k_i % 2]

    entries.append(
        ManifestEntry(
            problem_id="binary_encoding_mix",
            problem_type="case_variant",
            columns=["churned"],
            n_cells=len(bin_mix_idx),
            n_rows=len(bin_mix_idx),
            row_indices_sample=bin_mix_idx[:20],
            description="Encoded ~5% of churned as mixed 'yes'/'no'/'Y'/'1'/'0' variants.",
            expected_pipeline_behavior="auto_fixed",
            details={"churned_variant_rows": bin_mix_idx},
        )
    )

    # -------------------------------------------------------------------------
    # 12. constant_column & 13. id_column (structural truth records)
    # -------------------------------------------------------------------------
    entries.append(
        ManifestEntry(
            problem_id="constant_column",
            problem_type="constant_column",
            columns=["constant_flag"],
            n_cells=n_rows,
            n_rows=n_rows,
            row_indices_sample=list(range(min(20, n_rows))),
            description="Column 'constant_flag' has a single constant value 'A'.",
            expected_pipeline_behavior="flagged_only",
        )
    )
    entries.append(
        ManifestEntry(
            problem_id="id_column",
            problem_type="id_column",
            columns=["customer_id"],
            n_cells=n_rows,
            n_rows=n_rows,
            row_indices_sample=list(range(min(20, n_rows))),
            description="Column 'customer_id' is a unique identifier column.",
            expected_pipeline_behavior="flagged_only",
        )
    )

    # -------------------------------------------------------------------------
    # 14. duplicates_exact (~3% of rows) & 15. duplicates_formatting (~1% of rows)
    # -------------------------------------------------------------------------
    n_dup_exact = max(1, int(round(n_rows * cfg_rates["duplicates_exact"])))
    n_dup_fmt = max(1, int(round(n_rows * cfg_rates["duplicates_formatting"])))
    dup_chosen = rng.choice(all_idx, size=n_dup_exact + n_dup_fmt, replace=False)
    dup_exact_src = sorted(dup_chosen[:n_dup_exact].tolist())
    dup_fmt_src = sorted(dup_chosen[n_dup_exact:].tolist())

    exact_copies = df.iloc[dup_exact_src].copy()
    exact_copies["_row_kind"] = "duplicate_exact"

    fmt_copies = df.iloc[dup_fmt_src].copy()
    fmt_copies["_row_kind"] = "duplicate_formatting"
    for r_i in fmt_copies.index:
        fmt_copies.loc[r_i, "gender"] = f"  {fmt_copies.loc[r_i, 'gender'].strip().lower()}  "
        fmt_copies.loc[r_i, "membership"] = f"{fmt_copies.loc[r_i, 'membership'].strip().upper()} "

    # -------------------------------------------------------------------------
    # 16. empty_rows: add ~10 fully empty rows
    # -------------------------------------------------------------------------
    n_empty_rows = int(cfg_rates["empty_rows_count"])
    empty_rows_df = pd.DataFrame(
        {col: [""] * n_empty_rows for col in df.columns},
    )
    empty_rows_df["_row_uid"] = -1
    empty_rows_df["_row_kind"] = "empty_row"

    # Combine primary + exact duplicates + formatting duplicates + empty rows
    df_combined = pd.concat([df, exact_copies, fmt_copies, empty_rows_df], ignore_index=True)

    dup_exact_messy_indices = df_combined.index[df_combined["_row_kind"] == "duplicate_exact"].tolist()
    dup_fmt_messy_indices = df_combined.index[df_combined["_row_kind"] == "duplicate_formatting"].tolist()
    empty_row_messy_indices = df_combined.index[df_combined["_row_kind"] == "empty_row"].tolist()

    entries.append(
        ManifestEntry(
            problem_id="duplicates_exact",
            problem_type="duplicate_rows",
            columns=list(df_clean.columns),
            n_cells=len(dup_exact_messy_indices) * n_cols,
            n_rows=len(dup_exact_messy_indices),
            row_indices_sample=dup_exact_messy_indices[:20],
            description="Appended ~3% exact duplicate rows.",
            expected_pipeline_behavior="auto_fixed",
            details={
                "source_rows": dup_exact_src,
                "messy_row_indices": dup_exact_messy_indices,
            },
        )
    )
    entries.append(
        ManifestEntry(
            problem_id="duplicates_formatting",
            problem_type="duplicate_rows",
            columns=["gender", "membership"],
            n_cells=len(dup_fmt_messy_indices) * 2,
            n_rows=len(dup_fmt_messy_indices),
            row_indices_sample=dup_fmt_messy_indices[:20],
            description="Appended ~1% duplicate rows with whitespace and case differences.",
            expected_pipeline_behavior="auto_fixed",
            details={
                "source_rows": dup_fmt_src,
                "messy_row_indices": dup_fmt_messy_indices,
            },
        )
    )
    entries.append(
        ManifestEntry(
            problem_id="empty_rows",
            problem_type="empty_rows",
            columns=list(df_clean.columns),
            n_cells=len(empty_row_messy_indices) * n_cols,
            n_rows=len(empty_row_messy_indices),
            row_indices_sample=empty_row_messy_indices[:20],
            description=f"Added {len(empty_row_messy_indices)} fully empty rows.",
            expected_pipeline_behavior="auto_fixed",
            details={"messy_row_indices": empty_row_messy_indices},
        )
    )

    # -------------------------------------------------------------------------
    # 17. empty_column: add a fully empty column 'unused'
    # -------------------------------------------------------------------------
    df_combined["unused"] = ""
    entries.append(
        ManifestEntry(
            problem_id="empty_column",
            problem_type="empty_columns",
            columns=["unused"],
            n_cells=len(df_combined),
            n_rows=len(df_combined),
            row_indices_sample=list(range(min(20, len(df_combined)))),
            description="Added fully empty column 'unused'.",
            expected_pipeline_behavior="auto_fixed",
        )
    )

    # -------------------------------------------------------------------------
    # 18. column_name_issues: trailing space in 'membership ', plus 'Unnamed: 0' index column
    # -------------------------------------------------------------------------
    unnamed_vals = [
        "" if kind == "empty_row" else str(int(uid) if uid >= 0 else idx)
        for idx, (uid, kind) in enumerate(zip(df_combined["_row_uid"], df_combined["_row_kind"]))
    ]
    df_combined.insert(0, "Unnamed: 0", unnamed_vals)
    df_combined = df_combined.rename(columns={"membership": "membership "})

    entries.append(
        ManifestEntry(
            problem_id="column_name_issues",
            problem_type="column_name",
            columns=["Unnamed: 0", "membership "],
            n_cells=len(df_combined) * 2,
            n_rows=len(df_combined),
            row_indices_sample=list(range(min(20, len(df_combined)))),
            description="Added 'Unnamed: 0' index column and trailing space in 'membership ' column header.",
            expected_pipeline_behavior="auto_fixed",
        )
    )

    # Build messy_to_truth_index.json payload BEFORE dropping _row_uid and _row_kind
    row_alignments: list[dict[str, Any]] = []
    for messy_idx in range(len(df_combined)):
        uid = int(df_combined.loc[messy_idx, "_row_uid"])
        kind = str(df_combined.loc[messy_idx, "_row_kind"])
        cid = str(df_combined.loc[messy_idx, "customer_id"]).strip()
        row_alignments.append(
            {
                "messy_row_index": messy_idx,
                "truth_row_index": uid if uid >= 0 else None,
                "row_kind": kind,
                "customer_id": cid if cid else None,
            }
        )

    customer_id_to_truth = {
        str(df_clean.loc[i, "customer_id"]): int(i) for i in range(n_rows)
    }

    df_messy = df_combined.drop(columns=["_row_uid", "_row_kind"])

    manifest = MessyManifest(
        dataset_name=dataset_name,
        seed=seed,
        n_rows_clean=n_rows,
        n_cols_clean=n_cols,
        n_rows_messy=int(len(df_messy)),
        n_cols_messy=int(len(df_messy.columns)),
        entries=entries,
    )

    index_map_payload = {
        "dataset_name": dataset_name,
        "seed": seed,
        "n_rows_clean": n_rows,
        "n_rows_messy": int(len(df_messy)),
        "customer_id_to_truth_row": customer_id_to_truth,
        "messy_rows": row_alignments,
    }

    return df_messy, manifest, index_map_payload


def generate_and_save_messy_dataset(
    out_dir: Path | str = Path("data/synthetic"),
    n_rows: int = 2000,
    seed: int = 42,
    rates: dict[str, float] | None = None,
    prefix: str = "messy",
) -> dict[str, Path]:
    """Generate clean base, inject problems, and save CSV + manifest + truth files (Section 12.2)."""
    target_dir = Path(out_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    df_clean = make_clean_base(n_rows=n_rows, seed=seed)
    df_messy, manifest, index_map = inject_problems(
        df_clean,
        seed=seed,
        rates=rates,
        dataset_name=f"{prefix}_synthetic" if prefix == "messy" else prefix,
    )

    messy_csv = target_dir / f"{prefix}_dataset.csv"
    manifest_json = target_dir / f"{prefix}_manifest.json"
    truth_csv = target_dir / f"{prefix}_clean_truth.csv"
    index_json = target_dir / f"{prefix}_to_truth_index.json"
    base_truth_json = target_dir / "base_truth.json"

    df_messy.to_csv(messy_csv, index=False, encoding="utf-8", lineterminator="\n")
    df_clean.to_csv(truth_csv, index=False, encoding="utf-8", lineterminator="\n")

    manifest_json.write_text(
        json.dumps(manifest.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    index_json.write_text(
        json.dumps(index_map, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    save_base_truth_json(df_clean, base_truth_json, seed=seed)

    return {
        "messy_csv": messy_csv,
        "manifest_json": manifest_json,
        "truth_csv": truth_csv,
        "index_json": index_json,
        "base_truth_json": base_truth_json,
    }

