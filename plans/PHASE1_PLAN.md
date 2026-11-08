# PHASE 1 — Data Ingestion, Profiling, Cleaning, EDA, and LLM Comparison

> **Audience:** an AI coding agent (Claude Code / Antigravity) implementing this from scratch, plus the human reviewing it.
> **How to use this file:** read it fully first. Implement in the order given in Section 17. Do not skip the acceptance criteria in Section 18. Where a decision is marked **DECISION**, follow it as written. Where marked **OPEN**, pick the stated default and note it in `docs/decisions.md`.

---

## 0. Project context (for the implementer)

The overall project is an **agentic data scientist** built with LangGraph. A user uploads any CSV. The system profiles it, proposes hypotheses, tests them with a fixed library of statistical tools, validates findings (Benjamini-Hochberg correction, effect-size and assumption checks), and reports validated findings with charts and plain-language explanations. A chat mode answers questions. **Every number comes from a tested tool, never from the LLM.**

The full project has five phases:

1. **Phase 1 (THIS FILE):** CSV ingestion + profiling, automated cleaning, EDA, visualizations, documented insights, cleaned dataset generation, and a comparison against an LLM given the same data.
2. Phase 2: hypothesis generation.
3. Phase 3: statistical testing + validation.
4. Phase 4: LangGraph agent + chat.
5. Phase 5: full evaluation (synthetic planted-truth benchmark, ablations, Kaggle runs, demo).

Phase 1 is also the **first deliverable to the course TA**. The TA asked for: data cleaning (missing values, duplicates, outliers, inconsistent formats), complete EDA with clear visualizations, written insights, normalization/scaling if needed, and a cleaned dataset. This plan satisfies all of that **and** builds the reusable front end of the real system.

### Two things Phase 1 must be at the same time

1. **A reusable, automated library** that works on *any* CSV (this becomes the profiling and cleaning node of the Phase 4 LangGraph agent).
2. **A documented analysis of 3-5 real datasets + 1 messy synthetic dataset**, with plots, logs, insights, and an LLM comparison (this is what the TA grades).

---

## 1. Scope

### In scope
- CSV ingestion with robust parsing.
- Column type inference.
- Dataset profiling (structured JSON + human-readable report).
- Automated, conservative, fully logged cleaning.
- Outlier detection (flag by default).
- EDA with plots, per dataset.
- Auto-generated insights plus a human-written insights section.
- Scaling/transformation analysis and a decision note per dataset (analysis and recommendation; transformed copy is optional output).
- Cleaned dataset outputs.
- A messy-data generator with a ground-truth manifest of injected problems.
- An LLM baseline that gets the same datasets.
- A comparison of pipeline vs LLM on profiling accuracy, issue detection, cleaning quality, number correctness, and insights.
- Final report for the TA.
- Unit tests and a reproducible CLI.

### Explicitly OUT of scope (do NOT build these now)
- Hypothesis generation, ranking, or schemas (Phase 2).
- Any hypothesis tests, p-values, confidence intervals, BH correction (Phase 3).
- LangGraph graph, chat, router (Phase 4).
- The planted-effects synthetic benchmark, recall/FDR metrics (Phase 5).
- Model training of any kind.

**Rule:** EDA may compute *descriptive* statistics (means, correlations coefficients, skewness, counts). It must **not** report p-values or "significant" language. Correlation coefficients in EDA are descriptive only and must be labelled as such. This keeps Phase 1 from bleeding into Phase 3.

---

## 2. Design principles

1. **Deterministic first.** No LLM calls anywhere inside the pipeline (profiling, cleaning, EDA, insights). The LLM only appears in the *baseline comparison* module.
2. **Conservative cleaning.** Fix obvious problems. Never silently change data in ways that could create or hide statistical patterns. Aggressive actions (outlier removal, heavy imputation) are opt-in via config.
3. **Everything is logged.** Every change to the data produces a structured log entry: what, where, how many rows/cells, why, before/after example.
4. **Never mutate the raw file.** Raw data is read-only. The pipeline always works on a copy.
5. **Reproducible.** Fixed seeds, pinned dependencies, a config file, a single CLI command per dataset.
6. **Generic, not dataset-specific.** No hard-coded column names inside library code. Dataset-specific knowledge lives only in per-dataset config files (`configs/datasets/<name>.yaml`).
7. **Stable handoff contract.** The outputs of Phase 1 (cleaned dataframe + `profile.json` + `column_schema.json` + `cleaning_log.json`) are the input contract for Phase 2. Do not change their structure casually; version it (`schema_version`).
8. **Typed, tested, documented.** Type hints, docstrings, unit tests for every cleaning rule and type-inference rule.

---

## 3. Tech stack and environment

- **Python 3.11+**
- Core: `pandas`, `numpy`, `scipy` (only for skew/kurtosis/descriptive helpers), `pydantic` (v2, for schemas), `pyyaml`
- Plotting: `matplotlib`, `seaborn` (static PNGs, 150 dpi). Optional: `plotly` for HTML versions (not required).
- Reports: `jinja2` (render markdown/HTML reports), optional `markdown`
- Testing: `pytest`, `pytest-cov`, `hypothesis` (optional)
- CLI: `typer` (or `argparse` if you prefer fewer deps)
- LLM baseline: `anthropic` SDK (API key via env var `ANTHROPIC_API_KEY`; never commit keys). Make provider pluggable behind an interface so another LLM can be swapped in.
- Datasets: `kaggle` CLI/API **optional**; manual download is acceptable (see Section 5).
- Tooling: `ruff` (lint), `black` (format), `mypy` (optional), `pre-commit` (optional)
- Provide `requirements.txt` (pinned) and `pyproject.toml`.
- Provide a `Makefile` with targets: `setup`, `test`, `lint`, `run-all`, `run-one DATASET=...`, `compare`, `report`.

---

## 4. Repository layout

Create exactly this structure (add files as needed, but keep the module boundaries):

```
agentic-ds/
├── README.md
├── pyproject.toml
├── requirements.txt
├── Makefile
├── .gitignore                      # ignore data/raw/*, outputs/*, .env, __pycache__
├── .env.example                    # ANTHROPIC_API_KEY=
├── configs/
│   ├── default.yaml                # global thresholds (Section 8, 9)
│   └── datasets/
│       ├── insurance.yaml
│       ├── telco_churn.yaml
│       ├── heart_disease.yaml
│       ├── student_performance.yaml
│       ├── bank_marketing.yaml
│       └── messy_synthetic.yaml
├── data/
│   ├── raw/                        # untouched originals (gitignored); README.md lists sources
│   │   └── README.md
│   ├── interim/                    # parsed-but-uncleaned snapshots (optional)
│   ├── cleaned/                    # pipeline outputs: <name>_cleaned.csv etc.
│   └── synthetic/                  # messy generator outputs + ground-truth manifests
├── src/ads/                        # "agentic data scientist" package
│   ├── __init__.py
│   ├── config.py                   # load/merge YAML configs, pydantic Config models
│   ├── schemas.py                  # pydantic models: ColumnProfile, DataProfile, CleaningLogEntry, etc.
│   ├── ingestion.py                # robust CSV loading
│   ├── type_inference.py           # semantic column types
│   ├── profiling.py                # profile_dataset(df) -> DataProfile
│   ├── cleaning/
│   │   ├── __init__.py             # clean_dataset(df, profile, config) -> CleaningResult
│   │   ├── steps.py                # one function per cleaning step
│   │   ├── missing.py              # missing-token normalization + handling policies
│   │   ├── outliers.py             # detection (IQR, modified z) + actions
│   │   ├── categories.py           # label standardization / near-duplicate merging
│   │   └── log.py                  # CleaningLog collector
│   ├── eda/
│   │   ├── __init__.py             # run_eda(df, profile, out_dir) -> EDAResult
│   │   ├── univariate.py
│   │   ├── bivariate.py
│   │   ├── missingness.py
│   │   └── plots.py                # plotting helpers, consistent style
│   ├── scaling.py                  # skew analysis, transform recommendations, optional transformed copy
│   ├── insights.py                 # rule-based insight generator -> insights.md + insights.json
│   ├── reporting.py                # jinja2 rendering of per-dataset report
│   ├── pipeline.py                 # run_phase1(input_csv, dataset_name, out_dir) orchestrator
│   ├── synthetic/
│   │   ├── __init__.py
│   │   ├── base_generator.py       # builds a clean base dataset with known structure
│   │   └── messy_injector.py       # injects known problems + writes manifest
│   ├── baselines/
│   │   ├── __init__.py
│   │   ├── llm_client.py           # provider-agnostic interface + Anthropic implementation
│   │   ├── prompts/                # saved, versioned prompt files (never inline)
│   │   │   ├── v1_system.txt
│   │   │   └── v1_task_summary_mode.txt
│   │   │   └── v1_task_code_mode.txt
│   │   ├── llm_summary_mode.py     # Mode A: sees summary + sample, no code execution
│   │   ├── llm_code_mode.py        # Mode B: writes pandas code, executed in sandbox subprocess
│   │   └── sandbox.py              # safe subprocess execution (timeout, no network, tmp dir)
│   └── comparison/
│       ├── __init__.py
│       ├── ground_truth.py         # compute exact truth from a dataframe (types, missing, dups, ...)
│       ├── scoring.py              # all metrics (Section 13)
│       ├── claim_extraction.py     # extract numeric claims from LLM output for verification
│       └── compare.py              # run scoring over datasets, produce tables/plots
├── scripts/
│   ├── download_datasets.md        # human instructions + optional kaggle commands
│   ├── run_all.py                  # run pipeline on all datasets
│   ├── make_messy_dataset.py       # generate messy synthetic + manifest
│   ├── run_llm_baseline.py         # run Mode A/B on all datasets, N repeats
│   └── build_report.py             # assemble final TA report
├── notebooks/
│   ├── 00_overview.ipynb           # thin: calls library, shows outputs (no logic here)
│   └── <dataset>_phase1.ipynb      # one per dataset: loads outputs, narrates insights
├── outputs/                        # gitignored except final_report/
│   ├── <dataset>/
│   │   ├── profile.json
│   │   ├── column_schema.json
│   │   ├── cleaning_log.json
│   │   ├── cleaning_log.md
│   │   ├── scaling_report.md
│   │   ├── insights.json
│   │   ├── insights.md             # auto section + MANUAL section (see Section 11)
│   │   ├── report.md
│   │   ├── report.html
│   │   └── figures/*.png
│   ├── llm_baseline/<dataset>/<mode>/run_<k>.json
│   └── comparison/
│       ├── metrics.csv
│       ├── tables/*.md
│       └── figures/*.png
├── final_report/
│   └── PHASE1_REPORT.md            # the TA deliverable (Section 15)
├── docs/
│   ├── decisions.md                # every DECISION/OPEN resolved + why
│   ├── datasets.md                 # dataset cards
│   └── contract.md                 # Phase 1 -> Phase 2 handoff contract
└── tests/
    ├── test_ingestion.py
    ├── test_type_inference.py
    ├── test_profiling.py
    ├── test_cleaning_*.py
    ├── test_outliers.py
    ├── test_scaling.py
    ├── test_messy_injector.py
    ├── test_scoring.py
    └── test_pipeline_end_to_end.py
```

