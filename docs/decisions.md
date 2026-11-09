# Phase 1 Design & Implementation Decisions (`docs/decisions.md`)

This document records every **DECISION** and **OPEN** item from `plans/PHASE1_PLAN.md`, the chosen resolution, and the engineering rationale.

---

## 1. Resolved `DECISION` Items

| ID | Section | Plan Requirement | Resolution & Rationale |
| :--- | :---: | :--- | :--- |
| **D1** | Sec 5.1 | Do **not** use Titanic as a main dataset. | **Followed.** Selected `insurance`, `telco_churn`, `heart_disease`, `student_performance`, and `bank_marketing`, plus `messy_synthetic`. Avoids LLM memorization contamination in the Section 13 comparison. |
| **D2** | Sec 5.1 | Record exact download source, date, license, and SHA-256; fail with a clear message if a raw file is missing. | **Followed.** `load_csv()` in `src/ads/ingestion.py` raises a clear `FileNotFoundError` pointing to `scripts/download_datasets.md` rather than an unhandled pandas traceback, and computes SHA-256 on every file. |
| **D3** | Sec 6.1 | Do not guess ordinality aggressively (`categorical_ordinal`). | **Followed.** `type_inference.py` only assigns `categorical_ordinal` when explicitly listed in `config.ordinal_orders` or when unique values exactly match a closed list of known ordinal sets (`low/medium/high`, `basic/silver/gold`, `poor/fair/good/excellent`). Otherwise defaults to `categorical_nominal`. |
| **D4** | Sec 7.2 | If column name matches `zip\|postal\|phone\|code` and values are fixed-length digit strings (or zero-padded strings), treat as categorical/`id_like`, not continuous. | **Followed.** Implemented in `_is_fixed_length_code_or_zip()` in `src/ads/type_inference.py`, running *before* Step 4 numeric parsing so ZIP codes and phone numbers are never averaged as continuous floats. |
| **D5** | Sec 8 | Token `"unknown"` is treated as missing only if configured per dataset; default to flagging it as a candidate missing token in warnings. | **Followed.** Controlled by `profiling.treat_unknown_as_missing` (default `false` in `configs/default.yaml`; enabled in `messy_synthetic.yaml` and `bank_marketing.yaml`). When `false`, `profiling.py` emits a candidate missing token warning with count and percentage. |
| **D6** | Sec 9.1 | Keep original column names (case/spaces preserved) after stripping leading/trailing/internal extra whitespace; do not `snake_case` by default. | **Followed.** `cleaning.snake_case_columns` defaults to `false` in `configs/default.yaml`, and all header normalizations are recorded in `name_map`. |
| **D7** | Sec 9.4 | Do **not** auto-merge fuzzy near-duplicates (`"Gender"`/`"Gendr"` or `"M"`/`"F"` abbreviations); emit a `warning` log entry unless `auto_merge_fuzzy: true`. Do not recode `Yes`/`No` to `1`/`0`. | **Followed.** `step4_standardize_categories()` in `src/ads/cleaning/categories.py` merges case-only variants (`"male"`/`"MALE"` -> `"Male"`) and mixed boolean tokens (`"yes"`/`"Y"`/`"1"` -> `"Yes"`), while logging fuzzy/abbreviation candidates with `action="flagged_fuzzy_variants"` and `severity="warning"`. |
| **D8** | Sec 9.5 | When stripping `%` during numeric conversion, do **not** divide by 100; keep the number and note `%` in the log. | **Followed.** `step5_convert_types()` keeps the numeric value as-is (e.g., `"12%"` -> `12.0`) and appends `"percentage symbol stripped without dividing by 100"` to the log entry reason. |
| **D9** | Sec 9.7 | Duplicate drop policy (`drop_duplicates: auto`): if no ID column and (`n_cols <= 4` or duplicate rate $> 20\%$), keep duplicates and log a warning. | **Followed.** Implemented in `step7_handle_duplicates()` in `src/ads/cleaning/steps.py`. Prevents dropping legitimate repeated observations in narrow survey/measurement tables (`insurance`, `heart_disease`). |
| **D10** | Sec 9.8 | Keep `constant`, `id_like`, and `free_text` columns in `df_clean_conservative` (mark `excluded` in schema). Drop columns with $>80\%$ missingness in `imputed` output only. | **Followed.** Implemented across `step8_structural_drops()`, `step9_handle_missing_values()`, and `build_column_schema()`. |
| **D11** | Sec 9.9 | Always use median imputation for numeric columns in `df_clean_imputed` for simplicity and robustness; add `<col>__was_missing` indicator when `pct_missing >= 5%`. | **Followed.** Implemented in `step9_handle_missing_values()` in `src/ads/cleaning/missing.py`. |
| **D12** | Sec 9.10 | Default `outlier_action` is `flag` for both outputs; run outlier detection after validity rules and before imputation. | **Followed.** `detect_outliers_pre_imputation()` runs before `step9_handle_missing_values()` so imputed medians never distort IQR/MAD fences. |
| **D13** | Sec 11b | Produce `data/cleaned/<name>_scaled.csv` for every dataset as a TA convenience copy; never feed into Phase 3 testing. | **Followed.** `analyze_scaling()` in `src/ads/scaling.py` generates `<name>_scaled.csv`, `scaling_params.json`, and `scaling_report.md` on every pipeline run. |
| **D14** | Sec 13.3 & 13.5 | Implement both Mode A (summary) and Mode B (sandboxed code) LLM baselines; run $N=3$ repeats at $T=0.0$ and $N=3$ at $T=0.7$ for Mode A. | **Followed.** Documented in `plans/PHASE1_WORK_SPLIT.md` for Partner 2's baseline runner. |

