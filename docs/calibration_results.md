# Calibration results (Phase 4, Section 7)

Run on the dev machine with `veridata bench calibrate --experiment all` (fixed seeds). Raw outputs:
`outputs/benchmark/calibration/` (`type1.csv`, `type1_size.png`, `type1_pvalue_hist.png`,
`fdr_dependence.csv`, `power.csv`, `type1_rerun_outlier_cell.csv`).

**Short version**

- The tests VeriData picks keep the false-positive rate close to 5% when there is no real effect.
  One small, very unbalanced cell looked high at first; a re-run with 12,000 datasets put it back
  inside the band. → **Pass** (after re-run).
- Benjamini–Hochberg (BH) kept the false discovery rate at about 5% or below in every dependence
  scenario we tried, including strongly correlated blocks. BY was much more cautious. → BH stays
  the default; no switch to BY is needed for these scenarios.
- The parametric tests have the power theory predicts. → implementation check **passes**.

---

## 1. Type I error of the selected tests (E3a)

Design: 5 distribution families (normal, lognormal σ = 0.8, t with 3 df, 30% zero-inflated,
bimodal) × n ∈ {20, 50, 200, 1000} × relationship × balanced or 90/10 groups. Each cell has
**1,000 null datasets** (the plan says 5,000; we used 1,000 to fit the time budget and added
Monte Carlo slack — decision P4-08). A run is "valid" when the pair passes the feasibility rules
(for example at least 8 rows per group); 15 of the 116 cells had no valid runs at all (n = 20 with
4 groups or a 90/10 split, and some n = 20 tables) and are left out.

Pass criterion (plan 7.1): size in [0.04, 0.06] widened by ± 2 Monte Carlo SE for at least 90% of
cells, and no cell above 0.075.

| Relationship | Test choice | Cells | Mean size | Largest size | Cells inside band |
| :--- | :--- | ---: | ---: | ---: | ---: |
| Table (2×2, 3×4) | VeriData (assumption-aware) | 13 | 0.040 | 0.060 | 77% |
| Table (2×2, 3×4) | Naive (always parametric) | 13 | 0.043 | 0.060 | 85% |
| Numeric vs 2 groups | VeriData (assumption-aware) | 38 | 0.045 | 0.098 | 92% |
| Numeric vs 2 groups | Naive (always parametric) | 38 | 0.048 | 0.098 | 84% |
| Numeric vs 4 groups | VeriData (assumption-aware) | 30 | 0.050 | 0.071 | 100% |
| Numeric vs 4 groups | Naive (always parametric) | 30 | 0.058 | 0.103 | 87% |
| Numeric vs numeric | VeriData (assumption-aware) | 20 | 0.050 | 0.061 | 100% |
| Numeric vs numeric | Naive (always parametric) | 20 | 0.050 | 0.059 | 100% |

Overall for VeriData's test choice: **101 cells, 94.1% inside the band**.

One cell was above 0.075 in the first run: numeric vs 2 groups, normal data, n = 50, 90/10 split.
Only 123 of its 1,000 datasets were valid (the small group often had fewer than 8 rows), so the
estimate was very noisy (0.098 ± 0.027). Re-run with **12,000** datasets (1,551 valid):

| Test choice | Valid runs | Size | Monte Carlo SE |
| :--- | ---: | ---: | ---: |
| VeriData (assumption-aware) | 1,551 | 0.059 | 0.006 |
| Naive (always Welch t) | 1,551 | 0.060 | 0.006 |

That is inside the band, so the cell passes. With this re-run the criterion is met.

What the comparison with the naive tests shows: for skewed or zero-inflated data with unbalanced
groups, the always-parametric choice goes up to **0.103** (lognormal, 4 groups, n = 200, 90/10),
while VeriData's choice stays at or below 0.071. That is the reason assumption-aware selection
exists.

Tables (chi-square / Fisher / Monte Carlo chi-square) are a little **conservative** (mean size
0.040): some cells fall *below* the band. A conservative test only makes VeriData slightly
cautious, so this is accepted.

## 2. FDR of BH under dependence (E3b)

