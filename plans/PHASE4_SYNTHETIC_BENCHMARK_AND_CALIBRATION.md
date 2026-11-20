# PHASE 4 — Synthetic Benchmark with Planted Truth, Metrics, Calibration

> Prerequisite reading: `00_MASTER_PLAN.md` (Sections 2, 5, 8), `PHASE3_STATISTICAL_TOOLS_AND_VALIDATION.md` (`run_all`, config switches).
> This phase builds the **measuring instrument** for the project's central claim. If the benchmark, the matching rule, or the metrics are wrong, Phase 8's results are meaningless. Build carefully; freeze the protocol before Phase 8 runs.
> This phase does **not** call LLMs (the LLM-only baseline is in Phase 8). Everything here is deterministic and offline.

---

## 1. Goals

1. A **generator** that produces datasets with **known ground-truth dependence structure** across a controlled grid: sample size, number of columns, number and strength of true effects, relationship types, distribution shapes, correlated noise, missingness, group imbalance, and messiness.
2. A **truth file** per dataset, listing which column pairs are truly dependent (including *induced* dependence), with direction.
3. A **matcher** that decides whether a reported finding corresponds to a true dependence (precise, documented rule).
4. **Metrics**: recall, precision, FDR, FWER on null datasets, false-positive counts, power curves.
5. A **benchmark runner** that runs any "system" (callable returning findings) over the suite in parallel and caches results.
6. **Calibration experiments** that check the tool library's Type I error and the BH procedure's FDR under dependence.
7. **Threshold tuning on a development split** (effect-floor defaults), with a held-out **test split** touched only once in Phase 8.

### Out of scope
LLM-only baseline and the final comparison (Phase 8). Real Kaggle data (Phase 8).

---

## 2. Design principles

- **Ground truth by construction** (structural equations), not by post-hoc statistics.
- **Truth includes induced dependence.** If X→Y and X→Z, then Y and Z are dependent; reporting Y–Z is a *true* discovery under the association definition. Truth is computed by graph reachability rules (Section 4), not just by the list of planted edges.
- **Dev/test split by seed.** Seeds 0-999 = development (tune thresholds, debug); seeds 10000-10999 = test (frozen, used once in Phase 8). The code enforces by requiring `split="dev"|"test"`; `test` requires an explicit `--confirm-final` flag.
- **Reproducible:** each dataset is a pure function of `(scenario_config, seed)`; file hashes are stable.
- **Realism through messy variants**, but main metrics are computed on *clean-ish* data (Phase 1 cleaning is applied to messy variants first so the metric reflects the whole pipeline in E7).

---

## 3. Repository additions (all under `src/veridata/benchmark/`)

```
generator.py   # make_dataset(scenario, seed) -> (df, truth)
dag.py         # structural equation model (SEM) builder + dependence reachability
truth.py       # GroundTruth pydantic models, I/O
matcher.py     # match_findings(findings, truth, rule) -> MatchResult
metrics.py     # per-dataset and aggregate metrics, bootstrap CIs over datasets
runner.py      # run_system_over_suite(system, suite, n_jobs, cache) -> results table
calibration.py # type I error + FDR-under-dependence experiments
tuning.py      # effect-floor tuning on dev split
suites.py      # named suites (smoke, core60, full) + dev/test seed lists
```
Configs: `configs/benchmark/suites.yaml`, `configs/benchmark/scenarios.yaml`.
Outputs: `outputs/benchmark/<suite>/<split>/<scenario_id>__seed<k>/{data.csv, truth.json, scenario.json}`; `outputs/benchmark/<suite>/<split>/results/<system>/...`.

---

## 4. Generator design (`generator.py`, `dag.py`)

### 4.1 Structural model
Each dataset is generated from a DAG of latent/observed variables.

**Column roles:**
- **Root/noise variables:** independent draws from a chosen distribution family.
- **Planted effect variables:** generated from parents with specified functional form and effect size.
- **Noise columns:** pure noise (independent of everything) — the stress test for BH.
- **Correlated-null blocks:** groups of columns that are correlated with each other through a *shared latent factor* that has no relationship with any other column. Purpose: stress BH's dependence assumption (PRDS). Pairs between a block column and any outside column are truly null, but their p-values are positively correlated because the block columns move together. Pairs *within* a block are truly dependent by construction, so they must appear in the truth list as `form: "latent_factor"` and the matcher treats them like any other true pair. Controlled by the scenario flag `null_blocks: {n_blocks, block_size, within_corr}`.

