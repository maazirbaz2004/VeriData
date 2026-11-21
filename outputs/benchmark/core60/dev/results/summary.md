# Benchmark results — `core60` / `dev`

Primary direction mode (`if_reported`): a true pair reported with the wrong sign / higher group counts as a false discovery. Brackets are 95% bootstrap CIs over datasets (2,000 resamples).

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

## Pair-only matching (direction ignored)

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

## Recall by effect form

| System | Form | Truths | Recall |
| :--- | :--- | ---: | ---: |
| `bh_only` | binary_shift | 52 | 61.5% |
| `bh_only` | cat_cat | 70 | 84.3% |
| `bh_only` | categorical_shift | 41 | 63.4% |
| `bh_only` | induced | 61 | 57.4% |
| `bh_only` | latent_factor | 93 | 94.6% |
| `bh_only` | linear | 66 | 75.8% |
| `bh_only` | monotonic | 22 | 77.3% |
| `bonferroni` | binary_shift | 52 | 73.1% |
| `bonferroni` | cat_cat | 70 | 64.3% |
| `bonferroni` | categorical_shift | 41 | 63.4% |
| `bonferroni` | induced | 61 | 54.1% |
| `bonferroni` | latent_factor | 93 | 93.5% |
| `bonferroni` | linear | 66 | 72.7% |
| `bonferroni` | monotonic | 22 | 63.6% |
| `by` | binary_shift | 52 | 69.2% |
| `by` | cat_cat | 70 | 60.0% |
| `by` | categorical_shift | 41 | 56.1% |
| `by` | induced | 61 | 54.1% |
| `by` | latent_factor | 93 | 93.5% |
| `by` | linear | 66 | 72.7% |
| `by` | monotonic | 22 | 63.6% |
| `floor_only` | binary_shift | 52 | 73.1% |
| `floor_only` | cat_cat | 70 | 87.1% |
| `floor_only` | categorical_shift | 41 | 75.6% |
| `floor_only` | induced | 61 | 63.9% |
| `floor_only` | latent_factor | 93 | 97.8% |
| `floor_only` | linear | 66 | 80.3% |
| `floor_only` | monotonic | 22 | 81.8% |
| `holm` | binary_shift | 52 | 73.1% |
| `holm` | cat_cat | 70 | 64.3% |
| `holm` | categorical_shift | 41 | 63.4% |
| `holm` | induced | 61 | 54.1% |
| `holm` | latent_factor | 93 | 93.5% |
| `holm` | linear | 66 | 72.7% |
| `holm` | monotonic | 22 | 63.6% |
| `naive_raw` | binary_shift | 52 | 80.8% |
| `naive_raw` | cat_cat | 70 | 94.3% |
| `naive_raw` | categorical_shift | 41 | 75.6% |
| `naive_raw` | induced | 61 | 72.1% |
| `naive_raw` | latent_factor | 93 | 97.8% |
| `naive_raw` | linear | 66 | 84.8% |
| `naive_raw` | monotonic | 22 | 86.4% |
| `naive_tests` | binary_shift | 52 | 57.7% |
| `naive_tests` | cat_cat | 70 | 77.1% |
| `naive_tests` | categorical_shift | 41 | 63.4% |
| `naive_tests` | induced | 61 | 52.5% |
| `naive_tests` | latent_factor | 93 | 94.6% |
| `naive_tests` | linear | 66 | 72.7% |
| `naive_tests` | monotonic | 22 | 72.7% |
| `veridata_full` | binary_shift | 52 | 75.0% |
| `veridata_full` | cat_cat | 70 | 72.9% |
| `veridata_full` | categorical_shift | 41 | 68.3% |
| `veridata_full` | induced | 61 | 59.0% |
| `veridata_full` | latent_factor | 93 | 97.8% |
| `veridata_full` | linear | 66 | 74.2% |
| `veridata_full` | monotonic | 22 | 72.7% |
| `veridata_nocorrection` | binary_shift | 52 | 86.5% |
| `veridata_nocorrection` | cat_cat | 70 | 94.3% |
| `veridata_nocorrection` | categorical_shift | 41 | 80.5% |
| `veridata_nocorrection` | induced | 61 | 77.0% |
| `veridata_nocorrection` | latent_factor | 93 | 98.9% |
| `veridata_nocorrection` | linear | 66 | 89.4% |
| `veridata_nocorrection` | monotonic | 22 | 90.9% |

## Recall by sample size

| System | n | Truths | Recall |
| :--- | ---: | ---: | ---: |
| `bh_only` | 100 | 92 | 44.6% |
| `bh_only` | 1000 | 104 | 88.5% |
| `bh_only` | 300 | 100 | 69.0% |
| `bh_only` | 5000 | 109 | 96.3% |
| `bonferroni` | 100 | 92 | 33.7% |
| `bonferroni` | 1000 | 104 | 86.5% |
| `bonferroni` | 300 | 100 | 71.0% |
| `bonferroni` | 5000 | 109 | 90.8% |
| `by` | 100 | 92 | 27.2% |
| `by` | 1000 | 104 | 85.6% |
| `by` | 300 | 100 | 70.0% |
| `by` | 5000 | 109 | 90.8% |
| `floor_only` | 100 | 92 | 68.5% |
| `floor_only` | 1000 | 104 | 89.4% |
| `floor_only` | 300 | 100 | 81.0% |
| `floor_only` | 5000 | 109 | 86.2% |
| `holm` | 100 | 92 | 33.7% |
| `holm` | 1000 | 104 | 86.5% |
| `holm` | 300 | 100 | 71.0% |
| `holm` | 5000 | 109 | 90.8% |
| `naive_raw` | 100 | 92 | 68.5% |
| `naive_raw` | 1000 | 104 | 94.2% |
| `naive_raw` | 300 | 100 | 81.0% |
| `naive_raw` | 5000 | 109 | 98.2% |
| `naive_tests` | 100 | 92 | 44.6% |
| `naive_tests` | 1000 | 104 | 86.5% |
| `naive_tests` | 300 | 100 | 69.0% |
| `naive_tests` | 5000 | 109 | 86.2% |
| `veridata_full` | 100 | 92 | 47.8% |
| `veridata_full` | 1000 | 104 | 89.4% |
| `veridata_full` | 300 | 100 | 74.0% |
| `veridata_full` | 5000 | 109 | 90.8% |
| `veridata_nocorrection` | 100 | 92 | 71.7% |
| `veridata_nocorrection` | 1000 | 104 | 97.1% |
| `veridata_nocorrection` | 300 | 100 | 87.0% |
| `veridata_nocorrection` | 5000 | 109 | 99.1% |
