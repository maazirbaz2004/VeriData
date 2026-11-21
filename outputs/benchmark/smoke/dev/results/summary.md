# Benchmark results — `smoke` / `dev`

Primary direction mode (`if_reported`): a true pair reported with the wrong sign / higher group counts as a false discovery. Brackets are 95% bootstrap CIs over datasets (2,000 resamples).

| System | Datasets | FDR (mean FDP) | Recall (testable truths) | Precision | FWER on zero-effect datasets | Mean reported | Mean false | Errors |
| :--- | ---: | :--- | :--- | :--- | :--- | ---: | ---: | ---: |
| `veridata_full` | 12 | 0.9% [0.0%, 2.8%] | 91.7% [83.3%, 100.0%] | 98.9% [96.7%, 100.0%] | 0.0% [0.0%, 0.0%] | 4.167 | 0.083 | 0 |
| `veridata_nocorrection` | 12 | 54.0% [43.2%, 66.9%] | 98.3% [95.0%, 100.0%] | 46.0% [33.1%, 56.8%] | 100.0% [100.0%, 100.0%] | 8.833 | 4.417 | 0 |
| `bh_only` | 12 | 3.7% [0.0%, 10.2%] | 86.9% [73.8%, 97.5%] | 95.6% [87.7%, 100.0%] | 0.0% [0.0%, 0.0%] | 4.083 | 0.250 | 0 |
| `floor_only` | 12 | 58.1% [47.9%, 69.3%] | 96.7% [90.0%, 100.0%] | 41.9% [30.7%, 52.1%] | 100.0% [100.0%, 100.0%] | 9.333 | 5.000 | 0 |
| `naive_tests` | 12 | 3.7% [0.0%, 10.2%] | 86.9% [73.8%, 97.5%] | 95.6% [87.7%, 100.0%] | 0.0% [0.0%, 0.0%] | 4.083 | 0.250 | 0 |
| `naive_raw` | 12 | 58.7% [48.9%, 69.5%] | 96.7% [90.0%, 100.0%] | 41.3% [30.5%, 51.1%] | 100.0% [100.0%, 100.0%] | 9.500 | 5.167 | 0 |
| `bonferroni` | 12 | 0.0% [0.0%, 0.0%] | 81.9% [71.5%, 92.8%] | 100.0% [100.0%, 100.0%] | 0.0% [0.0%, 0.0%] | 3.667 | 0.000 | 0 |
| `holm` | 12 | 0.0% [0.0%, 0.0%] | 81.9% [71.5%, 92.8%] | 100.0% [100.0%, 100.0%] | 0.0% [0.0%, 0.0%] | 3.667 | 0.000 | 0 |
| `by` | 12 | 0.0% [0.0%, 0.0%] | 79.4% [63.7%, 92.8%] | 100.0% [100.0%, 100.0%] | 0.0% [0.0%, 0.0%] | 3.583 | 0.000 | 0 |

## Pair-only matching (direction ignored)

| System | FDR | Recall |
| :--- | :--- | :--- |
| `veridata_full` | 0.9% [0.0%, 2.8%] | 91.7% [83.3%, 100.0%] |
| `veridata_nocorrection` | 54.0% [43.2%, 66.9%] | 98.3% [95.0%, 100.0%] |
| `bh_only` | 3.7% [0.0%, 10.2%] | 86.9% [73.8%, 97.5%] |
| `floor_only` | 58.1% [47.9%, 69.3%] | 96.7% [90.0%, 100.0%] |
| `naive_tests` | 3.7% [0.0%, 10.2%] | 86.9% [73.8%, 97.5%] |
| `naive_raw` | 58.7% [48.9%, 69.5%] | 96.7% [90.0%, 100.0%] |
| `bonferroni` | 0.0% [0.0%, 0.0%] | 81.9% [71.5%, 92.8%] |
| `holm` | 0.0% [0.0%, 0.0%] | 81.9% [71.5%, 92.8%] |
| `by` | 0.0% [0.0%, 0.0%] | 79.4% [63.7%, 92.8%] |

## Recall by effect form