Design: n = 200 rows, p ∈ {20, 60, 120} columns, 300 repetitions per cell, all numeric–numeric
Pearson tests (vectorised), corrected with VeriData's own `apply_correction`.

- `independent`: global null, independent columns.
- `null_blocks (ρ)`: 40% of the columns are in blocks of 5 with within-block correlation ρ; the
  within-block pairs are real dependencies, everything else is null.
- `sparse_truth`: blocks with ρ = 0.6 plus extra true pairs (correlation 0.25).

### Empirical FDR (target ≤ 0.05)

| Scenario | Columns (p) | bh | by | bonferroni | holm | none |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| independent | 20 | 0.060 | 0.013 | 0.060 | 0.060 | 1.000 |
| independent | 60 | 0.067 | 0.030 | 0.067 | 0.067 | 1.000 |
| independent | 120 | 0.033 | 0.000 | 0.033 | 0.033 | 1.000 |
| null_blocks (ρ=0.3) | 20 | 0.047 | 0.008 | 0.004 | 0.005 | 0.394 |
| null_blocks (ρ=0.3) | 60 | 0.051 | 0.006 | 0.002 | 0.002 | 0.652 |
| null_blocks (ρ=0.3) | 120 | 0.051 | 0.006 | 0.001 | 0.001 | 0.792 |
| null_blocks (ρ=0.6) | 20 | 0.048 | 0.010 | 0.005 | 0.006 | 0.395 |
| null_blocks (ρ=0.6) | 60 | 0.049 | 0.006 | 0.001 | 0.001 | 0.650 |
| null_blocks (ρ=0.6) | 120 | 0.049 | 0.005 | 0.001 | 0.001 | 0.791 |
| null_blocks (ρ=0.9) | 20 | 0.050 | 0.009 | 0.005 | 0.005 | 0.388 |
| null_blocks (ρ=0.9) | 60 | 0.045 | 0.006 | 0.001 | 0.001 | 0.642 |
| null_blocks (ρ=0.9) | 120 | 0.047 | 0.005 | 0.001 | 0.001 | 0.790 |
| sparse_truth (ρ=0.6) | 20 | 0.044 | 0.007 | 0.002 | 0.002 | 0.304 |
| sparse_truth (ρ=0.6) | 60 | 0.048 | 0.006 | 0.001 | 0.001 | 0.572 |
| sparse_truth (ρ=0.6) | 120 | 0.049 | 0.005 | 0.000 | 0.000 | 0.732 |

### Empirical FWER (chance of at least one false discovery)

| Scenario | Columns (p) | bh | by | bonferroni | holm | none |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| independent | 20 | 0.060 | 0.013 | 0.060 | 0.060 | 1.000 |
| independent | 60 | 0.067 | 0.030 | 0.067 | 0.067 | 1.000 |
| independent | 120 | 0.033 | 0.000 | 0.033 | 0.033 | 1.000 |
| null_blocks (ρ=0.3) | 20 | 0.447 | 0.090 | 0.050 | 0.057 | 1.000 |
| null_blocks (ρ=0.3) | 60 | 0.870 | 0.180 | 0.053 | 0.053 | 1.000 |
| null_blocks (ρ=0.3) | 120 | 0.973 | 0.267 | 0.053 | 0.053 | 1.000 |
| null_blocks (ρ=0.6) | 20 | 0.483 | 0.123 | 0.070 | 0.080 | 1.000 |
| null_blocks (ρ=0.6) | 60 | 0.883 | 0.220 | 0.053 | 0.060 | 1.000 |
| null_blocks (ρ=0.6) | 120 | 0.983 | 0.360 | 0.067 | 0.070 | 1.000 |
| null_blocks (ρ=0.9) | 20 | 0.383 | 0.087 | 0.053 | 0.053 | 1.000 |
| null_blocks (ρ=0.9) | 60 | 0.777 | 0.207 | 0.030 | 0.033 | 1.000 |
| null_blocks (ρ=0.9) | 120 | 0.973 | 0.253 | 0.050 | 0.050 | 1.000 |
| sparse_truth (ρ=0.6) | 20 | 0.540 | 0.113 | 0.033 | 0.037 | 1.000 |
| sparse_truth (ρ=0.6) | 60 | 0.920 | 0.240 | 0.060 | 0.060 | 1.000 |
| sparse_truth (ρ=0.6) | 120 | 0.990 | 0.360 | 0.037 | 0.037 | 1.000 |

