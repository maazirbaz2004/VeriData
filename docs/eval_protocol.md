# VeriData evaluation protocol (Phase 4 -> Phase 8)

**Status: DRAFT** — written in Phase 4 and completed for Phase 8. Both partners review it, then change `DRAFT` to `FROZEN`
in the line above **before any test-split run** (with tag `eval-protocol-frozen`). The code refuses `--split test` unless
this file is frozen and `--confirm-final` is passed (`src/veridata/benchmark/suites.py::check_split`).

Everything a Phase 8 run needs is defined here. If a definition here and the code disagree, the
code is a bug: fix the code, not the protocol, after the freeze.

---

## 1. What is being measured

The claim under test: *VeriData reports dataset relationships with a controlled false discovery
rate, while still finding most real, non-trivial relationships, and never introduces unverified numbers.*
We measure this on synthetic datasets where the true relationships are known exactly ("planted truth"),
on real datasets via pre-registered findings and ground-truth-free stress tests, and in interactive chat.

## 2. Datasets (suites)

Defined in `configs/benchmark/suites.yaml` and expanded by `src/veridata/benchmark/suites.py`.
The expanded scenario list is hashed (`suite_hash`) and the hash is stored with every result.

| Suite | Purpose | Size |
| :--- | :--- | :--- |
| `smoke` | CI and quick checks | 6 scenarios x 2 seeds = 12 datasets |
| `core60` | Primary suite | 60 datasets per split |

`core60` design (seeded, `design_seed: 4242`):

- n (rows) in {100, 300, 1000, 5000}; p (columns) in {10, 30, 60}.
- **12 zero-effect datasets**: one per (n, p) cell; 4 of them contain correlated null blocks.
- **48 effect datasets**: every (n, p, k) cell with k in {3, 8} planted effects gets 2 of the 4
  strengths {small, medium, large, mixed}, rotated so each strength appears 12 times.
- Distribution shape (normal, lognormal, t3, zero-inflated, bimodal, mixed), group imbalance,
  missingness (0% or 5% MCAR on half the columns), null blocks, quadratic and interaction decoys
  and common-cause confounders are assigned by seeded rotation.

### Generator (summary)

- Two-layer structural model: root columns and a few latent factors feed child columns; each child
  has one parent edge (linear, monotonic, binary shift, categorical shift or category-category).
- Effect sizes are set on **population-standardised** variables, so the planted Pearson r,
  Cohen's d, eta^2 and Cramer's V are exact; Spearman targets are calibrated by simulation.
- Column names are neutral (`v01`, `v02`, ...) and level names are `L0`, `L1`, ...; columns and rows
  are shuffled, so names and order leak nothing.

## 3. Seeds and splits

| Split | Seeds | Used for |
| :--- | :--- | :--- |
| `dev` | base 0 (seed = 0 + 10*i + r) | debugging, tuning, all Phase 4-7 work & Phase 8 dry runs |
| `test` | base 10000 (seed = 10000 + 10*i + r) | **once**, in Phase 8, after the freeze |

Tuning variants (`tune_floor_x*`) are refused on any split other than `dev`.

## 4. Ground truth for each dataset

For every unordered column pair the truth file (`truth.json`) says which group it is in:

- **true pair** — the two columns are dependent in the population:
  - `direct`: one is the parent of the other;
  - `induced`: they share a parent or an ancestor (siblings, common cause) and the population
    dependence is at least 0.05.
- **gray pair** — induced dependence weaker than 0.05. These are **ignored** (neither a hit nor a
  false discovery), because no realistic sample size could be expected to find them.
- **null pair** — independent in the population (includes colliders: two parents of the same child
  are independent).

Dependence is measured as |Spearman rho| (numeric-numeric), bias-corrected rank eta (numeric-group)
and bias-corrected Cramer's V (group-group), computed on a 20,000-row population draw.

A true pair is **testable** when, after missingness, it has at least 20 complete rows and (for
group columns) at least 2 levels with 8 or more rows each, and its form is detectable by the
default tests (quadratic and interaction decoys are not).

## 5. Systems under test (Phase 4 & Phase 8)

All VeriData systems run the same pipeline: Phase 1 profile + conservative clean -> Phase 2
exhaustive pair enumeration (no LLM) -> Phase 3 Stage A tests (`benchmark_fast_mode`, no bootstrap
CIs) -> validation with the variant's settings. Stage A results are shared between variants that
use the same test-selection mode; validation is re-run per variant.

