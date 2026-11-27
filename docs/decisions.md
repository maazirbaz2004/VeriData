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

---

## 4. Phase 2 Decisions (Hypothesis Generation)

| ID | Section | Plan Requirement / Open Question | Chosen Default & Rationale |
| :--- | :---: | :--- | :--- |
| **P2-H1** | Master Plan | Package rename `ads` -> `veridata`. | **Followed.** Renamed `src/ads` to `src/veridata`, updated imports, `pyproject.toml`, `Makefile`, and CLI entrypoint (`veridata`), and added `CLAUDE.md`/`AGENTS.md`. |
| **P2-H2** | Sec 3.2 | `numeric_discrete` with $\le 10$ distinct values. | **Chosen:** Treated as categorical (`NUM_CATEGORICAL` or `CAT_CAT`; `NUM_BINARY` if 2 levels) by default; configurable via `hypotheses.treat_small_discrete_as_numeric: false`. Recorded in `hypothesis_manifest.json`. |
| **P2-H3** | Sec 4 | Rare-level policy during feasibility screening (`NUM_CATEGORICAL`, `CAT_CAT`). | **Chosen:** Levels with $n < \text{min\_group\_n}$ (default `8`) are excluded from that test and recorded in `FeasibilityReport.dropped_levels` and `reasons`. The hypothesis remains feasible iff $\ge 2$ levels remain (for `CAT_CAT`, $\ge 2$ rows and $\ge 2$ columns) and remaining $n \ge \text{min\_n\_pairwise}$ (default `20`). Optional rare-level lumping into `"Other"` is off by default (`lump_rare_levels: false`). |
| **P2-H4** | Sec 6 | Outcome-independent pruning order when feasible $m > \text{max\_tests}$ (default `3000`). | **Chosen:** (1) If `target` is configured, switch to `target_focused`; (2) else drop `NUM_CATEGORICAL` / `CAT_CAT` pairs with highest cardinality first; (3) else keep highest outcome-independent `priority_score` (tie-break alphabetical `id`). Every step and pruned count is recorded in `hypothesis_manifest.json -> pruning_steps`. |
| **P2-H5** | Sec 5.3 | Causal-language and digit validation on LLM rationales before Phase 5 shared linter exists. | **Chosen:** Implemented local regex validators in `contracts/hypothesis.py` (digit rejection) and `hypotheses/llm_proposer.py` (causal verb rejection); will unify with Phase 5 `reporting/language_lint.py` once built. |
| **P2-H6** | Sec 7 | Offline natural-language hypothesis parsing fallback when no LLM API key is configured. | **Chosen:** Deterministic normalized token + light stemming + `difflib` fuzzy matching against column names and non-generic categorical levels, plus deterministic regex detection for unsupported causal/ML/time-series questions. Achieves $\ge 85\%$ accuracy on `tests/gold/nl_hypotheses.jsonl` completely offline. |

---

## 5. Phase 3 Decisions (Statistical Tool Library & Validation Layer)

| ID | Section | Plan Requirement / Open Question | Chosen Default & Rationale |
| :--- | :---: | :--- | :--- |
| **P3-S1** | Sec 2 | Two-stage execution for bootstrap CIs and sensitivity checks. | **Followed.** Stage A computes all p-values and point effect sizes; Stage B runs bootstrap CIs, paired sensitivity checks (Welch↔MWU, Pearson↔Spearman), and leave-1%-out outlier influence checks only for candidates ($q \le \alpha$ or $p_{\text{raw}} < 0.10$). |
| **P3-S2** | Sec 4.4 | Yates continuity correction for $2 \times 2$ chi-square (`yates`). | **Chosen:** `stats.yates: false` by default because sparse/small $2 \times 2$ tables (expected $< 5$ or $n < 40$) are routed directly to Fisher's exact test, where Yates's overly conservative correction is unnecessary. |
| **P3-S3** | Sec 7.6 | Batch vs. chat multiple-testing family accounting. | **Chosen:** Unified session ledger (`ledger.jsonl`). Batch tests form the initial family; chat follow-ups append to the same ledger and recompute BH over `batch ∪ chat`, surfacing any status flips via `Ledger.revalidate()` diffs. |
| **P3-S4** | Sec 6 | Confidence intervals for selected findings. | **Chosen:** Nominal 95% CIs (unadjusted for post-selection multiplicity), documented in `docs/stats_methods.md` Section 4. `strict_ci` (rejecting CIs that cross 0) defaults to `false`. |
| **P3-S5** | Sec 9 | Parallelism threshold in `runner.run_all`. | **Chosen:** Use `joblib.Parallel(backend="loky")` when `n_jobs != 1` and there are $\ge 40$ hypotheses; run sequentially for smaller sets to avoid Windows process-spawn overhead while keeping deterministic per-hypothesis RNG seeds (`sha256(seed:hypothesis_id)`). |



