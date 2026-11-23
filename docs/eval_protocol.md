# VeriData evaluation protocol (Phase 4 → Phase 8)

**Status: DRAFT** — written in Phase 4. Both partners review it, then change `DRAFT` to `FROZEN`
in the line above **before any test-split run**. The code refuses `--split test` unless this file is
frozen and `--confirm-final` is passed (`src/veridata/benchmark/suites.py::check_split`).

Everything a Phase 8 run needs is defined here. If a definition here and the code disagree, the
code is a bug: fix the code, not the protocol, after the freeze.

---

## 1. What is being measured

The claim under test: *VeriData reports dataset relationships with a controlled false discovery
rate, while still finding most real, non-trivial relationships.* We measure this on synthetic
datasets where the true relationships are known exactly ("planted truth").

## 2. Datasets (suites)

Defined in `configs/benchmark/suites.yaml` and expanded by `src/veridata/benchmark/suites.py`.
The expanded scenario list is hashed (`suite_hash`) and the hash is stored with every result.

| Suite | Purpose | Size |
| :--- | :--- | :--- |
| `smoke` | CI and quick checks | 6 scenarios × 2 seeds = 12 datasets |
| `core60` | Primary suite | 60 datasets per split |

`core60` design (seeded, `design_seed: 4242`):

- n (rows) ∈ {100, 300, 1000, 5000}; p (columns) ∈ {10, 30, 60}.
- **12 zero-effect datasets**: one per (n, p) cell; 4 of them contain correlated null blocks.
- **48 effect datasets**: every (n, p, k) cell with k ∈ {3, 8} planted effects gets 2 of the 4
  strengths {small, medium, large, mixed}, rotated so each strength appears 12 times.
- Distribution shape (normal, lognormal, t3, zero-inflated, bimodal, mixed), group imbalance,
  missingness (0% or 5% MCAR on half the columns), null blocks, quadratic and interaction decoys
  and common-cause confounders are assigned by seeded rotation.

### Generator (summary)

- Two-layer structural model: root columns and a few latent factors feed child columns; each child
  has one parent edge (linear, monotonic, binary shift, categorical shift or category-category).
- Effect sizes are set on **population-standardised** variables, so the planted Pearson r,
  Cohen's d, η² and Cramér's V are exact; Spearman targets are calibrated by simulation.
- Column names are neutral (`v01`, `v02`, …) and level names are `L0`, `L1`, …; columns and rows
  are shuffled, so names and order leak nothing.

## 3. Seeds and splits

| Split | Seeds | Used for |
| :--- | :--- | :--- |
| `dev` | base 0 (seed = 0 + 10·i + r) | debugging, tuning, all Phase 4–7 work |
| `test` | base 10000 (seed = 10000 + 10·i + r) | **once**, in Phase 8, after the freeze |

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

Dependence is measured as |Spearman ρ| (numeric–numeric), bias-corrected rank η (numeric–group)
and bias-corrected Cramér's V (group–group), computed on a 20,000-row population draw.

A true pair is **testable** when, after missingness, it has at least 20 complete rows and (for
group columns) at least 2 levels with 8 or more rows each, and its form is detectable by the
default tests (quadratic and interaction decoys are not).

## 5. Systems

All VeriData systems run the same pipeline: Phase 1 profile + conservative clean → Phase 2
exhaustive pair enumeration (no LLM) → Phase 3 Stage A tests (`benchmark_fast_mode`, no bootstrap
CIs) → validation with the variant's settings. Stage A results are shared between variants that
use the same test-selection mode; validation is re-run per variant.

| System | Test choice | Multiple-testing correction | Effect-size floor |
| :--- | :--- | :--- | :--- |
| `veridata_full` | assumption-aware | Benjamini–Hochberg | on |
| `veridata_nocorrection` | assumption-aware | none (raw p < 0.05) | off |
| `assumption_only` | alias of `veridata_nocorrection` | | |
| `bh_only` | naive | Benjamini–Hochberg | off |
| `floor_only` | naive | none | on |
| `naive_tests` | naive (Welch t / ANOVA / Pearson / chi-square always) | Benjamini–Hochberg | on |
| `naive_raw` | naive | none | off |
| `bonferroni`, `holm`, `by` | assumption-aware | that method | on |

