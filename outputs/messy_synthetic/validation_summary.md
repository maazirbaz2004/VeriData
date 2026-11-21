# Phase 3 Statistical Validation Summary — `messy_synthetic`

## Overview
- **Tests planned (manifest):** `36`
- **Tests executed in family (`m`):** `32` (`4` skipped, `0` errors)
- **Correction method:** `bh` at $\alpha = 0.05$ (effect floor enabled: `True`)
- **Naive raw $p < \alpha$:** `7`
- **Significant after correction ($q \le \alpha$):** `5`
- **Accepted findings (all gates):** `5`
- **Fallback rate:** `46.9%` · **Runtime:** `20.73s`

## Accepted Findings (5)

| Column A | Column B | Test | n | Raw p | Adj q | Effect | 95% CI | Magnitude | Flags |
| :--- | :--- | :--- | ---: | ---: | ---: | ---: | :--- | :--- | :--- |
| `income` | `monthly_spend` | `spearman` | 1840 | 0 | 0 | `spearman_rho=0.894` | `[0.879, 0.907]` | `large` | test_sensitive |
| `income` | `membership` | `kruskal_wallis` | 1840 | 9.07e-106 | 1.45e-104 | `epsilon_squared=0.263` | `[0.224, 0.302]` | `large` |  |
| `monthly_spend` | `membership` | `kruskal_wallis` | 2000 | 1.24e-99 | 1.32e-98 | `epsilon_squared=0.228` | `[0.193, 0.262]` | `large` |  |
| `tenure_months` | `churned` | `welch_t` | 1970 | 1.44e-48 | 1.15e-47 | `hedges_g=0.713` | `[0.618, 0.809]` | `medium` |  |
| `churned` | `satisfaction` | `chi_square` | 1940 | 1.08e-32 | 6.89e-32 | `cramers_v_bc=0.280` | `[0.242, 0.327]` | `small` |  |

## Rejected / Skipped Hypotheses (31)