---

## 5. Datasets

### 5.1 Real datasets (use 5; minimum 3)

| # | Name | Why chosen | Known relationships for sanity checks | Target-like column |
|---|---|---|---|---|
| 1 | **Medical Cost / Insurance** (`insurance.csv`, ~1,338 rows, 7 cols) | Small, clean-ish, mixed types, strong known effects | smoker → charges (very strong), age → charges, BMI → charges (esp. with smoker) | `charges` |
| 2 | **Telco Customer Churn** (~7,043 rows, ~21 cols) | Realistic mess: `TotalCharges` is stored as string with blanks, many categoricals, class imbalance | contract type ↔ churn, tenure ↔ churn | `Churn` |
| 3 | **Heart Disease (UCI/Kaggle)** (~300-1,000 rows, ~14 cols) | Encoded categoricals as ints, some missing/placeholder values, binary target | chest pain type, max heart rate ↔ disease | `target`/`HeartDisease` |
| 4 | **Student Performance (UCI math/portuguese)** (~395/649 rows, 33 cols) | Many categorical/ordinal columns, small n, wide | prior grades (G1,G2) ↔ G3 | `G3` |
| 5 | **Bank Marketing** (or Adult Census Income) (~10k-45k rows) | Larger n, strong class imbalance, "unknown" as missing placeholder | `duration`, `poutcome` ↔ outcome | `y` / `income` |

**DECISION:** Do **not** use Titanic as a main dataset (LLMs have memorized it, which contaminates the LLM comparison).

**DECISION:** Record the exact download source, version/date, license note, and SHA-256 of each raw file in `docs/datasets.md` and `data/raw/README.md`. If Kaggle API access is unavailable, the human downloads manually into `data/raw/<name>/`; write `scripts/download_datasets.md` with exact steps and expected filenames. The pipeline must fail with a clear message if a file is missing (not a stack trace).

### 5.2 Messy synthetic dataset (1, mandatory)

Generated by `src/ads/synthetic/` (Section 12). It has **known injected problems** with a ground-truth manifest. It exists because real datasets don't come with a list of their own problems, and the comparison with the LLM needs an objective answer key.

### 5.3 Dataset cards (`docs/datasets.md`)

