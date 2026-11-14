# Cleaning Log — `heart_disease`

## Summary
2 cleaning step group(s) recorded; 0 column(s) type-converted; 0 cell(s) normalized (whitespace/missing tokens/categories); 1 duplicate row(s) removed; 0 row(s) dropped for structural/missingness rules.

## Step-by-Step Log

| Step | Column | Action | Severity | Cells Affected | Rows (Before -> After) | Reason | Examples (Before -> After) |
| :--- | :--- | :--- | :--- | ---: | ---: | :--- | :--- |
| `handle_duplicates` | *(table)* | `dropped_duplicate_rows` | info | 14 | 303 -> 302 | Dropped 1 exact duplicate row(s) (kept first occurrence). | - |
| `handle_outliers` | `trestbps` | `flagged_outliers` | info | 0 | 302 -> 302 | Flagged 9 outlier(s) (3.0%) and 0 extreme outlier(s) in 'trestbps' (action=flag; values untouched). | `172` -> `172`; `178` -> `178`; `180` -> `180` |
| `handle_outliers` | `chol` | `flagged_outliers` | info | 0 | 302 -> 302 | Flagged 5 outlier(s) (1.7%) and 1 extreme outlier(s) in 'chol' (action=flag; values untouched). | `417` -> `417`; `564` -> `564`; `394` -> `394` |
| `handle_outliers` | `thalach` | `flagged_outliers` | info | 0 | 302 -> 302 | Flagged 1 outlier(s) (0.3%) and 0 extreme outlier(s) in 'thalach' (action=flag; values untouched). | `71` -> `71` |
| `handle_outliers` | `oldpeak` | `flagged_outliers` | info | 0 | 302 -> 302 | Flagged 5 outlier(s) (1.7%) and 0 extreme outlier(s) in 'oldpeak' (action=flag; values untouched). | `4.2` -> `4.2`; `6.2` -> `6.2`; `5.6` -> `5.6` |
| `handle_outliers` | `ca` | `flagged_outliers` | info | 0 | 302 -> 302 | Flagged 24 outlier(s) (7.9%) and 0 extreme outlier(s) in 'ca' (action=flag; values untouched). | `3` -> `3`; `4` -> `4`; `3` -> `3` |
