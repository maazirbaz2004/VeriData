# Phase 3 Statistical Validation Summary — `telco_churn`

## Overview
- **Tests planned (manifest):** `190`
- **Tests executed in family (`m`):** `190` (`0` skipped, `0` errors)
- **Correction method:** `bh` at $\alpha = 0.05$ (effect floor enabled: `True`)
- **Naive raw $p < \alpha$:** `157`
- **Significant after correction ($q \le \alpha$):** `157`
- **Accepted findings (all gates):** `151`
- **Fallback rate:** `2.1%` · **Runtime:** `60.22s`

## Accepted Findings (151)

| Column A | Column B | Test | n | Raw p | Adj q | Effect | 95% CI | Magnitude | Flags |
| :--- | :--- | :--- | ---: | ---: | ---: | ---: | :--- | :--- | :--- |
| `StreamingMovies` | `StreamingTV` | `chi_square` | 7043 | 0 | 0 | `cramers_v_bc=0.771` | `[0.765, 0.778]` | `large` |  |
| `DeviceProtection` | `StreamingMovies` | `chi_square` | 7043 | 0 | 0 | `cramers_v_bc=0.736` | `[0.731, 0.741]` | `large` |  |
| `DeviceProtection` | `StreamingTV` | `chi_square` | 7043 | 0 | 0 | `cramers_v_bc=0.734` | `[0.729, 0.738]` | `large` |  |
| `OnlineSecurity` | `TechSupport` | `chi_square` | 7043 | 0 | 0 | `cramers_v_bc=0.733` | `[0.729, 0.738]` | `large` |  |
| `DeviceProtection` | `TechSupport` | `chi_square` | 7043 | 0 | 0 | `cramers_v_bc=0.726` | `[0.722, 0.731]` | `large` |  |
| `InternetService` | `OnlineSecurity` | `chi_square` | 7043 | 0 | 0 | `cramers_v_bc=0.724` | `[0.720, 0.728]` | `large` |  |
| `InternetService` | `TechSupport` | `chi_square` | 7043 | 0 | 0 | `cramers_v_bc=0.723` | `[0.719, 0.727]` | `large` |  |
| `OnlineBackup` | `TechSupport` | `chi_square` | 7043 | 0 | 0 | `cramers_v_bc=0.720` | `[0.717, 0.724]` | `large` |  |
| `DeviceProtection` | `OnlineBackup` | `chi_square` | 7043 | 0 | 0 | `cramers_v_bc=0.719` | `[0.716, 0.722]` | `large` |  |
| `OnlineBackup` | `OnlineSecurity` | `chi_square` | 7043 | 0 | 0 | `cramers_v_bc=0.718` | `[0.715, 0.721]` | `large` |  |
| `DeviceProtection` | `OnlineSecurity` | `chi_square` | 7043 | 0 | 0 | `cramers_v_bc=0.717` | `[0.714, 0.721]` | `large` |  |
| `InternetService` | `StreamingTV` | `chi_square` | 7043 | 0 | 0 | `cramers_v_bc=0.717` | `[0.714, 0.720]` | `large` |  |
| `StreamingMovies` | `TechSupport` | `chi_square` | 7043 | 0 | 0 | `cramers_v_bc=0.716` | `[0.714, 0.719]` | `large` |  |
| `StreamingTV` | `TechSupport` | `chi_square` | 7043 | 0 | 0 | `cramers_v_bc=0.716` | `[0.713, 0.719]` | `large` |  |
| `InternetService` | `StreamingMovies` | `chi_square` | 7043 | 0 | 0 | `cramers_v_bc=0.716` | `[0.714, 0.719]` | `large` |  |
| `OnlineBackup` | `StreamingTV` | `chi_square` | 7043 | 0 | 0 | `cramers_v_bc=0.715` | `[0.712, 0.718]` | `large` |  |
| `OnlineBackup` | `StreamingMovies` | `chi_square` | 7043 | 0 | 0 | `cramers_v_bc=0.714` | `[0.711, 0.717]` | `large` |  |
| `OnlineSecurity` | `StreamingMovies` | `chi_square` | 7043 | 0 | 0 | `cramers_v_bc=0.708` | `[0.707, 0.709]` | `large` |  |
| `OnlineSecurity` | `StreamingTV` | `chi_square` | 7043 | 0 | 0 | `cramers_v_bc=0.708` | `[0.707, 0.709]` | `large` |  |
| `InternetService` | `OnlineBackup` | `chi_square` | 7043 | 0 | 0 | `cramers_v_bc=0.707` | `[0.707, 0.708]` | `large` |  |
| `DeviceProtection` | `InternetService` | `chi_square` | 7043 | 0 | 0 | `cramers_v_bc=0.707` | `[0.707, 0.707]` | `large` |  |
| `TotalCharges` | `tenure` | `spearman` | 7032 | 0 | 0 | `spearman_rho=0.889` | `[0.882, 0.896]` | `large` | test_sensitive |
| `MonthlyCharges` | `InternetService` | `welch_anova` | 7043 | 0 | 0 | `eta_squared=0.821` | `[0.816, 0.826]` | `large` |  |
| `MonthlyCharges` | `StreamingTV` | `welch_anova` | 7043 | 0 | 0 | `eta_squared=0.701` | `[0.691, 0.711]` | `large` |  |
| `MonthlyCharges` | `StreamingMovies` | `welch_anova` | 7043 | 0 | 0 | `eta_squared=0.698` | `[0.688, 0.708]` | `large` |  |
| `MonthlyCharges` | `TotalCharges` | `spearman` | 7032 | 0 | 0 | `spearman_rho=0.638` | `[0.623, 0.652]` | `large` | test_sensitive |
| `MonthlyCharges` | `DeviceProtection` | `welch_anova` | 7043 | 0 | 0 | `eta_squared=0.626` | `[0.616, 0.636]` | `large` |  |
| `MonthlyCharges` | `OnlineBackup` | `welch_anova` | 7043 | 0 | 0 | `eta_squared=0.609` | `[0.599, 0.620]` | `large` |  |
| `MonthlyCharges` | `TechSupport` | `welch_anova` | 7043 | 0 | 0 | `eta_squared=0.591` | `[0.581, 0.601]` | `large` |  |
| `MonthlyCharges` | `OnlineSecurity` | `welch_anova` | 7043 | 0 | 0 | `eta_squared=0.585` | `[0.576, 0.596]` | `large` |  |
| `InternetService` | `MultipleLines` | `chi_square` | 7043 | 0 | 0 | `cramers_v_bc=0.396` | `[0.384, 0.409]` | `large` |  |
| `Contract` | `TechSupport` | `chi_square` | 7043 | 0 | 0 | `cramers_v_bc=0.331` | `[0.317, 0.344]` | `medium` |  |
| `tenure` | `Contract` | `welch_anova` | 7043 | 0 | 0 | `eta_squared=0.457` | `[0.438, 0.478]` | `large` |  |
| `Dependents` | `Partner` | `chi_square` | 7043 | 0 | 0 | `cramers_v_bc=0.453` | `[0.434, 0.473]` | `medium` |  |
| `InternetService` | `PhoneService` | `chi_square` | 7043 | 0 | 0 | `cramers_v_bc=0.452` | `[0.435, 0.469]` | `medium` |  |
| `TotalCharges` | `DeviceProtection` | `welch_anova` | 7032 | 0 | 0 | `eta_squared=0.310` | `[0.293, 0.329]` | `large` |  |
| `TotalCharges` | `StreamingMovies` | `welch_anova` | 7032 | 0 | 0 | `eta_squared=0.300` | `[0.284, 0.317]` | `large` |  |
| `TotalCharges` | `OnlineBackup` | `welch_anova` | 7032 | 0 | 0 | `eta_squared=0.298` | `[0.283, 0.315]` | `large` |  |
| `TotalCharges` | `StreamingTV` | `welch_anova` | 7032 | 0 | 0 | `eta_squared=0.297` | `[0.281, 0.314]` | `large` |  |
| `MonthlyCharges` | `MultipleLines` | `welch_anova` | 7043 | 0 | 0 | `eta_squared=0.254` | `[0.238, 0.271]` | `large` |  |
| `TotalCharges` | `TechSupport` | `welch_anova` | 7032 | 0 | 0 | `eta_squared=0.247` | `[0.232, 0.263]` | `large` |  |
| `TotalCharges` | `OnlineSecurity` | `welch_anova` | 7032 | 0 | 0 | `eta_squared=0.234` | `[0.220, 0.249]` | `large` |  |
| `TotalCharges` | `InternetService` | `welch_anova` | 7032 | 0 | 0 | `eta_squared=0.185` | `[0.174, 0.197]` | `large` |  |
| `InternetService` | `PaymentMethod` | `chi_square` | 7043 | 3.03e-295 | 1.28e-294 | `cramers_v_bc=0.312` | `[0.299, 0.327]` | `medium` |  |
| `MonthlyCharges` | `PhoneService` | `welch_t` | 7043 | 8.69e-290 | 3.59e-289 | `hedges_g=-0.863` | `[-0.943, -0.783]` | `large` |  |
| `PaymentMethod` | `TechSupport` | `chi_square` | 7043 | 1.86e-283 | 7.54e-283 | `cramers_v_bc=0.306` | `[0.290, 0.324]` | `medium` |  |
| `TotalCharges` | `Contract` | `welch_anova` | 7032 | 1.11e-281 | 4.41e-281 | `eta_squared=0.210` | `[0.193, 0.228]` | `large` |  |
| `MonthlyCharges` | `PaymentMethod` | `welch_anova` | 7043 | 9.55e-281 | 3.7e-280 | `eta_squared=0.161` | `[0.147, 0.177]` | `large` |  |
| `OnlineSecurity` | `PaymentMethod` | `chi_square` | 7043 | 7.43e-280 | 2.82e-279 | `cramers_v_bc=0.304` | `[0.289, 0.321]` | `medium` |  |
| `TotalCharges` | `MultipleLines` | `welch_anova` | 7032 | 4.06e-278 | 1.51e-277 | `eta_squared=0.220` | `[0.203, 0.238]` | `large` |  |
| `Contract` | `OnlineSecurity` | `chi_square` | 7043 | 1.1e-275 | 4e-275 | `cramers_v_bc=0.301` | `[0.287, 0.314]` | `medium` |  |
| `Contract` | `DeviceProtection` | `chi_square` | 7043 | 1.07e-267 | 3.83e-267 | `cramers_v_bc=0.297` | `[0.282, 0.311]` | `medium` |  |
| `Churn` | `Contract` | `chi_square` | 7043 | 5.86e-258 | 2.06e-257 | `cramers_v_bc=0.410` | `[0.394, 0.425]` | `medium` |  |
| `DeviceProtection` | `PaymentMethod` | `chi_square` | 7043 | 1.76e-247 | 6.08e-247 | `cramers_v_bc=0.286` | `[0.272, 0.302]` | `medium` |  |
| `tenure` | `PaymentMethod` | `welch_anova` | 7043 | 1.97e-246 | 6.69e-246 | `eta_squared=0.160` | `[0.145, 0.177]` | `large` |  |
| `OnlineBackup` | `PaymentMethod` | `chi_square` | 7043 | 1.16e-239 | 3.87e-239 | `cramers_v_bc=0.282` | `[0.268, 0.296]` | `medium` |  |
| `tenure` | `Partner` | `welch_t` | 7043 | 1.09e-238 | 3.57e-238 | `hedges_g=-0.821` | `[-0.870, -0.772]` | `large` |  |
| `TotalCharges` | `PaymentMethod` | `kruskal_wallis` | 7032 | 3.54e-233 | 1.14e-232 | `epsilon_squared=0.153` | `[0.139, 0.168]` | `large` |  |
| `tenure` | `Churn` | `welch_t` | 7043 | 1.2e-232 | 3.79e-232 | `hedges_g=0.852` | `[0.797, 0.907]` | `large` |  |
| `PaymentMethod` | `StreamingMovies` | `chi_square` | 7043 | 2.56e-226 | 7.97e-226 | `cramers_v_bc=0.274` | `[0.259, 0.290]` | `medium` |  |
| `PaymentMethod` | `StreamingTV` | `chi_square` | 7043 | 1.14e-224 | 3.47e-224 | `cramers_v_bc=0.273` | `[0.259, 0.286]` | `medium` |  |
| `tenure` | `DeviceProtection` | `welch_anova` | 7043 | 1.15e-224 | 3.47e-224 | `eta_squared=0.141` | `[0.126, 0.157]` | `large` |  |
| `tenure` | `OnlineBackup` | `welch_anova` | 7043 | 4.42e-223 | 1.31e-222 | `eta_squared=0.141` | `[0.127, 0.156]` | `large` |  |
| `InternetService` | `PaperlessBilling` | `chi_square` | 7043 | 9.62e-220 | 2.81e-219 | `cramers_v_bc=0.378` | `[0.359, 0.396]` | `medium` |  |
| `Contract` | `PaymentMethod` | `chi_square` | 7043 | 4.07e-213 | 1.17e-212 | `cramers_v_bc=0.266` | `[0.253, 0.280]` | `medium` |  |
| `MultipleLines` | `StreamingMovies` | `chi_square` | 7043 | 1.42e-208 | 4.01e-208 | `cramers_v_bc=0.262` | `[0.247, 0.277]` | `medium` |  |
| `MultipleLines` | `StreamingTV` | `chi_square` | 7043 | 1.13e-207 | 3.17e-207 | `cramers_v_bc=0.261` | `[0.247, 0.276]` | `medium` |  |
| `Contract` | `OnlineBackup` | `chi_square` | 7043 | 1.47e-202 | 4.06e-202 | `cramers_v_bc=0.258` | `[0.244, 0.273]` | `medium` |  |
| `MonthlyCharges` | `PaperlessBilling` | `welch_t` | 7043 | 9.3e-196 | 2.53e-195 | `hedges_g=-0.765` | `[-0.815, -0.716]` | `medium` |  |
| `Churn` | `OnlineSecurity` | `chi_square` | 7043 | 2.66e-185 | 7.12e-185 | `cramers_v_bc=0.347` | `[0.329, 0.367]` | `medium` |  |
| `DeviceProtection` | `MultipleLines` | `chi_square` | 7043 | 1.03e-183 | 2.72e-183 | `cramers_v_bc=0.246` | `[0.233, 0.260]` | `medium` |  |
| `MultipleLines` | `OnlineBackup` | `chi_square` | 7043 | 6.07e-182 | 1.58e-181 | `cramers_v_bc=0.245` | `[0.230, 0.259]` | `medium` |  |
| `Churn` | `TechSupport` | `chi_square` | 7043 | 1.44e-180 | 3.71e-180 | `cramers_v_bc=0.343` | `[0.322, 0.364]` | `medium` |  |
| `OnlineSecurity` | `PaperlessBilling` | `chi_square` | 7043 | 2.13e-179 | 5.4e-179 | `cramers_v_bc=0.341` | `[0.320, 0.363]` | `medium` |  |
| `tenure` | `OnlineSecurity` | `welch_anova` | 7043 | 8.53e-176 | 2.13e-175 | `eta_squared=0.113` | `[0.099, 0.127]` | `medium` |  |
| `PaperlessBilling` | `StreamingTV` | `chi_square` | 7043 | 1.9e-173 | 4.68e-173 | `cramers_v_bc=0.336` | `[0.315, 0.357]` | `medium` |  |
| `tenure` | `TechSupport` | `welch_anova` | 7043 | 5.86e-173 | 1.43e-172 | `eta_squared=0.111` | `[0.097, 0.125]` | `medium` |  |
| `Contract` | `StreamingMovies` | `chi_square` | 7043 | 2.58e-172 | 6.22e-172 | `cramers_v_bc=0.238` | `[0.224, 0.254]` | `medium` |  |
| `PaperlessBilling` | `StreamingMovies` | `chi_square` | 7043 | 2.06e-169 | 4.9e-169 | `cramers_v_bc=0.332` | `[0.308, 0.355]` | `medium` |  |
| `Contract` | `StreamingTV` | `chi_square` | 7043 | 2.38e-168 | 5.59e-168 | `cramers_v_bc=0.235` | `[0.220, 0.250]` | `medium` |  |
| `PaperlessBilling` | `TechSupport` | `chi_square` | 7043 | 8.54e-167 | 1.98e-166 | `cramers_v_bc=0.329` | `[0.307, 0.350]` | `medium` |  |
| `tenure` | `MultipleLines` | `welch_anova` | 7043 | 1.12e-166 | 2.57e-166 | `eta_squared=0.118` | `[0.104, 0.133]` | `medium` |  |
| `TotalCharges` | `Partner` | `welch_t` | 7032 | 1.04e-162 | 2.36e-162 | `hedges_g=-0.674` | `[-0.722, -0.626]` | `medium` |  |
| `MultipleLines` | `TechSupport` | `chi_square` | 7043 | 3.45e-160 | 7.71e-160 | `cramers_v_bc=0.230` | `[0.215, 0.244]` | `medium` |  |
| `Churn` | `InternetService` | `chi_square` | 7043 | 9.57e-160 | 2.11e-159 | `cramers_v_bc=0.322` | `[0.301, 0.342]` | `medium` |  |
| `MultipleLines` | `OnlineSecurity` | `chi_square` | 7043 | 2.06e-159 | 4.5e-159 | `cramers_v_bc=0.229` | `[0.217, 0.243]` | `medium` |  |
| `DeviceProtection` | `PaperlessBilling` | `chi_square` | 7043 | 6.19e-159 | 1.34e-158 | `cramers_v_bc=0.321` | `[0.302, 0.343]` | `medium` |  |
| `OnlineBackup` | `PaperlessBilling` | `chi_square` | 7043 | 2.33e-158 | 4.97e-158 | `cramers_v_bc=0.321` | `[0.297, 0.340]` | `medium` |  |
| `tenure` | `StreamingMovies` | `welch_anova` | 7043 | 2.85e-141 | 6.01e-141 | `eta_squared=0.090` | `[0.077, 0.104]` | `medium` |  |
| `Churn` | `PaymentMethod` | `chi_square` | 7043 | 3.68e-140 | 7.69e-140 | `cramers_v_bc=0.303` | `[0.283, 0.327]` | `medium` |  |
| `Contract` | `Partner` | `chi_square` | 7043 | 9.27e-135 | 1.91e-134 | `cramers_v_bc=0.296` | `[0.274, 0.317]` | `small` |  |
| `tenure` | `StreamingTV` | `welch_anova` | 7043 | 2.98e-134 | 6.08e-134 | `eta_squared=0.085` | `[0.073, 0.099]` | `medium` |  |
| `Churn` | `OnlineBackup` | `chi_square` | 7043 | 2.08e-131 | 4.2e-131 | `cramers_v_bc=0.292` | `[0.272, 0.310]` | `small` |  |
| `Contract` | `InternetService` | `chi_square` | 7043 | 3.29e-129 | 6.58e-129 | `cramers_v_bc=0.206` | `[0.190, 0.223]` | `small` |  |
| `MonthlyCharges` | `tenure` | `spearman` | 7043 | 1.03e-123 | 2.03e-123 | `spearman_rho=0.276` | `[0.255, 0.299]` | `small` |  |
| `Churn` | `DeviceProtection` | `chi_square` | 7043 | 5.51e-122 | 1.08e-121 | `cramers_v_bc=0.281` | `[0.262, 0.301]` | `small` |  |
| `InternetService` | `SeniorCitizen` | `chi_square` | 7043 | 2.17e-108 | 4.22e-108 | `cramers_v_bc=0.265` | `[0.245, 0.286]` | `small` |  |
| `MonthlyCharges` | `SeniorCitizen` | `welch_t` | 7043 | 3.83e-98 | 7.34e-98 | `hedges_g=-0.612` | `[-0.676, -0.548]` | `medium` |  |
| `PaperlessBilling` | `PaymentMethod` | `chi_square` | 7043 | 4.12e-94 | 7.82e-94 | `cramers_v_bc=0.248` | `[0.225, 0.270]` | `small` |  |
| `Contract` | `Dependents` | `chi_square` | 7043 | 6.15e-92 | 1.16e-91 | `cramers_v_bc=0.244` | `[0.223, 0.267]` | `small` |  |
| `Churn` | `StreamingMovies` | `chi_square` | 7043 | 2.67e-82 | 4.97e-82 | `cramers_v_bc=0.230` | `[0.212, 0.246]` | `small` |  |
| `Churn` | `StreamingTV` | `chi_square` | 7043 | 5.53e-82 | 1.02e-81 | `cramers_v_bc=0.230` | `[0.214, 0.246]` | `small` |  |
| `MultipleLines` | `PaymentMethod` | `chi_square` | 7043 | 1.14e-81 | 2.08e-81 | `cramers_v_bc=0.166` | `[0.153, 0.182]` | `small` |  |
| `SeniorCitizen` | `TechSupport` | `chi_square` | 7043 | 1.69e-77 | 3.06e-77 | `cramers_v_bc=0.223` | `[0.205, 0.243]` | `small` |  |
| `TotalCharges` | `Churn` | `welch_t` | 7032 | 1.15e-75 | 2.07e-75 | `hedges_g=0.461` | `[0.407, 0.514]` | `small` |  |
| `MonthlyCharges` | `Churn` | `welch_t` | 7043 | 8.59e-73 | 1.53e-72 | `hedges_g=-0.446` | `[-0.500, -0.393]` | `small` |  |
| `Dependents` | `SeniorCitizen` | `chi_square` | 7043 | 2.78e-70 | 4.88e-70 | `cramers_v_bc=0.211` | `[0.195, 0.226]` | `small` |  |
| `OnlineSecurity` | `SeniorCitizen` | `chi_square` | 7043 | 7.34e-69 | 1.28e-68 | `cramers_v_bc=0.210` | `[0.193, 0.228]` | `small` |  |
| `Dependents` | `OnlineSecurity` | `chi_square` | 7043 | 1.25e-58 | 2.16e-58 | `cramers_v_bc=0.194` | `[0.173, 0.215]` | `small` |  |
| `PaymentMethod` | `SeniorCitizen` | `chi_square` | 7043 | 2.38e-58 | 4.08e-58 | `cramers_v_bc=0.195` | `[0.176, 0.215]` | `small` |  |
| `Churn` | `PaperlessBilling` | `chi_square` | 7043 | 2.61e-58 | 4.44e-58 | `cramers_v_bc=0.191` | `[0.171, 0.211]` | `small` |  |
| `SeniorCitizen` | `StreamingMovies` | `chi_square` | 7043 | 2.46e-55 | 4.14e-55 | `cramers_v_bc=0.188` | `[0.173, 0.204]` | `small` |  |
| `SeniorCitizen` | `StreamingTV` | `chi_square` | 7043 | 2.12e-53 | 3.53e-53 | `cramers_v_bc=0.185` | `[0.171, 0.200]` | `small` |  |
| `DeviceProtection` | `SeniorCitizen` | `chi_square` | 7043 | 5.54e-52 | 9.15e-52 | `cramers_v_bc=0.182` | `[0.169, 0.197]` | `small` |  |
| `OnlineBackup` | `SeniorCitizen` | `chi_square` | 7043 | 8.12e-52 | 1.33e-51 | `cramers_v_bc=0.182` | `[0.168, 0.197]` | `small` |  |
| `Dependents` | `TechSupport` | `chi_square` | 7043 | 1.35e-51 | 2.2e-51 | `cramers_v_bc=0.182` | `[0.159, 0.206]` | `small` |  |
| `PhoneService` | `StreamingTV` | `chi_square` | 7043 | 1.62e-50 | 2.61e-50 | `cramers_v_bc=0.180` | `[0.170, 0.191]` | `small` |  |
| `Dependents` | `InternetService` | `chi_square` | 7043 | 2e-50 | 3.19e-50 | `cramers_v_bc=0.179` | `[0.158, 0.205]` | `small` |  |
| `Contract` | `PaperlessBilling` | `chi_square` | 7043 | 5.45e-49 | 8.63e-49 | `cramers_v_bc=0.177` | `[0.153, 0.201]` | `small` |  |
| `PhoneService` | `StreamingMovies` | `chi_square` | 7043 | 6.37e-49 | 1e-48 | `cramers_v_bc=0.177` | `[0.168, 0.188]` | `small` |  |
| `PhoneService` | `TechSupport` | `chi_square` | 7043 | 1.26e-48 | 1.96e-48 | `cramers_v_bc=0.176` | `[0.167, 0.187]` | `small` |  |
| `OnlineSecurity` | `PhoneService` | `chi_square` | 7043 | 3.02e-48 | 4.66e-48 | `cramers_v_bc=0.175` | `[0.167, 0.186]` | `small` |  |
| `OnlineBackup` | `PhoneService` | `chi_square` | 7043 | 2.11e-46 | 3.23e-46 | `cramers_v_bc=0.172` | `[0.165, 0.182]` | `small` |  |
| `DeviceProtection` | `PhoneService` | `chi_square` | 7043 | 3.87e-46 | 5.89e-46 | `cramers_v_bc=0.172` | `[0.165, 0.180]` | `small` |  |
| `TotalCharges` | `PhoneService` | `welch_t` | 7032 | 9.1e-45 | 1.37e-44 | `hedges_g=-0.385` | `[-0.464, -0.305]` | `small` |  |
| `Churn` | `Dependents` | `chi_square` | 7043 | 3.28e-43 | 4.9e-43 | `cramers_v_bc=0.164` | `[0.144, 0.184]` | `small` |  |
| `DeviceProtection` | `Partner` | `chi_square` | 7043 | 3.7e-43 | 5.49e-43 | `cramers_v_bc=0.166` | `[0.144, 0.190]` | `small` |  |
| `MultipleLines` | `PaperlessBilling` | `chi_square` | 7043 | 4.83e-43 | 7.11e-43 | `cramers_v_bc=0.165` | `[0.144, 0.188]` | `small` |  |
| `TotalCharges` | `PaperlessBilling` | `welch_t` | 7032 | 1.09e-42 | 1.59e-42 | `hedges_g=-0.325` | `[-0.373, -0.277]` | `small` |  |
| `Dependents` | `OnlineBackup` | `chi_square` | 7043 | 3.06e-41 | 4.44e-41 | `cramers_v_bc=0.162` | `[0.139, 0.184]` | `small` |  |
| `tenure` | `Dependents` | `welch_t` | 7043 | 3.91e-41 | 5.63e-41 | `hedges_g=-0.353` | `[-0.404, -0.302]` | `small` |  |
| `Partner` | `PaymentMethod` | `chi_square` | 7043 | 3.34e-40 | 4.78e-40 | `cramers_v_bc=0.161` | `[0.142, 0.187]` | `small` |  |
| `PaperlessBilling` | `SeniorCitizen` | `chi_square` | 7043 | 2.04e-39 | 2.89e-39 | `cramers_v_bc=0.156` | `[0.135, 0.177]` | `small` |  |
| `Dependents` | `DeviceProtection` | `chi_square` | 7043 | 1.07e-38 | 1.5e-38 | `cramers_v_bc=0.157` | `[0.132, 0.179]` | `small` |  |
| `Churn` | `SeniorCitizen` | `chi_square` | 7043 | 9.48e-37 | 1.32e-36 | `cramers_v_bc=0.150` | `[0.125, 0.173]` | `small` |  |
| `OnlineBackup` | `Partner` | `chi_square` | 7043 | 1.1e-36 | 1.52e-36 | `cramers_v_bc=0.152` | `[0.128, 0.176]` | `small` |  |
| `Churn` | `Partner` | `chi_square` | 7043 | 1.52e-36 | 2.09e-36 | `cramers_v_bc=0.150` | `[0.128, 0.172]` | `small` |  |
| `OnlineSecurity` | `Partner` | `chi_square` | 7043 | 4.58e-36 | 6.26e-36 | `cramers_v_bc=0.151` | `[0.129, 0.178]` | `small` |  |
| `Dependents` | `PaymentMethod` | `chi_square` | 7043 | 1.79e-34 | 2.43e-34 | `cramers_v_bc=0.149` | `[0.127, 0.169]` | `small` |  |
| `Dependents` | `StreamingTV` | `chi_square` | 7043 | 8.22e-34 | 1.11e-33 | `cramers_v_bc=0.146` | `[0.120, 0.169]` | `small` |  |
| `MultipleLines` | `SeniorCitizen` | `chi_square` | 7043 | 1.29e-33 | 1.73e-33 | `cramers_v_bc=0.146` | `[0.121, 0.169]` | `small` |  |
| `MultipleLines` | `Partner` | `chi_square` | 7043 | 2.15e-32 | 2.85e-32 | `cramers_v_bc=0.143` | `[0.122, 0.169]` | `small` |  |
| `Contract` | `SeniorCitizen` | `chi_square` | 7043 | 2.21e-32 | 2.92e-32 | `cramers_v_bc=0.143` | `[0.122, 0.162]` | `small` |  |
| `Dependents` | `StreamingMovies` | `chi_square` | 7043 | 2.82e-31 | 3.69e-31 | `cramers_v_bc=0.140` | `[0.114, 0.166]` | `small` |  |
| `Partner` | `StreamingTV` | `chi_square` | 7043 | 1.42e-29 | 1.84e-29 | `cramers_v_bc=0.136` | `[0.113, 0.158]` | `small` |  |
| `Partner` | `StreamingMovies` | `chi_square` | 7043 | 2.1e-26 | 2.72e-26 | `cramers_v_bc=0.128` | `[0.105, 0.151]` | `small` |  |
| `Partner` | `TechSupport` | `chi_square` | 7043 | 1.21e-25 | 1.55e-25 | `cramers_v_bc=0.127` | `[0.104, 0.150]` | `small` |  |
| `Dependents` | `PaperlessBilling` | `chi_square` | 7043 | 9.01e-21 | 1.15e-20 | `cramers_v_bc=0.111` | `[0.087, 0.134]` | `small` |  |
| `MonthlyCharges` | `Dependents` | `welch_t` | 7043 | 1.28e-20 | 1.62e-20 | `hedges_g=0.250` | `[0.199, 0.301]` | `small` |  |
| `Contract` | `MultipleLines` | `chi_square` | 7043 | 7.8e-19 | 9.81e-19 | `cramers_v_bc=0.079` | `[0.064, 0.097]` | `small` |  |
| `TotalCharges` | `SeniorCitizen` | `welch_t` | 7032 | 2.12e-16 | 2.65e-16 | `hedges_g=-0.279` | `[-0.343, -0.216]` | `small` |  |

