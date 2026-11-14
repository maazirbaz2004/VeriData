# Scaling & Transformation Analysis — `student_performance`

## Decision Summary

> Primary cleaned output is **not** scaled. The Phase 3 test library is rank-based or scale-invariant (Welch/Mann-Whitney, Spearman, Kruskal, chi-square), so scaling would not change results. Log transforms are recommended for columns [traveltime, failures, Dalc, absences] only for plotting and for parametric/regression use. A scaled copy is provided for TA review and for any future modeling.

## Scale Disparity Across Numeric Features

- **Max standard deviation:** `8.0031`
- **Min standard deviation:** `0.6975`
- **Scale disparity ratio (`max_std / min_std`):** `11.47x`
- **Z-score standardization recommended for scale-sensitive models (PCA/L1/L2/KNN):** `True`

## Per-Column Transformation Recommendations

| Column | Skewness | Kurtosis | Min | Max | Std | Min >= 0 | Recommended Transform | Reason |
| :--- | ---: | ---: | ---: | ---: | ---: | :---: | :--- | :--- |
| `age` | 0.466 | -0.001 | 15 | 22 | 1.276 | True | `none` | Moderate/low skewness (skew=0.47); no non-linear transform needed. |
| `Medu` | -0.318 | -1.090 | 0 | 4 | 1.095 | True | `none` | Moderate/low skewness (skew=-0.32); no non-linear transform needed. |
| `Fedu` | -0.032 | -1.199 | 0 | 4 | 1.088 | True | `none` | Moderate/low skewness (skew=-0.03); no non-linear transform needed. |
| `traveltime` | 1.607 | 2.344 | 1 | 4 | 0.698 | True | `log1p` | Right-skewed (skew=1.61 > 1.0) with non-negative domain (min=1); log1p recommended. |
| `studytime` | 0.632 | -0.014 | 1 | 4 | 0.839 | True | `none` | Moderate/low skewness (skew=0.63); no non-linear transform needed. |
| `failures` | 2.387 | 5.005 | 0 | 3 | 0.744 | True | `log1p` | Right-skewed (skew=2.39 > 1.0) with non-negative domain (min=0); log1p recommended. |
| `famrel` | -0.952 | 1.140 | 1 | 5 | 0.897 | True | `none` | Moderate/low skewness (skew=-0.95); no non-linear transform needed. |
| `freetime` | -0.163 | -0.302 | 1 | 5 | 0.999 | True | `none` | Moderate/low skewness (skew=-0.16); no non-linear transform needed. |
| `goout` | 0.117 | -0.770 | 1 | 5 | 1.113 | True | `none` | Moderate/low skewness (skew=0.12); no non-linear transform needed. |
| `Dalc` | 2.191 | 4.759 | 1 | 5 | 0.891 | True | `log1p` | Right-skewed (skew=2.19 > 1.0) with non-negative domain (min=1); log1p recommended. |
| `Walc` | 0.612 | -0.791 | 1 | 5 | 1.288 | True | `none` | Moderate/low skewness (skew=0.61); no non-linear transform needed. |
| `health` | -0.495 | -1.014 | 1 | 5 | 1.390 | True | `none` | Moderate/low skewness (skew=-0.49); no non-linear transform needed. |
| `absences` | 3.672 | 21.719 | 0 | 75 | 8.003 | True | `log1p` | Right-skewed (skew=3.67 > 1.0) with non-negative domain (min=0); log1p recommended. |
| `G1` | 0.241 | -0.694 | 3 | 19 | 3.319 | True | `none` | Moderate/low skewness (skew=0.24); no non-linear transform needed. |
| `G2` | -0.432 | 0.628 | 0 | 19 | 3.762 | True | `none` | Moderate/low skewness (skew=-0.43); no non-linear transform needed. |
| `G3` | -0.733 | 0.403 | 0 | 20 | 4.581 | True | `none` | Moderate/low skewness (skew=-0.73); no non-linear transform needed. |

## Generated Convenience Artifacts

- **Scaled CSV (TA review / downstream modeling copy):** `data\cleaned\student_performance_scaled.csv`