---

## 2. Resolved `OPEN` Items

| ID | Section | Open Question | Chosen Default & Rationale |
| :--- | :---: | :--- | :--- |
| **O1** | Sec 3 & 14.2 | CLI framework: `typer` vs. `argparse` (fewer dependencies). | **Chosen:** Built `src/ads/cli.py` with Python's standard-library `argparse` while exposing the `ads` console script entrypoint in `pyproject.toml`. **Why:** Zero external CLI dependency failures in minimal/sandboxed environments while supporting the exact CLI flags in Section 14.2 (`ads run`, `ads run-all`, `ads make-messy`, `ads llm-baseline`, `ads compare`, `ads report`). |
| **O2** | Sec 11b | Yeo-Johnson power transform implementation: `sklearn.preprocessing.PowerTransformer` vs. `scipy.stats.yeojohnson`. | **Chosen:** Used `scipy.stats.yeojohnson` (already part of core dependency `scipy`) in `src/ads/scaling.py` while also listing `scikit-learn` in `pyproject.toml`. **Why:** `scipy.stats.yeojohnson` computes the exact Yeo-Johnson transformation and directly returns the fitted $\lambda$ parameter for `scaling_params.json` with zero extra dependency overhead. |
| **O3** | Sec 7.2 | `discrete_max_ratio` threshold on very small unit-test series ($<100$ rows). | **Chosen:** Use configured `discrete_max_ratio = 0.05` when $n_{\text{nonnull}} \ge 100$, and relax to `0.40` when $n_{\text{nonnull}} < 100$. **Why:** On a 20-row unit-test series with 4 integer levels (`1, 2, 3, 4`), $4/20 = 0.20 > 0.05$; relaxing the ratio for $n < 100$ allows tiny constructed unit tests to exercise the `numeric_discrete` branch while keeping the strict `0.05` ratio on all real datasets. |
| **O4** | Sec 16 | Determinism of `profile.json` across repeated runs (`generated_at` timestamp). | **Chosen:** Set `generated_at = "deterministic"` inside `profile.json` and record wall-clock UTC timestamps and execution durations in `outputs/<name>/run_meta.json`. **Why:** Satisfies Section 16's requirement: *"Determinism test: two runs -> identical output hashes (excluding timestamps; keep timestamps only in a separate `run_meta.json`)."* |