## Rejected / Skipped Hypotheses (39)

| Column A | Column B | Test | Raw p | Adj q | Reasons | Explanation |
| :--- | :--- | :--- | ---: | ---: | :--- | :--- |
| `MultipleLines` | `PhoneService` | `chi_square` | 0 | 0 | `trivial_relationship` | Near-deterministic relationship (effect=0.9999) suggests a derived or duplicate column. |
| `MonthlyCharges` | `Partner` | `welch_t` | 4.35e-16 | 5.4e-16 | `effect_below_threshold` | Standardized effect /hedges_g/=0.1947 is below the practical floor (0.20). |
| `MonthlyCharges` | `Contract` | `welch_anova` | 2.33e-08 | 2.88e-08 | `effect_below_threshold` | Standardized effect /eta_squared/=0.0059 is below the practical floor (0.01). |
| `TotalCharges` | `Dependents` | `welch_t` | 8.48e-08 | 1.04e-07 | `effect_below_threshold` | Standardized effect /hedges_g/=0.1415 is below the practical floor (0.20). |
| `Churn` | `MultipleLines` | `chi_square` | 0.00346 | 0.00422 | `effect_below_threshold` | Standardized effect /cramers_v_bc/=0.0364 is below the practical floor (0.10). |
| `tenure` | `InternetService` | `welch_anova` | 0.00432 | 0.00523 | `effect_below_threshold` | Standardized effect /eta_squared/=0.0015 is below the practical floor (0.01). |
| `Dependents` | `MultipleLines` | `chi_square` | 0.109 | 0.131 | `not_significant_after_correction, effect_below_threshold` | Adjusted q=0.1309 exceeds alpha=0.05 (raw p=0.1089, family m=190). Standardized effect /cramers_v_bc/=0.0186 is below the practical floor (0.10). |
| `Partner` | `PhoneService` | `chi_square` | 0.137 | 0.164 | `not_significant_after_correction, effect_below_threshold` | Adjusted q=0.1641 exceeds alpha=0.05 (raw p=0.1373, family m=190). Standardized effect /cramers_v_bc/=0.0131 is below the practical floor (0.10). |
| `tenure` | `SeniorCitizen` | `welch_t` | 0.16 | 0.189 | `not_significant_after_correction, effect_below_threshold` | Adjusted q=0.1894 exceeds alpha=0.05 (raw p=0.1595, family m=190). Standardized effect /hedges_g/=0.0449 is below the practical floor (0.20). |
| `PaperlessBilling` | `PhoneService` | `chi_square` | 0.166 | 0.195 | `not_significant_after_correction, effect_below_threshold` | Adjusted q=0.1955 exceeds alpha=0.05 (raw p=0.1660, family m=190). Standardized effect /cramers_v_bc/=0.0114 is below the practical floor (0.10). |
| `Partner` | `SeniorCitizen` | `chi_square` | 0.167 | 0.195 | `not_significant_after_correction, effect_below_threshold` | Adjusted q=0.1955 exceeds alpha=0.05 (raw p=0.1667, family m=190). Standardized effect /cramers_v_bc/=0.0114 is below the practical floor (0.10). |
| `PaperlessBilling` | `Partner` | `chi_square` | 0.212 | 0.247 | `not_significant_after_correction, effect_below_threshold` | Adjusted q=0.2469 exceeds alpha=0.05 (raw p=0.2119, family m=190). Standardized effect /cramers_v_bc/=0.0089 is below the practical floor (0.10). |
| `MonthlyCharges` | `gender` | `welch_t` | 0.221 | 0.257 | `not_significant_after_correction, effect_below_threshold` | Adjusted q=0.2566 exceeds alpha=0.05 (raw p=0.2215, family m=190). Standardized effect /hedges_g/=0.0291 is below the practical floor (0.20). |
| `Churn` | `PhoneService` | `chi_square` | 0.316 | 0.364 | `not_significant_after_correction, effect_below_threshold` | Adjusted q=0.3642 exceeds alpha=0.05 (raw p=0.3162, family m=190). Standardized effect /cramers_v_bc/=0.0008 is below the practical floor (0.10). |
| `PaperlessBilling` | `gender` | `chi_square` | 0.324 | 0.371 | `not_significant_after_correction, effect_below_threshold` | Adjusted q=0.3708 exceeds alpha=0.05 (raw p=0.3239, family m=190). Standardized effect /cramers_v_bc/=0.0000 is below the practical floor (0.10). |
| `OnlineSecurity` | `gender` | `chi_square` | 0.36 | 0.41 | `not_significant_after_correction, effect_below_threshold` | Adjusted q=0.4100 exceeds alpha=0.05 (raw p=0.3603, family m=190). Standardized effect /cramers_v_bc/=0.0024 is below the practical floor (0.10). |
| `Dependents` | `gender` | `chi_square` | 0.377 | 0.427 | `not_significant_after_correction, effect_below_threshold` | Adjusted q=0.4269 exceeds alpha=0.05 (raw p=0.3775, family m=190). Standardized effect /cramers_v_bc/=0.0000 is below the practical floor (0.10). |
| `tenure` | `PhoneService` | `welch_t` | 0.473 | 0.526 | `not_significant_after_correction, effect_below_threshold` | Adjusted q=0.5259 exceeds alpha=0.05 (raw p=0.4733, family m=190). Standardized effect /hedges_g/=0.0286 is below the practical floor (0.20). |
| `Churn` | `gender` | `chi_square` | 0.47 | 0.526 | `not_significant_after_correction, effect_below_threshold` | Adjusted q=0.5259 exceeds alpha=0.05 (raw p=0.4698, family m=190). Standardized effect /cramers_v_bc/=0.0000 is below the practical floor (0.10). |
| `PhoneService` | `SeniorCitizen` | `chi_square` | 0.472 | 0.526 | `not_significant_after_correction, effect_below_threshold` | Adjusted q=0.5259 exceeds alpha=0.05 (raw p=0.4717, family m=190). Standardized effect /cramers_v_bc/=0.0000 is below the practical floor (0.10). |
| `PaymentMethod` | `gender` | `chi_square` | 0.485 | 0.535 | `not_significant_after_correction, effect_below_threshold` | Adjusted q=0.5354 exceeds alpha=0.05 (raw p=0.4846, family m=190). Standardized effect /cramers_v_bc/=0.0000 is below the practical floor (0.10). |
| `OnlineBackup` | `gender` | `chi_square` | 0.511 | 0.562 | `not_significant_after_correction, effect_below_threshold` | Adjusted q=0.5617 exceeds alpha=0.05 (raw p=0.5115, family m=190). Standardized effect /cramers_v_bc/=0.0000 is below the practical floor (0.10). |
| `PhoneService` | `gender` | `chi_square` | 0.586 | 0.64 | `not_significant_after_correction, effect_below_threshold` | Adjusted q=0.6400 exceeds alpha=0.05 (raw p=0.5861, family m=190). Standardized effect /cramers_v_bc/=0.0000 is below the practical floor (0.10). |
| `tenure` | `PaperlessBilling` | `welch_t` | 0.606 | 0.658 | `not_significant_after_correction, effect_below_threshold` | Adjusted q=0.6579 exceeds alpha=0.05 (raw p=0.6060, family m=190). Standardized effect /hedges_g/=0.0125 is below the practical floor (0.20). |
| `InternetService` | `gender` | `chi_square` | 0.637 | 0.687 | `not_significant_after_correction, effect_below_threshold` | Adjusted q=0.6875 exceeds alpha=0.05 (raw p=0.6368, family m=190). Standardized effect /cramers_v_bc/=0.0000 is below the practical floor (0.10). |
| `tenure` | `gender` | `welch_t` | 0.668 | 0.716 | `not_significant_after_correction, effect_below_threshold` | Adjusted q=0.7164 exceeds alpha=0.05 (raw p=0.6683, family m=190). Standardized effect /hedges_g/=0.0102 is below the practical floor (0.20). |
| `StreamingMovies` | `gender` | `chi_square` | 0.671 | 0.716 | `not_significant_after_correction, effect_below_threshold` | Adjusted q=0.7164 exceeds alpha=0.05 (raw p=0.6712, family m=190). Standardized effect /cramers_v_bc/=0.0000 is below the practical floor (0.10). |
| `TechSupport` | `gender` | `chi_square` | 0.717 | 0.761 | `not_significant_after_correction, effect_below_threshold` | Adjusted q=0.7609 exceeds alpha=0.05 (raw p=0.7169, family m=190). Standardized effect /cramers_v_bc/=0.0000 is below the practical floor (0.10). |
| `MultipleLines` | `gender` | `chi_square` | 0.73 | 0.771 | `not_significant_after_correction, effect_below_threshold` | Adjusted q=0.7706 exceeds alpha=0.05 (raw p=0.7301, family m=190). Standardized effect /cramers_v_bc/=0.0000 is below the practical floor (0.10). |
| `StreamingTV` | `gender` | `chi_square` | 0.759 | 0.797 | `not_significant_after_correction, effect_below_threshold` | Adjusted q=0.7970 exceeds alpha=0.05 (raw p=0.7592, family m=190). Standardized effect /cramers_v_bc/=0.0000 is below the practical floor (0.10). |
| `Contract` | `gender` | `chi_square` | 0.791 | 0.826 | `not_significant_after_correction, effect_below_threshold` | Adjusted q=0.8261 exceeds alpha=0.05 (raw p=0.7913, family m=190). Standardized effect /cramers_v_bc/=0.0000 is below the practical floor (0.10). |
| `PaymentMethod` | `PhoneService` | `chi_square` | 0.862 | 0.895 | `not_significant_after_correction, effect_below_threshold` | Adjusted q=0.8951 exceeds alpha=0.05 (raw p=0.8621, family m=190). Standardized effect /cramers_v_bc/=0.0000 is below the practical floor (0.10). |
| `DeviceProtection` | `gender` | `chi_square` | 0.88 | 0.897 | `not_significant_after_correction, effect_below_threshold` | Adjusted q=0.8966 exceeds alpha=0.05 (raw p=0.8798, family m=190). Standardized effect /cramers_v_bc/=0.0000 is below the practical floor (0.10). |
| `Dependents` | `PhoneService` | `chi_square` | 0.882 | 0.897 | `not_significant_after_correction, effect_below_threshold` | Adjusted q=0.8966 exceeds alpha=0.05 (raw p=0.8825, family m=190). Standardized effect /cramers_v_bc/=0.0000 is below the practical floor (0.10). |
| `SeniorCitizen` | `gender` | `chi_square` | 0.875 | 0.897 | `not_significant_after_correction, effect_below_threshold` | Adjusted q=0.8966 exceeds alpha=0.05 (raw p=0.8751, family m=190). Standardized effect /cramers_v_bc/=0.0000 is below the practical floor (0.10). |
| `Partner` | `gender` | `chi_square` | 0.879 | 0.897 | `not_significant_after_correction, effect_below_threshold` | Adjusted q=0.8966 exceeds alpha=0.05 (raw p=0.8794, family m=190). Standardized effect /cramers_v_bc/=0.0000 is below the practical floor (0.10). |
| `Contract` | `PhoneService` | `chi_square` | 0.946 | 0.956 | `not_significant_after_correction, effect_below_threshold` | Adjusted q=0.9559 exceeds alpha=0.05 (raw p=0.9458, family m=190). Standardized effect /cramers_v_bc/=0.0000 is below the practical floor (0.10). |
| `TotalCharges` | `gender` | `welch_t` | 0.997 | 0.997 | `not_significant_after_correction, effect_below_threshold` | Adjusted q=0.9971 exceeds alpha=0.05 (raw p=0.9968, family m=190). Standardized effect /hedges_g/=0.0001 is below the practical floor (0.20). |
| `InternetService` | `Partner` | `chi_square` | 0.997 | 0.997 | `not_significant_after_correction, effect_below_threshold` | Adjusted q=0.9971 exceeds alpha=0.05 (raw p=0.9971, family m=190). Standardized effect /cramers_v_bc/=0.0000 is below the practical floor (0.10). |