| System | Form | Truths | Recall |
| :--- | :--- | ---: | ---: |
| `bh_only` | binary_shift | 5 | 100.0% |
| `bh_only` | cat_cat | 9 | 100.0% |
| `bh_only` | categorical_shift | 7 | 71.4% |
| `bh_only` | induced | 8 | 37.5% |
| `bh_only` | latent_factor | 12 | 100.0% |
| `bh_only` | linear | 6 | 100.0% |
| `bh_only` | monotonic | 5 | 100.0% |
| `bonferroni` | binary_shift | 5 | 100.0% |
| `bonferroni` | cat_cat | 9 | 77.8% |
| `bonferroni` | categorical_shift | 7 | 100.0% |
| `bonferroni` | induced | 8 | 25.0% |
| `bonferroni` | latent_factor | 12 | 100.0% |
| `bonferroni` | linear | 6 | 100.0% |
| `bonferroni` | monotonic | 5 | 100.0% |
| `by` | binary_shift | 5 | 80.0% |
| `by` | cat_cat | 9 | 77.8% |
| `by` | categorical_shift | 7 | 100.0% |
| `by` | induced | 8 | 25.0% |
| `by` | latent_factor | 12 | 100.0% |
| `by` | linear | 6 | 100.0% |
| `by` | monotonic | 5 | 100.0% |
| `floor_only` | binary_shift | 5 | 100.0% |
| `floor_only` | cat_cat | 9 | 100.0% |
| `floor_only` | categorical_shift | 7 | 100.0% |
| `floor_only` | induced | 8 | 75.0% |
| `floor_only` | latent_factor | 12 | 100.0% |
| `floor_only` | linear | 6 | 100.0% |
| `floor_only` | monotonic | 5 | 100.0% |
| `holm` | binary_shift | 5 | 100.0% |
| `holm` | cat_cat | 9 | 77.8% |
| `holm` | categorical_shift | 7 | 100.0% |
| `holm` | induced | 8 | 25.0% |
| `holm` | latent_factor | 12 | 100.0% |
| `holm` | linear | 6 | 100.0% |
| `holm` | monotonic | 5 | 100.0% |
| `naive_raw` | binary_shift | 5 | 100.0% |
| `naive_raw` | cat_cat | 9 | 100.0% |
| `naive_raw` | categorical_shift | 7 | 100.0% |
| `naive_raw` | induced | 8 | 75.0% |
| `naive_raw` | latent_factor | 12 | 100.0% |
| `naive_raw` | linear | 6 | 100.0% |
| `naive_raw` | monotonic | 5 | 100.0% |
| `naive_tests` | binary_shift | 5 | 100.0% |
| `naive_tests` | cat_cat | 9 | 100.0% |
| `naive_tests` | categorical_shift | 7 | 71.4% |
| `naive_tests` | induced | 8 | 37.5% |
| `naive_tests` | latent_factor | 12 | 100.0% |
| `naive_tests` | linear | 6 | 100.0% |
| `naive_tests` | monotonic | 5 | 100.0% |
| `veridata_full` | binary_shift | 5 | 100.0% |
| `veridata_full` | cat_cat | 9 | 100.0% |
| `veridata_full` | categorical_shift | 7 | 100.0% |
| `veridata_full` | induced | 8 | 50.0% |
| `veridata_full` | latent_factor | 12 | 100.0% |
| `veridata_full` | linear | 6 | 100.0% |
| `veridata_full` | monotonic | 5 | 100.0% |
| `veridata_nocorrection` | binary_shift | 5 | 100.0% |
| `veridata_nocorrection` | cat_cat | 9 | 100.0% |
| `veridata_nocorrection` | categorical_shift | 7 | 100.0% |
| `veridata_nocorrection` | induced | 8 | 87.5% |
| `veridata_nocorrection` | latent_factor | 12 | 100.0% |
| `veridata_nocorrection` | linear | 6 | 100.0% |
| `veridata_nocorrection` | monotonic | 5 | 100.0% |

## Recall by sample size

| System | n | Truths | Recall |
| :--- | ---: | ---: | ---: |
| `bh_only` | 250 | 7 | 100.0% |
| `bh_only` | 300 | 29 | 75.9% |
| `bh_only` | 400 | 16 | 100.0% |
| `bonferroni` | 250 | 7 | 71.4% |
| `bonferroni` | 300 | 29 | 79.3% |
| `bonferroni` | 400 | 16 | 100.0% |
| `by` | 250 | 7 | 71.4% |
| `by` | 300 | 29 | 75.9% |
| `by` | 400 | 16 | 100.0% |
| `floor_only` | 250 | 7 | 100.0% |
| `floor_only` | 300 | 29 | 93.1% |
| `floor_only` | 400 | 16 | 100.0% |
| `holm` | 250 | 7 | 71.4% |
| `holm` | 300 | 29 | 79.3% |
| `holm` | 400 | 16 | 100.0% |
| `naive_raw` | 250 | 7 | 100.0% |
| `naive_raw` | 300 | 29 | 93.1% |
| `naive_raw` | 400 | 16 | 100.0% |
| `naive_tests` | 250 | 7 | 100.0% |
| `naive_tests` | 300 | 29 | 75.9% |
| `naive_tests` | 400 | 16 | 100.0% |
| `veridata_full` | 250 | 7 | 100.0% |
| `veridata_full` | 300 | 29 | 86.2% |
| `veridata_full` | 400 | 16 | 100.0% |
| `veridata_nocorrection` | 250 | 7 | 100.0% |
| `veridata_nocorrection` | 300 | 29 | 96.6% |
| `veridata_nocorrection` | 400 | 16 | 100.0% |
