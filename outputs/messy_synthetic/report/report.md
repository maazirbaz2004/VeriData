# VeriData findings report — `messy_synthetic`

2,000 rows × 13 columns after cleaning · VeriData 0.1.0 · config `3a94527dfcc5` · generated 2026-11-21

## 1. Executive summary

VeriData tested 32 column pairs. 6 of them had a raw p-value below 0.05, the usual threshold. After correcting for the number of tests (Benjamini-Hochberg method) and requiring an effect that is not negligible, 5 remain as validated findings. The others were rejected for the reasons shown below. Every finding is an association, not evidence of cause and effect.

- Tests run: 32
- Raw p below 0.05: 6
- Validated findings: 5
- Rejected — effect too small: 27
- Rejected — not enough data: 4
- Rejected — not supported after correction: 27

_A rejected test can have more than a single reason, so these counts can add up to more than the number of rejected tests._

![5 validated findings out of 32 tests](figures/summary_rejections.png)

**Highlights** (largest effects):

- `income` ↔ `monthly_spend`: large (Spearman rho = 0.89)
- `tenure_months` ↔ `churned`: medium (Hedges' g = 0.71)
- `churned` ↔ `satisfaction`: small (Cramér's V = 0.28)

## 2. Validated findings

### 2.1 `income` ↔ `monthly_spend`

income and monthly_spend are positively associated (Spearman rank correlation rho = 0.89, 95% CI 0.88 to 0.91; n = 1,840). The relationship is monotonic and may not be linear. The association is large. After correcting for 32 tests (Benjamini-Hochberg method, false discovery rate 5.0%), the association is statistically supported (adjusted p <0.001). The data were not close enough to the shape a parametric test needs, so a rank-based test was used instead. A second test (Pearson correlation test) did not fully agree, so treat this result with some caution. This is an association, not evidence of cause and effect.

![income and monthly_spend are positively associated](figures/f01_income__monthly_spend.png)

| | |
| :--- | :--- |
| Test used | Spearman rank correlation test |
| Test statistic | 0.89 |
| Degrees of freedom | 1,838 |
| Raw p-value | <0.001 |
| Adjusted p-value (q) | <0.001 |
| Effect size | Spearman rho = 0.89 (95% CI 0.88 to 0.91), large |
| Records used | 1,840 |
| Flags | test sensitive |

<details markdown="1">
<summary>How was this tested?</summary>

The columns were skewed, had outliers or many ties, so the rank-based Spearman correlation was used.

</details>

<details markdown="1">
<summary>Where do the numbers come from?</summary>

| Fact | Shown as | Comes from |
| :--- | :--- | :--- |
| `alt_effect_value` | 0.09 | `TestResult.descriptives.sensitivity_alt_test.effect_value` |
| `alt_test_name` | Pearson correlation test | `TestResult.descriptives.sensitivity_alt_test.test_name` |
| `ci_high` | 0.91 | `TestResult.effect.ci_high` |
| `ci_low` | 0.88 | `TestResult.effect.ci_low` |
| `col_a` | income | `Hypothesis.column_a` |
| `col_b` | monthly_spend | `Hypothesis.column_b` |
| `comparable_value` | 0.89 | `TestResult.effect.comparable_value` |
| `df` | 1,838 | `TestResult.df` |
| `direction_word` | positive | `TestResult.direction_observed` |
| `effect_abs` | 0.89 | `abs(TestResult.effect.value)` |
| `effect_name` | Spearman rho | `TestResult.effect.name` |
| `effect_value` | 0.89 | `TestResult.effect.value` |
| `family_size` | 32 | `ValidationDecision.family_size` |
| `magnitude_label` | large | `TestResult.effect.magnitude` |
| `n_used` | 1,840 | `TestResult.n_used` |
| `ols_slope` | 0.00030 | `TestResult.descriptives.ols_slope` |
| `p_raw` | <0.001 | `ValidationDecision.p_raw` |
| `q_value` | <0.001 | `ValidationDecision.q_value` |
| `statistic` | 0.89 | `TestResult.statistic` |
| `test_name` | Spearman rank correlation test | `TestResult.test_name` |

</details>

### 2.2 `tenure_months` ↔ `churned`

Among 1,970 records, the average tenure_months was 68.84 for churned = No and 45.44 for churned = Yes (difference 23.40, 95% CI 20.38 to 26.41). On average, tenure_months is higher for churned = No. The difference is medium (Hedges' g = 0.71, 95% CI 0.62 to 0.81). After correcting for 32 tests (Benjamini-Hochberg method, false discovery rate 5.0%), the association is statistically supported (adjusted p <0.001). This is an association, not evidence of cause and effect.

![tenure_months is higher on average for churned = No](figures/f02_tenure_months__churned.png)

| | |
| :--- | :--- |
| Test used | Welch's t-test |
| Test statistic | 15.22 |
| Degrees of freedom | 1,415.6 |
| Raw p-value | <0.001 |
| Adjusted p-value (q) | <0.001 |
| Effect size | Hedges' g = 0.71 (95% CI 0.62 to 0.81), medium |
| Records used | 1,970 |

<details markdown="1">
<summary>How was this tested?</summary>

Both groups looked close enough to normal (or were large enough), so the means were compared with Welch's t-test, which does not assume equal spreads.

</details>

<details markdown="1">
<summary>Where do the numbers come from?</summary>

| Fact | Shown as | Comes from |
| :--- | :--- | :--- |
| `alt_effect_value` | 0.39 | `TestResult.descriptives.sensitivity_alt_test.effect_value` |
| `alt_test_name` | Mann-Whitney U test | `TestResult.descriptives.sensitivity_alt_test.test_name` |
| `ci_high` | 0.81 | `TestResult.effect.ci_high` |
| `ci_low` | 0.62 | `TestResult.effect.ci_low` |
| `col_a` | tenure_months | `Hypothesis.column_a` |
| `col_b` | churned | `Hypothesis.column_b` |
| `comparable_value` | 0.71 | `TestResult.effect.comparable_value` |
| `df` | 1,415.6 | `TestResult.df` |
| `direction_word` | a_greater | `TestResult.direction_observed` |
| `effect_abs` | 0.71 | `abs(TestResult.effect.value)` |
| `effect_name` | Hedges' g | `TestResult.effect.name` |
| `effect_value` | 0.71 | `TestResult.effect.value` |
| `family_size` | 32 | `ValidationDecision.family_size` |
| `g1` | No | `TestResult.descriptives.group_order[0]` |
| `g2` | Yes | `TestResult.descriptives.group_order[1]` |
| `group_label0` | No | `TestResult.group_sizes key 0` |
| `group_label1` | Yes | `TestResult.group_sizes key 1` |
| `group_size0` | 1,294 | `TestResult.group_sizes[No]` |
| `group_size1` | 676 | `TestResult.group_sizes[Yes]` |
| `higher_group` | No | `TestResult.descriptives.higher_group` |
| `magnitude_label` | medium | `TestResult.effect.magnitude` |
| `mean_diff` | 23.40 | `TestResult.descriptives.mean_diff` |
| `mean_diff_abs` | 23.40 | `abs(TestResult.descriptives.mean_diff)` |
| `mean_diff_ci_high` | 26.41 | `TestResult.descriptives.mean_diff_ci_high` |
| `mean_diff_ci_low` | 20.38 | `TestResult.descriptives.mean_diff_ci_low` |
| `mean_g1` | 68.84 | `TestResult.descriptives.groups[No].mean` |
| `mean_g2` | 45.44 | `TestResult.descriptives.groups[Yes].mean` |
| `mean_high` | 68.84 | `same as mean_g1` |
| `mean_other` | 45.44 | `same as mean_g2` |
| `median_g1` | 71.00 | `TestResult.descriptives.groups[No].median` |
| `median_g2` | 40.00 | `TestResult.descriptives.groups[Yes].median` |
| `median_high` | 71.00 | `same as median_g1` |
| `median_other` | 40.00 | `same as median_g2` |
| `n_g1` | 1,294 | `TestResult.descriptives.groups[No].n` |
| `n_g2` | 676 | `TestResult.descriptives.groups[Yes].n` |
| `n_groups` | 2 | `len(TestResult.group_sizes)` |
| `n_used` | 1,970 | `TestResult.n_used` |
| `other_group` | Yes | `the other group in TestResult.descriptives.group_order` |
| `p_raw` | <0.001 | `ValidationDecision.p_raw` |
| `q_value` | <0.001 | `ValidationDecision.q_value` |
| `sd_g1` | 33.20 | `TestResult.descriptives.groups[No].sd` |
| `sd_g2` | 31.96 | `TestResult.descriptives.groups[Yes].sd` |
| `statistic` | 15.22 | `TestResult.statistic` |
| `test_name` | Welch's t-test | `TestResult.test_name` |

</details>

### 2.3 `churned` ↔ `satisfaction`

churned and satisfaction are associated (Cramér's V = 0.28, 95% CI 0.24 to 0.33, small; n = 1,940). The largest departure from independence: fewer records with churned = No and satisfaction = 1.0 than expected if the columns were unrelated (82 observed vs 131.75 expected). After correcting for 32 tests (Benjamini-Hochberg method, false discovery rate 5.0%), the association is statistically supported (adjusted p <0.001). This is an association, not evidence of cause and effect.

![churned and satisfaction are associated](figures/f03_churned__satisfaction.png)

| | |
| :--- | :--- |
| Test used | chi-square test of independence |
| Test statistic | 155.96 |
| Degrees of freedom | 4 |
| Raw p-value | <0.001 |
| Adjusted p-value (q) | <0.001 |
| Effect size | Cramér's V = 0.28 (95% CI 0.24 to 0.33), small |
| Records used | 1,940 |

<details markdown="1">
<summary>How was this tested?</summary>

Every cell of the table had enough expected records, so the standard chi-square test of independence was used.

</details>

<details markdown="1">
<summary>Where do the numbers come from?</summary>

| Fact | Shown as | Comes from |
| :--- | :--- | :--- |
| `cell1_col` | 1.0 | `TestResult.descriptives.top_residual_cells[0].col` |
| `cell1_expected` | 131.75 | `TestResult.descriptives.top_residual_cells[0].expected` |
| `cell1_more_or_fewer` | fewer | `observed vs expected count` |
| `cell1_observed` | 82 | `TestResult.descriptives.top_residual_cells[0].observed` |
| `cell1_row` | No | `TestResult.descriptives.top_residual_cells[0].row` |
| `cell2_col` | 1.0 | `TestResult.descriptives.top_residual_cells[1].col` |
| `cell2_expected` | 68.25 | `TestResult.descriptives.top_residual_cells[1].expected` |
| `cell2_more_or_fewer` | more | `observed vs expected count` |
| `cell2_observed` | 118 | `TestResult.descriptives.top_residual_cells[1].observed` |
| `cell2_row` | Yes | `TestResult.descriptives.top_residual_cells[1].row` |
| `ci_high` | 0.33 | `TestResult.effect.ci_high` |
| `ci_low` | 0.24 | `TestResult.effect.ci_low` |
| `col_a` | churned | `Hypothesis.column_a` |
| `col_b` | satisfaction | `Hypothesis.column_b` |
| `col_label0` | 1.0 | `TestResult.descriptives.col_labels[0]` |
| `col_label1` | 2.0 | `TestResult.descriptives.col_labels[1]` |
| `col_label2` | 3.0 | `TestResult.descriptives.col_labels[2]` |
| `col_label3` | 4.0 | `TestResult.descriptives.col_labels[3]` |
| `col_label4` | 5.0 | `TestResult.descriptives.col_labels[4]` |
| `comparable_value` | 0.28 | `TestResult.effect.comparable_value` |
| `df` | 4 | `TestResult.df` |
| `direction_word` | any | `TestResult.direction_observed` |
| `effect_abs` | 0.28 | `abs(TestResult.effect.value)` |
| `effect_name` | Cramér's V | `TestResult.effect.name` |
| `effect_value` | 0.28 | `TestResult.effect.value` |
| `family_size` | 32 | `ValidationDecision.family_size` |
| `magnitude_label` | small | `TestResult.effect.magnitude` |
| `n_cols_table` | 5 | `len(TestResult.descriptives.col_labels)` |
| `n_rows_table` | 2 | `len(TestResult.descriptives.row_labels)` |
| `n_used` | 1,940 | `TestResult.n_used` |
| `p_raw` | <0.001 | `ValidationDecision.p_raw` |
| `q_value` | <0.001 | `ValidationDecision.q_value` |
| `row_label0` | No | `TestResult.descriptives.row_labels[0]` |
| `row_label1` | Yes | `TestResult.descriptives.row_labels[1]` |
| `statistic` | 155.96 | `TestResult.statistic` |
| `test_name` | chi-square test of independence | `TestResult.test_name` |

</details>

### 2.4 `income` ↔ `membership`

Values of income tend to differ across the 3 groups of membership: highest for Gold (median 92,981.43) and lowest for Basic (median 40,303.65). About 26.3% of the variation in the ranks of income is associated with membership (epsilon squared = 0.26, 95% CI 0.22 to 0.30, large). After correcting for 32 tests (Benjamini-Hochberg method, false discovery rate 5.0%), the association is statistically supported (adjusted p <0.001). The data were not close enough to the shape a parametric test needs, so a rank-based test was used instead. This is an association, not evidence of cause and effect.

![income tends to be higher for membership = Gold](figures/f04_income__membership.png)

| | |
| :--- | :--- |
| Test used | Kruskal-Wallis test |
| Test statistic | 483.74 |
| Degrees of freedom | 2 |
| Raw p-value | <0.001 |
| Adjusted p-value (q) | <0.001 |
| Effect size | epsilon squared = 0.26 (95% CI 0.22 to 0.30), large |
| Records used | 1,840 |

<details markdown="1">
<summary>How was this tested?</summary>

Some groups were not close enough to normal, so the rank-based Kruskal-Wallis test was used.

</details>

<details markdown="1">
<summary>Where do the numbers come from?</summary>

| Fact | Shown as | Comes from |
| :--- | :--- | :--- |
| `ci_high` | 0.30 | `TestResult.effect.ci_high` |
| `ci_low` | 0.22 | `TestResult.effect.ci_low` |
| `col_a` | income | `Hypothesis.column_a` |
| `col_b` | membership | `Hypothesis.column_b` |
| `comparable_value` | 0.26 | `TestResult.effect.comparable_value` |
| `df` | 2 | `TestResult.df` |
| `direction_word` | any | `TestResult.direction_observed` |
| `effect_abs` | 0.26 | `abs(TestResult.effect.value)` |
| `effect_name` | epsilon squared | `TestResult.effect.name` |
| `effect_value` | 0.26 | `TestResult.effect.value` |
| `eta_sq_pct` | 26.3% | `100 * TestResult.effect.value (epsilon_squared)` |
| `family_size` | 32 | `ValidationDecision.family_size` |
| `g1` | Basic | `TestResult.descriptives.group_order[0]` |
| `g2` | Gold | `TestResult.descriptives.group_order[1]` |
| `g3` | Silver | `TestResult.descriptives.group_order[2]` |
| `group_label0` | Basic | `TestResult.group_sizes key 0` |
| `group_label1` | Gold | `TestResult.group_sizes key 1` |
| `group_label2` | Silver | `TestResult.group_sizes key 2` |
| `group_size0` | 922 | `TestResult.group_sizes[Basic]` |
| `group_size1` | 327 | `TestResult.group_sizes[Gold]` |
| `group_size2` | 591 | `TestResult.group_sizes[Silver]` |
| `highest_group` | Gold | `TestResult.descriptives.highest_group` |
| `lowest_group` | Basic | `TestResult.descriptives.lowest_group` |
| `magnitude_label` | large | `TestResult.effect.magnitude` |
| `mean_g1` | 49,668.99 | `TestResult.descriptives.groups[Basic].mean` |
| `mean_g2` | 106,497.02 | `TestResult.descriptives.groups[Gold].mean` |
| `mean_g3` | 69,340.81 | `TestResult.descriptives.groups[Silver].mean` |
| `mean_high` | 106,497.02 | `same as mean_g2` |
| `mean_low` | 49,668.99 | `same as mean_g1` |
| `median_g1` | 40,303.65 | `TestResult.descriptives.groups[Basic].median` |
| `median_g2` | 92,981.43 | `TestResult.descriptives.groups[Gold].median` |
| `median_g3` | 61,399.87 | `TestResult.descriptives.groups[Silver].median` |
| `median_high` | 92,981.43 | `same as median_g2` |
| `median_low` | 40,303.65 | `same as median_g1` |
| `n_g1` | 922 | `TestResult.descriptives.groups[Basic].n` |
| `n_g2` | 327 | `TestResult.descriptives.groups[Gold].n` |
| `n_g3` | 591 | `TestResult.descriptives.groups[Silver].n` |
| `n_groups` | 3 | `len(TestResult.group_sizes)` |
| `n_used` | 1,840 | `TestResult.n_used` |
| `other_group` | Basic | `the other group in TestResult.descriptives.group_order` |
| `p_raw` | <0.001 | `ValidationDecision.p_raw` |
| `q_value` | <0.001 | `ValidationDecision.q_value` |
| `sd_g1` | 68,414.73 | `TestResult.descriptives.groups[Basic].sd` |
| `sd_g2` | 139,642.83 | `TestResult.descriptives.groups[Gold].sd` |
| `sd_g3` | 88,995.19 | `TestResult.descriptives.groups[Silver].sd` |
| `statistic` | 483.74 | `TestResult.statistic` |
| `test_name` | Kruskal-Wallis test | `TestResult.test_name` |

</details>

### 2.5 `monthly_spend` ↔ `membership`

Values of monthly_spend tend to differ across the 3 groups of membership: highest for Gold (median 217.99) and lowest for Basic (median 110.66). About 22.8% of the variation in the ranks of monthly_spend is associated with membership (epsilon squared = 0.23, 95% CI 0.19 to 0.26, large). After correcting for 32 tests (Benjamini-Hochberg method, false discovery rate 5.0%), the association is statistically supported (adjusted p <0.001). The data were not close enough to the shape a parametric test needs, so a rank-based test was used instead. This is an association, not evidence of cause and effect.

![monthly_spend tends to be higher for membership = Gold](figures/f05_monthly_spend__membership.png)

| | |
| :--- | :--- |
| Test used | Kruskal-Wallis test |
| Test statistic | 455.48 |
| Degrees of freedom | 2 |
| Raw p-value | <0.001 |
| Adjusted p-value (q) | <0.001 |
| Effect size | epsilon squared = 0.23 (95% CI 0.19 to 0.26), large |
| Records used | 2,000 |

<details markdown="1">
<summary>How was this tested?</summary>

Some groups were not close enough to normal, so the rank-based Kruskal-Wallis test was used.

</details>

<details markdown="1">
<summary>Where do the numbers come from?</summary>

| Fact | Shown as | Comes from |
| :--- | :--- | :--- |
| `ci_high` | 0.26 | `TestResult.effect.ci_high` |
| `ci_low` | 0.19 | `TestResult.effect.ci_low` |
| `col_a` | monthly_spend | `Hypothesis.column_a` |
| `col_b` | membership | `Hypothesis.column_b` |
| `comparable_value` | 0.23 | `TestResult.effect.comparable_value` |
| `df` | 2 | `TestResult.df` |
| `direction_word` | any | `TestResult.direction_observed` |
| `effect_abs` | 0.23 | `abs(TestResult.effect.value)` |
| `effect_name` | epsilon squared | `TestResult.effect.name` |
| `effect_value` | 0.23 | `TestResult.effect.value` |
| `eta_sq_pct` | 22.8% | `100 * TestResult.effect.value (epsilon_squared)` |
| `family_size` | 32 | `ValidationDecision.family_size` |
| `g1` | Basic | `TestResult.descriptives.group_order[0]` |
| `g2` | Gold | `TestResult.descriptives.group_order[1]` |
| `g3` | Silver | `TestResult.descriptives.group_order[2]` |
| `group_label0` | Basic | `TestResult.group_sizes key 0` |
| `group_label1` | Gold | `TestResult.group_sizes key 1` |
| `group_label2` | Silver | `TestResult.group_sizes key 2` |
| `group_size0` | 988 | `TestResult.group_sizes[Basic]` |
| `group_size1` | 358 | `TestResult.group_sizes[Gold]` |
| `group_size2` | 654 | `TestResult.group_sizes[Silver]` |
| `highest_group` | Gold | `TestResult.descriptives.highest_group` |
| `lowest_group` | Basic | `TestResult.descriptives.lowest_group` |
| `magnitude_label` | large | `TestResult.effect.magnitude` |
| `mean_g1` | 130.70 | `TestResult.descriptives.groups[Basic].mean` |
| `mean_g2` | 238.47 | `TestResult.descriptives.groups[Gold].mean` |
| `mean_g3` | 194.32 | `TestResult.descriptives.groups[Silver].mean` |
| `mean_high` | 238.47 | `same as mean_g2` |
| `mean_low` | 130.70 | `same as mean_g1` |
| `median_g1` | 110.66 | `TestResult.descriptives.groups[Basic].median` |
| `median_g2` | 217.99 | `TestResult.descriptives.groups[Gold].median` |
| `median_g3` | 154.45 | `TestResult.descriptives.groups[Silver].median` |
| `median_high` | 217.99 | `same as median_g2` |
| `median_low` | 110.66 | `same as median_g1` |
| `n_g1` | 988 | `TestResult.descriptives.groups[Basic].n` |
| `n_g2` | 358 | `TestResult.descriptives.groups[Gold].n` |
| `n_g3` | 654 | `TestResult.descriptives.groups[Silver].n` |
| `n_groups` | 3 | `len(TestResult.group_sizes)` |
| `n_used` | 2,000 | `TestResult.n_used` |
| `other_group` | Basic | `the other group in TestResult.descriptives.group_order` |
| `p_raw` | <0.001 | `ValidationDecision.p_raw` |
| `q_value` | <0.001 | `ValidationDecision.q_value` |
| `sd_g1` | 219.96 | `TestResult.descriptives.groups[Basic].sd` |
| `sd_g2` | 235.34 | `TestResult.descriptives.groups[Gold].sd` |
| `sd_g3` | 437.09 | `TestResult.descriptives.groups[Silver].sd` |
| `statistic` | 455.48 | `TestResult.statistic` |
| `test_name` | Kruskal-Wallis test | `TestResult.test_name` |

</details>

![Effect sizes of the 5 validated findings](figures/summary_forest.png)

## 3. Patterns that looked interesting but were rejected

These patterns had the lowest raw p-values among the rejected tests. Each of them would look like a discovery to a naive analysis that tests 32 pairs without correction.

| Columns | Test | Raw p | Adjusted p | Effect | Why it was rejected |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `income` ↔ `churned` | Mann-Whitney U test | 0.020 | 0.105 | rank-biserial correlation = 0.07 | Raw p = 0.020, but after correcting for 32 tests the adjusted p is 0.105. With this many comparisons, a pattern like this is expected by chance, so it is not reported as a finding. Also, the effect is tiny but the effect is negligible (rank-biserial correlation = 0.07, below the 0.10 threshold), so it has little practical importance. |
| `monthly_spend` ↔ `churned` | Mann-Whitney U test | 0.050 | 0.226 | rank-biserial correlation = 0.05 | Raw p = 0.050, but after correcting for 32 tests the adjusted p is 0.226. With this many comparisons, a pattern like this is expected by chance, so it is not reported as a finding. Also, the effect is tiny but the effect is negligible (rank-biserial correlation = 0.05, below the 0.10 threshold), so it has little practical importance. |
| `gender` ↔ `satisfaction` | Monte Carlo (permutation) chi-square test | 0.159 | 0.634 | Cramér's V = 0.03 | Raw p = 0.159, but after correcting for 32 tests the adjusted p is 0.634. With this many comparisons, a pattern like this is expected by chance, so it is not reported as a finding. Also, the effect is tiny but the effect is negligible (Cramér's V = 0.03 (comparable value 0.05), below the 0.10 threshold), so it has little practical importance. |
| `monthly_spend` ↔ `region` | Kruskal-Wallis test | 0.198 | 0.703 | epsilon squared = 0.00 | Raw p = 0.198, but after correcting for 32 tests the adjusted p is 0.703. With this many comparisons, a pattern like this is expected by chance, so it is not reported as a finding. Also, the effect is tiny but the effect is negligible (epsilon squared = 0.00, below the 0.01 threshold), so it has little practical importance. |
| `monthly_spend` ↔ `tenure_months` | Spearman rank correlation test | 0.288 | 0.836 | Spearman rho = -0.02 | Raw p = 0.288, but after correcting for 32 tests the adjusted p is 0.836. With this many comparisons, a pattern like this is expected by chance, so it is not reported as a finding. Also, the effect is tiny but the effect is negligible (Spearman rho = -0.02, below the 0.10 threshold), so it has little practical importance. |
| `churned` ↔ `membership` | chi-square test of independence | 0.295 | 0.836 | Cramér's V = 0.01 | Raw p = 0.295, but after correcting for 32 tests the adjusted p is 0.836. With this many comparisons, a pattern like this is expected by chance, so it is not reported as a finding. Also, the effect is tiny but the effect is negligible (Cramér's V = 0.01 (comparable value 0.01), below the 0.10 threshold), so it has little practical importance. |
| `income` ↔ `region` | Kruskal-Wallis test | 0.314 | 0.836 | epsilon squared = 0.00 | Raw p = 0.314, but after correcting for 32 tests the adjusted p is 0.836. With this many comparisons, a pattern like this is expected by chance, so it is not reported as a finding. Also, the effect is tiny but the effect is negligible (epsilon squared = 0.00, below the 0.01 threshold), so it has little practical importance. |
| `gender` ↔ `region` | chi-square test of independence | 0.359 | 0.853 | Cramér's V = 0.01 | Raw p = 0.359, but after correcting for 32 tests the adjusted p is 0.853. With this many comparisons, a pattern like this is expected by chance, so it is not reported as a finding. Also, the effect is tiny but the effect is negligible (Cramér's V = 0.01 (comparable value 0.02), below the 0.10 threshold), so it has little practical importance. |
| `membership` ↔ `region` | chi-square test of independence | 0.421 | 0.853 | Cramér's V = 0.01 | Raw p = 0.421, but after correcting for 32 tests the adjusted p is 0.853. With this many comparisons, a pattern like this is expected by chance, so it is not reported as a finding. Also, the effect is tiny but the effect is negligible (Cramér's V = 0.01 (comparable value 0.01), below the 0.10 threshold), so it has little practical importance. |
| `income` ↔ `tenure_months` | Spearman rank correlation test | 0.439 | 0.853 | Spearman rho = -0.02 | Raw p = 0.439, but after correcting for 32 tests the adjusted p is 0.853. With this many comparisons, a pattern like this is expected by chance, so it is not reported as a finding. Also, the effect is tiny but the effect is negligible (Spearman rho = -0.02, below the 0.10 threshold), so it has little practical importance. |

