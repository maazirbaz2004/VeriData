# PHASE 3 — Statistical Tool Library & Validation Layer

> Prerequisite reading: `00_MASTER_PLAN.md` (esp. Sections 5, 6, 7, 8) and `PHASE2_HYPOTHESIS_GENERATION.md` (contract: `HypothesisSet`).
> This is the **scientific core** of VeriData. Correctness here matters more than anywhere else. Every function must be validated against reference implementations and hand-computed examples.
> No LLM calls anywhere in `stats/` or `validation/` (P1, CLAUDE.md rule 2).

---

## 1. Goal and scope

1. Build the **fixed tool library**: given a `Hypothesis` and a dataframe, select an appropriate test, check assumptions, run the test (SciPy/Statsmodels), compute effect size and confidence interval, and return a `TestResult`.
2. Build the **validation layer**: apply multiple-testing correction (Benjamini-Hochberg) across the whole family, enforce an effect-size floor, handle assumption violations and degenerate/derived relationships, and emit a `ValidationDecision` with an explicit rejection reason for every non-accepted test.
3. Build the **ledger**: an append-only record of every test run, so the family is honest across batch and chat (Phase 6).

### In scope
Test registry and selection rules, assumption checks, effect sizes with CIs, BH (plus BY/Holm/Bonferroni for ablation), validator with reason codes, derived/trivial relationship detection, ledger, batch runner with parallelism, JSON outputs, thorough tests.

### Out of scope
Report text and charts (Phase 5), LangGraph (Phase 6), benchmark generation/metrics (Phase 4, though calibration experiments use this library), regression/adjusted tests (optional stretch, Section 14).

---

## 2. Architecture

```
HypothesisSet ──► runner.run_tests() ──► [TestResult ...] ──► validator.validate() ──► [ValidationDecision ...] ──► [Finding ...]
                    │   (per hypothesis)                         │
                    ├─ selection.select_test()                   ├─ correction.apply_correction()  (BH over family)
                    ├─ assumptions.check_*()                     ├─ rules.effect_floor(), rules.assumption_gate(), rules.trivial_gate()
                    ├─ tests_*.run_*()                           └─ ledger.append()
                    └─ effect_sizes.*, intervals.*
```

**Two-stage computation for speed (important):**
- **Stage A (all tests):** prepare data, assumption checks (cheap), select test, compute statistic, **p-value**, and **point estimate of effect size**. No bootstrap.
- **Stage B (candidates only):** after BH, compute expensive **confidence intervals** (bootstrap, permutation refinements) only for tests with `q ≤ alpha` or raw `p < 0.10` (configurable `ci_candidate_p`). CIs are needed for reporting and strict mode, not for rejected tests. This keeps 1,000+ test runs fast.

---

## 3. Data preparation per test (`stats/runner.py::prepare_inputs`)

Given `Hypothesis` and cleaned df:
- Select the two columns; drop rows with NaN in either (pairwise deletion); record `n_used`.
- **NUM_BINARY / NUM_CATEGORICAL:** group by the grouping column; groups with n < `min_group_n` are dropped (recorded as `dropped_levels` in `warnings` and `descriptives`); if < 2 groups remain → status `skipped_infeasible`. Binary means exactly 2 groups; if rare-level dropping leaves 2 groups for a categorical, still treated as NUM_CATEGORICAL→ converted internally to the two-group test (record in selection trace: `"collapsed_to_two_groups"`).
- **NUM_NUM:** convert to float; infinite values → NaN → dropped; if either column has zero variance after dropping → `degenerate`.
- **CAT_CAT:** build contingency table of observed counts after dropping rare levels (n < `min_group_n` marginal) and empty rows/cols; ≥ 2×2 required.
- Return a typed `PreparedData` object; never mutate the input frame.
- Ordinal categoricals: treated as nominal in this version (documented).
- Numeric columns stored as `Int64`/`float64`; booleans converted to categorical strings.

---

## 4. Test library (`stats/`)

