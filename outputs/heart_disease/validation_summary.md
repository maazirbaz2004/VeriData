# Phase 3 Statistical Validation Summary — `heart_disease`

## Overview
- **Tests planned (manifest):** `91`
- **Tests executed in family (`m`):** `91` (`0` skipped, `0` errors)
- **Correction method:** `bh` at $\alpha = 0.05$ (effect floor enabled: `True`)
- **Naive raw $p < \alpha$:** `50`
- **Significant after correction ($q \le \alpha$):** `47`
- **Accepted findings (all gates):** `47`
- **Fallback rate:** `25.3%` · **Runtime:** `39.26s`

## Accepted Findings (47)

| Column A | Column B | Test | n | Raw p | Adj q | Effect | 95% CI | Magnitude | Flags |
| :--- | :--- | :--- | ---: | ---: | ---: | ---: | :--- | :--- | :--- |
| `oldpeak` | `slope` | `kruskal_wallis` | 302 | 1.01e-23 | 9.19e-22 | `epsilon_squared=0.352` | `[0.268, 0.448]` | `large` |  |
| `target` | `thal` | `chi_square` | 300 | 4.25e-19 | 1.93e-17 | `cramers_v_bc=0.526` | `[0.431, 0.619]` | `large` |  |
| `cp` | `target` | `chi_square` | 302 | 1.89e-17 | 5.74e-16 | `cramers_v_bc=0.509` | `[0.405, 0.607]` | `large` |  |
| `ca` | `target` | `chi_square` | 298 | 1.01e-15 | 2.3e-14 | `cramers_v_bc=0.485` | `[0.401, 0.579]` | `medium` |  |
| `oldpeak` | `thalach` | `spearman` | 302 | 4.68e-15 | 8.52e-14 | `spearman_rho=-0.430` | `[-0.522, -0.326]` | `medium` |  |
| `cp` | `exang` | `chi_square` | 302 | 2.04e-14 | 3.1e-13 | `cramers_v_bc=0.460` | `[0.368, 0.560]` | `medium` |  |
| `exang` | `target` | `chi_square` | 302 | 3.73e-14 | 4.85e-13 | `cramers_v_bc=0.432` | `[0.327, 0.531]` | `medium` |  |
| `thalach` | `target` | `welch_t` | 302 | 6.9e-14 | 7.85e-13 | `hedges_g=-0.924` | `[-1.162, -0.685]` | `large` |  |
| `oldpeak` | `target` | `welch_t` | 302 | 1.38e-13 | 1.39e-12 | `hedges_g=0.948` | `[0.709, 1.187]` | `large` |  |
| `age` | `thalach` | `spearman` | 302 | 1.27e-12 | 1.16e-11 | `spearman_rho=-0.393` | `[-0.488, -0.289]` | `medium` |  |
| `thalach` | `exang` | `welch_t` | 302 | 2.39e-11 | 1.98e-10 | `hedges_g=0.863` | `[0.613, 1.113]` | `large` |  |
| `thalach` | `slope` | `welch_anova` | 302 | 3.36e-11 | 2.55e-10 | `eta_squared=0.203` | `[0.132, 0.294]` | `large` |  |
| `slope` | `target` | `chi_square` | 302 | 6.58e-11 | 4.6e-10 | `cramers_v_bc=0.386` | `[0.278, 0.491]` | `medium` |  |
| `sex` | `thal` | `chi_square` | 300 | 1.76e-10 | 1.15e-09 | `cramers_v_bc=0.379` | `[0.286, 0.478]` | `medium` |  |
| `oldpeak` | `thal` | `kruskal_wallis` | 300 | 2.43e-09 | 1.47e-08 | `epsilon_squared=0.133` | `[0.072, 0.215]` | `medium` |  |
| `oldpeak` | `cp` | `kruskal_wallis` | 302 | 3.68e-09 | 2.1e-08 | `epsilon_squared=0.140` | `[0.089, 0.217]` | `large` |  |
| `age` | `ca` | `welch_anova` | 298 | 4.63e-09 | 2.48e-08 | `eta_squared=0.151` | `[0.091, 0.235]` | `large` |  |
| `thalach` | `cp` | `welch_anova` | 302 | 6.37e-09 | 3.22e-08 | `eta_squared=0.151` | `[0.089, 0.233]` | `large` |  |
| `exang` | `thal` | `chi_square` | 300 | 9.38e-08 | 4.49e-07 | `cramers_v_bc=0.319` | `[0.223, 0.441]` | `medium` |  |
| `age` | `trestbps` | `spearman` | 302 | 2.99e-07 | 1.36e-06 | `spearman_rho=0.290` | `[0.179, 0.395]` | `small` |  |
| `cp` | `thal` | `chi_square` | 300 | 3.55e-07 | 1.54e-06 | `cramers_v_bc=0.241` | `[0.183, 0.330]` | `medium` |  |
| `slope` | `thal` | `chi_square` | 300 | 5.62e-07 | 2.32e-06 | `cramers_v_bc=0.227` | `[0.160, 0.310]` | `medium` |  |
| `sex` | `target` | `chi_square` | 302 | 8.28e-07 | 3.28e-06 | `cramers_v_bc=0.278` | `[0.158, 0.393]` | `small` |  |
| `oldpeak` | `exang` | `welch_t` | 302 | 2.44e-06 | 9.24e-06 | `hedges_g=-0.634` | `[-0.880, -0.388]` | `medium` |  |
| `age` | `oldpeak` | `spearman` | 302 | 3.4e-06 | 1.24e-05 | `spearman_rho=0.264` | `[0.150, 0.372]` | `small` |  |
| `exang` | `slope` | `chi_square` | 302 | 4.21e-06 | 1.47e-05 | `cramers_v_bc=0.275` | `[0.172, 0.392]` | `small` |  |
| `thalach` | `ca` | `welch_anova` | 298 | 6.37e-06 | 2.15e-05 | `eta_squared=0.094` | `[0.047, 0.176]` | `medium` |  |
| `thalach` | `thal` | `welch_anova` | 300 | 1.07e-05 | 3.48e-05 | `eta_squared=0.091` | `[0.042, 0.168]` | `medium` |  |
| `oldpeak` | `ca` | `kruskal_wallis` | 298 | 1.87e-05 | 5.87e-05 | `epsilon_squared=0.083` | `[0.038, 0.160]` | `medium` |  |
| `age` | `target` | `welch_t` | 302 | 8.18e-05 | 0.000248 | `hedges_g=0.453` | `[0.224, 0.683]` | `small` |  |
| `cp` | `slope` | `chi_square` | 302 | 0.000122 | 0.000359 | `cramers_v_bc=0.189` | `[0.115, 0.291]` | `small` |  |
| `ca` | `cp` | `chi_square` | 298 | 0.000294 | 0.000837 | `cramers_v_bc=0.158` | `[0.120, 0.236]` | `small` |  |
| `age` | `chol` | `spearman` | 302 | 0.000971 | 0.00268 | `spearman_rho=0.189` | `[0.078, 0.306]` | `small` |  |
| `ca` | `thal` | `monte_carlo_chi_square` | 296 | 0.002 | 0.00535 | `cramers_v_bc=0.164` | `[0.092, 0.271]` | `small` |  |
| `chol` | `sex` | `welch_t` | 302 | 0.0034 | 0.00862 | `hedges_g=0.426` | `[0.181, 0.670]` | `small` |  |
| `chol` | `restecg` | `welch_t` | 298 | 0.00341 | 0.00862 | `hedges_g=0.342` | `[0.113, 0.571]` | `small` |  |
| `restecg` | `target` | `chi_square` | 298 | 0.00388 | 0.00954 | `cramers_v_bc=0.157` | `[0.000, 0.280]` | `small` |  |
| `ca` | `exang` | `chi_square` | 298 | 0.00614 | 0.0147 | `cramers_v_bc=0.178` | `[0.041, 0.313]` | `small` |  |
| `oldpeak` | `trestbps` | `spearman` | 302 | 0.00632 | 0.0147 | `spearman_rho=0.157` | `[0.044, 0.269]` | `small` |  |
| `age` | `slope` | `welch_anova` | 302 | 0.00728 | 0.0166 | `eta_squared=0.036` | `[0.008, 0.095]` | `small` |  |
| `trestbps` | `fbs` | `welch_t` | 302 | 0.00792 | 0.0176 | `hedges_g=-0.505` | `[-0.825, -0.186]` | `medium` |  |
| `age` | `restecg` | `welch_t` | 298 | 0.0102 | 0.0221 | `hedges_g=0.299` | `[0.070, 0.527]` | `small` |  |
| `trestbps` | `target` | `welch_t` | 302 | 0.012 | 0.0254 | `hedges_g=0.295` | `[0.067, 0.523]` | `small` |  |
| `trestbps` | `restecg` | `welch_t` | 298 | 0.0127 | 0.0257 | `hedges_g=0.290` | `[0.062, 0.518]` | `small` |  |
| `exang` | `sex` | `chi_square` | 302 | 0.0127 | 0.0257 | `cramers_v_bc=0.132` | `[0.000, 0.232]` | `small` |  |
| `age` | `fbs` | `welch_t` | 302 | 0.0138 | 0.0273 | `hedges_g=-0.336` | `[-0.654, -0.018]` | `small` | test_sensitive |
| `chol` | `trestbps` | `spearman` | 302 | 0.0236 | 0.0458 | `spearman_rho=0.130` | `[0.017, 0.237]` | `small` |  |

