# Cleaning Log — `insurance`

## Summary
2 cleaning step group(s) recorded; 0 column(s) type-converted; 0 cell(s) normalized (whitespace/missing tokens/categories); 1 duplicate row(s) removed; 0 row(s) dropped for structural/missingness rules.

## Step-by-Step Log

| Step | Column | Action | Severity | Cells Affected | Rows (Before -> After) | Reason | Examples (Before -> After) |
| :--- | :--- | :--- | :--- | ---: | ---: | :--- | :--- |
| `handle_duplicates` | *(table)* | `dropped_duplicate_rows` | info | 7 | 1338 -> 1337 | Dropped 1 exact duplicate row(s) (kept first occurrence). | - |
| `handle_outliers` | `bmi` | `flagged_outliers` | info | 0 | 1337 -> 1337 | Flagged 9 outlier(s) (0.7%) and 0 extreme outlier(s) in 'bmi' (action=flag; values untouched). | `49.06` -> `49.06`; `48.07` -> `48.07`; `47.52` -> `47.52` |
| `handle_outliers` | `charges` | `flagged_outliers` | info | 0 | 1337 -> 1337 | Flagged 139 outlier(s) (10.4%) and 6 extreme outlier(s) in 'charges' (action=flag; values untouched). | `39611.8` -> `39611.8`; `36837.5` -> `36837.5`; `37701.9` -> `37701.9` |