![Correcting for 32 tests: points under the line pass](figures/summary_bh.png)

![Effect size vs evidence: validated findings need both](figures/summary_volcano.png)

## 4. Likely derived or duplicated columns

None found.

## 5. Data quality summary

- Raw file: 2,090 rows × 15 columns; after cleaning: 2,000 rows × 13 columns.
- Missing cells in the raw file: 13.2%.
- Exact duplicate rows removed: 80.
- Logged cleaning changes: 34, touching 12,214 cells (see the cleaning log).

## 6. Methods

**Hypotheses.** Hypotheses were generated in exhaustive mode from the column types only, before any test was run. 9 of 13 columns were eligible and 32 pairs were tested. A language model was not used to choose or change the tests.

**Tests.** Each pair is tested with a fixed, unit-tested test chosen by rules that check the data's shape first:

| Relationship | Default test | Fallback when assumptions fail |
| :--- | :--- | :--- |
| numeric vs a binary column | Welch's t-test | Mann-Whitney U test |
| numeric vs several groups | Welch's ANOVA | Kruskal-Wallis test |
| numeric vs numeric | Pearson correlation | Spearman rank correlation |
| category vs category | chi-square test | Fisher's exact test or a Monte Carlo (permutation) chi-square test |

Groups with fewer than 8 records are left out, and a pair needs at least 20 complete records. Groups of at least 50 records may use the parametric test when skewness stays below 2.00. Confidence intervals use 2,000 bootstrap resamples; permutation tests use 9,999 resamples.

