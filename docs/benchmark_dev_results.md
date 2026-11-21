# Benchmark results on the dev split (Phase 4)

**These are development numbers.** They were used to debug and tune VeriData and must not be
reported as the final result. The final numbers come from the frozen test split in Phase 8
(`docs/eval_protocol.md`).

Reproduce:

```bash
veridata bench gen --suite core60 --split dev
veridata bench run-all-variants --suite core60 --split dev --n-jobs 2
veridata bench eval --suite core60 --split dev --resamples 2000
veridata bench tune --suite core60 --split dev
```

Full outputs (per-dataset metrics, stratified tables, q-value calibration) are in
`outputs/benchmark/core60/dev/results/`. Generated datasets and per-system result files are not
committed (they are rebuilt in a few minutes by the commands above).

## Short version

- **VeriData (`veridata_full`) kept the false discovery rate at 4.7%** (95% CI 2.0–7.9%) and
  found **66.6%** of all testable planted relationships, and **98.2%** of medium and large effects
  when the dataset had at least 300 rows.
- Without correction (`veridata_nocorrection`) the false discovery rate jumps to **70.7%**: most
  "findings" are noise. This is the gap the product is built to close.
- Each safety layer matters: correction alone (`bh_only`, 13.5%) or the effect floor alone
  (`floor_only`, 52.0%) is not enough; together with assumption-aware test choice they reach 4.7%.
- Stricter corrections (Bonferroni, Holm, BY) lower the false discovery rate further (1.2–2.8%)
  but find fewer real relationships (60.6–62.8%).

## 1. Main table (60 datasets; direction checked when reported)

Brackets are 95% bootstrap confidence intervals over datasets (2,000 resamples).

| System | Datasets | FDR (mean FDP) | Recall (testable truths) | Precision | FWER on zero-effect datasets | Mean reported | Mean false | Errors |
| :--- | ---: | :--- | :--- | :--- | :--- | ---: | ---: | ---: |
| `veridata_full` | 60 | 4.7% [2.0%, 7.9%] | 66.6% [56.5%, 76.3%] | 93.6% [89.6%, 97.3%] | 8.3% [0.0%, 27.3%] | 5.400 | 0.233 | 0 |
| `veridata_nocorrection` | 60 | 70.7% [62.5%, 78.5%] | 84.6% [77.7%, 91.0%] | 29.3% [21.5%, 37.5%] | 100.0% [100.0%, 100.0%] | 44.067 | 37.950 | 0 |
| `bh_only` | 60 | 13.5% [7.7%, 20.5%] | 68.9% [58.7%, 78.3%] | 83.5% [75.2%, 90.4%] | 41.7% [14.3%, 72.7%] | 5.883 | 0.733 | 0 |
| `floor_only` | 60 | 52.0% [42.4%, 62.0%] | 74.0% [66.4%, 81.3%] | 45.3% [35.2%, 55.0%] | 75.0% [50.0%, 100.0%] | 27.933 | 22.400 | 0 |
| `naive_tests` | 60 | 10.4% [5.2%, 16.7%] | 63.3% [53.5%, 72.7%] | 86.7% [78.7%, 93.1%] | 33.3% [8.3%, 63.6%] | 5.450 | 0.550 | 0 |
| `naive_raw` | 60 | 72.7% [64.6%, 79.7%] | 81.4% [74.5%, 88.1%] | 27.3% [20.3%, 35.4%] | 100.0% [100.0%, 100.0%] | 45.267 | 39.367 | 0 |
| `bonferroni` | 60 | 2.8% [0.4%, 6.7%] | 62.8% [52.5%, 72.8%] | 96.2% [90.8%, 99.5%] | 8.3% [0.0%, 27.3%] | 4.933 | 0.083 | 0 |
| `holm` | 60 | 2.8% [0.4%, 6.7%] | 62.8% [52.5%, 72.8%] | 96.2% [90.8%, 99.5%] | 8.3% [0.0%, 27.3%] | 4.933 | 0.083 | 0 |
| `by` | 60 | 1.2% [0.3%, 2.5%] | 60.6% [49.7%, 71.2%] | 98.1% [96.2%, 99.6%] | 8.3% [0.0%, 27.3%] | 4.800 | 0.083 | 0 |

### Same, with direction ignored (pair only)

| System | FDR | Recall |
| :--- | :--- | :--- |
| `veridata_full` | 4.7% [2.0%, 7.9%] | 66.6% [56.5%, 76.3%] |
| `veridata_nocorrection` | 70.7% [62.5%, 78.5%] | 84.6% [77.7%, 91.0%] |
| `bh_only` | 13.5% [7.7%, 20.5%] | 68.9% [58.7%, 78.3%] |
| `floor_only` | 51.7% [42.1%, 61.6%] | 74.2% [66.5%, 81.5%] |
| `naive_tests` | 10.4% [5.2%, 16.7%] | 63.3% [53.5%, 72.7%] |
| `naive_raw` | 72.4% [64.2%, 79.6%] | 81.5% [74.7%, 88.2%] |
| `bonferroni` | 2.8% [0.4%, 6.7%] | 62.8% [52.5%, 72.8%] |
| `holm` | 2.8% [0.4%, 6.7%] | 62.8% [52.5%, 72.8%] |
| `by` | 1.2% [0.3%, 2.5%] | 60.6% [49.7%, 71.2%] |

