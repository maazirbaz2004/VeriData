# Cleaning Log — `telco_churn`

## Summary
4 cleaning step group(s) recorded; 0 column(s) type-converted; 11 cell(s) normalized (whitespace/missing tokens/categories); 0 duplicate row(s) removed; 0 row(s) dropped for structural/missingness rules.

## Step-by-Step Log

| Step | Column | Action | Severity | Cells Affected | Rows (Before -> After) | Reason | Examples (Before -> After) |
| :--- | :--- | :--- | :--- | ---: | ---: | :--- | :--- |
| `clean_whitespace_unicode` | `TotalCharges` | `stripped_and_normalized_ws` | info | 11 | 7043 -> 7043 | Stripped leading/trailing whitespace, collapsed internal spaces, and cleaned unicode chars. | `' '` -> `''`; `' '` -> `''`; `' '` -> `''` |
| `structural_drops` | `customerID` | `marked_excluded` | info | 0 | 7043 -> 7043 | Kept column 'customerID' in data but marked role as id (id_like). | - |
| `handle_missing_values` | `TotalCharges` | `imputed_median` | info | 11 | 7043 -> 7043 | Imputed 11 missing cell(s) (0.2%) in 'TotalCharges' with median=1397.475 (imputed output only). | `NaN` -> `1397.475`; `NaN` -> `1397.475`; `NaN` -> `1397.475` |
| `handle_outliers` | `TotalCharges` | `flagged_outliers` | info | 0 | 7043 -> 7043 | Flagged 136 outlier(s) (1.9%) and 0 extreme outlier(s) in 'TotalCharges' (action=flag; values untouched). | `7895.15` -> `7895.15`; `7853.7` -> `7853.7`; `7930.55` -> `7930.55` |