**Correction.** All tests form a single family. The Benjamini-Hochberg method controls the false discovery rate at 5.0%: on average, at most this share of the reported findings should be false.

**Effect-size floors.** A result must also have an effect that is not negligible:

| Effect measure | Smallest effect reported |
| :--- | :--- |
| Hedges' g (binary groups) | 0.20 |
| rank-biserial correlation | 0.10 |
| Pearson r / Spearman rho | 0.10 |
| eta squared | 0.01 |
| epsilon squared | 0.01 |
| Cramér's V (comparable scale) | 0.10 |

**What 'validated' means.** A finding is validated when its adjusted p-value is below the false discovery rate, its effect is above the floor, and its test's assumptions were met or a suitable fallback test was used.

## 7. Limitations

- **Association, not causation.** Every finding describes how columns move together in this data. None of them shows that a column is the reason for another.
- **Rows are assumed independent.** The tests assume each row is a separate, unrelated record. Repeated measurements of the same person, place or time period break this assumption and make the results look more reliable than they are.
- **Pairwise only.** Each test looks at a single pair of columns. Interactions between several columns and confounding by a third column are not controlled for.
- **Correction under dependence.** The Benjamini-Hochberg correction assumes the tests are independent or positively dependent. Tests that share columns are dependent. In the planted-truth calibration it still kept the false discovery rate near the target with strongly correlated columns, but unusual (negative) dependence is not covered; the Benjamini-Yekutieli option (`stats.correction: by`) is the safer choice then.
- **Adjusted p-values are not per-finding error chances.** The correction controls the share of false findings across the whole list. A finding whose adjusted p-value is close to the cut-off is more likely to be a false lead than a finding far below it.
- **Effects of selected findings are optimistic.** Effect sizes and confidence intervals are reported for the findings that passed the checks, so they tend to be somewhat larger than the true effects. The intervals are not adjusted for this selection.
- **Missing data.** Each test uses the rows where both columns are present (pairwise deletion). If values are missing for a reason related to the columns, results can be biased.
- **Cleaning choices matter.** The results depend on the cleaning steps listed in the data quality section, such as removing duplicates and turning placeholder text into missing values.
- **Role of the language model.** No language model produced or changed any number in this report. The explanations are filled from fixed templates and every number is checked against the computed results.