All tests: two-sided; seeded RNG (`np.random.default_rng(seed)` derived from config seed + hypothesis id hash, so results are reproducible and independent of execution order).

### 4.1 `NUM_BINARY` — compare a numeric variable between two groups

Candidate tests: **Welch's t-test** (`scipy.stats.ttest_ind(equal_var=False)`), **Mann-Whitney U** (`scipy.stats.mannwhitneyu(alternative='two-sided', method='auto')`, with tie handling).

**Selection rule (documented, deterministic, recorded in `selection_trace`):**
1. Let `n1, n2` be group sizes; compute per-group skewness and excess kurtosis; run Shapiro-Wilk per group if n ≤ `normality_n_max` (else rule on skew/kurtosis only: |skew| < 1 and |excess kurt| < 3 counts as "approximately normal").
2. If both groups approx normal (Shapiro p > 0.01 *or* the skew/kurt rule passes) → **Welch t**. (Welch needs no equal-variance assumption.)
3. Else if both `n ≥ large_n_clt` (default 50) and neither group has |skew| > `extreme_skew` (2.0) → **Welch t** (CLT justification; record).
4. Else → **Mann-Whitney U**. Record `fallback_used = True` when step 4 applied because normality failed.
5. If one group has n < 8 *and* non-normal → Mann-Whitney (small-n: use `method='exact'` when no ties and n1+n2 ≤ 50).
6. If either group has zero variance (all identical) → t undefined → Mann-Whitney; if both groups all-identical and equal → `degenerate`.
7. Equality of variances (Levene, `center='median'`) is **recorded** as an assumption (info/warning) but does not change the choice (Welch handles it). For Mann-Whitney, record that the test is interpreted as a stochastic-dominance/location-shift test only when distribution shapes are similar (warning if Levene rejects and spreads differ markedly).
8. Heavy outliers (> 5% outside 3×IQR in either group) with Welch selected → record warning; selection rule 3 still applies; Welch t is used only if skew condition holds, else MWU.

**Effect sizes:**
- Welch path: **Hedges' g** (bias-corrected Cohen's d using the pooled SD for the *standardizer*; document that with unequal variances d is approximate; also report mean difference). CI: analytic (Hedges & Olkin SE: `se = sqrt((n1+n2)/(n1*n2) + g²/(2(n1+n2-2)))`, normal approx) — validated against bootstrap in tests. Also CI for raw mean difference from Welch's t distribution (Welch-Satterthwaite df).
- MWU path: **rank-biserial correlation** `r_rb = 1 − 2U/(n1 n2)` (sign from group orientation) and **probability of superiority** `P(X1>X2)+0.5P(X1=X2) = U1/(n1 n2)`; CI by **percentile/BCa bootstrap** (`scipy.stats.bootstrap`, stratified resampling within groups, `bootstrap_resamples`). Also report Hodges-Lehmann shift estimate (median of pairwise differences) when n1·n2 ≤ 2.5M, else subsample pairs with fixed seed.
- `comparable_value` for the floor: |g| for Welch; for MWU use |r_rb| mapped to the rank-biserial threshold (do not convert between scales; use separate thresholds per effect type).
- Descriptives: per-group n, mean, sd, median, IQR, min, max.
- Direction observed: `A_GREATER` if group-order-first group's location (mean for Welch; median/HL for MWU) greater, per orientation: record which group label is higher in `descriptives.higher_group`.

### 4.2 `NUM_CATEGORICAL` — numeric across k ≥ 3 groups

Candidates: **Welch's ANOVA** (`statsmodels.stats.oneway.anova_oneway(data, groups, use_var="unequal", welch_correction=True)`), **Kruskal-Wallis** (`scipy.stats.kruskal`).

**Selection rule:**
1. Per-group normality (as above) and Levene/Brown-Forsythe across groups.
2. If all groups approx normal **or** all groups have n ≥ `large_n_clt` with no |skew| > 2 → **Welch ANOVA**.
3. Else → **Kruskal-Wallis**; `fallback_used = True`.
4. Any group n < 5 (should not occur after `min_group_n`) → recorded as infeasible.

