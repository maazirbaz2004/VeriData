# Scaling & Transformation Analysis — `messy_synthetic`

## Decision Summary

> Primary cleaned output is **not** scaled. The Phase 3 test library is rank-based or scale-invariant (Welch/Mann-Whitney, Spearman, Kruskal, chi-square), so scaling would not change results. Log transforms are recommended for columns [income, monthly_spend] only for plotting and for parametric/regression use. A scaled copy is provided for TA review and for any future modeling.

## Scale Disparity Across Numeric Features

- **Max standard deviation:** `93652.5419`
- **Min standard deviation:** `1.1998`
- **Scale disparity ratio (`max_std / min_std`):** `78059.53x`
- **Z-score standardization recommended for scale-sensitive models (PCA/L1/L2/KNN):** `True`

## Per-Column Transformation Recommendations

| Column | Skewness | Kurtosis | Min | Max | Std | Min >= 0 | Recommended Transform | Reason |
| :--- | ---: | ---: | ---: | ---: | ---: | :---: | :--- | :--- |
| `age` | 0.158 | -0.420 | 18 | 80 | 13.385 | True | `none` | Moderate/low skewness (skew=0.16); no non-linear transform needed. |
| `income` | 13.040 | 214.622 | 15000 | 2.05922e+06 | 93652.542 | True | `log1p` | Right-skewed (skew=13.04 > 1.0) with non-negative domain (min=15000); log1p recommended. |
| `tenure_months` | -0.030 | -1.173 | 0 | 120 | 34.601 | True | `none` | Moderate/low skewness (skew=-0.03); no non-linear transform needed. |
| `monthly_spend` | 17.986 | 387.119 | 5 | 8468.39 | 313.020 | True | `log1p` | Right-skewed (skew=17.99 > 1.0) with non-negative domain (min=5); log1p recommended. |
| `satisfaction` | -0.221 | -0.806 | 1 | 5 | 1.200 | True | `none` | Moderate/low skewness (skew=-0.22); no non-linear transform needed. |

## Generated Convenience Artifacts

- **Scaled CSV (TA review / downstream modeling copy):** `data\cleaned\messy_synthetic_scaled.csv`