Phase 8 adds an LLM-only system through the same `SystemOutput` interface.

## 6. Matching rule

Unit of evaluation: an **unordered column pair**. Several reports of the same pair count once.

For each reported pair:

1. Gray pair → ignored.
2. Null pair → **false discovery**.
3. Unknown column name (not in the dataset) → **false discovery**.
4. True pair:
   - If the system reports a direction **and** the truth has one, they must agree, otherwise it is
     a **false discovery** (wrong sign / wrong group).
   - Direction is only checked where it is well defined: the sign for numeric–numeric pairs, and
     the higher group for a numeric column against a **2-level** group column. Other true pairs
     count as hits whenever the pair is right.
   - Group labels are compared after normalising numbers written as text ("1.0" = "1").

Primary metric: direction checked when reported (`direction_mode="if_reported"`).
Secondary metric: pair only (`direction_mode="ignore"`). Both are always reported.

## 7. Metrics

Per dataset: reported, TP, FP, FN, recall, precision, FDP, false discoveries on null pairs,
false discoveries from wrong direction.

- **FDP** = FP / (TP + FP); a dataset with no reports has FDP = 0.
- **FDR** = mean FDP over all datasets (headline). Mean FDP over datasets with ≥ 1 report is
  shown too.
- **Recall** = mean of per-dataset recall over *testable* true pairs (datasets with ≥ 1 testable
  truth); micro-averaged recall and recall over all true pairs are secondary.
- **Precision** = TP / (TP + FP), averaged over datasets with ≥ 1 report.
- **FWER on zero-effect datasets** = share of the zero-effect datasets (no planted edges) with at
  least one **false** discovery. Correlated null blocks create real (true) pairs, so a report on a
  block pair is not counted as an error.
- Stratified recall by effect size bin, form, n, p, distribution shape; power table by
  (form, n, effect bin).
- q-value calibration: false fraction of reported findings by q-value bin.
- **Uncertainty:** 95% percentile bootstrap CIs over datasets, 2,000 resamples, fixed seed.

## 8. Calibration experiments (no planted-truth datasets needed)

1. **Type I error of the selected tests:** 5 distribution families × n ∈ {20, 50, 200, 1000} ×
   relationship (numeric–binary, numeric–4-group, numeric–numeric, 2×2 and 3×4 tables) ×
   balanced / 90-10. Pass: empirical size in [0.04, 0.06] (± 2 Monte Carlo SE) for ≥ 90% of cells
   and no cell above 0.075 (a cell above 0.075 is re-run with ≥ 10,000 reps before it counts as a
   failure).
2. **FDR of BH under dependence:** global null (independent and correlated blocks with
   ρ ∈ {0.3, 0.6, 0.9}) and sparse truth with blocks; p ∈ {20, 60, 120}; BH, BY, Bonferroni,
   Holm, none.
3. **Power check:** Welch t and Pearson empirical power vs analytic power.

## 9. What is tuned and what is not

- **Tuned (dev only):** one multiplier applied to all effect-size floors, grid
  {0.5, 0.75, 1.0, 1.25, 1.5}. Objective: highest recall with FDR ≤ 5%. If the best value is within
  one grid step of 1.0, keep 1.0 (conventional floors). Result: 1.0 was kept
  (`configs/tuned_defaults.yaml`).
- **Not tuned:** α = 0.05, the BH method, `large_n_clt`, `extreme_skew`, minimum sample sizes,
  the generator, the matching rule and every definition in this file.

## 10. Phase 8 procedure (after the freeze)

1. Both partners review this file, the scenario grid and the matching rule; change `DRAFT` to
   `FROZEN` in the status line and commit.
2. `veridata bench gen --suite core60 --split test --confirm-final`
3. `veridata bench run-all-variants --suite core60 --split test --confirm-final`
4. `veridata bench eval --suite core60 --split test --confirm-final`
5. Report the test numbers once. Do not change code or settings because of them.

## 11. Known limitations of the benchmark

- Synthetic data cannot capture all real-world structure (measurement error, time trends,
  clustered rows). Real datasets are covered separately in Phase 8.
- Only one seed per scenario in each split; CIs are wide (see `docs/benchmark_dev_results.md`).
- Only 12 zero-effect datasets, so the FWER estimate is coarse; the calibration experiments use
  thousands of null datasets to compensate.