**Relationship types to plant (each maps to a Phase 3 relationship):**
| Planted form | Example | Phase 3 relationship | Effect parameter |
|---|---|---|---|
| Linear numeric | Y = βX + ε | NUM_NUM | target |r| ∈ {0.1, 0.2, 0.3, 0.5} |
| Monotonic nonlinear | Y = exp(βX)+ε or X³ | NUM_NUM | target Spearman ρ |
| Binary → numeric shift | Y = δ·G + ε, G binary | NUM_BINARY | Cohen's d ∈ {0.2, 0.5, 0.8} |
| Categorical → numeric | Y mean differs by k levels | NUM_CATEGORICAL | η² ∈ {0.02, 0.06, 0.14} |
| Categorical ↔ categorical | joint probability table with Cramér's V | CAT_CAT | V ∈ {0.1, 0.2, 0.3, 0.5} (adjusted for df*) |
| Non-monotonic (quadratic/U-shape) | Y = X² + ε | NUM_NUM (default tests *should miss* it) | dcor-based |
| Interaction-only (XOR-like) | Y depends on X1×X2 only | not detectable pairwise | marks "undetectable by design" |

Non-monotonic and interaction effects are **flagged `detectable_by_default_tests: false`** and excluded from the primary recall denominator but reported separately (honest limitation analysis, and shows the optional dcor test's value).

**Distribution shapes** for numeric noise/ε and roots: normal, lognormal (skewed), student t(3) (heavy tails), zero-inflated (30% zeros + positive part), bimodal mixture. Per-scenario setting; also mixed ("realistic": a random mix across columns).

**Categorical generation:** levels count ∈ {2, 3, 5, 8}; level frequencies from Dirichlet (balanced or imbalanced, minority down to 5-10%).

**Missingness:** MCAR at rate r ∈ {0, 0.05, 0.2} per column (random subset of columns); optional MAR (missingness in Y depends on observed X) — flag; truth is unaffected.

**Messiness (optional layer):** apply Phase 1's messy injector (`messy_injector.py`) *after* generating, with the manifest linked; used for E7 robustness. Core suite is clean.

### 4.2 Scenario config
```yaml
scenario_id: n300_p30_k5_med
n_rows: 300
n_cols: 30                     # total observed columns incl. effects and noise
n_effects: 5                   # planted direct effects (edges)
effect_mix: {linear: 0.3, monotonic: 0.1, binary_shift: 0.2, categorical_shift: 0.2, cat_cat: 0.2}
effect_strength: medium        # small|medium|large|mixed — maps to the parameter grids above
dist: mixed                    # normal|lognormal|t3|zero_inflated|bimodal|mixed
null_blocks: {n_blocks: 2, block_size: 4, within_corr: 0.6}
missing_rate: 0.05
imbalance: moderate            # affects binary/categorical frequencies
col_type_mix: {numeric: 0.55, binary: 0.15, categorical: 0.30}
n_nonlinear_decoys: 1          # non-monotonic effects (not in primary recall)
n_interaction_decoys: 0
confounder: none               # none|common_cause (creates induced dependence)
messy: false
```

### 4.3 Procedure (deterministic given seed)
1. Seed `np.random.default_rng(seed)`; derive sub-seeds for each component.
2. Allocate columns by `col_type_mix`; name them semantically neutral and non-leaking (`v01, v02, ...` with a random permutation of roles so position doesn't reveal truth; also provide realistic-name variant `use_realistic_names` for LLM baselines? — **no**: LLM baselines may exploit name semantics; keep neutral names).
3. Build the DAG: choose effect edges among columns respecting type compatibility (e.g., a binary parent → numeric child). Optionally add `common_cause` confounders (an observed or latent variable affecting 2+ columns).
4. Generate roots → children in topological order using the structural equations calibrated to hit the target effect size **approximately in the population**: calibrate by solving analytically where possible (e.g., for linear: β so that population r = target given variances; for binary shift: δ = d·σ_ε), else by a fast calibration loop (simulate n=50,000 once per (form, target), cache calibrations in `configs/benchmark/calibration_cache.json`).
5. Convert latent variables to final observed types (e.g., thresholds → categories, Bernoulli for binary).
6. Insert missingness; shuffle row order; shuffle column order (seeded).
7. Write `data.csv`, `truth.json`, `scenario.json`.

### 4.4 Truth computation (`dag.py::dependence_closure`)
Truth is a list of **dependent unordered pairs** with attributes:
```json
{
  "pairs": [
    {"col_a":"v03","col_b":"v17","type":"direct","form":"binary_shift",
     "population_effect":{"name":"cohens_d","value":0.5},
     "direction":{"kind":"group_diff","higher_group_of":"v03","level":"1"},  // or {"kind":"sign","value":"+"}
     "detectable_by_default_tests":true,"relationship":"numeric_vs_binary"},
    {"col_a":"v05","col_b":"v09","type":"induced","via":["v03"], ... "population_effect": {"approx": 0.15}, "detectable_by_default_tests":true}
  ],
  "null_pairs_count": 312,
  "n_columns": 30,
  "n_pairs_total": 435,
  "notes": {...}
}
```
- **Direct** pairs: planted edges.
- **Induced** pairs: any two columns sharing an ancestor/descendant path (d-connected without conditioning) with non-negligible implied dependence. Compute from the DAG: pair is dependent if one is an ancestor of the other, or they share a common ancestor, **and** implied population effect ≥ 0.05 (compute via simulation of large n from the SEM once per scenario instance: `n_truth=20000`; threshold pairs by an exact-ish independence criterion (see below)); pairs below 0.05 are recorded as `"weak_induced"` and **excluded from both numerator and denominator** (neither counted as true discovery nor false discovery — "gray zone"; reported as separate count). Rationale: a theoretically nonzero but tiny induced dependence shouldn't create arbitrary false-discovery labels.
- Within `null_blocks`: within-block pairs are direct true dependences (`form: "latent_factor"`).
- **Truth for evaluation**: `true_pairs` (dependent, ≥ threshold) and `null_pairs` (independent by DAG, no path). `gray_pairs` (weak induced) ignored.
- **Direction** is always recorded (sign for numeric-numeric; higher group for binary/categorical shifts; for cat-cat direction is not required).
- Sanity self-test: generate 20,000-row version, compute Phase-3-free empirical stats (plain numpy), verify truth pairs show empirical dependence and null pairs do not (|r|<0.02 etc.) → `truth_selfcheck()` run in tests for all scenario types.

### 4.5 Suites (`suites.py`)
- **`smoke`** (CI, fast): 6 scenarios × 2 seeds.
- **`core60`** (primary): grid over n ∈ {100, 300, 1000, 5000} × p ∈ {10, 30, 60} × k ∈ {0, 3, 8} (k=0 are **pure-null datasets**) × strength ∈ {small, medium, large, mixed} sampled to ~60 distinct scenarios (Latin-hypercube-style design, seeded), at least **12 pure-null datasets** spanning n and p and including null_blocks, heavy-tailed and zero-inflated shapes. Each scenario gets 1 seed in dev and 1 seed in test (or more if compute allows).
- **`full`**: ~150 datasets incl. missingness variants, imbalance, confounders.
- **`robustness`**: core subset + messy layer (E7).
- Document each suite's definition in `configs/benchmark/suites.yaml`; the suite hash is recorded in results.

---

## 5. Systems interface (what the runner evaluates)

```python
class SystemOutput(BaseModel):
    system_name: str
    findings: list[ReportedFinding]
    n_tests_attempted: int | None
    runtime_s: float
    cost_usd: float | None
    meta: dict

class ReportedFinding(BaseModel):
    col_a: str; col_b: str
    direction: dict | None            # same encoding as truth.direction.kind/value, if the system reports one
    effect: float | None; p_value: float | None; q_value: float | None
    claim_text: str | None
    source_id: str | None

SystemFn = Callable[[pd.DataFrame, dict, int], SystemOutput]    # (df, context, seed)
```
Phase 4 builds adapters for **VeriData variants only**; Phase 8 adds LLM-only. Variants (all via config flags of Phase 3):
`veridata_full`, `veridata_nocorrection` (raw p<alpha, no floor), `bh_only` (BH, no floor, no assumption-aware selection), `floor_only` (no correction, floor on), `assumption_only` (assumption-aware selection, raw p<alpha, no floor), `bonferroni`, `by`, `holm`, `naive_tests` (no fallback: Welch t / ANOVA / Pearson / chi-square always).
Each adapter: run Phase 1 profile+clean (conservative) on the CSV → Phase 2 enumeration (`exhaustive`, `--no-llm`) → Phase 3 with the variant config → map `Finding`s with `accepted=True` (variant-defined acceptance) into `ReportedFinding`s.

---

## 6. The matching rule (`matcher.py`) — define precisely, freeze before Phase 8

**Unit of evaluation:** an *unordered column pair* (col_a, col_b). Duplicate reports of the same pair collapse to one.

For each reported finding `f` on pair `P`:
1. If `P ∈ gray_pairs` → ignored (neither TP nor FP).
2. If `P ∈ null_pairs` → **false discovery**.
3. If `P ∈ true_pairs`:
   - If the system reports a direction **and** truth has a direction: direction agrees → **true discovery**; disagrees → **false discovery** (wrong sign/wrong group). VeriData variants always report direction (observed from the test); LLM-only outputs may omit direction: for those, the **primary** metric ignores direction (true discovery if pair correct) and a **secondary** metric requires direction when reported. Document both.
   - If the system reports no direction: direction ignored (primary).
4. Pair not in any category (should not happen) → error (matcher asserts completeness: every possible pair is classified).

**Recall denominator:** `true_pairs` with `detectable_by_default_tests = true` **and** feasible (i.e., n_pairwise ≥ min_n after missingness, group sizes ok) — "testable truths". Also report recall over *all* true pairs (including undetectable decoys) as a secondary figure.
**Precision / FDP:** TP/(TP+FP) over reported findings; datasets with zero reports: FDP = 0, precision = undefined (excluded from precision mean; counted in `n_empty`).
**Per-dataset metrics:** `n_reported, TP, FP, FN, recall, precision, fdp, fp_on_null_pairs, any_false_discovery (bool)`.
**Aggregate metrics (over datasets):**
- `FDR = mean(fdp)` over all datasets (including those with zero reports as 0) — the standard definition; also report mean FDP over datasets with ≥ 1 report.
- `Recall` as mean of per-dataset recall over datasets with ≥ 1 testable truth; also micro-averaged recall.
- `FWER_null = fraction of pure-null datasets with ≥ 1 reported finding` (target ≤ ~0.05 for BH under global null; this equals the false-positive rate per dataset).
- `Mean FP count on null datasets`.
- Stratified by effect strength (via per-pair `population_effect` bins), by relationship form, n, p, dist shape, null-block presence.
- **Power curves:** recall as function of (n, effect size) per form.
- **Bootstrap CIs over datasets** (resample datasets with replacement, 2,000 resamples, percentile CI) for every aggregate; keep resampling code in `evaluation/stats_utils.py`-compatible form (put in `metrics.py` now, reuse later).
- **Calibration of q-values:** among reported findings with q in bins, empirical false fraction (should be ≲ q) — a reliability-style plot.

---

## 7. Calibration experiments (`calibration.py`)

### 7.1 Type-I error of the *selected* tests (E3a)
For each scenario family {normal, lognormal, t3, zero-inflated, bimodal} × n ∈ {20, 50, 200, 1000} × relationship ∈ {NUM_BINARY, NUM_CATEGORICAL(k=4), NUM_NUM, CAT_CAT(2×2, 3×4)} × imbalance ∈ {balanced, 90/10}: simulate R = 5,000 null datasets (use `fast` mode: Stage A only, no CIs), run **selection + test** exactly as Phase 3, record rejection rate at 0.05 and the p-value distribution. Outputs: table of empirical size (with Monte Carlo SE), QQ plot or histogram of p-values per cell, KS statistic vs uniform. Compare with `naive_tests` (always parametric) to *show* why assumption-aware selection exists. Pass criterion: selected-test empirical size in [0.04, 0.06] for ≥ 90% of cells and no cell above 0.075 (else open a bug/adjust selection rule).

### 7.2 FDR of BH under dependence (E3b)
Scenarios: (a) global null, independent columns; (b) global null with correlated blocks (within_corr 0.3, 0.6, 0.9); (c) sparse truth (5% true) with correlated blocks. p ∈ {20, 60, 120}. Compute empirical FDR/FWER for BH, BY, Bonferroni, Holm, none. Expectation: BH ≈ ≤ 5% under independence; may drift above under strong dependence — **report honestly** and recommend BY if exceeded (documented in the limitations). 

### 7.3 Power sanity
For fixed effect sizes the empirical power of each test vs analytic power (e.g., `statsmodels.stats.power`) should be within tolerance for the parametric tests (Welch t: `TTestIndPower`; Pearson via Fisher z power). Serves as an implementation check.

### 7.4 Runtime budget
Time the pipeline vs (n, p); write `outputs/benchmark/runtime.csv`; used to plan Phase 8 compute.

---

## 8. Threshold tuning (`tuning.py`) — dev split only

Tunable (documented, bounded) parameters: effect-floor thresholds, `large_n_clt`, `extreme_skew`. Procedure: grid search over a small, pre-declared grid on the **dev split of core60**, objective = maximize recall subject to mean FDP ≤ 0.05 on dev, tie-break by simplicity (closest to Cohen conventions). Output `configs/tuned_defaults.yaml` with the chosen values and a `tuning_report.md` (grid, results, chosen). **If the tuned values equal the conventions or are within one grid step, keep the conventional values** (avoid overfitting; prefer principled defaults). The test split must not be touched here (code asserts `split == "dev"`).

---

## 9. CLI

```
veridata bench gen --suite core60 --split dev [--n-jobs N]
veridata bench run --suite core60 --split dev --system veridata_full [--no-cache]
veridata bench run-all-variants --suite core60 --split dev
veridata bench eval --suite core60 --split dev --systems veridata_full,veridata_nocorrection,...
veridata bench calibrate --experiment type1|fdr_dependence|power
veridata bench tune --suite core60
veridata bench truth-selfcheck
```
`--split test` requires `--confirm-final` and refuses if `docs/eval_protocol.md` is not marked `FROZEN`.

Result caching key: `hash(system config, scenario, seed, code_version)`; stored as JSON per dataset.

---

## 10. Tests

- **Generator:** determinism (same seed → identical CSV hash); schema (n_rows, n_cols as requested); column type mix; calibration of effects (large-n empirical effect within ±15% of target for each form); missingness rate; neutral column names; null datasets contain zero planted pairs and `true_pairs == []`.
- **Truth:** `truth_selfcheck` across all scenario forms; induced pairs have empirical dependence in large-n draw; null pairs don't; gray pairs identified; completeness (every pair classified exactly once).
- **Matcher:** hand-built truth + finding lists covering TP/FP/gray/duplicates/wrong-direction/no-direction; unordered pair handling (a,b)==(b,a); every classification path.
- **Metrics:** hand-computed small examples for recall, precision, FDP, FWER; empty-report conventions; stratification; bootstrap CI reproducibility.
- **Runner:** caching hit/miss; parallel determinism; failure of one dataset doesn't kill the suite (recorded as error, excluded from metrics with count).
- **Calibration:** smoke versions (R=200) run in CI; full versions marked slow.
- **Variants:** `bh_only`/`bonferroni` etc. produce different accepted sets on a fixture where the difference is known by construction.
- **Dev/test guard:** test split requires flag and FROZEN protocol.

---

## 11. Milestones

| ID | Work | Est. |
|---|---|---|
| P4-M0 | Contracts (`truth.py`, `SystemOutput`), configs, CLI stubs | 0.5 d |
| P4-M1 | SEM generator: roots, effect forms with calibration, categorical/binary conversion, missingness | 2 d |
| P4-M2 | DAG + dependence closure + truth file + `truth_selfcheck` | 1.5 d |
| P4-M3 | Suites + generation CLI + caching | 0.5 d |
| P4-M4 | Matcher + metrics + bootstrap CIs | 1.5 d |
| P4-M5 | Systems adapters (VeriData variants) + runner | 1 d |
| P4-M6 | Calibration experiments (type I, FDR under dependence, power) | 1.5 d |
| P4-M7 | Tuning + dev-split evaluation report + freeze `docs/eval_protocol.md` draft | 1 d |

(The generator and matcher can begin before Phase 3 finishes; the runner/adapters need Phase 3.)

---

## 12. Deliverables / outputs

- `outputs/benchmark/core60/dev/...` datasets, truths.
- `outputs/benchmark/core60/dev/results/<system>/*.json`, `metrics.csv`.
- `outputs/benchmark/calibration/{type1.csv, type1_pvalue_hist.png, fdr_dependence.csv, power.csv}`.
- `outputs/benchmark/tuning/tuning_report.md`, `configs/tuned_defaults.yaml`.
- `docs/eval_protocol.md` (draft here; frozen at the start of Phase 8): suite definitions, matching rule, metrics, systems, seeds, statistical procedures, what will and will not be tuned.
- Dev-split results table comparing VeriData variants (the first evidence for the claim; used to debug, not to report as final).

---

## 13. Acceptance criteria

- [ ] `core60` and `smoke` suites generate deterministically; truth self-check passes for every scenario form.
- [ ] Matcher classifies every pair exactly once; all matcher tests pass.
- [ ] Metrics reproduce hand-computed examples; bootstrap CIs reproducible with seed.
- [ ] Type-I calibration experiment meets the criterion in 7.1, or deviations are documented with a fix/limitation.
- [ ] On the **dev** split: `veridata_full` mean FDP ≤ 0.08 (target ≤ 0.05) and `veridata_nocorrection` FDP clearly higher; global-null FWER for `veridata_full` ≤ 0.10 (target ≈ 0.05); recall for `veridata_full` ≥ 0.6 on medium/large effects at n ≥ 300. If not met: investigate (selection rules, floor, dependence) before moving on. These are sanity targets, not final claims.
- [ ] Dependence experiment completed; BH vs BY behavior documented.
- [ ] `tuned_defaults.yaml` produced (or documented decision to keep conventional values).
- [ ] `docs/eval_protocol.md` drafted with every definition needed for Phase 8.
- [ ] Test split untouched (no files under `.../test/results`).

---

## 14. Handoff

- **To Phase 8:** suites, truths, matcher, metrics, runner, variant adapters, calibration results, frozen protocol. Phase 8 adds the LLM-only system adapter implementing `SystemFn`.
- **To Phase 5/6:** none directly, but the tuned defaults feed the config.

---

## 15. Pitfalls

1. **Mislabeling induced dependence as false discoveries.** Without closure over the DAG, the FDR will be wrongly inflated. Test it.
2. **Leakage through naming or order.** Use neutral names and shuffle columns.
3. **Tuning on the test split.** The guard exists for a reason.
4. **Effect size mismatch.** If the realized effect is far from the target, the stratified power curves lie. The calibration test is mandatory.
5. **Too few null datasets** makes FWER estimates noisy: ≥ 12 pure-null datasets plus calibration with thousands of nulls.
6. **Directional matching hides errors.** Keep both primary (pair-only) and secondary (direction-aware) metrics.
7. **Overfitting the generator to the tests' assumptions** (e.g., only normal data). Include heavy-tailed, skewed, zero-inflated, imbalanced and missing-data scenarios, and state in limitations that synthetic data cannot capture all real-world structure (Phase 8 covers real data).
8. **Compute blow-up.** 60 datasets × 10 variants × 700 tests. Use Stage A-only fast mode (no bootstrap CIs) in benchmark runs (`bootstrap_resamples_benchmark`), cache aggressively, parallelize by dataset.

---

## 16. Human tasks

- Review the scenario grid and the matching rule (a short meeting-level sign-off), then freeze `docs/eval_protocol.md` before Phase 8 test-split runs.
- Spot-check 3 generated datasets visually (plots of planted effects) to confirm they look like what the truth says.
- Decide compute budget (cores/time) for the full suite.
