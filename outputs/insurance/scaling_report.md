# Scaling & Transformation Analysis — `insurance`

## Decision Summary

> Primary cleaned output is **not** scaled. The Phase 3 test library is rank-based or scale-invariant (Welch/Mann-Whitney, Spearman, Kruskal, chi-square), so scaling would not change results. Log transforms are recommended for columns [charges] only for plotting and for parametric/regression use. A scaled copy is provided for TA review and for any future modeling.

## Scale Disparity Across Numeric Features

- **Max standard deviation:** `12110.3597`
- **Min standard deviation:** `1.2056`
- **Scale disparity ratio (`max_std / min_std`):** `10045.33x`
- **Z-score standardization recommended for scale-sensitive models (PCA/L1/L2/KNN):** `True`

## Per-Column Transformation Recommendations

| Column | Skewness | Kurtosis | Min | Max | Std | Min >= 0 | Recommended Transform | Reason |
| :--- | ---: | ---: | ---: | ---: | ---: | :---: | :--- | :--- |
| `age` | 0.055 | -1.244 | 18 | 64 | 14.044 | True | `none` | Moderate/low skewness (skew=0.05); no non-linear transform needed. |
| `bmi` | 0.284 | -0.053 | 15.96 | 53.13 | 6.100 | True | `none` | Moderate/low skewness (skew=0.28); no non-linear transform needed. |
| `children` | 0.937 | 0.201 | 0 | 5 | 1.206 | True | `none` | Moderate/low skewness (skew=0.94); no non-linear transform needed. |
| `charges` | 1.515 | 1.604 | 1121.87 | 63770.4 | 12110.360 | True | `log1p` | Right-skewed (skew=1.52 > 1.0) with non-negative domain (min=1121.87); log1p recommended. |

## Generated Convenience Artifacts

- **Scaled CSV (TA review / downstream modeling copy):** `data\cleaned\insurance_scaled.csv`
