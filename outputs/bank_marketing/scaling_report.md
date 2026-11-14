# Scaling & Transformation Analysis — `bank_marketing`

## Decision Summary

> Primary cleaned output is **not** scaled. The Phase 3 test library is rank-based or scale-invariant (Welch/Mann-Whitney, Spearman, Kruskal, chi-square), so scaling would not change results. Log transforms are recommended for columns [duration, campaign, previous] only for plotting and for parametric/regression use. A scaled copy is provided for TA review and for any future modeling.

## Scale Disparity Across Numeric Features

- **Max standard deviation:** `259.3053`
- **Min standard deviation:** `0.4950`
- **Scale disparity ratio (`max_std / min_std`):** `523.89x`
- **Z-score standardization recommended for scale-sensitive models (PCA/L1/L2/KNN):** `True`

## Per-Column Transformation Recommendations

| Column | Skewness | Kurtosis | Min | Max | Std | Min >= 0 | Recommended Transform | Reason |
| :--- | ---: | ---: | ---: | ---: | ---: | :---: | :--- | :--- |
| `age` | 0.785 | 0.791 | 17 | 98 | 10.421 | True | `none` | Moderate/low skewness (skew=0.78); no non-linear transform needed. |
| `duration` | 3.263 | 20.244 | 0 | 4918 | 259.305 | True | `log1p` | Right-skewed (skew=3.26 > 1.0) with non-negative domain (min=0); log1p recommended. |
| `campaign` | 4.762 | 36.972 | 1 | 56 | 2.770 | True | `log1p` | Right-skewed (skew=4.76 > 1.0) with non-negative domain (min=1); log1p recommended. |
| `pdays` | -4.921 | 22.222 | 0 | 999 | 186.937 | True | `none` | Moderate/low skewness (skew=-4.92); no non-linear transform needed. |
| `previous` | 3.831 | 20.102 | 0 | 7 | 0.495 | True | `log1p` | Right-skewed (skew=3.83 > 1.0) with non-negative domain (min=0); log1p recommended. |
| `emp.var.rate` | -0.724 | -1.063 | -3.4 | 1.4 | 1.571 | False | `none` | Moderate/low skewness (skew=-0.72); no non-linear transform needed. |
| `cons.price.idx` | -0.231 | -0.830 | 92.201 | 94.767 | 0.579 | True | `none` | Moderate/low skewness (skew=-0.23); no non-linear transform needed. |
| `cons.conf.idx` | 0.303 | -0.359 | -50.8 | -26.9 | 4.628 | False | `none` | Moderate/low skewness (skew=0.30); no non-linear transform needed. |
| `euribor3m` | -0.709 | -1.407 | 0.634 | 5.045 | 1.734 | True | `none` | Moderate/low skewness (skew=-0.71); no non-linear transform needed. |
| `nr.employed` | -1.044 | -0.004 | 4963.6 | 5228.1 | 72.251 | True | `none` | Moderate/low skewness (skew=-1.04); no non-linear transform needed. |

## Generated Convenience Artifacts

- **Scaled CSV (TA review / downstream modeling copy):** `data\cleaned\bank_marketing_scaled.csv`