**Effect sizes:**
- ANOVA path: **η²** (SS_between/SS_total, from raw data) and **ω²** (bias-corrected); report both; `comparable_value = η²` (floor uses η²; also record ω²). CI by bootstrap (BCa if feasible; percentile fallback) for η².
- KW path: **ε²** = H/(n−1) (Tomczak & Tomczak). CI bootstrap.
- Descriptives: per-group n, mean, sd, median; group with highest/lowest mean (or median for KW).
- Post-hoc pairwise comparisons: **not** part of the family. Optional `posthoc.py` (STRETCH): Games-Howell (for Welch) / Dunn with Holm for **accepted findings only**, labeled as "descriptive follow-up (adjusted within test)".

### 4.3 `NUM_NUM` — association between two numeric variables

Candidates: **Pearson r** (`scipy.stats.pearsonr`), **Spearman ρ** (`scipy.stats.spearmanr`).

**Selection rule:**
1. If n < 30 → Spearman (small-n robustness).
2. Compute skew/kurtosis of each variable, outlier rate (3×IQR rule) and a linearity check (see below).
3. If both variables approx normal (Shapiro p > 0.01 or skew/kurt rule) and outlier rate < 2% in each → **Pearson**.
4. Else if n ≥ 200 and both |skew| ≤ `extreme_skew` and outlier rate < 5% → **Pearson** (large-n robustness; record).
5. Else → **Spearman**; `fallback_used = True`.
6. Ties-heavy variables (> 50% ties after dropping) → Spearman with tie correction (scipy handles); record.
7. Linearity check (info only for Pearson): compare R² of linear fit vs quadratic fit (F-test) for **warning** purposes only, **not** as a selection step (selection must not depend on the test outcome of the relationship itself, to avoid a second layer of selection; the check is purely advisory and does not alter p-values). Document this explicitly.

**Effect sizes:** r or ρ themselves; CI: Fisher z for Pearson (`atanh`, se = 1/sqrt(n−3)); Spearman CI via Fisher z with se = sqrt((1+ρ²/2)/(n−3)) (Fieller et al.) **or** bootstrap (default bootstrap for fidelity at moderate cost; Fisher approximation allowed in benchmark fast mode). `comparable_value = |r|` or `|ρ|`.
- Descriptives: n, means/sds (Pearson) or medians (Spearman), the coefficient, slope of OLS fit (for charts only), `direction_observed` from sign.

### 4.3b `NUM_NUM_NONLINEAR` (OPTIONAL; default off)
**Distance correlation** (implement via the unbiased/bias-corrected estimator, O(n²) memory: subsample to `max_n_dcor = 2000` with fixed seed when larger; record) with **permutation p-value** (`permutation_resamples` capped at 999 for speed). Effect = bias-corrected dcor (0..1). Floor: 0.10. Purpose: show honest handling of non-monotonic relationships (Phase 4 plants quadratic effects). When enabled, it is a *separate hypothesis* and counts in the family.

### 4.4 `CAT_CAT` — association between two categorical variables

Candidates: **Pearson chi-square test of independence** (`scipy.stats.chi2_contingency(correction=False)`), **Fisher's exact** (2×2: `scipy.stats.fisher_exact`), **Monte Carlo (permutation) chi-square** for sparse r×c.