| Column A | Column B | Test | Raw p | Adj q | Reasons | Explanation |
| :--- | :--- | :--- | ---: | ---: | :--- | :--- |
| `income` | `churned` | `mann_whitney_u` | 0.0197 | 0.105 | `not_significant_after_correction, effect_below_threshold` | Adjusted q=0.1049 exceeds alpha=0.05 (raw p=0.0197, family m=32). Standardized effect /rank_biserial/=0.0660 is below the practical floor (0.10). |
| `monthly_spend` | `churned` | `mann_whitney_u` | 0.0495 | 0.226 | `not_significant_after_correction, effect_below_threshold` | Adjusted q=0.2263 exceeds alpha=0.05 (raw p=0.0495, family m=32). Standardized effect /rank_biserial/=0.0535 is below the practical floor (0.10). |
| `gender` | `satisfaction` | `monte_carlo_chi_square` | 0.159 | 0.634 | `not_significant_after_correction, effect_below_threshold` | Adjusted q=0.6340 exceeds alpha=0.05 (raw p=0.1585, family m=32). Standardized effect /cramers_v_bc/=0.0493 is below the practical floor (0.10). |
| `monthly_spend` | `region` | `kruskal_wallis` | 0.198 | 0.703 | `not_significant_after_correction, effect_below_threshold` | Adjusted q=0.7029 exceeds alpha=0.05 (raw p=0.1977, family m=32). Standardized effect /epsilon_squared/=0.0031 is below the practical floor (0.01). |
| `monthly_spend` | `tenure_months` | `spearman` | 0.288 | 0.836 | `not_significant_after_correction, effect_below_threshold` | Adjusted q=0.8365 exceeds alpha=0.05 (raw p=0.2885, family m=32). Standardized effect /spearman_rho/=0.0239 is below the practical floor (0.10). |
| `churned` | `membership` | `chi_square` | 0.295 | 0.836 | `not_significant_after_correction, effect_below_threshold` | Adjusted q=0.8365 exceeds alpha=0.05 (raw p=0.2947, family m=32). Standardized effect /cramers_v_bc/=0.0149 is below the practical floor (0.10). |
| `income` | `region` | `kruskal_wallis` | 0.314 | 0.836 | `not_significant_after_correction, effect_below_threshold` | Adjusted q=0.8365 exceeds alpha=0.05 (raw p=0.3137, family m=32). Standardized effect /epsilon_squared/=0.0027 is below the practical floor (0.01). |
| `gender` | `region` | `chi_square` | 0.359 | 0.853 | `not_significant_after_correction, effect_below_threshold` | Adjusted q=0.8533 exceeds alpha=0.05 (raw p=0.3590, family m=32). Standardized effect /cramers_v_bc/=0.0243 is below the practical floor (0.10). |
| `income` | `tenure_months` | `spearman` | 0.439 | 0.853 | `not_significant_after_correction, effect_below_threshold` | Adjusted q=0.8533 exceeds alpha=0.05 (raw p=0.4392, family m=32). Standardized effect /spearman_rho/=0.0182 is below the practical floor (0.10). |
| `membership` | `region` | `chi_square` | 0.421 | 0.853 | `not_significant_after_correction, effect_below_threshold` | Adjusted q=0.8533 exceeds alpha=0.05 (raw p=0.4207, family m=32). Standardized effect /cramers_v_bc/=0.0082 is below the practical floor (0.10). |
| `tenure_months` | `region` | `welch_anova` | 0.456 | 0.853 | `not_significant_after_correction, effect_below_threshold` | Adjusted q=0.8533 exceeds alpha=0.05 (raw p=0.4564, family m=32). Standardized effect /eta_squared/=0.0019 is below the practical floor (0.01). |
| `tenure_months` | `satisfaction` | `welch_anova` | 0.475 | 0.853 | `not_significant_after_correction, effect_below_threshold` | Adjusted q=0.8533 exceeds alpha=0.05 (raw p=0.4750, family m=32). Standardized effect /eta_squared/=0.0017 is below the practical floor (0.01). |
| `churned` | `region` | `chi_square` | 0.48 | 0.853 | `not_significant_after_correction, effect_below_threshold` | Adjusted q=0.8533 exceeds alpha=0.05 (raw p=0.4800, family m=32). Standardized effect /cramers_v_bc/=0.0000 is below the practical floor (0.10). |
| `gender` | `membership` | `chi_square` | 0.526 | 0.886 | `not_significant_after_correction, effect_below_threshold` | Adjusted q=0.8858 exceeds alpha=0.05 (raw p=0.5259, family m=32). Standardized effect /cramers_v_bc/=0.0000 is below the practical floor (0.10). |
| `age` | `satisfaction` | `welch_anova` | 0.618 | 0.942 | `not_significant_after_correction, effect_below_threshold` | Adjusted q=0.9423 exceeds alpha=0.05 (raw p=0.6184, family m=32). Standardized effect /eta_squared/=0.0015 is below the practical floor (0.01). |
| `tenure_months` | `membership` | `welch_anova` | 0.602 | 0.942 | `not_significant_after_correction, effect_below_threshold` | Adjusted q=0.9423 exceeds alpha=0.05 (raw p=0.6017, family m=32). Standardized effect /eta_squared/=0.0005 is below the practical floor (0.01). |
| `age` | `churned` | `welch_t` | 0.797 | 0.977 | `not_significant_after_correction, effect_below_threshold` | Adjusted q=0.9765 exceeds alpha=0.05 (raw p=0.7974, family m=32). Standardized effect /hedges_g/=0.0125 is below the practical floor (0.20). |
| `age` | `tenure_months` | `spearman` | 0.859 | 0.977 | `not_significant_after_correction, effect_below_threshold` | Adjusted q=0.9765 exceeds alpha=0.05 (raw p=0.8590, family m=32). Standardized effect /spearman_rho/=0.0042 is below the practical floor (0.10). |
| `age` | `income` | `spearman` | 0.903 | 0.977 | `not_significant_after_correction, effect_below_threshold` | Adjusted q=0.9765 exceeds alpha=0.05 (raw p=0.9035, family m=32). Standardized effect /spearman_rho/=0.0029 is below the practical floor (0.10). |
| `age` | `monthly_spend` | `spearman` | 0.928 | 0.977 | `not_significant_after_correction, effect_below_threshold` | Adjusted q=0.9765 exceeds alpha=0.05 (raw p=0.9282, family m=32). Standardized effect /spearman_rho/=0.0021 is below the practical floor (0.10). |
| `income` | `satisfaction` | `kruskal_wallis` | 0.952 | 0.977 | `not_significant_after_correction, effect_below_threshold` | Adjusted q=0.9765 exceeds alpha=0.05 (raw p=0.9519, family m=32). Standardized effect /epsilon_squared/=0.0004 is below the practical floor (0.01). |
| `age` | `region` | `welch_anova` | 0.966 | 0.977 | `not_significant_after_correction, effect_below_threshold` | Adjusted q=0.9765 exceeds alpha=0.05 (raw p=0.9663, family m=32). Standardized effect /eta_squared/=0.0003 is below the practical floor (0.01). |
| `monthly_spend` | `satisfaction` | `kruskal_wallis` | 0.977 | 0.977 | `not_significant_after_correction, effect_below_threshold` | Adjusted q=0.9765 exceeds alpha=0.05 (raw p=0.9765, family m=32). Standardized effect /epsilon_squared/=0.0002 is below the practical floor (0.01). |
| `age` | `membership` | `welch_anova` | 0.849 | 0.977 | `not_significant_after_correction, effect_below_threshold` | Adjusted q=0.9765 exceeds alpha=0.05 (raw p=0.8486, family m=32). Standardized effect /eta_squared/=0.0002 is below the practical floor (0.01). |
| `membership` | `satisfaction` | `chi_square` | 0.809 | 0.977 | `not_significant_after_correction, effect_below_threshold` | Adjusted q=0.9765 exceeds alpha=0.05 (raw p=0.8085, family m=32). Standardized effect /cramers_v_bc/=0.0000 is below the practical floor (0.10). |
| `churned` | `gender` | `chi_square` | 0.827 | 0.977 | `not_significant_after_correction, effect_below_threshold` | Adjusted q=0.9765 exceeds alpha=0.05 (raw p=0.8273, family m=32). Standardized effect /cramers_v_bc/=0.0000 is below the practical floor (0.10). |
| `region` | `satisfaction` | `chi_square` | 0.94 | 0.977 | `not_significant_after_correction, effect_below_threshold` | Adjusted q=0.9765 exceeds alpha=0.05 (raw p=0.9398, family m=32). Standardized effect /cramers_v_bc/=0.0000 is below the practical floor (0.10). |
| `age` | `gender` | `none` | n/a | n/a | `insufficient_data` | Skipped before testing: Binary grouping requires 2 groups with n >= 8 (dropped=[]).. |
| `income` | `gender` | `none` | n/a | n/a | `insufficient_data` | Skipped before testing: Binary grouping requires 2 groups with n >= 8 (dropped=[]).. |
| `monthly_spend` | `gender` | `none` | n/a | n/a | `insufficient_data` | Skipped before testing: Binary grouping requires 2 groups with n >= 8 (dropped=[]).. |
| `tenure_months` | `gender` | `none` | n/a | n/a | `insufficient_data` | Skipped before testing: Binary grouping requires 2 groups with n >= 8 (dropped=[]).. |