---

## 6. Phase 4 Decisions (Synthetic Benchmark & Calibration)

| ID | Section | Plan Requirement / Open Question | Chosen Default & Rationale |
| :--- | :---: | :--- | :--- |
| **P4-01** | Sec 4.1 | Shape of the structural model. | **Chosen:** two layers — root columns and a few latent factors feed child columns, one parent edge per child. Induced dependence comes only from siblings / common ancestors, so the dependence closure is easy to compute and test; colliders (two parents of one child) stay independent. |
| **P4-02** | Sec 4.1 | How to plant exact effect sizes in skewed / heavy-tailed data. | **Chosen:** every family (normal, lognormal σ = 0.8, t3, 30% zero-inflated, bimodal) is **standardised to population mean 0, SD 1** before the edge is applied, so r, d and η² are exact. Spearman targets are calibrated by simulation; Cramér's V targets by bisection on the analytic table. Truth is re-measured on a 20,000-row draw. |
| **P4-03** | Sec 4.4 | Weak induced dependence. | **Chosen:** induced pairs with population dependence < 0.05 are **gray** and ignored by the matcher (neither hit nor error). They are not realistically detectable and would otherwise punish correct behaviour. |
| **P4-04** | Sec 5 | Cost of running 9 variants. | **Chosen:** variants that share a test-selection mode share one Stage A run per dataset; only validation (correction + floor) is re-run per variant. Results are cached by (variant, data hash, seed, code hash). |
| **P4-05** | Sec 5 | Variant list. | **Followed**, plus `naive_raw` (naive tests, no correction, no floor) as the "what an untrained analyst does" baseline. `assumption_only` is an **alias** of `veridata_nocorrection` because Phase 3's default already uses assumption-aware selection with raw p < α and no floor. |
| **P4-06** | Sec 6 | Which directions to check. | **Chosen:** only where the truth has a clear direction — the sign for numeric–numeric pairs and the higher group for a numeric column vs a **2-level** group column. Other true pairs count when the pair is right. |
| **P4-07** | Sec 6 | FWER definition with correlated null blocks. | **Chosen:** FWER is computed over **zero-planted** datasets (no planted edges) and counts datasets with ≥ 1 *false* discovery. Null blocks create real dependence, so a report on a block pair is a true discovery, not an error. |
| **P4-08** | Sec 7.1 | 5,000 reps per Type I cell. | **Changed:** 1,000 reps per cell (116 cells) to fit the time budget, with ± 2 Monte Carlo SE slack in the pass band; any cell above 0.075 is re-run with ≥ 10,000 reps before counting as a failure (one cell was: 0.098 → 0.059 with 12,000 reps). |
| **P4-09** | Sec 8 | What to tune. | **Chosen:** only a single multiplier on all effect floors (grid 0.5–1.5). `large_n_clt` and `extreme_skew` are **not tuned**: the Type I calibration already passes with the defaults, and tuning them on 60 datasets would overfit. Result: multiplier 1.0 kept. |
| **P4-10** | Sec 7.2 | How to run the dependence experiment fast enough. | **Chosen:** vectorised Pearson p-values for all pairs of a correlated Gaussian matrix, corrected with the product's own `stats.correction.apply_correction`, 300 reps per cell. The correction code under test is the real one; only the p-value computation is vectorised. |
| **P4-11** | Sec 4.5 | core60 design. | **Chosen:** 12 zero-effect datasets (every n × p cell, 4 with null blocks) + 48 effect datasets (every n × p × k cell with 2 of the 4 strengths, rotated). Shapes, imbalance, missingness, decoys and confounders are assigned by seeded rotation so each appears across n and p. |

---

## 7. Phase 5 Decisions (Reporting & Number Verification)