**Selection rule:**
1. Build table. Compute expected counts.
2. 2×2 table: if any expected count < 5 (or n < 40) → **Fisher exact**; else chi-square (no Yates correction by default; document, config `yates: false`).
3. r×c larger: if ≥ 80% of cells have expected ≥ 5 and none < 1 → **chi-square**.
4. Else → **Monte Carlo chi-square** (permute one column's labels, `permutation_resamples`, p = (1 + #≥observed)/(1 + B)); `fallback_used = True`. Rare-level lumping is **not** done automatically here (only the min_group_n level filter from Section 3).
5. Extremely wide tables (r×c > 100 cells) with n < 5·cells → warning "sparse table".

**Effect sizes:**
- **Bias-corrected Cramér's V** (Bergsma 2013): `V~ = sqrt(max(0, φ²~)/min(k~−1, r~−1))`, where φ²~ = max(0, φ² − (k−1)(r−1)/(n−1)), r~ = r − (r−1)²/(n−1), k~ = k − (k−1)²/(n−1). Validate against hand-computed values.
- 2×2: **phi**, **odds ratio** with Woolf CI (add 0.5 continuity if any zero; record) via `statsmodels.stats.contingency_tables.Table2x2`, and risk difference + CI.
- Standardized floor: `comparable_value = V~ * sqrt(df*)` where df* = min(r−1, c−1), so that the threshold "small" equals 0.10 for any table size (Cohen's w equivalence: w = V·sqrt(df*)). Document. (Equivalent: V threshold = 0.10/sqrt(df*).)
- CI for V~ via bootstrap (resample rows) at stage B.
- Descriptives: contingency table, row percentages, standardized (adjusted) residuals, top 3 cells by |residual|, min expected count.
- Direction: for 2×2: which level of A is associated with higher proportion of level of B; for larger: list top residual cells.

### 4.5 Tool registry (`registry.py`)
```python
@dataclass(frozen=True)
class ToolSpec:
    name: str                    # "welch_t", ...
    relationship: RelationshipType
    run: Callable[[PreparedData, StatsConfig, np.random.Generator], RawTestOutput]
    effect_name: str
    description: str             # one line, used by the Phase 6 LLM tool definitions
REGISTRY: dict[str, ToolSpec]
def select_test(prepared: PreparedData, config) -> tuple[ToolSpec, list[AssumptionCheck], list[dict]]  # trace
def run_hypothesis(h: Hypothesis, df, config, *, stage: Literal["A","B"]="A") -> TestResult
```
The registry is the **only** list of tools the Phase 6 agent may call (P6). Adding a tool = adding a `ToolSpec` + tests.

---

## 5. Assumption checks (`assumptions.py`)

Each returns `AssumptionCheck` with a `severity`:

| Check | Method | Applies to | Pass rule | Severity if fail |
|---|---|---|---|---|
| Normality per group | Shapiro-Wilk (n ≤ 5000) else skew/kurtosis rule; also report skew & excess kurtosis | t-test, ANOVA, Pearson | p > 0.01 or rule pass | `info` (it triggers fallback, not rejection) |
| Equal variance | Levene (median-centered / Brown-Forsythe) | t/ANOVA/MWU interpretation | p > 0.05 | `info` for Welch paths; `warning` for MWU interpretation |
| Minimum group size | counts | group tests | n ≥ min_group_n | `violation` → infeasible |
| Expected counts | min expected, % cells < 5 | chi-square | rules in 4.4 | `info` (triggers Fisher/MC) |
| Outlier influence | % points outside 3×IQR; leave-out check: recompute the statistic dropping the top 1% most extreme observations of each variable; flag if effect sign flips or |effect| changes by > 50% | all numeric tests | no flip & change ≤ 50% | `warning` ("fragile to outliers") |
| Independence | cannot test. Heuristic: if column pair involves a high-repeat grouping-like column or Phase 1 flagged an ID-like column with repeated values (clustered rows), warn | all | n/a | `warning` (one global note per run: "rows assumed independent") |
| Linearity (advisory) | quadratic vs linear fit F-test | Pearson | p > 0.01 | `info` |
| Ties | % tied values | rank tests | < 50% | `info` |

**Assumption gate for validation (Section 7.3):** a result is rejected for `ASSUMPTION_VIOLATED` only if a `violation`-severity check remains after the fallback test was applied (e.g., group-size violation, test returned non-finite, MWU on two groups where all values identical). `warning`s become `flags` on accepted findings (displayed to the user), they do not reject.

**Sensitivity check (adds credibility):** for accepted findings, run the "other" test too (Welch vs MWU; Pearson vs Spearman) and record whether both agree on significance at raw p < 0.05 and sign; discordance becomes flag `"test_sensitive"`. Computed at stage B only.

---

## 6. Confidence intervals (`intervals.py`)

- Analytic where well-founded (Hedges' g, Pearson via Fisher z, odds ratio Woolf, mean difference Welch).
- Bootstrap otherwise: `scipy.stats.bootstrap` with `method='BCa'` when n ≥ 30 and statistic non-degenerate, else `'percentile'`; confidence level 0.95; stratified resampling for groups; seeded generator; `bootstrap_resamples` (2000 default; 500 in benchmark mode).
- CI level is **not** multiplicity-adjusted by default (document). Optional `report_adjusted_ci: false`; stretch: BH-selected-adjusted CIs (Benjamini-Yekutieli FCR) — mention in limitations as not implemented.
- If CI computation fails (degenerate resamples), set CI fields to None and add a warning; never fabricate.

---

## 7. Validation layer (`validation/`)

### 7.1 Correction (`correction.py`)
```python
def apply_correction(p_values: np.ndarray, method: str, alpha: float) -> CorrectionOutput  # q_values, reject_mask, ranks, m
```
- **BH implemented from scratch** (sort p ascending; `q_(i) = min_{j≥i} (m/j)·p_(j)`, capped at 1; reject where q ≤ alpha) **and** cross-checked in tests against `statsmodels.stats.multitest.multipletests(method='fdr_bh')` on random inputs (equality to 1e-12) including ties, p = 0, p = 1, m = 1, m = 0 (empty → no-op).
- Also: `by` (Benjamini-Yekutieli; q multiplied by Σ 1/i), `holm`, `bonferroni`, `none` (for ablation).
- Only tests with `status=="ok"` and finite p form the family; family size m recorded in every decision.
- Optional (STRETCH) `storey_qvalue` — do not implement unless time permits; not needed.

### 7.2 Family definition
`family_id`: `"batch"` for the initial exhaustive batch; chat tests join the **session family** (see 7.6). Validator receives *all* ledger entries for the session so correction is over everything run so far.

### 7.3 Rules (`rules.py`), applied in this order to each test; every failing rule appends a `RejectionReason`:

1. **Status gates:** `skipped_infeasible` → `INSUFFICIENT_DATA`; `error` → `TEST_ERROR`; degenerate → `DEGENERATE_DATA`. (These have no p-value and are not in the family; they appear in the rejection table with reason.)
2. **Multiple-testing gate:** q > alpha → `NOT_SIGNIFICANT_AFTER_CORRECTION`.
3. **Effect-size floor (if enabled):** `comparable_value < threshold[effect_type]` → `EFFECT_BELOW_THRESHOLD`. Thresholds from config; for Cramér's V use the df*-scaled rule in 4.4. Applies even when q ≤ alpha (the "significant but trivial" case).
4. **Assumption gate:** unresolved `violation` after fallback → `ASSUMPTION_VIOLATED`.
5. **Trivial/derived gate:** `|r| ≥ 0.999`, or `V~ ≥ 0.99`, or group means perfectly separated (e.g., rank-biserial |r| = 1 with n ≥ 20 and zero overlap), or numeric pair with exactly linear relationship → not accepted as a discovery; reason `TRIVIAL_RELATIONSHIP` and flag `possible_derived_column`. Reported in a separate "likely derived/duplicate columns" section (a useful data-quality finding, but not an insight).
6. **Strict mode (optional, off by default):** CI crossing 0 (or crossing floor) → `UNSTABLE_CI` (needs stage B CIs).
- A test is **accepted** iff no rejection reason applies. `reason_text` is generated by a deterministic template per reason code (no LLM), using values from the result (these numbers will later become Facts).
- `would_pass_without_correction = (p_raw < alpha)` and `would_pass_without_effect_floor = (q ≤ alpha)` are always stored — these power "what naive analysis would claim" views and the ablations.

### 7.4 Validator API (`validator.py`)
```python
def validate(results: list[TestResult], hypotheses: dict[str, Hypothesis], config, *, family_id="batch") -> list[ValidationDecision]
def build_findings(hypotheses, results, decisions) -> list[Finding]
```
Pure function; deterministic; order independent.

### 7.5 Ledger (`ledger.py`)
- Persisted as JSONL (`outputs/<run>/ledger.jsonl`) + in-memory index by hypothesis id.
- `Ledger.add(test_result, stage)`; refuses duplicates (returns the cached result); `Ledger.family()` returns all `ok` entries; `Ledger.revalidate(config)` recomputes BH over all entries and returns decisions **plus a diff vs. the previous decisions** (which findings changed status). Phase 6 surfaces diffs to the user ("adding this test changed finding #3 from accepted to not significant").
- The dataset SHA-256 is stored; loading a ledger for a different dataset raises an error.
- STRETCH: `LONDOnlineFDR` as an alternative `session_correction: lond` for sequential chat testing; implement only after everything else; note in docs.

### 7.6 Batch vs chat families (decision)
- **Batch run:** BH over all batch tests. Findings reported.
- **Chat:** every new test is appended to the ledger; session decisions are recomputed with BH over *batch ∪ chat* tests. The chat answer shows raw p, session q, effect, and an "exploratory" label. Status changes of earlier findings are surfaced via the diff. Rationale: honest multiplicity accounting without hidden hypothesis counts. Record in `docs/decisions.md`.

---

## 8. Rare-group handling and other edge cases (specified, so the agent does not improvise)

- Groups with n < `min_group_n` are excluded from that test, listed in `warnings` and `descriptives.dropped_levels`. Pairwise complete count `n_used` reflects retained rows.
- Binary column with a level of n < `min_group_n` → infeasible.
- Numeric column with < 5 distinct values → still testable (ties); Spearman/MWU selection triggers via tie rule; add warning.
- Huge n (> 200k): tests still run (vectorized); skip Shapiro (use skew/kurtosis rule); MWU uses `method='asymptotic'`; bootstrap on subsample of 50k with fixed seed (recorded `subsampled=true`).
- Infinite/NaN statistics → `status="error"` with message; never leave NaN p-value in the family.
- p-values below 1e-300 reported as `<1e-300` display (the numeric field keeps the float).
- Floating-point: clamp p to [0, 1].
- Time budget per test (`test_timeout_s`, default 20); on timeout → `error` with reason; the runner continues.
- Boolean columns → categorical strings; numeric-coded binary columns (0/1) → binary group labels "0"/"1" as strings in group keys (`descriptives` preserve the original dtype).

---

## 9. Batch runner (`runner.py::run_all`)

```python
def run_all(hset: HypothesisSet, df, config, *, n_jobs: int = -1, stage_b: bool = True, progress=None) -> RunOutput
class RunOutput(BaseModel): results: list[TestResult]; decisions: list[ValidationDecision]; findings: list[Finding]; ledger_path: str; summary: dict
```
- Parallelize with `joblib` (`loky`), chunked; each worker gets a seeded generator derived from `seed + int(hypothesis.id,16)`.
- Results sorted by hypothesis id before correction (determinism).
- Summary: m tested, m skipped, # raw p<alpha, # BH-rejected-null (i.e., q≤alpha), # accepted after all rules, counts by rejection reason, counts by test used, runtime, fallback rate. **Assert `len(family) == manifest.n_in_family_planned − (#skipped/errored)`**; mismatch raises `ValidationError` unless explained.
- Progress callback hook for UI.
- Outputs: `results.json`, `decisions.json`, `findings.json`, `ledger.jsonl`, `validation_summary.json`, `validation_summary.md` (table of accepted + table of rejected with reasons).

CLI:
```
veridata test --dataset NAME [--alpha 0.05] [--correction bh|by|holm|bonferroni|none] [--no-effect-floor] [--n-jobs N]
veridata validate --dataset NAME   # re-run validation over an existing ledger (e.g. after config change)
```
Config switches that Phase 8 ablations need must work from the CLI and programmatically: `correction`, `effect_floor.enabled`, `assumption_aware_selection` (new key: if false, always use Welch t / Welch-ANOVA? **No:** the naive baseline is *always* Student/Welch t, ANOVA, Pearson, chi-square without fallback), `enable_assumption_gate`.

---

## 10. Tests (the most important section of this phase)

### 10.1 Reference-implementation tests
For each test function: generate fixed-seed data, compare statistic and p-value to the direct scipy/statsmodels call (equality within 1e-10), for several shapes (balanced/unbalanced, ties, small n, large n).

### 10.2 Hand-computed micro cases
Tiny tables/vectors with answers computed by hand in the test file's comments: 2×2 table odds ratio and Woolf CI; Cramér's V bias correction for a 3×3 table; Hedges' g for two 5-element vectors; rank-biserial from known U; BH q-values for `[0.01, 0.04, 0.03, 0.005]` (m=4); epsilon-squared from known H.

### 10.3 Correction tests
BH vs statsmodels on 1,000 random vectors; monotonicity (q non-decreasing in sorted p); idempotence; m=0/1; all p=1; all p=0; ties; family invariance to input order.

### 10.4 Selection-rule tests
Table-driven: construct data that must choose each test (normal → Welch; skewed small n → MWU; skewed large n with moderate skew → Welch; zero-variance group → MWU; sparse 2×2 → Fisher; sparse 4×4 → Monte Carlo; heavy outliers → Spearman). Assert `selection_trace` content.

### 10.5 Effect-size and CI coverage tests (marked slow)
Simulate 1,000 datasets with known true d (or r, V) and verify 95% CI coverage within [0.92, 0.98] for analytic CIs and [0.90, 0.99] for bootstrap CIs (looser, since bootstrap).

### 10.6 Type-I error calibration smoke tests (full study in Phase 4)
Under the null, 2,000 simulated datasets for: normal, lognormal, t(3), zero-inflated; n ∈ {20, 100}; verify rejection rate at 0.05 within [0.035, 0.065] for the **selected** test. Failures indicate a selection or implementation bug.

### 10.7 Validator tests
Hand-built `TestResult` lists: significant-but-trivial → `EFFECT_BELOW_THRESHOLD`; just-below BH line; skipped tests excluded from m; derived pair → `TRIVIAL_RELATIONSHIP`; ordering invariance; `would_pass_*` flags; reasons text includes only numbers present in the result (preparation for P1).

### 10.8 Ledger tests
Append-only; duplicate suppression; revalidate diff (add a test that flips an earlier finding); dataset-hash mismatch error; JSONL round trip.

### 10.9 End-to-end
On the Phase 1 messy synthetic data and the insurance dataset: run Phase 2 → Phase 3; assert outputs and invariants (family count equals manifest; every non-accepted decision has ≥ 1 reason; every accepted has none). For insurance: smoker→charges (NUM_BINARY) accepted with large effect; at least one known strong effect (age↔charges) accepted; an injected pure-noise column pair is not accepted.

### 10.10 Property tests (optional with `hypothesis`)
Shuffling rows does not change p-values; permuting column order does not change results; scaling a numeric column by a positive constant does not change results (for all tests selected; Welch/MWU/Pearson/Spearman are scale invariant, check).

---

## 11. Milestones

| ID | Work | Est. |
|---|---|---|
| P3-M0 | Contracts finalized (`results.py`, `validation.py`, `ledger.py`), config keys, registry skeleton | 0.5 d |
| P3-M1 | `prepare_inputs`, assumptions module | 1 d |
| P3-M2 | NUM_BINARY tests + effect sizes + CIs + selection + tests | 1.5 d |
| P3-M3 | NUM_CATEGORICAL + NUM_NUM tests | 1.5 d |
| P3-M4 | CAT_CAT tests (Fisher/MC/bias-corrected V/OR) | 1.5 d |
| P3-M5 | Correction (BH/BY/Holm/Bonf) + rules + validator + trivial gate | 1.5 d |
| P3-M6 | Ledger + runner (parallel, stage A/B) + outputs + CLI | 1 d |
| P3-M7 | Calibration smoke tests, CI coverage tests, end-to-end, docs | 1 d |
| P3-M8 (STRETCH) | Nonlinear dcor; posthoc; adjusted association; LOND | 2+ d |

---

## 12. Acceptance criteria

- [ ] Every test in the library matches scipy/statsmodels references (10.1) and hand-computed values (10.2).
- [ ] BH matches statsmodels exactly; BY/Holm/Bonferroni implemented for ablation.
- [ ] Selection rules documented in code docstrings and `docs/stats_methods.md` with a table; every `TestResult` carries `selection_trace`.
- [ ] Null calibration smoke tests pass (rejection rates within bounds) for all selected tests across the scenarios in 10.6.
- [ ] CI coverage tests pass.
- [ ] `veridata test --dataset insurance` produces `findings.json` where smoker→charges is accepted, and `validation_summary.md` lists rejected hypotheses with reasons; count identity with manifest holds.
- [ ] A shuffled-column version of insurance (each column independently permuted) yields **zero accepted findings** in ≥ 95% of 50 seeds (smoke version of the pure-noise FWER check).
- [ ] No imports of LLM clients anywhere under `stats/` and `validation/` (lint test).
- [ ] Runtime: 700 tests on 5,000 rows ≤ 90 s on a laptop with 8 cores (stage A + stage B on candidates).
- [ ] `docs/stats_methods.md` explains each test, selection rule, effect size, CI, correction, and limitations in plain language (this doubles as report appendix material).

---

## 13. Handoff

- **To Phase 4:** callable `run_all(...)` and config switches for ablations; `TestResult` and `ValidationDecision` schemas; ledger.
- **To Phase 5:** `Finding` objects with `descriptives` containing every number narration may use; `reason_text` templates; `selection_trace`.
- **To Phase 6:** `registry.REGISTRY` tool specs; `Ledger` and `revalidate` with diffs; single-hypothesis `run_hypothesis`.

---

## 14. Stretch items (only after all acceptance criteria pass)

1. **Adjusted association tool** (`adjusted.py`): OLS with HC3 robust SEs (numeric outcome) or logistic regression (binary outcome) with one or more covariates, reporting the coefficient of interest, CI, and comparing with the unadjusted effect ("controlling for age, the smoker difference is ..."). Not in the BH family automatically; each use is a ledger entry labeled `ADJUSTED_ASSOCIATION`.
2. **Post-hoc tests** (Games-Howell/Dunn+Holm) for accepted multi-group findings.
3. **Online FDR (LOND)** for chat.
4. **Nonlinear dcor** tests.
5. **Simpson's paradox check:** for accepted numeric-binary/num-num findings, re-estimate within strata of the strongest categorical covariate (chosen *independent of the outcome relationship*, e.g., the target-less lowest-cardinality binary column) and flag sign reversals.

---

## 15. Pitfalls

1. **Choosing the test by looking at the p-value.** Selection depends only on assumption diagnostics, never on the p-value or effect of the pair being tested.
2. **Silent family shrinkage.** Always compare actual family size with the manifest.
3. **Shapiro at large n** rejects trivially; hence the n-aware rules. Do not use Shapiro alone to force Mann-Whitney at n = 50,000.
4. **Mann-Whitney is not a "median test".** Narration (Phase 5) must say "tends to be higher", unless distribution shapes are similar.
5. **Bias-corrected V** can be 0 for small samples; handle without NaN.
6. **Bootstrap cost explosion.** Keep stage B restricted to candidates.
7. **Numeric-coded categoricals** (0/1, 1-5) mis-typed upstream lead to wrong tests; rely on Phase 1 schema; surface the type used in every result.
8. **Dependence among tests** may inflate FDR; measured in Phase 4; documented; BY available.
9. **Post-selection inference:** CIs for accepted findings are optimistic (winner's curse); mention in limitations.

---

## 16. Human tasks

- Review `docs/stats_methods.md` and the selection rule table for statistical sanity (ideally by a person with a stats background or the course instructor).
- Spot-check 10 `selection_trace`s on real datasets.
- Approve effect-size floor defaults or adjust (document why).