| ID | Alias / Variant | Test choice | Multiple-testing correction | Effect-size floor | Validation gates |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `S3` | `veridata_full` | assumption-aware | Benjamini-Hochberg (q <= 0.05) | on | assumption + trivial gates on |
| `S2` | `veridata_nocorrection` | assumption-aware | none (raw p < 0.05) | off | gates on |
| `A1` | `bh_only` | naive | Benjamini-Hochberg | off | gates on |
| `A2` | `floor_only` | naive | none (raw p < 0.05) | on | gates on |
| `A3` | `assumption_only` | assumption-aware | none (raw p < 0.05) | off | gates on |
| `A4` | `naive_tests` | naive (Welch t / ANOVA / Pearson / chi-square) | Benjamini-Hochberg | on | gates on |
| `A5` | `bonferroni`, `holm`, `by` | assumption-aware | respective method | on | gates on |
| `A6a` | `full_minus_floor` | assumption-aware | Benjamini-Hochberg | off | gates on |
| `A6b` | `full_minus_gates` | assumption-aware | Benjamini-Hochberg | on | assumption + trivial gates off |
| `N0` | `naive_raw` | naive | none | off | gates on |
| `S1a` | `llm_summary_standard`, `llm_summary_careful` | LLM only (schema + `describe()` + sample, no code) | LLM self-disciplined | LLM self-disciplined | n/a |
| `S1b` | `llm_code_standard`, `llm_code_careful` | LLM + restricted Python sandbox (<= 6 turns) | LLM self-disciplined | LLM self-disciplined | n/a |

### LLM-only fairness rules & budget

- **Models & providers**: Primary LLM = `configs/default.yaml` (`gemini-2.5-flash` when `GEMINI_API_KEY` is configured; `claude-sonnet-4-5` when `ANTHROPIC_API_KEY` is configured). Model version is logged in `outputs/eval/run_manifest.json`.
- **Prompts**: Frozen versioned prompts in `configs/prompts/eval_llm_summary_{standard,careful}_v1.txt` and `eval_llm_code_{standard,careful}_v1.txt`. Both instruct the analyst to consider multiple testing, avoid spurious discoveries, and use exact schema names.
- **Data access**: Both `S1a` and `S1b` see only `data.csv` (or the cleaned CSV in E5) with neutral column names (`v01`, ...), no truth metadata, and no suite hints. `S1b` runs in a sandboxed subprocess with `pandas`, `numpy`, `scipy.stats`, and `math`.
- **Repeats & aggregation**: On synthetic benchmarks, `R = 5` repeats at `T = 0.7` (plus one `T = 0.0` reference run); on real datasets (E5), `R = 3` repeats. Per-dataset metrics are averaged across repeats *before* dataset-level bootstrap CIs or paired Wilcoxon tests so repeats are never treated as independent datasets.
- **Output parsing & hallucinated columns**: Findings are returned in closed Pydantic JSON `{col_a, col_b, direction_sign?, higher_group?, p_value?, effect_size?, claim}`. Canonical unordered pairs are mapped automatically; pairs referencing columns not in `df.columns` count as false discoveries (`unknown_column`) and are logged in `hallucinated_columns`.
- **Budget cap**: `eval.max_cost_usd = 15.0` hard cap enforced by `CostTracker` with disk caching (`outputs/eval/` and `.cache/llm/`) so interrupted runs resume cleanly.

## 6. Matching rule

Unit of evaluation: an **unordered column pair**. Several reports of the same pair count once.

For each reported pair:

1. Gray pair -> ignored.
2. Null pair -> **false discovery**.
3. Unknown column name (not in the dataset) -> **false discovery**.
4. True pair:
   - If the system reports a direction **and** the truth has one, they must agree, otherwise it is
     a **false discovery** (wrong sign / wrong group).
   - Direction is only checked where it is well defined: the sign for numeric-numeric pairs, and
     the higher group for a numeric column against a **2-level** group column. Other true pairs
     count as hits whenever the pair is right.
   - Group labels are compared after normalising numbers written as text ("1.0" = "1").

Primary metric: direction checked when reported (`direction_mode="if_reported"`).
Secondary metric: pair only (`direction_mode="ignore"`). Both are always reported.

## 7. Metrics & statistical comparisons

Per dataset: reported, TP, FP, FN, recall, precision, FDP, false discoveries on null pairs,
false discoveries from wrong direction, false discoveries from unknown columns.

- **FDP** = FP / (TP + FP); a dataset with no reports has FDP = 0.
- **FDR** = mean FDP over all datasets (headline). Mean FDP over datasets with >= 1 report is
  shown too.
- **Recall** = mean of per-dataset recall over *testable* true pairs (datasets with >= 1 testable
  truth); micro-averaged recall and recall over all true pairs are secondary.
- **Precision** = TP / (TP + FP), averaged over datasets with >= 1 report.
- **FWER on zero-effect datasets** = share of the zero-effect datasets (no planted edges) with at
  least one **false** discovery.
- **Uncertainty & paired tests:** 95% percentile bootstrap CIs over datasets (2,000 resamples, fixed seed = 0); paired two-sided Wilcoxon signed-rank tests on per-dataset FDP and recall differences (`S3` vs `S2`, `S1a`, `S1b`).
- **Pre-registered primary hypothesis & falsification criterion:**
  - *Supported* if `S3` (`veridata_full`) achieves `FDR <= 0.06`, significantly lower FDP than `S2`, `S1a`, and `S1b` (or lower point FDR than any available LLM baseline), and recall >= `0.80 * recall(S2)` on medium/large effects at `n >= 300`.
  - *Falsified* if `S3` exceeds `FDR > 0.08` on `core60/test`, or fails to improve FDR over `S2`/`S1b`, or drops below `0.80 * recall(S2)` on medium/large effects at `n >= 300`.