The two tables are almost the same: VeriData never reported a real pair with the wrong direction
(0 wrong-direction errors for `veridata_full`).

## 2. Where `veridata_full` goes wrong

14 false discoveries in total, spread over 12 of the 60 datasets, all on **null pairs** (no
wrong-direction errors). The one zero-effect dataset with false discoveries is
`c08_null_n1000_p60` (t-distributed data with correlated null blocks): it reported 6 real
block pairs and 2 null pairs. The other 11 of the 12 zero-effect datasets had no false
discoveries, giving FWER 8.3% (1 of 12) — inside the sanity target of ≤ 10%, but based on only
12 datasets, so the CI is wide (0–27%).

## 3. What `veridata_full` finds (recall)

By effect size and dataset size (testable planted pairs):

| Effect size | n ≥ 300 | n < 300 |
| :--- | ---: | ---: |
| Large | 98.6% (142 pairs) | 87.2% (39 pairs) |
| Medium | 97.4% (76 pairs) | 40.9% (22 pairs) |
| Small | 54.7% (95 pairs) | 3.2% (31 pairs) |

By number of rows: n = 100 → 47.8%, n = 300 → 74.0%, n = 1000 → 89.4%, n = 5000 → 90.8%.

By relationship form: latent-factor pairs 97.8%, binary shift 75.0%, linear 74.2%, category ×
category 72.9%, monotonic 72.7%, categorical shift 68.3%, induced (sibling / common cause) 59.0%.

By distribution: bimodal 80.9%, mixed 81.1%, t3 79.5%, zero-inflated 73.6%, normal 69.8%,
lognormal 69.0% (differences mostly reflect which scenarios each shape was rotated into).

Small effects at small n are mostly missed — by design: the effect floor and the correction prefer
missing a weak effect over reporting noise.

## 4. Are the q-values honest?

Reported findings of `veridata_full`, grouped by adjusted p-value (q):

| q bin | Findings | Share that were false |
| :--- | ---: | ---: |
| below 0.001 | 273 | 0.0% |
| 0.001–0.01 | 16 | 31.3% |
| 0.01–0.02 | 12 | 8.3% |
| 0.02–0.03 | 6 | 0.0% |
| 0.03–0.04 | 10 | 40.0% |
| 0.04–0.05 | 7 | 57.1% |

Almost all findings have q < 0.001 and none of those were false. Findings close to the 0.05
cut-off are false much more often than their q-value suggests. This is expected: BH controls the
*average* share of false findings over the whole list, not the chance that one particular
borderline finding is false. The counts in the upper bins are small, but the pattern is clear
enough that the Phase 5 report now says so in its Limitations section.

## 5. Effect-floor tuning (dev only)

All effect-size floors were multiplied by one factor; objective: highest recall with FDR ≤ 5%.

| Multiplier | Mean FDP (FDR) | Recall | FWER on zero-effect datasets | Precision |
| ---: | ---: | ---: | ---: | ---: |
| 0.5 | 7.3% | 71.2% | 16.7% | 90.4% |
| 0.75 | 6.6% | 70.7% | 16.7% | 91.4% |
| 1.0 | 4.7% | 66.6% | 8.3% | 93.6% |
| 1.25 | 4.6% | 65.8% | 8.3% | 93.7% |
| 1.5 | 4.5% | 64.3% | 8.3% | 93.9% |

**Decision:** keep **1.0** (the conventional floors: d 0.2, r 0.1, η² 0.01, ε² 0.01,
rank-biserial 0.1, Cramér's V (df = 1) 0.1). It is the best value that meets the 5% target, and it
equals the convention, so nothing is changed (`configs/tuned_defaults.yaml`). `large_n_clt` and
`extreme_skew` were not tuned (decision P4-09).

## 6. Phase 4 acceptance check (plan Section 13)

| Criterion | Result |
| :--- | :--- |
| core60 and smoke generate deterministically; truth self-check passes | Yes (tests in `tests/benchmark/`) |
| Matcher classifies every pair exactly once | Yes (tests) |
| Metrics reproduce hand-computed examples; bootstrap CIs reproducible | Yes (tests) |
| Type I criterion met or deviations documented | Met after re-running one noisy cell (`docs/calibration_results.md`) |
| `veridata_full` FDR ≤ 0.08 (target 0.05) | 4.7% |
| `veridata_nocorrection` clearly higher | 70.7% |
| FWER on zero-effect datasets ≤ 0.10 | 8.3% |
| Recall ≥ 0.6 on medium/large effects at n ≥ 300 | 98.2% |
| Dependence experiment done; BH vs BY documented | Yes (`docs/calibration_results.md`) |
| `tuned_defaults.yaml` produced | Yes (kept conventional values) |
| `docs/eval_protocol.md` drafted | Yes (Status: DRAFT; freeze before Phase 8) |
| Test split untouched | Yes (no `test/` folder exists under `outputs/benchmark/`) |