For each dataset write: source URL, rows, columns, one-line description per column (from the source's documentation), target/interesting variables, known quirks noticed during loading, license, SHA-256.

### 5.4 Per-dataset config (`configs/datasets/<name>.yaml`)

Optional overrides only. Example fields:

```yaml
name: telco_churn
file: data/raw/telco_churn/WA_Fn-UseC_-Telco-Customer-Churn.csv
target: Churn                      # optional; used only for imbalance + EDA grouping
id_columns: [customerID]           # optional hints; inference should also find these
forced_types:                      # optional; use sparingly, document why
  SeniorCitizen: categorical       # stored as 0/1 but semantically categorical
missing_tokens_extra: []           # dataset-specific placeholders beyond the global list
validity_rules:                    # optional domain rules -> out-of-range becomes NaN (logged)
  tenure: {min: 0}
  MonthlyCharges: {min: 0}
```

Rule: library code never reads dataset names. Only `config.py` merges `default.yaml` + dataset YAML.

---

## 6. Core data contracts (`schemas.py`, pydantic v2)

Define and version these. Serialize to JSON for outputs.

### 6.1 Semantic column types (enum `SemanticType`)

- `numeric_continuous`
- `numeric_discrete` (integers with limited distinct values, counts-like)
- `binary` (exactly 2 distinct non-null values, any encoding: 0/1, Yes/No, True/False, M/F)
- `categorical_nominal`
- `categorical_ordinal` (only if config marks it or values match known ordinal patterns, e.g. low/medium/high; otherwise treat as nominal; **DECISION:** do not guess ordinality aggressively)
- `datetime`
- `id_like`
- `free_text`
- `constant` (≤1 distinct non-null value)
- `unknown` (fallback; flagged for human review)

### 6.2 `ColumnProfile`

```
name: str
raw_dtype: str                    # pandas dtype as loaded
semantic_type: SemanticType
semantic_type_reason: str         # human-readable why (e.g. "object, 2 unique values")
n_total: int
n_missing: int
pct_missing: float
n_unique: int                     # excluding NaN
pct_unique: float                 # n_unique / n_nonnull
mode: Any | None
top_values: list[{value, count, pct}]   # up to 10, categorical/binary/discrete
# numeric only:
min, max, mean, median, std, q1, q3, iqr, skewness, kurtosis, n_zeros, n_negative
# outlier summary (detection only, numeric only):
n_outliers_iqr_1_5, n_outliers_iqr_3_0, n_outliers_modz
# string-quality flags:
has_leading_trailing_ws: bool
has_mixed_case_variants: bool
n_missing_token_cells: int        # cells equal to placeholder tokens like "?", "N/A"
looks_numeric_but_object: bool    # e.g. "1,234", "$5", " 12 "
mixed_types: bool                 # column mixes numbers and non-numeric strings
# datetime only:
min_date, max_date, n_unparseable
```

### 6.3 `DataProfile`

```
schema_version: "1.0"
dataset_name, source_file, sha256
n_rows, n_cols, memory_mb
n_duplicate_rows, pct_duplicate_rows
n_fully_empty_rows, n_fully_empty_cols
columns: list[ColumnProfile]
missing_matrix_summary: {rows_with_any_missing, rows_with_gt_half_missing, ...}
correlation_candidates_note: (none; Phase 2)
warnings: list[str]               # e.g. "column X looks like an ID", "column Y is constant"
generated_at, library_versions
```

### 6.4 `CleaningLogEntry`

```
step: str                         # e.g. "strip_whitespace", "normalize_missing_tokens"
column: str | None                # None for row/table-level steps
action: str                       # e.g. "stripped", "converted_to_NaN", "dropped_rows", "cast_dtype"
n_cells_affected: int
n_rows_affected: int
rows_before: int
rows_after: int
reason: str
before_examples: list[str]        # max 5, as strings
after_examples: list[str]         # max 5
parameters: dict                  # thresholds used
severity: "info" | "warning"      # warning = changed data meaningfully or needs human eyes
```

### 6.5 `CleaningResult`

```
df_clean_conservative: pd.DataFrame      # PRIMARY output (see 9.9)
df_clean_imputed: pd.DataFrame           # SECONDARY output (TA-style, missing handled)
log: list[CleaningLogEntry]
dropped_columns: list[{name, reason}]
dropped_row_count: int
outlier_report: dict[column -> {indices_flagged, bounds, method}]
summary: dict                            # counts per step
```

### 6.6 `column_schema.json` (the Phase 2 handoff)

A slim file: `{column_name: {semantic_type, role, n_unique, pct_missing}}` where `role ∈ {feature, target_candidate, id, excluded}`. Excluded = constant, id_like, free_text (kept in data but marked). **This is what Phase 2 reads to decide which column pairs are testable.**

---

## 7. Module specs: ingestion and type inference

### 7.1 `ingestion.py`: `load_csv(path, config) -> IngestionResult`

Requirements:
- Detect **encoding** (try `utf-8`, `utf-8-sig`, `latin-1`, `cp1252` in that order; record which worked; log a warning if fallback used).
- Detect **delimiter** with `csv.Sniffer` (fallback `,`); support `;`, `\t`, `|`.
- Handle quoted fields, embedded newlines, BOM, trailing delimiters, ragged rows (`on_bad_lines="warn"` then report count of skipped lines; do not crash).
- Read **everything as `str` first** (`dtype=str, keep_default_na=False`), so no silent coercion happens during load. Type conversion is a **logged cleaning step**, not a loader side effect. Store `df_raw_str`.
- Also produce `df_naive` = pandas default parse, used only to record `raw_dtype` for the profile and to quantify "what pandas would have guessed".
- Guardrails: reject files > configurable size (default 200 MB) with a clear error; sample-based profiling for > 1M rows is **OUT of scope** now (note as future work).
- Strip BOM and whitespace from **column names**; if duplicate column names exist, suffix `.1`, `.2` and log; if column names are empty, name `unnamed_<i>` and log.
- Compute and store SHA-256 of the file.
- Return: `df_raw_str`, `df_naive`, metadata (encoding, delimiter, n_bad_lines, sha256, n_rows, n_cols).

### 7.2 `type_inference.py`: `infer_column_types(df_raw_str, config) -> dict[col, (SemanticType, reason)]`

Work from the raw string frame. For each column, in this order:

1. Normalize candidate series: strip whitespace; treat configured missing tokens as NaN (for inference only, do not mutate).
2. If non-null count == 0 → `constant` (reason "all missing"; also flag as fully empty column).
3. If n_unique ≤ 1 → `constant`.
4. **Numeric test:** try parsing after removing thousands separators `,`, currency symbols (`$ € £`), `%`, and surrounding whitespace, handling parentheses negatives `(12)` → `-12`. If ≥ `numeric_parse_threshold` (default 0.95) of non-null values parse → numeric candidate. The 5% that fail are `mixed_types` evidence and are logged as "unparseable numeric tokens".
   - If numeric: if all parsed values are integers **and** n_unique ≤ `discrete_max_unique` (default 20) **and** n_unique / n_nonnull < `discrete_max_ratio` (default 0.05) → `numeric_discrete`, else `numeric_continuous`.
   - If numeric and n_unique == 2 → `binary` (reason "numeric with two values").
   - If numeric and integer, `n_unique == n_nonnull` (all unique) and monotonic or named like id (`id`, `_id`, `uuid`, `index`) → `id_like`.
5. **Datetime test:** try `pd.to_datetime` with multiple explicit formats first (`%Y-%m-%d`, `%d/%m/%Y`, `%m/%d/%Y`, `%Y-%m-%d %H:%M:%S`, ISO8601), then a flexible parse fallback. If ≥ 0.9 of non-null parse AND values are not purely small integers → `datetime`. Record ambiguity: if both `%d/%m/%Y` and `%m/%d/%Y` parse every value, log a warning "ambiguous day/month order, defaulted to <X>" (default month-first only if config says so; otherwise day-first = false → keep ISO preferred).
6. **Binary test (strings):** exactly 2 distinct values after normalization (case/whitespace-insensitive) → `binary`. Recognize boolean-like pairs: yes/no, y/n, true/false, t/f, 0/1, male/female, m/f (reason records the pair).
7. **ID-like test (strings):** `n_unique / n_nonnull ≥ id_unique_ratio` (default 0.98) AND n_nonnull > 50 AND (average length consistent OR name matches id patterns) → `id_like`.
8. **Free text test:** mean string length > `text_mean_len` (default 40) OR mean word count > 6 AND n_unique / n_nonnull > 0.5 → `free_text`.
9. **Categorical:** n_unique ≤ `max_categorical_unique` (default 50, or ≤ 5% of rows, whichever is greater) → `categorical_nominal`. Higher → if unique ratio high → `id_like` or `free_text`, else `categorical_nominal` with warning "high cardinality".
10. Else → `unknown`.

Rules:
- Always return a **reason string** for every decision (it appears in the report and helps debugging).
- `forced_types` in dataset config override inference (log that an override was applied).
- Unit-test each branch with tiny constructed series, including adversarial ones: numeric IDs, ZIP codes (should be categorical or id_like, not continuous: **DECISION:** if column name matches `zip|postal|phone|code` and values are fixed-length digit strings, treat as categorical/id_like), years as ints, binary 0/1 stored as float, "1,234.50" strings, "N/A"-polluted numeric columns, columns with all-unique floats.

---

## 8. Module spec: profiling (`profiling.py`)

`profile_dataset(df_raw_str, df_naive, ingestion_meta, config) -> DataProfile`

- Uses the inferred types to compute every field in `ColumnProfile` (Section 6.2) **on the type-converted view of the column**, without mutating the input.
- **Duplicates:** exact duplicate **rows** counted on the stripped/normalized string frame (so " Male" and "Male" rows are recognized as duplicates only *after* normalization; also report `n_duplicate_rows_raw` vs `n_duplicate_rows_after_normalization`, because this difference is itself an inconsistent-format signal).
- **Missing:** count NaN, empty string, and **placeholder tokens**. Global token list (config `missing_tokens`): `""`, `" "`, `NA`, `N/A`, `n/a`, `NaN`, `nan`, `NULL`, `null`, `None`, `none`, `?`, `-`, `--`, `unknown`, `Unknown`, `missing`, `#N/A`. **DECISION:** the token `unknown` is treated as missing **only if** configured per dataset or if it constitutes < 30% of that column and the column is not otherwise "unknown"-semantic. Default: flag it as a *candidate* missing token in warnings, treat as missing only when the dataset config lists it (Bank Marketing config will list it).
- **Outlier summary** for numeric columns: counts using IQR×1.5, IQR×3.0, and modified z-score (|Mz| > 3.5, using median and MAD; guard MAD = 0 by falling back to mean absolute deviation or skipping). **Detection only.**
- **String quality flags:** leading/trailing whitespace count, internal multiple spaces, case variants (group values by `casefold().strip()`; if a group has > 1 raw spellings, flag with the spellings), unicode oddities (non-breaking spaces `\u00a0`, zero-width chars).
- **Near-duplicate labels:** for categorical columns with ≤ 50 uniques, find label pairs with normalized edit-distance similarity ≥ `label_similarity_threshold` (default 0.9, use `difflib.SequenceMatcher`; skip pairs of short strings < 4 chars unless case-only differences). **Report only; merge only case/whitespace variants automatically (Section 9.4).**
- **Warnings list:** constant columns, ID-like columns, high missingness (> 40%), high cardinality, columns with mixed types, extreme skew (|skew| > 2), highly imbalanced binary/categorical (minority < 10%), fully empty rows/cols, suspected leakage-like names (`target`, `label`, `outcome`: info only).
- Write `profile.json` and a rendered table in `report.md`.
- Performance target: < 5 s for 50k rows × 40 cols.

---

## 9. Module spec: cleaning (`cleaning/`)

`clean_dataset(df_raw_str, profile, config) -> CleaningResult`

**Steps run in this fixed order.** Each step is a pure function `(df, ctx) -> df` that appends to a `CleaningLog`. Each is individually toggleable in config. Each is unit-tested.

### 9.1 Step 1: Column-name normalization
- Strip whitespace, collapse internal runs of whitespace. **DECISION:** keep original names (case/spaces preserved) in the cleaned output so Phase 2 and the user see familiar names; store a `name_map` (original → cleaned) in the log for any change. Do not snake_case by default (config flag `snake_case_columns: false`).

### 9.2 Step 2: Whitespace and unicode cleanup (string columns)
- Strip leading/trailing whitespace; collapse internal multiple spaces to one; replace non-breaking spaces and remove zero-width chars. Log per column: n cells changed, 5 examples.

### 9.3 Step 3: Missing-token normalization
- Replace configured placeholder tokens with NaN (case-insensitive, after strip). Log per column and per token counts. Severity `warning` if a token replaced > 10% of a column's cells.

### 9.4 Step 4: Category label standardization (strings, categorical/binary columns only)
- Merge **case-only and whitespace-only variants** into the **most frequent spelling** (e.g., "male", "Male", "MALE" → "Male"). Log the mapping.
- Do **not** auto-merge fuzzy near-duplicates ("Gender"/"Gendr"); instead emit a `warning` log entry listing candidate pairs for human review (with counts), unless config `auto_merge_fuzzy: true` (default false). **DECISION.**
- Binary normalization: leave the original labels in the cleaned output (do not recode Yes/No → 1/0). Recoding is a Phase 2/3 convenience, not a cleaning action. Record the mapping in the schema (`binary_positive_label` guess is OPTIONAL and must not be relied upon).

### 9.5 Step 5: Type conversion
- Apply inferred types: numeric parsing (strip `,`, currency, `%` (divide by 100? **DECISION:** do **not** divide; keep the number and note the % in the log), parentheses negatives), datetime parsing with the chosen format, boolean-likes stay as their label strings (see 9.4) but numeric 0/1 binaries stay numeric.
- Cells that fail to parse become NaN **and are counted as `coerced_to_NaN`** with examples (`warning`). Telco's blank `TotalCharges` must show up here or in Step 3.
- Categorical columns become pandas `category` dtype only in the final output; keep object dtype during processing.
- `numeric_discrete` → nullable `Int64` where all non-null values are integral; `numeric_continuous` → `float64`.

### 9.6 Step 6: Validity rules (optional, from dataset config)
- For each rule `{min, max, allowed_values}`, set violating cells to NaN. Log counts and examples. Severity `warning`. (E.g., negative age, BMI = 0.) If no rules are configured, additionally run **generic sanity checks** that only *flag* (not change): negative values in columns whose names suggest counts/ages/prices (`age`, `count`, `price`, `charges`, `amount`, `tenure`), percentages > 100 in columns with `%`/`pct`/`percent` in the name, future dates (> today) in datetime columns.

### 9.7 Step 7: Duplicates
- Drop **exact duplicate rows** (after Steps 2-5, so formatting-variant duplicates are caught). Keep first occurrence. Log count and the row indices (first 20). **DECISION:** if the dataset has no ID column, a duplicate row may be a legitimately repeated observation (e.g., survey with few columns). If `n_cols ≤ 4` or the duplicate rate > 20%, do not drop; log a `warning` "possible legitimate duplicates, kept" (config override `drop_duplicates: always|never|auto`, default `auto`).
- Report near-duplicate rows (identical on all but ID/timestamp columns) as info only. Optional; skip if time is short.

### 9.8 Step 8: Structural drops
- Drop **fully empty rows** and **fully empty columns** (log).
- Mark (do **not** drop) `constant`, `id_like`, `free_text` columns as `excluded` in the schema. **DECISION:** keep them in `df_clean_conservative` so no information is lost, but exclude them from EDA correlation plots and from Phase 2 hypothesis enumeration via the schema `role`.
- Drop columns with `pct_missing > column_drop_threshold` (default 0.80) in the **imputed** output only; in the conservative output keep the column but mark `excluded` with reason "mostly missing". **DECISION.**
- Drop rows with `pct_missing_in_row > row_drop_threshold` (default 0.50): **both outputs**, logged with counts. Rationale: rows that are mostly empty carry no usable information.

### 9.9 Step 9: Missing value handling, producing TWO outputs

**Output A: `df_clean_conservative` (PRIMARY, used by the real pipeline and Phase 2+)**
- No imputation. Remaining NaNs stay NaN. Rationale: downstream tests use pairwise/listwise deletion per test; imputing would fabricate data and bias effect sizes. Add a per-column `missing_mechanism_note`: "MCAR/MAR/MNAR unknown; not tested".

**Output B: `df_clean_imputed` (SECONDARY, TA-facing, and for any later modeling)**
- Numeric columns: median imputation (if |skew| > 1 use median; otherwise mean is acceptable but **DECISION:** always median for simplicity and robustness).
- Categorical/binary columns: mode imputation, **or** a new level `"Missing"` if `pct_missing ≥ 5%` (config `categorical_missing_as_level_threshold`). Log which.
- For any column with `pct_missing ≥ missing_indicator_threshold` (default 0.05), add a boolean indicator column `<col>__was_missing` so the information of missingness is preserved.
- Datetime: leave NaT (no imputation), log.
- Never impute the `target` column; instead drop rows with missing target in this output (log) or leave per config `target_missing: drop|keep`, default `drop`.
- Log every column: strategy, n imputed, fill value.

### 9.10 Step 10: Outliers (detection + configurable action)
- Methods per numeric (continuous/discrete) column: IQR fences (k = 1.5 and 3.0) and modified z-score. A value is "flagged" if outside IQR×1.5 fences **or** |Mz| > 3.5, and "extreme" if outside IQR×3.0.
- Actions (config `outlier_action`): `flag` (DEFAULT: record in `outlier_report`, add no columns, change no values), `cap` (winsorize to the 1.5×IQR fences, **imputed output only**), `remove` (drop rows; **imputed output only**; log count; refuse if it would remove > 5% of rows unless forced).
- **DECISION:** Default is `flag` for both outputs. In the report explain: for rank-based tests (Phase 3) outliers do not distort results; robust tests are preferred to deletion; true extreme values (e.g., very high medical charges) are real signal. Provide an `outlier_report` per column: n flagged, n extreme, fence values, min/max flagged value, and 5 sample row indices.
- Ensure the outlier step runs on the type-converted data, after validity rules, before imputation (so imputed values do not influence fences).

### 9.11 Step 11: Final validation of cleaned output
- Assertions: no duplicated column names; dtype per column matches schema; no remaining placeholder tokens in string columns; no leading/trailing whitespace; row count change equals the sum of logged row removals; `df_clean_conservative` and `df_clean_imputed` have the same row count except for target-missing/row-drop rules (reconcile and log).
- On assertion failure raise a `CleaningInvariantError` with details (do not silently continue). This guards against a cleaner that damages data.

### 9.12 Cleaning log outputs
- `cleaning_log.json` (list of `CleaningLogEntry`) and `cleaning_log.md`: a readable table grouped by step with before/after examples, plus a one-paragraph summary (e.g., "12 steps ran; 3 columns type-converted; 1,200 cells normalized; 84 duplicate rows removed; 0 rows dropped for missingness").
- **Idempotence requirement:** running `clean_dataset` on its own cleaned output must produce an empty (or info-only) change log. Test this.

---

## 10. Module spec: EDA (`eda/`)

`run_eda(df_clean_conservative, profile, schema, config, out_dir) -> EDAResult`

All figures: PNG, 150 dpi, consistent style (seaborn `whitegrid`, one palette, readable fonts, titles that state the takeaway not just the variable, axis labels with units if known). Save to `outputs/<dataset>/figures/` with deterministic filenames. Never display interactively (use `Agg` backend). Cap the number of plots: if > 30 numeric or > 30 categorical columns, plot the top-N by variance/entropy and say so in the report.

### 10.1 Dataset overview
- `overview_table.png`/markdown: rows, cols, types count, memory, duplicates removed, missing cells %, per-type column counts.
- `dtype_breakdown.png`: bar of semantic type counts.

### 10.2 Missingness (`missingness.py`)
- `missing_bar.png`: % missing per column (only columns with missing > 0; if none, say so in the report instead of plotting an empty chart).
- `missing_heatmap.png`: row × column missing matrix (sample up to 500 rows if larger; sort rows by missing count).
- `missing_correlation.png` (nullity correlation between columns that have missing values; skip if < 2 such columns). Descriptive only.
- Note whether missingness appears concentrated in a few rows or spread out.

### 10.3 Univariate numeric
- Per numeric column: histogram + KDE, with vertical lines for mean and median, annotated skewness; boxplot strip below. Combine into one multi-panel figure per ~6 columns (`numeric_distributions_<n>.png`) to keep file counts manageable, plus a per-column file for columns flagged skewed or with many outliers.
- `outlier_summary.png`: bar of flagged-outlier % per numeric column.
- Summary stats table (`numeric_summary.md`): count, mean, std, min, quartiles, max, skew, kurtosis.
- For columns with extreme right skew (skew > 1 and min ≥ 0), add a **log1p-scale** panel next to the raw one.

### 10.4 Univariate categorical/binary
- Per categorical column: horizontal bar of value counts (top 15 + "Other" lump), with % labels; mark the minority fraction. Multi-panel files, same batching as numeric.
- `cardinality_bar.png`: n_unique per categorical column (log scale if range is wide).
- `categorical_summary.md`: n_unique, mode, mode %, entropy (normalized), rarest level %.

### 10.5 Target / class balance (if `target` configured)
- Count + % bar of target classes (or histogram if numeric target). Compute imbalance ratio (majority/minority) and state "balanced / mildly imbalanced / highly imbalanced" using thresholds (minority < 10% → highly).
- Optional: target distribution by key categorical columns (stacked proportion bars) for the top 6 categoricals by association strength **(descriptive Cramér's V only; no p-values)**.

### 10.6 Bivariate (descriptive only)
- **Numeric-numeric:** correlation heatmap (Pearson and Spearman, two panels, annotated, masked upper triangle, numeric columns only, excluding `excluded` roles). Top-10 strongest absolute correlation pairs table. Scatter plots (with LOWESS or linear fit line, alpha-blended, subsample 5,000 points) for the top 6 pairs. Add a note: "descriptive coefficients, not significance tests".
- **Numeric-categorical:** box/violin plots of the target (or of the most informative numeric columns) grouped by categorical columns with ≤ 8 levels; rank pairs by descriptive effect size (eta-squared computed via simple sums of squares; **no p-values**) and plot the top 6.
- **Categorical-categorical:** Cramér's V matrix heatmap (bias-corrected), plus contingency-proportion bars for the top 4 pairs. **No chi-square p-values.**
- If a `target` exists, produce a "target vs. each feature" summary (`target_relationships.png` + table), ranked by descriptive association strength.
- Collinearity note: list numeric pairs with |r| > 0.9.

### 10.7 Datetime columns (if any)
- Counts over time (resampled monthly/weekly depending on range), plus min/max date and gaps. Skip gracefully if none.

### 10.8 Dataset-specific manual EDA
- Beyond the automated EDA, the human adds a small section in each dataset notebook for anything dataset-specific that automation cannot see (e.g., "smoker × BMI interaction on charges in insurance"). These notes go into the **MANUAL** section of `insights.md` (Section 11).

### 10.9 EDA result object
- `EDAResult`: list of generated figure paths with captions, tables (as DataFrames and markdown), and a dictionary of headline numbers used by the insights generator (so every figure/number in insights traces to computed values).

---

## 11. Module spec: insights (`insights.py`)

`generate_insights(profile, cleaning_result, eda_result, config) -> Insights`

Rule-based, deterministic (no LLM). Each insight is a record: `{id, category, severity, statement, evidence: {numbers...}, figure_ref}`. The statement is built from templates filled **only** with computed values, so every number is traceable.

Categories and rule templates (implement all; thresholds in config):

1. **Data quality:** "Column X has Y% missing (n=…)"; "N duplicate rows removed"; "Column X stored as text but numeric (n cells coerced)"; "Placeholder token 'T' used for missing in column X (n cells)"; "Column X is constant / ID-like and excluded from analysis".
2. **Distributions:** skew > 1 → "right-skewed (skew=…), median < mean, log transform advisable"; bimodality hint (Hartigan-style is out of scope; use a simple histogram peak count heuristic and label as heuristic); zero-inflation (> 30% zeros); heavy outlier presence (> 5% flagged).
3. **Class balance:** target imbalance statement with ratio.
4. **Relationships (descriptive):** top correlated numeric pairs with coefficients; strongest numeric↔target; strongest categorical↔target by Cramér's V/eta²; collinear pairs.
5. **Cardinality/structure:** high-cardinality columns; rare levels (< 1% of rows) that will cause sparse contingency cells in later chi-square tests (this is a Phase 3 forward-looking note); small-n warning if n < 200 or if any group n < 20.
6. **Scaling notes:** forwarded from `scaling.py` (Section 11b).
7. **Modeling/testing implications:** e.g., "Rank-based tests recommended for X (skewed, outliers)", "Group sizes unbalanced for Y".

Output:
- `insights.json` (list of records).
- `insights.md` with two parts:
  - `## Automated insights` (generated, grouped by category, most severe first, each with a figure link).
  - `## Manual insights (written by the analyst)`: a template with prompts the human fills in: What surprised you? Which relationships look real vs. likely spurious? Anything suspicious about data collection? Known domain relationships present or absent? Which findings should the Phase 5 evaluation recover for this dataset? **This section is mandatory for the TA deliverable and doubles as the reference-findings list for later phases.** The pipeline must not overwrite the manual section on re-run (preserve content between `<!-- MANUAL:START -->` and `<!-- MANUAL:END -->` markers).

### 11b. Scaling and transformation (`scaling.py`)

`analyze_scaling(df_clean_conservative, schema, config) -> ScalingReport`

- For each numeric column: skewness, kurtosis, range, min ≥ 0 flag, recommended transform from a fixed rule table:
  - skew > 1, min ≥ 0 → `log1p`;
  - skew > 1, min < 0 → `yeo-johnson` (recommend only; implement via `sklearn.preprocessing.PowerTransformer` **or** a manual implementation to avoid the dependency; **OPEN:** default to scikit-learn as an optional dependency);
  - otherwise → `none`.
- Also report scale disparity across numeric columns (ratio of max std to min std) and recommend z-score standardization **only** for scale-sensitive downstream methods (regression with regularization, distance-based, PCA). 
- Output `scaling_report.md` per dataset: a table (column, skew, recommended transform, reason), plus an explicit decision paragraph. Standard text to adapt per dataset:
  > "Primary cleaned output is **not** scaled. The Phase 3 test library is rank-based or scale-invariant (Welch/Mann-Whitney, Spearman, Kruskal, chi-square), so scaling would not change results. Log transforms are recommended for columns [..] only for plotting and for parametric/regression use. A scaled copy is provided for TA review and for any future modeling."
- Optional outputs: `data/cleaned/<name>_scaled.csv` containing the cleaned-imputed frame with `log1p` applied to recommended columns (new columns suffixed `__log1p`, originals kept) and z-score standardization of numeric columns (suffixed `__z`). **DECISION:** produce this file for every dataset so the TA sees normalization/scaling "done"; clearly label it as a convenience copy and never feed it into the testing pipeline.
- The transformations must be **fit on the cleaned data and stored** (means/stds/lambdas in `scaling_params.json`) so they are reversible and reproducible.

---

## 12. Messy synthetic dataset generator (`synthetic/`)

Purpose: give an objective answer key for "which data-quality problems exist", so the comparison with the LLM is measurable.

### 12.1 `base_generator.py`: `make_clean_base(n_rows=2000, seed=...) -> pd.DataFrame`

A clean realistic table with known structure (this is also reusable in Phase 5). Columns (all synthetic):
- `customer_id` (unique string ids, e.g., `C000123`)
- `age` (int, 18-80, roughly normal)
- `gender` (Male/Female, ~50/50)
- `income` (right-skewed lognormal, positive)
- `region` (5 levels, unequal frequencies)
- `membership` (Basic/Silver/Gold, related to income)
- `tenure_months` (int, 0-120)
- `monthly_spend` (float, correlated with income)
- `signup_date` (dates over 5 years)
- `satisfaction` (ordinal 1-5 ints)
- `churned` (Yes/No, ~20%, related to tenure and satisfaction)
- `notes` (short random free text for ~30% rows, else empty)
- `constant_flag` (constant "A" column)

Plant a few simple known relationships (documented in code comments and `data/synthetic/base_truth.json`): income↔monthly_spend, tenure↔churn, satisfaction↔churn. These are not the Phase 5 benchmark; they only let the EDA sanity-check that plots show real structure.

### 12.2 `messy_injector.py`: `inject_problems(df_clean, seed, rates) -> (df_messy, manifest)`

Inject the following problem types, each at a configurable rate, each recorded in the manifest. Use a **fixed seed**; all injections must be exactly reproducible.

| Problem id | Injection | Manifest records |
|---|---|---|
| `ws_leading_trailing` | add leading/trailing spaces to ~5% of cells in 3 string columns | column, row indices |
| `ws_internal` | double internal spaces in ~2% of `region` cells | column, rows |
| `case_variants` | "Male"/"male"/"MALE"/"M" style variants in `gender` (case-only: ~10%; "M"/"F" abbreviations: ~3% as **non-auto-merged fuzzy** problem) | column, rows, mapping |
| `missing_tokens` | replace ~8% of `income` with a mix of `""`, `"N/A"`, `"?"`, `"null"`, `"-"`; ~4% of `region` with `"Unknown"` | column, rows, token |
| `real_nan` | true NaN in `age` (~6%) and `satisfaction` (~3%) | column, rows |
| `numeric_as_string` | `income` and `monthly_spend` stored with `$` and thousands commas for ~all cells; 1% as `"1.2e3"` | column |
| `mixed_types` | few cells in `tenure_months` replaced by words ("twelve", "n/a") ~1% | column, rows |
| `date_formats` | `signup_date` mixed `YYYY-MM-DD`, `DD/MM/YYYY`, `Mon DD, YYYY` (~33% each) + ~1% garbage strings | column, rows, format per row |
| `duplicates_exact` | duplicate ~3% of rows exactly | row indices of duplicates |
| `duplicates_formatting` | duplicate ~1% of rows with whitespace/case changes (should be caught after normalization) | row indices |
| `outliers_numeric` | multiply ~0.5% of `income` and `monthly_spend` by 10-50× (extreme but plausible-looking) | column, rows, factor |
| `impossible_values` | negative `age`, `age` > 120, negative `tenure_months` (~0.5% each) | column, rows |
| `constant_column` | `constant_flag` already constant (record it) | column |
| `id_column` | `customer_id` (record it) | column |
| `empty_rows` | add ~10 fully empty rows | row indices |
| `empty_column` | add a fully empty column `unused` | column |
| `column_name_issues` | trailing space in one column name, mixed-case duplicates (`Region` vs `region ` if desired), one `Unnamed: 0`-style index column | names |
| `binary_encoding_mix` | `churned` encoded as `Yes/No/yes/Y/1/0` mix (~5% variants) | column, rows, mapping |

Each manifest entry: `{problem_id, problem_type, column(s), n_cells, n_rows, row_indices_sample, description, expected_pipeline_behavior}` where `expected_pipeline_behavior ∈ {auto_fixed, flagged_only, left_alone}` (e.g., fuzzy "M"/"F" = `flagged_only`; outliers = `flagged_only`; whitespace = `auto_fixed`).

Write `data/synthetic/messy_dataset.csv`, `data/synthetic/messy_manifest.json`, and `data/synthetic/messy_clean_truth.csv` (the original clean base, rows aligned via a hidden `_row_uid` that is **removed before saving the messy CSV** but retained in the truth file's index map `messy_to_truth_index.json` so cleaned outputs can be compared cell-by-cell).

Also generate **2 more messy variants at different seeds/rates** (`messy_light`, `messy_heavy`) if time allows, to show scaling of difficulty.

### 12.3 Tests
- Manifest counts match actual differences between clean and messy frames.
- Re-running with the same seed yields identical files (hash equality).

---

## 13. LLM baseline and comparison

### 13.1 What is compared (Phase 1 tasks only)

Pipeline vs LLM on: **(a) profiling accuracy, (b) data-quality issue detection, (c) cleaning quality, (d) number correctness, (e) insights (qualitative).** Statistical-findings comparison is **Phase 5**, not here.

### 13.2 Datasets for the comparison
All 5 real datasets + the messy synthetic (+ light/heavy variants if built). The messy synthetic is where objective scoring of (b) and (c) is possible; real datasets support (a), (d), (e) with truth computed by `comparison/ground_truth.py`.

### 13.3 Two LLM modes (**DECISION:** implement both; Mode A is mandatory, Mode B strongly recommended)

**Mode A: "summary mode" (no code execution):**
- Input: dataset name, `df.shape`, `df.dtypes`, `df.head(20)` as CSV, `df.sample(20, seed=0)`, and `df.describe(include='all')` text. This is what a user would get by pasting data into a chat.
- Task prompt (saved in `prompts/v1_task_summary_mode.txt`): profile the dataset, list data-quality issues, state the cleaning steps you would take, and report key insights.
- Output required: **strict JSON** following a schema (below). Use JSON mode / schema-constrained output where the SDK supports it; otherwise parse robustly and retry once on parse failure.

**Mode B: "code mode" (strong baseline):**
- The LLM is given the file path and may write Python/pandas code, executed by `sandbox.py`. Loop up to `max_turns` (default 8): LLM emits code → sandbox runs (timeout 60 s, working dir temp, no network, restricted imports allow-list: pandas, numpy, scipy, matplotlib, json, re) → stdout/stderr returned to the LLM. Final turn: LLM must (1) save a cleaned CSV to a designated path, (2) emit the same strict JSON report as Mode A.
- This gives the LLM **real computation** so the comparison is fair: the pipeline's advantage then lies in systematic, logged, deterministic behavior, not merely "LLMs can't compute".
- Sandbox security: run in a subprocess with resource limits (`resource.setrlimit` CPU/memory), cwd in tmp, env scrubbed (no API keys), reject code containing `os.system`, `subprocess`, `socket`, `requests`, `open(` writes outside the tmp dir. Log all executed code to the run JSON for auditing.

### 13.4 LLM output schema (both modes)

```json
{
  "column_types": {"col": "numeric|categorical|binary|datetime|id|text|constant"},
  "missing_counts": {"col": int},
  "n_duplicate_rows": int,
  "issues": [
    {"issue_type": "whitespace|case_variant|missing_token|numeric_as_string|mixed_types|date_format|duplicate_rows|outliers|impossible_values|constant_column|id_column|empty_rows|empty_columns|column_name|other",
     "columns": ["..."], "n_affected": int|null, "description": "..."}
  ],
  "cleaning_plan": ["step description", "..."],
  "insights": [{"statement": "...", "numbers_cited": [{"label": "...", "value": number}]}]
}
```

Keeping issue types in a **closed vocabulary** (matching the manifest's `problem_type` values) is what makes scoring automatic. The pipeline's own outputs are mapped into the same schema by an adapter (`comparison/pipeline_adapter.py`) so both sides are scored with identical code.

### 13.5 Run protocol
- Prompts saved under `src/ads/baselines/prompts/` with version tags; the version used is recorded in each run JSON.
- Same prompt for every dataset; no per-dataset tuning.
- **N = 3 repeats** per (dataset, mode) with the same temperature (default 0.0 for reproducibility, and also one set at 0.7 to show variance, or just repeat at default temperature 1.0; **DECISION:** use temperature 0.0 for N=3 *and* note that identical outputs at T=0 are possible; additionally run N=3 at T=0.7 for Mode A only).
- Record: model id, date, prompt version, token counts, latency, cost estimate, raw response, parsed JSON, parse-failure flag, executed code (Mode B).
- Cache runs on disk keyed by (dataset sha, mode, prompt version, model, temperature, repeat); re-running must not re-spend API credits unless `--force`.
- The API key comes from environment only. If no key is present, the comparison module must degrade gracefully: skip the LLM runs, and the final report states "LLM baseline not run" (do not crash). Also support loading **pre-saved LLM responses from JSON files** so the human can paste results from a chat UI manually (`outputs/llm_baseline/<dataset>/manual/response.json`) and have them scored with the same code.

### 13.6 Metrics (`comparison/scoring.py`)

Compute for both pipeline and LLM, per dataset, per run:

**(a) Profiling accuracy** (truth from `ground_truth.py`, which uses independent simple pandas code on the raw file, written separately from the pipeline's profiler to avoid circular validation):
- Column-type accuracy: fraction of columns whose type matches truth, after mapping vocabularies to a common coarse set {numeric, categorical, binary, datetime, id, text, constant}. Truth for real datasets = human-verified type map stored in `configs/datasets/<name>.yaml` under `truth_types` (the human fills this; the implementer provides a script that proposes a draft for review).
- Missing-count exact-match rate; mean absolute error of missing % per column.
- Duplicate-row count: exact match flag and absolute error.
- Cardinality (n_unique) exact-match rate, if the LLM reports it (Mode B only).

**(b) Issue detection (messy datasets, manifest-based):**
- For each manifest problem: *detected* if the system reports an issue with matching `issue_type` and overlapping `columns` (match rule in code, documented).
- **Issue recall** = detected / total injected; **issue precision** = correct reports / total reports (a reported issue with no manifest counterpart is a false alarm unless it matches a naturally occurring truth, such as the base generator's own constant column).
- Per-problem-type breakdown (heatmap: problem type × system).
- Count accuracy: for detected issues, relative error between reported `n_affected` and manifest `n_cells`.

**(c) Cleaning quality (messy dataset only, requires a cleaned output):**
- Compare each system's cleaned CSV to `messy_clean_truth.csv` via the index map, cell-wise on the shared rows/columns after standardizing dtypes:
  - **Cell fidelity:** % of cells equal to truth (numeric within 1e-9 relative tolerance).
  - **Problems fixed:** per `auto_fixed` manifest entry, % of affected cells now equal to truth.
  - **Damage:** cells that were correct in the messy data but are wrong after cleaning (data corruption), plus rows incorrectly dropped, plus values incorrectly imputed (counted separately; the conservative pipeline output should show zero imputed cells).
  - **Row accounting:** rows after vs truth rows (duplicates removed correctly? empty rows removed? any legit rows lost?).
- Mode A has no cleaned CSV; it is scored on (b) only plus a plan-quality rubric (checklist: does the plan cover each injected problem type? yes/no count).
- Score both pipeline outputs (conservative and imputed) separately.

**(d) Number correctness:**
- Extract every numeric claim from LLM `insights[].numbers_cited` and, via `claim_extraction.py`, from the free-text statements (regex for percentages, counts, means, correlations next to a column name; keep this conservative; unparseable = not counted).
- Verify each claim against recomputed ground truth within tolerance (counts exact; percentages ±0.5 pp; means/correlations ±1% relative). Metric: **verified-claim rate** = correct / checkable. Also report n unverifiable.
- For the pipeline, the verified-claim rate is 100% by construction if insights are template-filled; **still compute it** with the same checker as a test that the pipeline never states a number it didn't compute (this is a regression test for the "every number comes from a tool" principle).

**(e) Insights (qualitative):**
- Side-by-side table per dataset: pipeline insights vs LLM insights, with a short human annotation column (matches / pipeline-only / LLM-only / LLM wrong). Also a small human-graded rubric (1-5) on usefulness, correctness, and actionability for 3 datasets. The human fills these in `outputs/comparison/qualitative_grades.csv`; implementer provides the template and a rendering script.

**(f) Efficiency (reported, not scored):** wall-clock time, LLM token and cost, and lines of code or turns used.

### 13.7 Variance and aggregation
- For LLM runs: mean ± std across repeats for every metric; show per-run values in an appendix table.
- For the pipeline: deterministic, so a single run; verify determinism by running twice and comparing output hashes (a test).
- Produce `outputs/comparison/metrics.csv` (long format: dataset, system, mode, run, metric, value), summary tables in markdown, and figures: grouped bar charts per metric (pipeline vs LLM-A vs LLM-B), issue-type detection heatmap, cleaning fidelity/damage bars.

---

## 14. Orchestration and CLI

### 14.1 `pipeline.py`: `run_phase1(input_csv, dataset_name, out_dir, config) -> Phase1Result`

Order: load → infer types → profile (raw) → clean → profile (cleaned) → schema/roles → EDA → scaling analysis → insights → render report → write all artifacts. Single function, no side effects outside `out_dir` and `data/cleaned/`. Return paths and key summaries.

Also write `data/cleaned/<name>_cleaned.csv` (conservative), `<name>_cleaned_imputed.csv`, `<name>_scaled.csv`. All with a header row, UTF-8, index not written, ISO dates.

### 14.2 CLI (Typer)

```
ads run --input PATH --name NAME [--config configs/datasets/NAME.yaml] [--out outputs/NAME]
ads run-all                      # runs every dataset in configs/datasets/
ads make-messy --seed 42         # generate messy synthetic + manifests
ads llm-baseline --mode a|b|both --repeats 3 [--force]
ads compare                      # score everything, make tables/figures
ads report                       # assemble final_report/PHASE1_REPORT.md
```

The CLI must work for **any user CSV** with no dataset config (`ads run --input mydata.csv --name mydata`), proving the generic design. Test this on a CSV the human supplies at demo time.

### 14.3 Logging
- Python `logging`, INFO to console, DEBUG to `outputs/<name>/run.log`. Never print raw data rows at INFO level for large frames.

### 14.4 Config precedence
`default.yaml` < dataset YAML < CLI flags. The fully resolved config is dumped to `outputs/<name>/config_resolved.yaml` for reproducibility.

---

## 15. Final deliverable for the TA: `final_report/PHASE1_REPORT.md`

Assembled by `scripts/build_report.py` from generated artifacts plus the human-written manual sections. Structure:

1. **Project one-paragraph context** (agentic data scientist; why Phase 1 looks like this: pipeline for *any* CSV, demonstrated on 5 datasets + messy synthetic).
2. **What was built:** architecture diagram (simple box diagram), module list.
3. **Datasets:** dataset cards table.
4. **Data cleaning:** the general policy table (every step, rule, default, rationale) and **per-dataset cleaning logs** (counts of missing, duplicates, outliers, format fixes). Explicit mapping to the TA's list: missing values ✔, duplicates ✔, outliers ✔, inconsistent formats ✔.
5. **EDA:** per dataset, the key figures embedded (missingness, distributions, correlation, class balance, target relationships), each with a one-line takeaway.
6. **Insights:** per dataset, automated + manual sections.
7. **Normalization/scaling:** per dataset decision note and the scaled file reference.
8. **Cleaned dataset generation:** list of produced files, row/column counts before and after.
9. **LLM comparison:** setup (modes, prompt versions, model, repeats), results tables and figures for (a)-(f), discussion of where the pipeline wins, where the LLM wins or ties, and honest limitations.
10. **Limitations and assumptions:** no time series, independent rows, conservative cleaning choices, thresholds are heuristics, type inference can be wrong (list known misclassifications), LLM baseline limitations (single model, prompt sensitivity).
11. **Handoff to Phase 2:** the contract (`docs/contract.md`) and what Phase 2 will consume.
12. **Reproduction instructions:** exact commands.
13. **Appendix:** per-run LLM tables, configs, test coverage summary.

Also render `PHASE1_REPORT.html` if simple (jinja2 + markdown). A PDF is optional.

**Notebooks (TA-friendly):** one per dataset, mostly narrative cells that load saved outputs and display figures/tables, plus the manual insights. They must run top-to-bottom with `Restart & Run All` on a clean checkout after `make run-all` and contain no pipeline logic (logic lives in `src/`).

---

## 16. Testing strategy

Use `pytest`. Target ≥ 85% coverage on `src/ads` excluding `baselines/llm_client.py` network code (mock the LLM).

- **Unit tests:** every type-inference branch; each cleaning step with tiny hand-built frames (before/after asserted exactly); missing-token handling; whitespace; case merge; numeric parsing edge cases (`"(1,234.5)"`, `"$ 12"`, `"1e3"`, `"12%"`, `"١٢"` should NOT crash); datetime ambiguity; duplicate drop policy (`auto` branches); outlier detection with known values (MAD = 0 guard); imputation strategies; scaling recommendations; Cramér's V and eta² against hand-computed values.
- **Property-style tests (optional with `hypothesis`):** cleaning never increases row count; cleaning is idempotent; column set after cleaning ⊆ original (conservative output); profile on a shuffled-row copy is identical.
- **Golden-file tests:** for a small fixture CSV (30 rows, every problem type), commit expected `cleaning_log.json` and the cleaned CSV; the test diffs against them.
- **End-to-end test:** run the pipeline on a tiny generated CSV and the messy synthetic; assert artifacts exist and invariants hold.
- **Determinism test:** two runs → identical output hashes (excluding timestamps; keep timestamps only in a separate `run_meta.json`).
- **Comparison tests:** scoring functions on hand-made fake LLM outputs with known expected scores (perfect, empty, hallucinating).
- **No-network test:** pipeline modules run with the network disabled and with `ANTHROPIC_API_KEY` unset.
- **Fuzz/robustness:** empty CSV, header-only CSV, single-column CSV, one-row CSV, all-NaN column, duplicate column names, 1,000-column CSV (should complete, and warn), file with only strings, BOM + semicolon delimiter, ragged rows. Each must either produce sensible output or a clear, specific error message, never an unhandled traceback.

---

## 17. Implementation order (milestones; implement strictly in this order)

Each milestone ends with its tests passing and a git commit.

**M0: Skeleton (≈ 0.5 day).** Repo layout, `pyproject`, `requirements`, Makefile, config loading, pydantic schemas, logging, CLI stub, CI-less `pytest` running with one placeholder test.

**M1: Ingestion + type inference (≈ 1 day).** `ingestion.py`, `type_inference.py`, their tests, including adversarial cases. Manually sanity-check on all 5 real datasets and fix misclassifications via logic first (config overrides last).

**M2: Profiling (≈ 1 day).** `profiling.py`, JSON output, warnings list, `column_schema.json`. Tests. Run on all datasets; eyeball results.

**M3: Messy generator (≈ 1 day).** Build **before** the cleaner so cleaning can be developed against a known answer key. `base_generator.py`, `messy_injector.py`, manifest, truth files, tests.

**M4: Cleaning steps 1-8 (≈ 2 days).** Whitespace, tokens, labels, types, validity, duplicates, structural. Log everything. Iterate against the messy dataset, checking cell fidelity with a quick script (the formal scorer comes later).

**M5: Cleaning steps 9-12 (≈ 1 day).** Missing handling (two outputs), outliers (flag/cap/remove), invariant checks, idempotence, golden tests.

**M6: EDA (≈ 2 days).** Plots module with the consistent style, univariate, missingness, bivariate descriptive, target section. Review all figures visually for readability (no overlapping labels, units, sensible binning).

**M7: Scaling + insights (≈ 1 day).** `scaling.py`, `insights.py`, markdown with preserved manual section.

**M8: Orchestrator + report rendering (≈ 1 day).** `run_phase1`, CLI, per-dataset `report.md`/`html`, `run-all`. Produce all outputs for all datasets. Test on an unseen CSV the human provides.

**M9: Ground truth + scoring + pipeline adapter (≈ 1.5 days).** `ground_truth.py`, `scoring.py`, `claim_extraction.py`, `pipeline_adapter.py`; test scoring with fakes. Score the pipeline alone first.

**M10: LLM baseline (≈ 1.5 days).** Prompts, `llm_client`, Mode A, caching, then Mode B with sandbox. Manual-response ingestion path. Run protocol: all datasets × modes × repeats.

**M11: Comparison + figures (≈ 1 day).** `compare.py`, tables, plots, qualitative template.

**M12: Notebooks + final report + polish (≈ 1.5 days).** Fill manual insights, per-dataset notebooks, `build_report.py`, README, `docs/*`, final run from a clean clone, tag `phase1-final`.

Total ≈ 15 working days of focused effort (compress by running M3 in parallel with M2, and M9 in parallel with M6 if multiple agents or people are available).

---

## 18. Acceptance criteria (Phase 1 is done when ALL are true)

**Functionality**
- [ ] `ads run --input <any csv> --name <x>` works on all 5 real datasets, the messy synthetic, and one unseen CSV, producing every artifact in Section 4's `outputs/<dataset>/` listing.
- [ ] Both cleaned outputs and the scaled copy are written for each dataset.
- [ ] No pipeline module imports an LLM SDK (verify with a grep test).
- [ ] No `NaN`/placeholder/whitespace issues remain in conservative output (assertions pass).

**Cleaning**
- [ ] Every cleaning action appears in the log with counts and examples; row accounting reconciles exactly.
- [ ] Cleaning is idempotent.
- [ ] On the messy synthetic: ≥ 95% of `auto_fixed` problems are fixed; 0 cells corrupted among cells that were correct beforehand (damage = 0); `flagged_only` problems are flagged and untouched.
- [ ] Telco's `TotalCharges` blank-string issue is detected, converted to numeric, and logged.

**Profiling**
- [ ] Type-inference accuracy ≥ 95% against the human-verified truth types across the 5 real datasets (misclassifications listed and explained in the report).
- [ ] Missing counts and duplicate counts match independent ground truth exactly.

**EDA and insights**
- [ ] All plots in Section 10 generated where applicable; every figure has a title, labelled axes, readable text, and a caption in the report.
- [ ] Insights JSON has no number that isn't in computed evidence (verified by the claim checker at 100%).
- [ ] Manual insights sections written for all 5 real datasets (≥ 5 substantive bullets each, including which findings Phase 5 should recover).
- [ ] EDA contains **no** p-values and no "significant" wording (grep test).

**Comparison**
- [ ] Mode A and (preferably) Mode B run on all datasets with ≥ 3 repeats, cached; scored with all metrics (a)-(f).
- [ ] Results tables and figures generated; report states honestly where the LLM matches or beats the pipeline.
- [ ] Without an API key, the pipeline and tests still pass and the report notes the missing LLM runs.

**Engineering**
- [ ] `make setup && make test && make run-all && make compare && make report` works from a clean clone.
- [ ] ≥ 85% test coverage on `src/ads`; lint clean.
- [ ] Determinism test passes; raw data files unchanged (checksum test).
- [ ] `docs/decisions.md` lists every DECISION/OPEN and the final choice; `docs/contract.md` documents the Phase 2 handoff.

**Deliverable**
- [ ] `final_report/PHASE1_REPORT.md` (+ HTML) complete per Section 15; notebooks run top-to-bottom.

---

## 19. Phase 1 → Phase 2 handoff contract (`docs/contract.md`)

Phase 2 may rely on exactly these artifacts per dataset:

1. `data/cleaned/<name>_cleaned.csv`: the conservative cleaned frame (NaN preserved).
2. `outputs/<name>/column_schema.json`: `{col: {semantic_type, role, n_unique, pct_missing}}`.
3. `outputs/<name>/profile.json`: full `DataProfile` (schema_version 1.0).
4. `outputs/<name>/cleaning_log.json`: what was done (so the final report can state it).
5. `outputs/<name>/insights.json`: descriptive insights, including candidate strong relationships (descriptive only), used by Phase 2 as hints, never as test results.
6. Python API: `ads.pipeline.run_phase1(...)`, `ads.profiling.profile_dataset(...)`, `ads.cleaning.clean_dataset(...)`, importable as pure functions with no I/O side effects beyond what is documented, so Phase 4 can wrap them as LangGraph nodes.

Breaking changes to these require bumping `schema_version` and updating this file.

---

## 20. Risks and pitfalls (read before coding)

1. **Silent coercion at load time.** Loading with pandas defaults hides problems (e.g., Telco `TotalCharges`). Always load as strings first.
2. **Over-cleaning.** Dropping outliers or imputing aggressively changes statistical conclusions in Phase 3. Keep defaults conservative; make aggressive options opt-in and logged.
3. **ID/ZIP/code columns misread as numeric.** Add name/format heuristics and tests.
4. **Ambiguous dates (01/02/2020).** Never guess silently; log a warning.
5. **Circular validation.** Ground-truth code must be written independently of the profiler (separate, simpler code), or the "accuracy" metric proves nothing.
6. **Unfair LLM baseline.** Same data access (Mode B), same prompt across datasets, saved prompts, repeats. Do not tune prompts against the messy dataset only to make the baseline look worse; if a prompt is revised, rerun everything and report the version.
7. **LLM familiarity with public datasets.** Note that the LLM may have seen some of the Kaggle datasets; the messy synthetic dataset is the contamination-free test. State this in the report.
8. **Scope creep into Phase 3.** No p-values, no "significant" in EDA text; correlation heatmaps are descriptive.
9. **Plot overload.** Cap figure counts; batch columns into multi-panel figures; never produce 200 PNGs.
10. **Notebook logic drift.** Notebooks are thin viewers; logic stays in `src/`.
11. **Overwriting manual insights on re-run.** Preserve content between the MANUAL markers.
12. **Secrets.** Never commit API keys; `.env` is gitignored; sandboxed code must not see environment secrets.
13. **Non-determinism.** Seed everything; avoid unordered set iteration in outputs; sort keys in JSON; keep timestamps out of hashed artifacts.
14. **Large files.** Avoid O(n²) operations on wide data (correlation of 1,000 columns); cap with warnings.

---

## 21. Things the human must do (the AI cannot)

- Download the 5 Kaggle datasets into `data/raw/<name>/` and fill `docs/datasets.md` with sources and licenses.
- Provide / verify the `truth_types` per real dataset (a draft is auto-proposed; the human corrects it).
- Provide an `ANTHROPIC_API_KEY` for the LLM baseline, or paste LLM responses manually into the `manual/` folder.
- Write the **manual insights** sections and the qualitative grades.
- Confirm with the TA that (a) the multi-dataset + generator framing and (b) including the LLM comparison in Phase 1 are acceptable.
- Review all figures once for readability, and spot-check cleaning logs on at least two datasets.

---

## 22. Definition of "done" in one sentence

Given any CSV, one command produces a profile, a fully-logged conservatively cleaned dataset, a complete set of readable EDA figures, auto-generated and manually written insights, a scaling decision note, and, for the 5 chosen datasets plus the messy synthetic benchmark, a reproducible, honest, scored comparison against an LLM, all packaged as the report the TA asked for, with outputs in the exact format Phase 2 will consume.