---

## 3. Partner 2 Decisions (EDA, Insights, Reports)

| ID | Section | Question | Chosen Default & Rationale |
| :--- | :---: | :--- | :--- |
| **P2-1** | Sec 10.6 | How to rank the "top-10 strongest" numeric pairs. | **Chosen:** rank by \|Spearman rho\| (ties broken by \|Pearson r\|), show both. **Why:** rank-based, so a few outliers cannot create or hide a "strong" pair; matches the rank-based Phase 3 test library. |
| **P2-2** | Sec 10.5 | Thresholds for "balanced / mildly / highly imbalanced". | **Chosen:** highly = smallest class < `profiling.minority_imbalance_threshold` (10%, from the plan); mildly = largest/smallest ratio ≥ 1.5; otherwise balanced. Implemented in `eda/stats.py::imbalance_label`. |
| **P2-3** | Sec 10.6 | Scatter trend line: LOWESS or linear. | **Chosen:** straight-line fit (`numpy.polyfit`). **Why:** LOWESS needs `statsmodels`, which is not a project dependency; the line is a visual guide only. |
| **P2-4** | Sec 11 | Bimodality heuristic (Hartigan's dip is out of scope). | **Chosen:** peak count on a 3-bin-smoothed 20-bin histogram; a peak must reach 10% of the tallest bar and be separated by a valley below 80% of the smaller peak. Only for columns with ≥ 10 distinct values and ≥ 30 values. Always labelled "heuristic". |
| **P2-5** | Sec 10.6 | Measure for "target vs. each feature". | **Chosen:** categorical target → eta² for numeric features, bias-corrected Cramér's V for categorical features; numeric target → Spearman rho for numeric features, eta² for categorical features. All descriptive (no p-values). |
| **P2-6** | Sec 10, Risk 9 | Figure caps beyond the plan's 30-column caps. | **Chosen:** at most 12 per-column "detail" figures (skewed/outlier-heavy columns, most skewed first); Cramér's V matrix capped at 30 columns with 2–50 levels. Typical dataset: 20–25 PNGs. |
| **P2-7** | Sec 15 | How to build `report.html` without the optional `markdown` package. | **Chosen:** `report.md` is rendered with Jinja2 and converted to HTML by a small built-in converter (`ads/report_render.py`) that supports exactly the constructs the report uses. One source → the two files never disagree. |
| **P2-8** | Sec 11 | How to keep every insight number traceable. | **Chosen:** each insight stores its numbers in `evidence` already rounded to the precision printed in the statement (2 decimals), and the statement is built from those stored values. No timestamps in `insights.json`, `eda_summary.json` or `report.*` (determinism). |
| **P2-9** | Sec 10 | What happens if one EDA chart fails on an unusual CSV. | **Chosen:** each EDA section runs independently; a failure is recorded in `eda_summary.json → eda_errors` and shown as a note in the report, and the rest of the pipeline continues. Tests assert `eda_errors` is empty for the bundled datasets. |
| **P2-10** | Sec 5.4 | Ordinal integer scales in Student Performance (`Medu`, `studytime`, `famrel`, `Dalc`, …). | **Chosen:** labelled `numeric` in `truth_types` and not forced to categorical, the same convention as `ca` in the heart-disease config. **Needs human confirmation** when the truth types are reviewed (plan Section 21). |
| **P2-11** | Sec 5.4 | Bank Marketing `pdays = 999` ("never contacted"). | **Chosen:** left unchanged (not turned into NaN, which would empty 96% of the column); documented in `docs/datasets.md` and expected to show up as extreme skew and a strong `poutcome` link in EDA. |
