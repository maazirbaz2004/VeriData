# Scaling & Transformation Analysis — `telco_churn`

## Decision Summary

> Primary cleaned output is **not** scaled. The Phase 3 test library is rank-based or scale-invariant (Welch/Mann-Whitney, Spearman, Kruskal, chi-square), so scaling would not change results. Log transforms are recommended for columns [none (no numeric column exceeded skewness threshold)] only for plotting and for parametric/regression use. A scaled copy is provided for TA review and for any future modeling.

## Scale Disparity Across Numeric Features

- **Max standard deviation:** `2266.7714`
- **Min standard deviation:** `24.5595`
- **Scale disparity ratio (`max_std / min_std`):** `92.30x`
- **Z-score standardization recommended for scale-sensitive models (PCA/L1/L2/KNN):** `True`

## Per-Column Transformation Recommendations

| Column | Skewness | Kurtosis | Min | Max | Std | Min >= 0 | Recommended Transform | Reason |
| :--- | ---: | ---: | ---: | ---: | ---: | :---: | :--- | :--- |
| `tenure` | 0.240 | -1.387 | 0 | 72 | 24.559 | True | `none` | Moderate/low skewness (skew=0.24); no non-linear transform needed. |
| `MonthlyCharges` | -0.221 | -1.257 | 18.25 | 118.75 | 30.090 | True | `none` | Moderate/low skewness (skew=-0.22); no non-linear transform needed. |
| `TotalCharges` | 0.962 | -0.232 | 18.8 | 8684.8 | 2266.771 | True | `none` | Moderate/low skewness (skew=0.96); no non-linear transform needed. |

## Generated Convenience Artifacts

- **Scaled CSV (TA review / downstream modeling copy):** `data\cleaned\telco_churn_scaled.csv`
