# Scaling & Transformation Analysis — `heart_disease`

## Decision Summary

> Primary cleaned output is **not** scaled. The Phase 3 test library is rank-based or scale-invariant (Welch/Mann-Whitney, Spearman, Kruskal, chi-square), so scaling would not change results. Log transforms are recommended for columns [chol, oldpeak, ca] only for plotting and for parametric/regression use. A scaled copy is provided for TA review and for any future modeling.

## Scale Disparity Across Numeric Features

- **Max standard deviation:** `51.7535`
- **Min standard deviation:** `1.0067`
- **Scale disparity ratio (`max_std / min_std`):** `51.41x`
- **Z-score standardization recommended for scale-sensitive models (PCA/L1/L2/KNN):** `True`

## Per-Column Transformation Recommendations

| Column | Skewness | Kurtosis | Min | Max | Std | Min >= 0 | Recommended Transform | Reason |
| :--- | ---: | ---: | ---: | ---: | ---: | :---: | :--- | :--- |
| `age` | -0.204 | -0.528 | 29 | 77 | 9.048 | True | `none` | Moderate/low skewness (skew=-0.20); no non-linear transform needed. |
| `trestbps` | 0.717 | 0.923 | 94 | 200 | 17.563 | True | `none` | Moderate/low skewness (skew=0.72); no non-linear transform needed. |
| `chol` | 1.147 | 4.543 | 126 | 564 | 51.753 | True | `log1p` | Right-skewed (skew=1.15 > 1.0) with non-negative domain (min=126); log1p recommended. |
| `thalach` | -0.533 | -0.062 | 71 | 202 | 22.904 | True | `none` | Moderate/low skewness (skew=-0.53); no non-linear transform needed. |
| `oldpeak` | 1.266 | 1.568 | 0 | 6.2 | 1.161 | True | `log1p` | Right-skewed (skew=1.27 > 1.0) with non-negative domain (min=0); log1p recommended. |
| `ca` | 1.296 | 0.781 | 0 | 4 | 1.007 | True | `log1p` | Right-skewed (skew=1.30 > 1.0) with non-negative domain (min=0); log1p recommended. |

## Generated Convenience Artifacts

- **Scaled CSV (TA review / downstream modeling copy):** `data\cleaned\heart_disease_scaled.csv`