| ID | Section | Plan Requirement / Open Question | Chosen Default & Rationale |
| :--- | :---: | :--- | :--- |
| **P5-01** | Cut list | LLM slot narration (P5-M5). | **Skipped for now** (deadline; the plan's cut list allows it). All explanations come from fixed templates filled from the `FactRegistry`. `--narration llm_slots` falls back to templates with a note. The verifier and linter are built so LLM slots can be added later without changes. |
| **P5-02** | Sec 3 | Where the old Phase 1 `reporting.py` goes. | **Chosen:** moved (git mv) to `reporting/dataset_report.py`; `veridata.reporting` re-exports `render_dataset_report`, so existing imports keep working. `veridata report` without `--dataset` still builds the Phase 1 report. |
| **P5-03** | Sec 6 | How numbers reach text. | **Chosen:** templates only contain `{.fact}` placeholders; `FactRegistry.render` fills the registered display string. Templates never format numbers (a test greps `templates.py`). |
| **P5-04** | Sec 6.2 | Matching rules of the number verifier. | **Chosen (conservative):** a number matches a fact if it equals the display, or lies within half a unit of the last shown digit; a number shown with *more* decimals than the fact must be the correct rounding of the real value. **No fraction ↔ percent conversion** (so "0.95" can never borrow the 95% CI level) and "<0.001" only matches tokens written with "<". Number words ("twice", "three") and non-ASCII digits are always violations. |
| **P5-05** | Sec 6.3 | Digits that are not numbers. | **Chosen:** masked before checking — numbered list markers, heading numbers, link targets, HTML tags/comments, and registered string facts (column names, level labels). **Known gap:** a level label that is itself a number (e.g. level "1") is allowed wherever that finding's facts are in scope. |
| **P5-06** | Sec 7 | Wording for rejected tests. | **Chosen:** "not supported after correction" instead of "not significant", so the bare word "significant" never appears; the linter only allows "statistically significant after correction". |
| **P5-07** | Sec 8 | HTML output. | **Chosen:** python-markdown (tables, fenced code, `md_in_html`) with inline CSS and charts embedded as base64 PNGs, so `report.html` is one self-contained file (insurance: 1.5 MB, limit 15 MB). |
| **P5-08** | Sec 9 | Report gate. | **Followed:** the final markdown, every chart's text, the linter, required sections and image checks must all pass, else `ReportingError` (`--allow-violations` for debugging only). |
| **P5-09** | Sec 6 (from Phase 4) | What adjusted p-values mean to a reader. | **Added** a Limitations line: BH controls the share of false findings in the list, so borderline q-values are more often false leads (seen in the dev q-calibration). |

---

## 8. Phase 8 Decisions (Evaluation, Gemini Integration & Final Deliverables)

| ID | Section | Plan Requirement / Open Question | Chosen Default & Rationale |
| :--- | :---: | :--- | :--- |
| **P8-01** | Master Plan §9.4 / P8 §3 | Supporting Google Gemini alongside Anthropic Claude without changing shared contracts. | **Chosen:** Added `GeminiLLMClient` in `src/veridata/agent/llm.py` using `httpx` against Gemini's `generateContent` REST endpoint with `responseMimeType: "application/json"` plus embedded Pydantic JSON schema instructions and automatic validation retries (avoiding Gemini's `responseSchema` rejection of `$defs`/`anyOf`). `get_llm_client()` auto-loads `.env` via `python-dotenv` and selects Gemini whenever `GEMINI_API_KEY` is set. |
| **P8-02** | P8 §3 / §6 | Executing LLM-written pandas/scipy code safely for `S1b` and E7 baseline. | **Chosen:** AST inspection (`evaluation/sandbox.py`) restricts imports to `pandas`, `numpy`, `scipy`, `math`, `statistics`, `collections`, `itertools`, `json`, blocks file/OS/eval builtins, and runs in an isolated `python -I` subprocess with a 15s timeout. |
| **P8-03** | P8 §4 (E1) | Aggregating `R = 5` LLM repeats without treating repeats as independent datasets. | **Chosen:** `collapse_repeats()` averages per-dataset FDP, recall, precision, and counts over repeats first, recording within-dataset repeat SD, before dataset-level bootstrap CIs (2,000 resamples) and paired Wilcoxon tests. |
| **P8-04** | P8 §4 (E4) / §6 | Preventing circular numeric verification in E4 and E7. | **Chosen:** `src/veridata/evaluation/independent_recompute.py` uses only `numpy`, `pandas`, and `scipy.stats` and is enforced by an AST unit test (`tests/evaluation/test_independent_recompute.py`) to have zero imports from `veridata.stats`, `veridata.validation`, `veridata.reporting`, or `veridata.agent`. |
| **P8-05** | P8 §3 (A6) | Isolating assumption & triviality validation gates in `A6_full_minus_gates`. | **Chosen:** Added `stats.enable_trivial_gate: bool = True` in `config.py` / `configs/default.yaml` / `validation/rules.py` alongside `enable_assumption_gate`. Default product behavior is unchanged (`true`). |
| **P8-06** | P8 §4 (E5) | Laptop runtime budget for permutation, noise, split-half, and bootstrap loops on wide/large real datasets. | **Chosen:** Adaptive parallelized resample counts (`e5_real.py`): 20 repeats on `insurance` and `heart_disease`, 10 on wide datasets (`telco_churn`, `student_performance`, >=20 cols), and 5 on `bank_marketing` (41,176 rows). |
| **P8-07** | P8 §2 / §10 | Protocol freeze and one-shot `test`-split execution discipline. | **Chosen:** Keep `docs/eval_protocol.md` at `Status: DRAFT` and `outputs/benchmark/core60/test` untouched until the user places `GEMINI_API_KEY` in `.env` and explicitly approves freezing and running the final test-split pass. |