## Rejected / Skipped Hypotheses (44)

| Column A | Column B | Test | Raw p | Adj q | Reasons | Explanation |
| :--- | :--- | :--- | ---: | ---: | :--- | :--- |
| `age` | `cp` | `welch_anova` | 0.0316 | 0.0599 | `not_significant_after_correction` | Adjusted q=0.0599 exceeds alpha=0.05 (raw p=0.0316, family m=91). |
| `oldpeak` | `restecg` | `welch_t` | 0.0389 | 0.0723 | `not_significant_after_correction` | Adjusted q=0.0723 exceeds alpha=0.05 (raw p=0.0389, family m=91). |
| `restecg` | `slope` | `chi_square` | 0.0464 | 0.0844 | `not_significant_after_correction` | Adjusted q=0.0844 exceeds alpha=0.05 (raw p=0.0464, family m=91). |
| `cp` | `restecg` | `chi_square` | 0.0519 | 0.0891 | `not_significant_after_correction` | Adjusted q=0.0891 exceeds alpha=0.05 (raw p=0.0519, family m=91). |
| `trestbps` | `cp` | `kruskal_wallis` | 0.0518 | 0.0891 | `not_significant_after_correction` | Adjusted q=0.0891 exceeds alpha=0.05 (raw p=0.0518, family m=91). |
| `trestbps` | `thal` | `welch_anova` | 0.0502 | 0.0891 | `not_significant_after_correction` | Adjusted q=0.0891 exceeds alpha=0.05 (raw p=0.0502, family m=91). |
| `ca` | `fbs` | `chi_square` | 0.0634 | 0.105 | `not_significant_after_correction` | Adjusted q=0.1048 exceeds alpha=0.05 (raw p=0.0634, family m=91). |
| `age` | `thal` | `welch_anova` | 0.0623 | 0.105 | `not_significant_after_correction` | Adjusted q=0.1048 exceeds alpha=0.05 (raw p=0.0623, family m=91). |
| `cp` | `sex` | `chi_square` | 0.0688 | 0.112 | `not_significant_after_correction` | Adjusted q=0.1117 exceeds alpha=0.05 (raw p=0.0688, family m=91). |
| `oldpeak` | `sex` | `welch_t` | 0.0832 | 0.133 | `not_significant_after_correction` | Adjusted q=0.1328 exceeds alpha=0.05 (raw p=0.0832, family m=91). |
| `age` | `exang` | `welch_t` | 0.0937 | 0.142 | `not_significant_after_correction, effect_below_threshold` | Adjusted q=0.1421 exceeds alpha=0.05 (raw p=0.0937, family m=91). Standardized effect /hedges_g/=0.1983 is below the practical floor (0.20). |
| `ca` | `slope` | `monte_carlo_chi_square` | 0.0933 | 0.142 | `not_significant_after_correction` | Adjusted q=0.1421 exceeds alpha=0.05 (raw p=0.0933, family m=91). |
| `chol` | `ca` | `kruskal_wallis` | 0.0915 | 0.142 | `not_significant_after_correction` | Adjusted q=0.1421 exceeds alpha=0.05 (raw p=0.0915, family m=91). |
| `age` | `sex` | `welch_t` | 0.108 | 0.161 | `not_significant_after_correction` | Adjusted q=0.1613 exceeds alpha=0.05 (raw p=0.1081, family m=91). |
| `exang` | `restecg` | `chi_square` | 0.128 | 0.188 | `not_significant_after_correction, effect_below_threshold` | Adjusted q=0.1882 exceeds alpha=0.05 (raw p=0.1283, family m=91). Standardized effect /cramers_v_bc/=0.0664 is below the practical floor (0.10). |
| `ca` | `restecg` | `chi_square` | 0.131 | 0.189 | `not_significant_after_correction, effect_below_threshold` | Adjusted q=0.1888 exceeds alpha=0.05 (raw p=0.1307, family m=91). Standardized effect /cramers_v_bc/=0.0947 is below the practical floor (0.10). |
| `thalach` | `restecg` | `welch_t` | 0.139 | 0.198 | `not_significant_after_correction, effect_below_threshold` | Adjusted q=0.1980 exceeds alpha=0.05 (raw p=0.1393, family m=91). Standardized effect /hedges_g/=0.1712 is below the practical floor (0.20). |
| `ca` | `sex` | `chi_square` | 0.142 | 0.199 | `not_significant_after_correction, effect_below_threshold` | Adjusted q=0.1990 exceeds alpha=0.05 (raw p=0.1421, family m=91). Standardized effect /cramers_v_bc/=0.0905 is below the practical floor (0.10). |
| `trestbps` | `slope` | `welch_anova` | 0.149 | 0.205 | `not_significant_after_correction` | Adjusted q=0.2053 exceeds alpha=0.05 (raw p=0.1489, family m=91). |
| `chol` | `target` | `welch_t` | 0.155 | 0.209 | `not_significant_after_correction, effect_below_threshold` | Adjusted q=0.2088 exceeds alpha=0.05 (raw p=0.1553, family m=91). Standardized effect /hedges_g/=0.1631 is below the practical floor (0.20). |
| `chol` | `thal` | `kruskal_wallis` | 0.156 | 0.209 | `not_significant_after_correction` | Adjusted q=0.2088 exceeds alpha=0.05 (raw p=0.1560, family m=91). |
| `fbs` | `thal` | `chi_square` | 0.169 | 0.223 | `not_significant_after_correction, effect_below_threshold` | Adjusted q=0.2227 exceeds alpha=0.05 (raw p=0.1688, family m=91). Standardized effect /cramers_v_bc/=0.0720 is below the practical floor (0.10). |
| `fbs` | `slope` | `chi_square` | 0.188 | 0.244 | `not_significant_after_correction, effect_below_threshold` | Adjusted q=0.2438 exceeds alpha=0.05 (raw p=0.1876, family m=91). Standardized effect /cramers_v_bc/=0.0667 is below the practical floor (0.10). |
| `trestbps` | `ca` | `welch_anova` | 0.201 | 0.258 | `not_significant_after_correction` | Adjusted q=0.2581 exceeds alpha=0.05 (raw p=0.2014, family m=91). |
| `fbs` | `restecg` | `chi_square` | 0.219 | 0.276 | `not_significant_after_correction, effect_below_threshold` | Adjusted q=0.2762 exceeds alpha=0.05 (raw p=0.2186, family m=91). Standardized effect /cramers_v_bc/=0.0415 is below the practical floor (0.10). |
| `trestbps` | `exang` | `welch_t` | 0.263 | 0.319 | `not_significant_after_correction, effect_below_threshold` | Adjusted q=0.3194 exceeds alpha=0.05 (raw p=0.2633, family m=91). Standardized effect /hedges_g/=0.1455 is below the practical floor (0.20). |
| `chol` | `exang` | `welch_t` | 0.256 | 0.319 | `not_significant_after_correction, effect_below_threshold` | Adjusted q=0.3194 exceeds alpha=0.05 (raw p=0.2565, family m=91). Standardized effect /hedges_g/=0.1360 is below the practical floor (0.20). |
| `cp` | `fbs` | `chi_square` | 0.261 | 0.319 | `not_significant_after_correction, effect_below_threshold` | Adjusted q=0.3194 exceeds alpha=0.05 (raw p=0.2609, family m=91). Standardized effect /cramers_v_bc/=0.0575 is below the practical floor (0.10). |
| `trestbps` | `sex` | `welch_t` | 0.344 | 0.412 | `not_significant_after_correction, effect_below_threshold` | Adjusted q=0.4122 exceeds alpha=0.05 (raw p=0.3443, family m=91). Standardized effect /hedges_g/=0.1233 is below the practical floor (0.20). |
| `thalach` | `sex` | `welch_t` | 0.39 | 0.461 | `not_significant_after_correction, effect_below_threshold` | Adjusted q=0.4611 exceeds alpha=0.05 (raw p=0.3901, family m=91). Standardized effect /hedges_g/=0.0993 is below the practical floor (0.20). |
| `fbs` | `sex` | `chi_square` | 0.424 | 0.494 | `not_significant_after_correction, effect_below_threshold` | Adjusted q=0.4945 exceeds alpha=0.05 (raw p=0.4238, family m=91). Standardized effect /cramers_v_bc/=0.0000 is below the practical floor (0.10). |
| `thalach` | `trestbps` | `spearman` | 0.46 | 0.53 | `not_significant_after_correction, effect_below_threshold` | Adjusted q=0.5296 exceeds alpha=0.05 (raw p=0.4597, family m=91). Standardized effect /spearman_rho/=0.0427 is below the practical floor (0.10). |
| `chol` | `thalach` | `spearman` | 0.485 | 0.551 | `not_significant_after_correction, effect_below_threshold` | Adjusted q=0.5513 exceeds alpha=0.05 (raw p=0.4846, family m=91). Standardized effect /spearman_rho/=0.0404 is below the practical floor (0.10). |
| `chol` | `oldpeak` | `spearman` | 0.493 | 0.554 | `not_significant_after_correction, effect_below_threshold` | Adjusted q=0.5543 exceeds alpha=0.05 (raw p=0.4934, family m=91). Standardized effect /spearman_rho/=0.0396 is below the practical floor (0.10). |
| `chol` | `cp` | `kruskal_wallis` | 0.515 | 0.571 | `not_significant_after_correction, effect_below_threshold` | Adjusted q=0.5710 exceeds alpha=0.05 (raw p=0.5145, family m=91). Standardized effect /epsilon_squared/=0.0076 is below the practical floor (0.01). |
| `oldpeak` | `fbs` | `mann_whitney_u` | 0.644 | 0.689 | `not_significant_after_correction, effect_below_threshold` | Adjusted q=0.6892 exceeds alpha=0.05 (raw p=0.6438, family m=91). Standardized effect /rank_biserial/=0.0425 is below the practical floor (0.10). |
| `fbs` | `target` | `chi_square` | 0.641 | 0.689 | `not_significant_after_correction, effect_below_threshold` | Adjusted q=0.6892 exceeds alpha=0.05 (raw p=0.6411, family m=91). Standardized effect /cramers_v_bc/=0.0000 is below the practical floor (0.10). |
| `restecg` | `sex` | `chi_square` | 0.639 | 0.689 | `not_significant_after_correction, effect_below_threshold` | Adjusted q=0.6892 exceeds alpha=0.05 (raw p=0.6390, family m=91). Standardized effect /cramers_v_bc/=0.0000 is below the practical floor (0.10). |
| `exang` | `fbs` | `chi_square` | 0.667 | 0.706 | `not_significant_after_correction, effect_below_threshold` | Adjusted q=0.7062 exceeds alpha=0.05 (raw p=0.6674, family m=91). Standardized effect /cramers_v_bc/=0.0000 is below the practical floor (0.10). |
| `restecg` | `thal` | `chi_square` | 0.678 | 0.71 | `not_significant_after_correction, effect_below_threshold` | Adjusted q=0.7096 exceeds alpha=0.05 (raw p=0.6784, family m=91). Standardized effect /cramers_v_bc/=0.0000 is below the practical floor (0.10). |
| `chol` | `slope` | `kruskal_wallis` | 0.723 | 0.739 | `not_significant_after_correction, effect_below_threshold` | Adjusted q=0.7393 exceeds alpha=0.05 (raw p=0.7231, family m=91). Standardized effect /epsilon_squared/=0.0022 is below the practical floor (0.01). |
| `sex` | `slope` | `chi_square` | 0.715 | 0.739 | `not_significant_after_correction, effect_below_threshold` | Adjusted q=0.7393 exceeds alpha=0.05 (raw p=0.7153, family m=91). Standardized effect /cramers_v_bc/=0.0000 is below the practical floor (0.10). |
| `chol` | `fbs` | `mann_whitney_u` | 0.778 | 0.787 | `not_significant_after_correction, effect_below_threshold` | Adjusted q=0.7871 exceeds alpha=0.05 (raw p=0.7785, family m=91). Standardized effect /rank_biserial/=0.0264 is below the practical floor (0.10). |
| `thalach` | `fbs` | `welch_t` | 0.899 | 0.899 | `not_significant_after_correction, effect_below_threshold` | Adjusted q=0.8990 exceeds alpha=0.05 (raw p=0.8990, family m=91). Standardized effect /hedges_g/=0.0200 is below the practical floor (0.20). |
