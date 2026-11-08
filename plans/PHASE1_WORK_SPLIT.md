# Phase 1 Work Division — Partner 1 & Partner 2

> **Reference Specification:** [`plans/PHASE1_PLAN.md`](./PHASE1_PLAN.md)
> **Total Estimated Effort:** 16.0 working days across Milestones `M0`–`M12`, split equally into **8.0 days for Partner 1** and **8.0 days for Partner 2**.

---

## 1. Architectural Split Overview

Phase 1 builds a deterministic CSV profiling, cleaning, EDA, and insight pipeline (`src/ads/`), validates it across 5 real datasets + 1 messy synthetic benchmark, and evaluates it against a 2-mode LLM baseline (`final_report/PHASE1_REPORT.md`).

To maximize parallel development and avoid merge conflicts or circular validation ([Section 20, Risk #5](./PHASE1_PLAN.md#20-risks-and-pitfalls-read-before-coding)):

- **Partner 1 (Core Data Engine & Synthetic Benchmark — 8.0 days):** Owns project scaffolding & data contracts (`M0`), CSV ingestion & semantic type inference (`M1`), dataset profiling (`M2`), messy synthetic dataset generator (`M3`), the 11-step conservative/imputed cleaning engine (`M4`–`M5`), scaling & transformation analysis (`M7a`), pipeline orchestration (`M8a`), and 3 of the 6 dataset analyses (`M12a`).
- **Partner 2 (EDA, Reporting & LLM Evaluation Suite — 8.0 days):** Owns automated EDA & visualizations (`M6`), rule-based insight generation (`M7b`), Jinja2 report rendering (`M8b`), independent ground-truth & scoring engine (`M9`), LLM baseline Modes A & B with subprocess sandboxing (`M10`), comparison tables/plots (`M11`), final TA report assembly, and 3 of the 6 dataset analyses (`M12b`).

---

## 2. Partner 1 Tasks (Core Data Engine & Synthetic Benchmark — 8.0 Days)

### Milestone Summary

| Milestone | Est. Effort | Plan Reference | Core Objective |
| :--- | :---: | :--- | :--- |
| **M0: Skeleton & Contracts** | `0.5d` | Sections 3, 4, 6 | Repo layout, build/test tooling, YAML config loader, and all Pydantic v2 schemas. **Must be completed first (Day 1) to unblock Partner 2.** |
| **M1: Ingestion & Type Inference** | `1.0d` | Section 7 | Robust string-first CSV ingestion (`load_csv`) and 10-rule semantic column type inference (`infer_column_types`). |
| **M2: Dataset Profiling** | `1.0d` | Section 8 | `profile_dataset()` producing `DataProfile`, `profile.json`, warnings list, and Phase 2 handoff `column_schema.json`. |
| **M3: Messy Synthetic Generator** | `1.0d` | Section 12 | `make_clean_base()` + `inject_problems()` (18 defect types) producing `messy_dataset.csv`, `messy_manifest.json`, and `messy_to_truth_index.json`. |
| **M4: Cleaning Steps 1–8** | `2.0d` | Sections 9.1–9.8 | Column normalization, whitespace/unicode cleanup, missing tokens, category label merging, type conversion, validity rules, duplicate & structural drops + `CleaningLog`. |
| **M5: Cleaning Steps 9–11** | `1.0d` | Sections 9.9–9.12 | Dual outputs (`df_clean_conservative` + `df_clean_imputed` with `__was_missing`), outlier detection/handling, `CleaningInvariantError`, idempotence & golden tests. |
| **M7a: Scaling & Transformations** | `0.5d` | Section 11b | Skewness/scale analysis, `log1p`/`yeo-johnson`/z-score recommendations, `scaling_report.md`, `scaling_params.json`, and `<name>_scaled.csv`. |
| **M8a: Pipeline Orchestrator & CLI** | `0.25d` | Section 14 | `run_phase1()` orchestrator in `pipeline.py`, `scripts/run_all.py`, and Typer CLI (`ads run`, `ads run-all`, `ads make-messy`). |
| **M12a: Datasets (3 of 6) & Handoff Docs** | `0.75d` | Sections 5, 15, 19 | Dataset setup, `truth_types`, notebooks, and manual insights for **Insurance**, **Telco Churn**, and **Heart Disease**, plus `docs/contract.md` and `docs/decisions.md`. |

### Exact Files & Modules Owned by Partner 1

```text
├── pyproject.toml
├── requirements.txt
├── Makefile
├── .gitignore
├── .env.example
├── configs/
│   ├── default.yaml
│   └── datasets/
│       ├── insurance.yaml
│       ├── telco_churn.yaml
│       └── heart_disease.yaml
├── src/ads/
│   ├── __init__.py
│   ├── config.py                   # YAML config loading & merging (default + dataset + CLI)
│   ├── schemas.py                  # Pydantic v2 contracts: SemanticType, ColumnProfile, DataProfile, CleaningLogEntry, CleaningResult, EDAResult, etc.
│   ├── ingestion.py                # load_csv() -> df_raw_str, df_naive, IngestionMetadata
│   ├── type_inference.py           # infer_column_types() -> (SemanticType, reason)
│   ├── profiling.py                # profile_dataset() -> DataProfile + column_schema.json
│   ├── cleaning/
│   │   ├── __init__.py             # clean_dataset() -> CleaningResult
│   │   ├── steps.py                # Steps 1, 2, 5, 6, 7, 8, 11
│   │   ├── missing.py              # Step 3 (token normalization) & Step 9 (conservative vs imputed)
│   │   ├── categories.py           # Step 4 (case/whitespace merging + fuzzy warnings)
│   │   ├── outliers.py             # Step 10 (IQR 1.5/3.0, modified z-score, flag/cap/remove)
│   │   └── log.py                  # CleaningLog collector + cleaning_log.json
│   ├── scaling.py                  # analyze_scaling() -> scaling_report.md, scaling_params.json, <name>_scaled.csv
│   ├── pipeline.py                 # run_phase1() orchestrator + Typer CLI entrypoints
│   └── synthetic/
│       ├── __init__.py
│       ├── base_generator.py       # make_clean_base() (2,000 rows, 14 cols, planted relationships)
│       └── messy_injector.py       # inject_problems() (18 defect types + manifest + truth index map)
├── scripts/
│   ├── make_messy_dataset.py
│   └── run_all.py
├── notebooks/
│   ├── 00_overview.ipynb
│   ├── insurance_phase1.ipynb
│   ├── telco_churn_phase1.ipynb
│   └── heart_disease_phase1.ipynb
├── docs/
│   ├── contract.md                 # Phase 1 -> Phase 2 handoff specification
│   └── decisions.md                # Resolution log for all DECISION/OPEN items
└── tests/
    ├── test_ingestion.py
    ├── test_type_inference.py
    ├── test_profiling.py
    ├── test_messy_injector.py
    ├── test_cleaning_*.py
    ├── test_outliers.py
    ├── test_scaling.py
    └── test_pipeline_end_to_end.py
```

### Partner 1 Acceptance Checklist
- [ ] `M0` schemas and config loader committed first so Partner 2 can import `DataProfile`, `ColumnProfile`, `CleaningResult`, and `EDAResult`.
- [ ] All CSVs load as `str` first (`dtype=str, keep_default_na=False`) without silent coercion; fallback encodings and bad lines are logged.
- [ ] Type inference achieves $\ge 95\%$ accuracy across the 5 real datasets against human-verified `truth_types`.
- [ ] Cleaning is idempotent: running `clean_dataset()` on its own cleaned output produces no further changes.
- [ ] On the messy synthetic dataset: $\ge 95\%$ of `auto_fixed` problems are repaired, `0` previously valid cells are corrupted (`damage = 0`), and `flagged_only` problems are logged without destructive mutation.
- [ ] Telco Churn's blank-string `TotalCharges` issue is automatically detected, converted to numeric, and logged.
- [ ] Both `<name>_cleaned.csv` (conservative), `<name>_cleaned_imputed.csv`, and `<name>_scaled.csv` are generated for each dataset.
- [ ] Manual insights ($\ge 5$ substantive bullets each) and notebooks completed for **Insurance**, **Telco Churn**, and **Heart Disease**.

---

## 3. Partner 2 Tasks (EDA, Reporting & LLM Evaluation Suite — 8.0 Days)

### Milestone Summary

| Milestone | Est. Effort | Plan Reference | Core Objective |
| :--- | :---: | :--- | :--- |
| **M6: Automated EDA & Plots** | `2.0d` | Section 10 | Publication-grade 150-DPI `Agg` plots (`overview`, `missingness`, `univariate`, `bivariate` descriptive correlations/Cramér's V/$\eta^2$, `target` analysis). |
| **M7b: Rule-Based Insights** | `0.5d` | Section 11 | Deterministic template-driven insight generator (`insights.json` + `insights.md`) preserving `<!-- MANUAL:START/END -->` sections on re-runs. |
| **M8b: Per-Dataset Report Rendering** | `0.75d` | Sections 4, 9.12, 14 | Jinja2 rendering of per-dataset `report.md`, `report.html`, and human-readable `cleaning_log.md`. |
| **M9: Ground Truth, Adapter & Scoring** | `1.5d` | Sections 13.4, 13.6 | Independent `ground_truth.py`, `pipeline_adapter.py`, `claim_extraction.py`, and `scoring.py` covering metrics (a)–(d). |
| **M10: LLM Baselines (Modes A & B)** | `1.5d` | Sections 13.3, 13.5 | Provider-agnostic `llm_client.py`, versioned prompts, disk caching, Mode A (summary), Mode B (multi-turn code execution in `sandbox.py`), and manual fallback. |
| **M11: Comparison Runner & Figures** | `1.0d` | Section 13.7 | `compare.py` computing mean $\pm$ std across repeats ($N=3$ at $T=0.0$ and $T=0.7$), outputting `metrics.csv`, markdown tables, comparison plots, and qualitative rubric template. |
| **M12b: Datasets (3 of 6) & Final TA Report** | `0.75d` | Sections 5, 15 | Dataset setup, `truth_types`, notebooks, and manual insights for **Student Performance**, **Bank Marketing**, and **Messy Synthetic**, plus `docs/datasets.md` and `scripts/build_report.py` (`final_report/PHASE1_REPORT.md`). |

### Exact Files & Modules Owned by Partner 2

```text
├── configs/
│   └── datasets/
│       ├── student_performance.yaml
│       ├── bank_marketing.yaml
│       └── messy_synthetic.yaml
├── src/ads/
│   ├── eda/
│   │   ├── __init__.py             # run_eda(df, profile, schema, config, out_dir) -> EDAResult
│   │   ├── plots.py                # Consistent 150-dpi seaborn whitegrid styling & multi-panel batching
│   │   ├── missingness.py          # missing_bar.png, missing_heatmap.png, missing_correlation.png
│   │   ├── univariate.py           # numeric histograms+KDE+boxplots (+log1p), categorical bars, summaries
│   │   └── bivariate.py            # Pearson/Spearman heatmaps, top scatters, Cramér's V, eta-squared box/violins
│   ├── insights.py                 # generate_insights() -> insights.json, insights.md (preserves MANUAL block)
│   ├── reporting.py                # Jinja2 renderer for outputs/<dataset>/report.md, report.html, cleaning_log.md
│   ├── baselines/
│   │   ├── __init__.py
│   │   ├── llm_client.py           # Pluggable LLM interface + Anthropic implementation + disk cache
│   │   ├── prompts/
│   │   │   ├── v1_system.txt
│   │   │   ├── v1_task_summary_mode.txt
│   │   │   └── v1_task_code_mode.txt
│   │   ├── llm_summary_mode.py     # Mode A runner (summary + sample -> strict JSON)
│   │   ├── llm_code_mode.py        # Mode B runner (multi-turn pandas code + cleaned CSV + strict JSON)
│   │   └── sandbox.py              # Restricted subprocess execution (timeout, tmp dir, import allow-list, scrubbed env)
│   └── comparison/
│       ├── __init__.py
│       ├── ground_truth.py         # Independent pandas ground-truth calculations (types, missing, duplicates)
│       ├── pipeline_adapter.py     # Maps pipeline outputs into the closed-vocabulary LLM output schema
│       ├── claim_extraction.py     # Extracts & verifies numeric claims from insights against ground truth
│       ├── scoring.py              # Computes metrics (a) profiling, (b) issue detection, (c) cleaning quality, (d) claim accuracy
│       └── compare.py              # Orchestrates comparison across datasets/runs -> metrics.csv, tables/*.md, figures/*.png
├── scripts/
│   ├── download_datasets.md
│   ├── run_llm_baseline.py
│   └── build_report.py             # Assembles final_report/PHASE1_REPORT.md (+ HTML)
├── notebooks/
│   ├── student_performance_phase1.ipynb
│   ├── bank_marketing_phase1.ipynb
│   └── messy_synthetic_phase1.ipynb
├── docs/
│   └── datasets.md                 # Dataset cards (sources, SHA-256, licenses, column descriptions)
├── final_report/
│   └── PHASE1_REPORT.md            # Final TA deliverable
└── tests/
    └── test_scoring.py             # Unit tests for ground truth, claim extraction, and scoring on synthetic/fake LLM outputs
```

### Partner 2 Acceptance Checklist
- [ ] All Section 10 EDA plots render with `Agg` backend at 150 DPI, readable labels, takeaways in titles, and zero p-values or `"significant"` wording.
- [ ] `insights.py` produces 100% verified numbers (every number in `insights.json` traces to computed `evidence` and passes `claim_extraction.py` at 100%).
- [ ] Re-running `insights.py` never overwrites human text between `<!-- MANUAL:START -->` and `<!-- MANUAL:END -->`.
- [ ] `ground_truth.py` is implemented independently of Partner 1's `profiling.py` to prevent circular validation.
- [ ] `sandbox.py` enforces timeouts, blocks network/system calls and out-of-directory writes, and scrubs API keys from subprocess environments.
- [ ] Without `ANTHROPIC_API_KEY` set, the pipeline and test suite still pass and `compare.py` / `build_report.py` degrade gracefully (or score pre-saved JSON responses in `outputs/llm_baseline/<dataset>/manual/`).
- [ ] Manual insights ($\ge 5$ substantive bullets each) and notebooks completed for **Student Performance**, **Bank Marketing**, and **Messy Synthetic**.
- [ ] `scripts/build_report.py` compiles the complete 13-section `final_report/PHASE1_REPORT.md` for the TA.

---

## 4. Synchronization Points & Shared Interfaces

1. **Sync 1 — Day 1 (`M0` Handoff):**
   - Partner 1 completes and commits `src/ads/schemas.py` and `src/ads/config.py`.
   - Both partners lock in the function signatures for `run_phase1`:
     - `run_eda(df_clean_conservative, profile, schema, config, out_dir) -> EDAResult`
     - `generate_insights(profile, cleaning_result, eda_result, scaling_report, config) -> Insights`
     - `render_dataset_report(profile, cleaning_result, eda_result, scaling_report, insights, out_dir) -> Path`
2. **Sync 2 — Day 3 (`M3` Handoff):**
   - Partner 1 generates and commits `data/synthetic/messy_dataset.csv`, `messy_manifest.json`, `messy_clean_truth.csv`, and `messy_to_truth_index.json`.
   - Partner 2 uses these artifacts to test `scoring.py` (`M9`) and run `eda/` (`M6`).
3. **Sync 3 — Day 6 (`M5` + `M8` Integration):**
   - Partner 1 finishes the cleaning engine (`M5`) and wires Partner 2's `run_eda`, `generate_insights`, and `render_dataset_report` into `pipeline.py` (`M8`).
   - Both run `ads run-all` on all 6 datasets (`5 real + 1 messy synthetic`).
4. **Sync 4 — Day 8 (`M12` Final Polish):**
   - Both partners finish their respective 3 dataset notebooks and manual insight sections, complete the qualitative comparison rubric (`outputs/comparison/qualitative_grades.csv`), and run `make setup && make test && make run-all && make compare && make report` from a clean checkout.