### Power (share of real pairs found)

| Scenario | Columns (p) | bh | by | bonferroni | holm | none |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| null_blocks (ρ=0.3) | 20 | 0.914 | 0.802 | 0.763 | 0.767 | 0.994 |
| null_blocks (ρ=0.3) | 60 | 0.864 | 0.684 | 0.559 | 0.560 | 0.993 |
| null_blocks (ρ=0.3) | 120 | 0.809 | 0.583 | 0.427 | 0.428 | 0.992 |
| null_blocks (ρ=0.6) | 20 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| null_blocks (ρ=0.6) | 60 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| null_blocks (ρ=0.6) | 120 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| null_blocks (ρ=0.9) | 20 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| null_blocks (ρ=0.9) | 60 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| null_blocks (ρ=0.9) | 120 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| sparse_truth (ρ=0.6) | 20 | 0.933 | 0.874 | 0.840 | 0.843 | 0.982 |
| sparse_truth (ρ=0.6) | 60 | 0.910 | 0.845 | 0.794 | 0.795 | 0.986 |
| sparse_truth (ρ=0.6) | 120 | 0.887 | 0.819 | 0.771 | 0.771 | 0.986 |

What this means:

- BH stays at about 5% FDR everywhere (the highest value, 0.067 for independent p = 60, is within
  Monte Carlo noise of 0.05: SE ≈ 0.014). Strong positive correlation between columns did **not**
  push BH above 5%.
- BH does **not** control FWER when there are real effects (FWER up to 0.99) — that is expected:
  BH promises a low *share* of false findings, not zero false findings. Bonferroni / Holm keep
  FWER near 5% but find far fewer real pairs (power 0.43 vs 0.81 at ρ = 0.3, p = 120).
- No correction is a disaster: FDR 0.30–0.79 and FWER 1.0.
- Recommendation: keep BH as the default; mention BY as the safer option for unusual dependence in
  the report's Limitations section (already done in Phase 5).

## 3. Power sanity check

400 repetitions per cell; "within 3 SE" compares empirical and analytic power
(`statsmodels` `TTestIndPower` for Welch t, Fisher z approximation for Pearson).

| Test | n | Effect | Empirical power | Analytic power | Within 3 SE |
| :--- | ---: | ---: | ---: | ---: | :---: |
| Welch t | 60 | d = 0.2 | 0.120 | 0.119 | yes |
| Welch t | 60 | d = 0.5 | 0.517 | 0.478 | yes |
| Welch t | 60 | d = 0.8 | 0.885 | 0.861 | yes |
| Welch t | 200 | d = 0.2 | 0.295 | 0.291 | yes |
| Welch t | 200 | d = 0.5 | 0.935 | 0.940 | yes |
| Welch t | 200 | d = 0.8 | 1.000 | 1.000 | yes |
| Pearson | 30 | r = 0.2 | 0.188 | 0.184 | yes |
| Pearson | 30 | r = 0.4 | 0.610 | 0.595 | yes |
| Pearson | 100 | r = 0.2 | 0.492 | 0.515 | yes |
| Pearson | 100 | r = 0.4 | 0.993 | 0.987 | yes |

All 10 cells agree, so the tests are implemented correctly.

## 4. Runtime (from the core60 dev run)

60 datasets, 45–1,770 tests each, 2 CPU cores: preparation (profile + clean + enumerate) mean 4.4 s,
Stage A tests mean 4.3 s, slowest dataset 14.9 s for Stage A. Per-dataset numbers are in
`outputs/benchmark/core60/dev/runtime.csv`. A full 9-variant run of core60 takes well under an hour
on a laptop, so the Phase 8 test run is cheap.