## 8. Appendix

### All results

| Columns | Test | Raw p | Adjusted p | Effect | Decision |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `income` ↔ `monthly_spend` | Spearman rank correlation test | <0.001 | <0.001 | Spearman rho = 0.89 | validated |
| `income` ↔ `membership` | Kruskal-Wallis test | <0.001 | <0.001 | epsilon squared = 0.26 | validated |
| `monthly_spend` ↔ `membership` | Kruskal-Wallis test | <0.001 | <0.001 | epsilon squared = 0.23 | validated |
| `tenure_months` ↔ `churned` | Welch's t-test | <0.001 | <0.001 | Hedges' g = 0.71 | validated |
| `churned` ↔ `satisfaction` | chi-square test of independence | <0.001 | <0.001 | Cramér's V = 0.28 | validated |
| `income` ↔ `churned` | Mann-Whitney U test | 0.020 | 0.105 | rank-biserial correlation = 0.07 | rejected: not supported after correction, effect too small |
| `monthly_spend` ↔ `churned` | Mann-Whitney U test | 0.050 | 0.226 | rank-biserial correlation = 0.05 | rejected: not supported after correction, effect too small |
| `gender` ↔ `satisfaction` | Monte Carlo (permutation) chi-square test | 0.159 | 0.634 | Cramér's V = 0.03 | rejected: not supported after correction, effect too small |
| `monthly_spend` ↔ `region` | Kruskal-Wallis test | 0.198 | 0.703 | epsilon squared = 0.00 | rejected: not supported after correction, effect too small |
| `monthly_spend` ↔ `tenure_months` | Spearman rank correlation test | 0.288 | 0.836 | Spearman rho = -0.02 | rejected: not supported after correction, effect too small |
| `churned` ↔ `membership` | chi-square test of independence | 0.295 | 0.836 | Cramér's V = 0.01 | rejected: not supported after correction, effect too small |
| `income` ↔ `region` | Kruskal-Wallis test | 0.314 | 0.836 | epsilon squared = 0.00 | rejected: not supported after correction, effect too small |
| `gender` ↔ `region` | chi-square test of independence | 0.359 | 0.853 | Cramér's V = 0.01 | rejected: not supported after correction, effect too small |
| `membership` ↔ `region` | chi-square test of independence | 0.421 | 0.853 | Cramér's V = 0.01 | rejected: not supported after correction, effect too small |
| `income` ↔ `tenure_months` | Spearman rank correlation test | 0.439 | 0.853 | Spearman rho = -0.02 | rejected: not supported after correction, effect too small |
| `tenure_months` ↔ `region` | Welch's ANOVA | 0.456 | 0.853 | eta squared = 0.00 | rejected: not supported after correction, effect too small |
| `tenure_months` ↔ `satisfaction` | Welch's ANOVA | 0.475 | 0.853 | eta squared = 0.00 | rejected: not supported after correction, effect too small |
| `churned` ↔ `region` | chi-square test of independence | 0.480 | 0.853 | Cramér's V = 0.00 | rejected: not supported after correction, effect too small |
| `gender` ↔ `membership` | chi-square test of independence | 0.526 | 0.886 | Cramér's V = 0.00 | rejected: not supported after correction, effect too small |
| `tenure_months` ↔ `membership` | Welch's ANOVA | 0.602 | 0.942 | eta squared = 0.00 | rejected: not supported after correction, effect too small |
| `age` ↔ `satisfaction` | Welch's ANOVA | 0.618 | 0.942 | eta squared = 0.00 | rejected: not supported after correction, effect too small |
| `age` ↔ `churned` | Welch's t-test | 0.797 | 0.977 | Hedges' g = -0.01 | rejected: not supported after correction, effect too small |
| `membership` ↔ `satisfaction` | chi-square test of independence | 0.809 | 0.977 | Cramér's V = 0.00 | rejected: not supported after correction, effect too small |
| `churned` ↔ `gender` | chi-square test of independence | 0.827 | 0.977 | Cramér's V = 0.00 | rejected: not supported after correction, effect too small |
| `age` ↔ `membership` | Welch's ANOVA | 0.849 | 0.977 | eta squared = 0.00 | rejected: not supported after correction, effect too small |
| `age` ↔ `tenure_months` | Spearman rank correlation test | 0.859 | 0.977 | Spearman rho = 0.00 | rejected: not supported after correction, effect too small |
| `age` ↔ `income` | Spearman rank correlation test | 0.903 | 0.977 | Spearman rho = 0.00 | rejected: not supported after correction, effect too small |
| `age` ↔ `monthly_spend` | Spearman rank correlation test | 0.928 | 0.977 | Spearman rho = 0.00 | rejected: not supported after correction, effect too small |
| `region` ↔ `satisfaction` | chi-square test of independence | 0.940 | 0.977 | Cramér's V = 0.00 | rejected: not supported after correction, effect too small |
| `income` ↔ `satisfaction` | Kruskal-Wallis test | 0.952 | 0.977 | epsilon squared = 0.00 | rejected: not supported after correction, effect too small |
| `age` ↔ `region` | Welch's ANOVA | 0.966 | 0.977 | eta squared = 0.00 | rejected: not supported after correction, effect too small |
| `monthly_spend` ↔ `satisfaction` | Kruskal-Wallis test | 0.977 | 0.977 | epsilon squared = 0.00 | rejected: not supported after correction, effect too small |
| `age` ↔ `gender` | no test (skipped) | – | – | – | rejected: not enough data |
| `income` ↔ `gender` | no test (skipped) | – | – | – | rejected: not enough data |
| `monthly_spend` ↔ `gender` | no test (skipped) | – | – | – | rejected: not enough data |
| `tenure_months` ↔ `gender` | no test (skipped) | – | – | – | rejected: not enough data |

### Reproducibility

- VeriData version: 0.1.0; resolved config hash: `3a94527dfcc5`.
- Dataset SHA-256: `c2124c6ccb1547fabb41a927466ec703571ac1eaaafa1d086bd6b27c2c224a92`.
- Narration: deterministic templates (no language model).
