# Phase 1 -> Phase 2 Handoff Contract (`docs/contract.md`)

> **Schema Version:** `1.0`
> **Reference:** `plans/PHASE1_PLAN.md` (Sections 6, 14, 19)

Phase 2 (Hypothesis Generation) and Phase 4 (LangGraph Agentic Data Scientist) rely on the exact file artifacts and pure Python APIs documented below. Any breaking change to field names, enum values, or file paths requires incrementing `schema_version` in `src/ads/schemas.py` and updating this document.

---

## 1. Per-Dataset File Artifacts

Running `ads run --input <csv_path> --name <dataset_name>` produces the following deterministic artifacts:

### 1.1 Cleaned Datasets (`data/cleaned/`)
1. **`data/cleaned/<name>_cleaned.csv` (PRIMARY — Consumed by Phase 2 & Phase 3):**
   - **Conservative cleaned DataFrame (`df_clean_conservative`).**
   - Missing values (`NaN`) are **preserved** (never imputed) so downstream statistical tests in Phase 3 can apply pairwise or listwise deletion without artificial variance reduction or effect-size bias.
   - Outliers are **flagged only** (not removed or capped) so rank-based and robust tests in Phase 3 see the true empirical distribution.
   - Datetime columns are formatted as canonical ISO-8601 strings (`YYYY-MM-DD` or `YYYY-MM-DDTHH:MM:SS`).
   - Redundant exported index columns (`Unnamed: 0`), fully empty columns, fully empty rows, exact/normalized duplicate rows, and rows with $>50\%$ missing values are removed.
   - Constant, ID-like, and free-text columns are **retained** in the CSV (so no user data is lost) and marked as `id` or `excluded` in `column_schema.json`.
2. **`data/cleaned/<name>_cleaned_imputed.csv` (SECONDARY — TA Deliverable & Modeling Copy):**
   - Drops columns with $>80\%$ missingness and drops rows where the configured `target` column is missing.
   - Adds `<col>__was_missing` boolean indicator columns for any column with $\ge 5\%$ missingness.
   - Imputes numeric columns with the median, and categorical/binary columns with the mode (or a `"Missing"` category level if $\ge 5\%$ missing).
3. **`data/cleaned/<name>_scaled.csv` (CONVENIENCE — TA Review & Parametric/Distance Modeling):**
   - Built from `df_clean_imputed`, appending `<col>__log1p` (for right-skewed non-negative features), `<col>__yeojohnson` (for right-skewed features with negative values), and `<col>__z` (z-score standardized features).
   - **Never fed into Phase 3 statistical hypothesis testing.**

---

### 1.2 Structured Metadata & Logs (`outputs/<name>/`)

1. **`outputs/<name>/column_schema.json` (Primary Phase 2 Enumeration Input):**
   - Maps every column name in `<name>_cleaned.csv` to a `ColumnSchemaEntry`:
     ```json
     {
       "charges": {
         "binary_labels": null,
         "exclude_reason": null,
         "n_unique": 1337,
         "pct_missing": 0.0,
         "role": "target_candidate",
         "semantic_type": "numeric_continuous"
       },
       "customerID": {
         "binary_labels": null,
         "exclude_reason": "id_like",
         "n_unique": 7043,
         "pct_missing": 0.0,
         "role": "id",
         "semantic_type": "id_like"
       }
     }
     ```
   - **`semantic_type` enum (`SemanticType`):**
     `numeric_continuous`, `numeric_discrete`, `binary`, `categorical_nominal`, `categorical_ordinal`, `datetime`, `id_like`, `free_text`, `constant`, `unknown`.
   - **`role` enum (`ColumnRole`):**
     - `feature`: Valid candidate variable for Phase 2 hypothesis enumeration.
     - `target_candidate`: Primary outcome/target variable (prioritized in Phase 2 hypothesis ranking).
     - `id`: Identifier column (excluded from statistical testing).
     - `excluded`: Constant, free-text, unknown, or $>80\%$ missing column (excluded from statistical testing and correlation heatmaps).

2. **`outputs/<name>/profile.json` (`DataProfile`, `schema_version: "1.0"`):**
   - Full dataset and per-column profile on the raw input ( plus `outputs/<name>/profile_cleaned.json` on the cleaned conservative frame).
   - Contains exact counts (`n_rows`, `n_cols`, `n_duplicate_rows_raw`, `n_duplicate_rows`, `n_fully_empty_rows`, `n_fully_empty_cols`), `missing_matrix_summary`, `warnings`, and per-column `ColumnProfile` records (`min`, `max`, `mean`, `median`, `std`, `q1`, `q3`, `iqr`, `skewness`, `kurtosis`, outlier counts, string quality flags, and `top_values`).

3. **`outputs/<name>/cleaning_log.json` (`list[CleaningLogEntry]`):**
   - Ordered audit trail of every action taken during `clean_dataset()`, with `step`, `column`, `action`, `n_cells_affected`, `n_rows_affected`, `rows_before`, `rows_after`, `reason`, `before_examples`, `after_examples`, `parameters`, and `severity`.

4. **`outputs/<name>/insights.json` (`list[InsightRecord]`):**
   - Rule-based descriptive insights (`data_quality`, `distributions`, `class_balance`, `relationships`, `cardinality_structure`, `scaling`, `modeling_testing_implications`) with structured numeric `evidence`. Used by Phase 2 as candidate relationship hints only, never as validated test findings.

---

## 2. Python API Contract (for Phase 4 LangGraph Nodes & Partner 2 Modules)

All core functions in `src/ads/` are deterministic and side-effect-free outside their designated output paths:

```python
from ads.config import PipelineConfig, load_config
from ads.ingestion import load_csv
from ads.type_inference import infer_column_types, infer_column_types_detailed
from ads.profiling import profile_dataset, build_column_schema
from ads.cleaning import clean_dataset
from ads.scaling import analyze_scaling
from ads.pipeline import run_phase1
```

### Partner 1 <-> Partner 2 Integration Hooks in `ads.pipeline.run_phase1`
`run_phase1()` automatically invokes Partner 2's modules when present:
1. `ads.eda.run_eda(df_clean_conservative, raw_profile, schema, config, out_dir) -> EDAResult`
2. `ads.insights.generate_insights(raw_profile, cleaning_result, eda_result, scaling_report, config, out_dir) -> InsightsReport`
3. `ads.reporting.render_dataset_report(raw_profile, cleaning_result, eda_result, scaling_report, out_dir) -> Path`

