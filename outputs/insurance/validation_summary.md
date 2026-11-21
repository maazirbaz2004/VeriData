# Phase 3 Statistical Validation Summary — `insurance`

## Overview
- **Tests planned (manifest):** `21`
- **Tests executed in family (`m`):** `21` (`0` skipped, `0` errors)
- **Correction method:** `bh` at $\alpha = 0.05$ (effect floor enabled: `True`)
- **Naive raw $p < \alpha$:** `8`
- **Significant after correction ($q \le \alpha$):** `7`
- **Accepted findings (all gates):** `6`
- **Fallback rate:** `19.1%` · **Runtime:** `12.80s`

## Accepted Findings (6)

| Column A | Column B | Test | n | Raw p | Adj q | Effect | 95% CI | Magnitude | Flags |
| :--- | :--- | :--- | ---: | ---: | ---: | ---: | :--- | :--- | :--- |
| `charges` | `smoker` | `welch_t` | 1337 | 6.26e-103 | 1.31e-101 | `hedges_g=-3.159` | `[-3.337, -2.980]` | `large` |  |
| `age` | `charges` | `spearman` | 1337 | 3.19e-99 | 3.35e-98 | `spearman_rho=0.534` | `[0.482, 0.582]` | `large` |  |
| `bmi` | `region` | `welch_anova` | 1337 | 1.24e-21 | 8.7e-21 | `eta_squared=0.082` | `[0.057, 0.115]` | `medium` |  |
| `bmi` | `charges` | `spearman` | 1337 | 1.16e-05 | 6.11e-05 | `spearman_rho=0.120` | `[0.063, 0.172]` | `small` |  |
| `charges` | `children` | `kruskal_wallis` | 1337 | 2.2e-05 | 9.22e-05 | `epsilon_squared=0.022` | `[0.011, 0.042]` | `small` |  |
| `age` | `bmi` | `spearman` | 1337 | 7.71e-05 | 0.00027 | `spearman_rho=0.108` | `[0.051, 0.161]` | `small` |  |

## Rejected / Skipped Hypotheses (15)

| Column A | Column B | Test | Raw p | Adj q | Reasons | Explanation |
| :--- | :--- | :--- | ---: | ---: | :--- | :--- |
| `sex` | `smoker` | `chi_square` | 0.0051 | 0.0153 | `effect_below_threshold` | Standardized effect /cramers_v_bc/=0.0716 is below the practical floor (0.10). |
| `charges` | `sex` | `welch_t` | 0.0336 | 0.0881 | `not_significant_after_correction, effect_below_threshold` | Adjusted q=0.0881 exceeds alpha=0.05 (raw p=0.0336, family m=21). Standardized effect /hedges_g/=0.1161 is below the practical floor (0.20). |
| `charges` | `region` | `welch_anova` | 0.0535 | 0.125 | `not_significant_after_correction, effect_below_threshold` | Adjusted q=0.1248 exceeds alpha=0.05 (raw p=0.0535, family m=21). Standardized effect /eta_squared/=0.0065 is below the practical floor (0.01). |
| `region` | `smoker` | `chi_square` | 0.0635 | 0.133 | `not_significant_after_correction, effect_below_threshold` | Adjusted q=0.1335 exceeds alpha=0.05 (raw p=0.0635, family m=21). Standardized effect /cramers_v_bc/=0.0566 is below the practical floor (0.10). |
| `bmi` | `sex` | `welch_t` | 0.0899 | 0.172 | `not_significant_after_correction, effect_below_threshold` | Adjusted q=0.1716 exceeds alpha=0.05 (raw p=0.0899, family m=21). Standardized effect /hedges_g/=0.0928 is below the practical floor (0.20). |
| `age` | `children` | `welch_anova` | 0.115 | 0.202 | `not_significant_after_correction, effect_below_threshold` | Adjusted q=0.2017 exceeds alpha=0.05 (raw p=0.1153, family m=21). Standardized effect /eta_squared/=0.0055 is below the practical floor (0.01). |
| `children` | `smoker` | `chi_square` | 0.23 | 0.372 | `not_significant_after_correction, effect_below_threshold` | Adjusted q=0.3719 exceeds alpha=0.05 (raw p=0.2302, family m=21). Standardized effect /cramers_v_bc/=0.0374 is below the practical floor (0.10). |
| `age` | `smoker` | `welch_t` | 0.347 | 0.521 | `not_significant_after_correction, effect_below_threshold` | Adjusted q=0.5207 exceeds alpha=0.05 (raw p=0.3471, family m=21). Standardized effect /hedges_g/=0.0633 is below the practical floor (0.20). |
| `age` | `sex` | `welch_t` | 0.469 | 0.657 | `not_significant_after_correction, effect_below_threshold` | Adjusted q=0.6568 exceeds alpha=0.05 (raw p=0.4691, family m=21). Standardized effect /hedges_g/=0.0396 is below the practical floor (0.20). |
| `children` | `region` | `chi_square` | 0.534 | 0.701 | `not_significant_after_correction, effect_below_threshold` | Adjusted q=0.7005 exceeds alpha=0.05 (raw p=0.5337, family m=21). Standardized effect /cramers_v_bc/=0.0000 is below the practical floor (0.10). |
| `bmi` | `smoker` | `welch_t` | 0.894 | 0.979 | `not_significant_after_correction, effect_below_threshold` | Adjusted q=0.9788 exceeds alpha=0.05 (raw p=0.8940, family m=21). Standardized effect /hedges_g/=0.0093 is below the practical floor (0.20). |
| `bmi` | `children` | `welch_anova` | 0.882 | 0.979 | `not_significant_after_correction, effect_below_threshold` | Adjusted q=0.9788 exceeds alpha=0.05 (raw p=0.8816, family m=21). Standardized effect /eta_squared/=0.0013 is below the practical floor (0.01). |
| `age` | `region` | `welch_anova` | 0.971 | 0.979 | `not_significant_after_correction, effect_below_threshold` | Adjusted q=0.9788 exceeds alpha=0.05 (raw p=0.9707, family m=21). Standardized effect /eta_squared/=0.0002 is below the practical floor (0.01). |
| `children` | `sex` | `chi_square` | 0.979 | 0.979 | `not_significant_after_correction, effect_below_threshold` | Adjusted q=0.9788 exceeds alpha=0.05 (raw p=0.9788, family m=21). Standardized effect /cramers_v_bc/=0.0000 is below the practical floor (0.10). |
| `region` | `sex` | `chi_square` | 0.924 | 0.979 | `not_significant_after_correction, effect_below_threshold` | Adjusted q=0.9788 exceeds alpha=0.05 (raw p=0.9239, family m=21). Standardized effect /cramers_v_bc/=0.0000 is below the practical floor (0.10). |
