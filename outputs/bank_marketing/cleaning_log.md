# Cleaning Log — `bank_marketing`

## Summary
4 cleaning step group(s) recorded; 0 column(s) type-converted; 12718 cell(s) normalized (whitespace/missing tokens/categories); 12 duplicate row(s) removed; 0 row(s) dropped for structural/missingness rules.

## Step-by-Step Log

| Step | Column | Action | Severity | Cells Affected | Rows (Before -> After) | Reason | Examples (Before -> After) |
| :--- | :--- | :--- | :--- | ---: | ---: | :--- | :--- |
| `normalize_missing_tokens` | `job` | `converted_to_NaN` | info | 330 | 41188 -> 41188 | Replaced placeholder missing token(s) ('unknown': 330) with NaN. | `unknown` -> `NaN`; `unknown` -> `NaN`; `unknown` -> `NaN` |
| `normalize_missing_tokens` | `marital` | `converted_to_NaN` | info | 80 | 41188 -> 41188 | Replaced placeholder missing token(s) ('unknown': 80) with NaN. | `unknown` -> `NaN`; `unknown` -> `NaN`; `unknown` -> `NaN` |
| `normalize_missing_tokens` | `education` | `converted_to_NaN` | info | 1731 | 41188 -> 41188 | Replaced placeholder missing token(s) ('unknown': 1731) with NaN. | `unknown` -> `NaN`; `unknown` -> `NaN`; `unknown` -> `NaN` |
| `normalize_missing_tokens` | `default` | `converted_to_NaN` | warning | 8597 | 41188 -> 41188 | Replaced placeholder missing token(s) ('unknown': 8597) with NaN. | `unknown` -> `NaN`; `unknown` -> `NaN`; `unknown` -> `NaN` |
| `normalize_missing_tokens` | `housing` | `converted_to_NaN` | info | 990 | 41188 -> 41188 | Replaced placeholder missing token(s) ('unknown': 990) with NaN. | `unknown` -> `NaN`; `unknown` -> `NaN`; `unknown` -> `NaN` |
| `normalize_missing_tokens` | `loan` | `converted_to_NaN` | info | 990 | 41188 -> 41188 | Replaced placeholder missing token(s) ('unknown': 990) with NaN. | `unknown` -> `NaN`; `unknown` -> `NaN`; `unknown` -> `NaN` |
| `handle_duplicates` | *(table)* | `dropped_duplicate_rows` | info | 252 | 41188 -> 41176 | Dropped 12 exact duplicate row(s) (kept first occurrence). | - |
| `handle_missing_values` | `job` | `imputed_mode` | info | 330 | 41176 -> 41176 | Imputed 330 missing cell(s) (0.8%) in 'job' with mode='admin.' (imputed output only). | `NaN` -> `admin.`; `NaN` -> `admin.`; `NaN` -> `admin.` |
| `handle_missing_values` | `marital` | `imputed_mode` | info | 80 | 41176 -> 41176 | Imputed 80 missing cell(s) (0.2%) in 'marital' with mode='married' (imputed output only). | `NaN` -> `married`; `NaN` -> `married`; `NaN` -> `married` |
| `handle_missing_values` | `education` | `imputed_mode` | info | 1730 | 41176 -> 41176 | Imputed 1730 missing cell(s) (4.2%) in 'education' with mode='university.degree' (imputed output only). | `NaN` -> `university.degree`; `NaN` -> `university.degree`; `NaN` -> `university.degree` |
| `handle_missing_values` | `default` | `imputed_missing_level` | info | 8596 | 41176 -> 41176 | Imputed 8596 missing cell(s) (20.9%) in 'default' with missing_level='Missing' (imputed output only). | `NaN` -> `Missing`; `NaN` -> `Missing`; `NaN` -> `Missing` |
| `handle_missing_values` | `housing` | `imputed_mode` | info | 990 | 41176 -> 41176 | Imputed 990 missing cell(s) (2.4%) in 'housing' with mode='yes' (imputed output only). | `NaN` -> `yes`; `NaN` -> `yes`; `NaN` -> `yes` |
| `handle_missing_values` | `loan` | `imputed_mode` | info | 990 | 41176 -> 41176 | Imputed 990 missing cell(s) (2.4%) in 'loan' with mode='no' (imputed output only). | `NaN` -> `no`; `NaN` -> `no`; `NaN` -> `no` |
| `handle_outliers` | `age` | `flagged_outliers` | info | 0 | 41176 -> 41176 | Flagged 468 outlier(s) (1.1%) and 4 extreme outlier(s) in 'age' (action=flag; values untouched). | `70` -> `70`; `76` -> `76`; `73` -> `73` |
| `handle_outliers` | `duration` | `flagged_outliers` | info | 0 | 41176 -> 41176 | Flagged 2963 outlier(s) (7.2%) and 1043 extreme outlier(s) in 'duration' (action=flag; values untouched). | `1666` -> `1666`; `787` -> `787`; `812` -> `812` |
| `handle_outliers` | `campaign` | `flagged_outliers` | info | 0 | 41176 -> 41176 | Flagged 2406 outlier(s) (5.8%) and 1094 extreme outlier(s) in 'campaign' (action=flag; values untouched). | `7` -> `7`; `8` -> `8`; `8` -> `8` |
| `handle_outliers` | `pdays` | `flagged_outliers` | info | 0 | 41176 -> 41176 | Flagged 1515 outlier(s) (3.7%) and 0 extreme outlier(s) in 'pdays' (action=flag; values untouched). | `6` -> `6`; `4` -> `4`; `4` -> `4` |
| `handle_outliers` | `previous` | `flagged_outliers` | info | 0 | 41176 -> 41176 | Flagged 5625 outlier(s) (13.7%) and 0 extreme outlier(s) in 'previous' (action=flag; values untouched). | `1` -> `1`; `1` -> `1`; `1` -> `1` |
| `handle_outliers` | `emp.var.rate` | `flagged_outliers` | info | 0 | 41176 -> 41176 | Flagged 13494 outlier(s) (32.8%) and 0 extreme outlier(s) in 'emp.var.rate' (action=flag; values untouched). | `-1.8` -> `-1.8`; `-1.8` -> `-1.8`; `-1.8` -> `-1.8` |
| `handle_outliers` | `cons.conf.idx` | `flagged_outliers` | info | 0 | 41176 -> 41176 | Flagged 446 outlier(s) (1.1%) and 0 extreme outlier(s) in 'cons.conf.idx' (action=flag; values untouched). | `-26.9` -> `-26.9`; `-26.9` -> `-26.9`; `-26.9` -> `-26.9` |
| `handle_outliers` | `euribor3m` | `flagged_outliers` | info | 0 | 41176 -> 41176 | Flagged 17081 outlier(s) (41.5%) and 0 extreme outlier(s) in 'euribor3m' (action=flag; values untouched). | `4.286` -> `4.286`; `4.286` -> `4.286`; `4.286` -> `4.286` |
| `handle_outliers` | `nr.employed` | `flagged_outliers` | info | 0 | 41176 -> 41176 | Flagged 1408 outlier(s) (3.4%) and 0 extreme outlier(s) in 'nr.employed' (action=flag; values untouched). | `4991.6` -> `4991.6`; `4991.6` -> `4991.6`; `4991.6` -> `4991.6` |