## 8. Phase 8 Experiments (E1-E8)

- **E1 (Main benchmark):** `S1a`, `S1b`, `S2`, `S3` on `core60` (test split once frozen). Includes alpha sweep `alpha in {0.01, 0.02, 0.05, 0.10, 0.15, 0.20}`, stratifications, and q-calibration.
- **E2 (Ablations):** `S3`, `S2`, `A1`-`A6`, `naive_raw` on `core60`, with marginal component deltas and targeted strata (`n = 5000`, non-normal distributions).
- **E3 (Calibration summary):** Phase 4 Type-I error (`1,000` reps/cell + `12,000` re-run on noisy cell), BH vs BY under correlated dependence (`rho in {0.3, 0.6, 0.9}`), and analytic vs empirical power.
- **E4 (Number correctness):** Independent recomputation (`src/veridata/evaluation/independent_recompute.py`, zero imports from `veridata.stats`/`validation`/`reporting`) + Phase 5 `verify_text` on VeriData reports and LLM claims. Tolerances: counts exact; percentages +/- 0.5 pp; continuous stats/effects +/- 1% relative (or +/- 0.005 when `|true| < 0.5`); p-values `|log10(p_claim) - log10(p_true)| <= 0.3` or both `< 0.001`.
- **E5 (Real datasets):** `insurance`, `telco_churn`, `heart_disease`, `student_performance`, `bank_marketing` evaluated against pre-registered `configs/eval/reference_findings/<dataset>.yaml`, plus permuted-column nulls (`K = max(5, ceil(0.25 * p))`, 20 seeds; 5 seeds on `bank_marketing` `n > 20k`), 10 injected noise columns, 20 split-half replications, 20 bootstrap Jaccard stability resamples, and blind human qualitative sheets.
- **E6 (Test-selection accuracy):** Acceptable-test oracle table:
  - `NUM_BINARY` / `NUM_CATEGORICAL`: normal or (`n_per_group >= 50` and `|skew| <= 2.0`) -> `{welch_t/welch_anova}` (and nonparametric acceptable when borderline); non-normal small-n or extreme skew -> `{mann_whitney_u/kruskal_wallis}`.
  - `NUM_NUM`: ties > 50% or `n < 30` or heavy skew/outliers -> `{spearman}`; normal/large-n moderate skew -> `{pearson, spearman}`.
  - `CAT_CAT`: 2x2 with expected >= 5 & `n >= 40` -> `{chi_square}`; 2x2 sparse -> `{fisher_exact}`; r x c Cochran satisfied -> `{chi_square}`, else `{monte_carlo_chi_square}`.
  - Consequence-based accuracy: calibration size in `[0.04, 0.06] +- 2 SE` and power >= 90% of best alternative.
- **E7 (Chat evaluation):** 85 single-turn questions (`tests/gold/chat_questions.jsonl`) + 12 multi-turn conversations (`configs/eval/chat_multiturn.jsonl`, 39 turns) across `insurance`, `telco_churn`, `heart_disease`, measuring intent/argument accuracy, independent numeric accuracy, `verify_text` rate, causal lint violations, clarification rate, guardrail refusal rate, follow-up executability, duplicate suppression, and comparison vs plain LLM CSV chat baseline.
- **E8 (Robustness):** End-to-end messy pipeline on `data/synthetic/messy_{light,_,heavy}_dataset.csv` vs `base_truth.json`, corrupted 12-dataset `core60` subset vs clean counterparts, plus edge cases (`n=40, p=10` and `n=500, p=80`).

## 9. What is tuned and what is not

- **Tuned (dev only):** one multiplier applied to all effect-size floors (`{0.5, 0.75, 1.0, 1.25, 1.5}`). Result: `1.0` kept (`configs/tuned_defaults.yaml`).
- **Not tuned:** `alpha = 0.05`, the BH method, `large_n_clt`, `extreme_skew`, minimum sample sizes, the generator, the matching rule, and every definition in this file.

## 10. Phase 8 procedure (after the freeze)

1. Both partners review this file, reference findings, and prompts; change `DRAFT` to `FROZEN` in the status line and tag `eval-protocol-frozen`.
2. `veridata bench gen --suite core60 --split test --confirm-final`
3. `veridata bench run-all-variants --suite core60 --split test --confirm-final`
4. `veridata eval run --experiment all --suite core60 --split test --confirm-final`
5. `veridata final-report`
6. Report the test numbers once. Do not change code or settings because of them.

## 11. Known limitations of the benchmark

- Synthetic data cannot capture all real-world structure (measurement error, time trends, clustered rows). Real datasets are covered separately in E5.
- Only one seed per scenario in each split; CIs are wide (`docs/benchmark_dev_results.md`).
- Only 12 zero-effect datasets, so the FWER estimate is coarse; the calibration experiments use thousands of null datasets to compensate.
- Public Kaggle/UCI datasets may appear in LLM pretraining corpora (contamination advantage for S1a/S1b in E5).
