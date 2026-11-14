# Cleaning Log — `messy_synthetic`

## Summary
10 cleaning step group(s) recorded; 5 column(s) type-converted; 952 cell(s) normalized (whitespace/missing tokens/categories); 80 duplicate row(s) removed; 10 row(s) dropped for structural/missingness rules.

## Step-by-Step Log

| Step | Column | Action | Severity | Cells Affected | Rows (Before -> After) | Reason | Examples (Before -> After) |
| :--- | :--- | :--- | :--- | ---: | ---: | :--- | :--- |
| `normalize_column_names` | *(table)* | `normalized_headers` | info | 1 | 2090 -> 2090 | Normalized 1 column name(s) (stripped whitespace/BOM). | `membership ` -> `membership` |
| `clean_whitespace_unicode` | `gender` | `stripped_and_normalized_ws` | info | 122 | 2090 -> 2090 | Stripped leading/trailing whitespace, collapsed internal spaces, and cleaned unicode chars. | `' MALE '` -> `'MALE'`; `' Female '` -> `'Female'`; `' female '` -> `'female'` |
| `clean_whitespace_unicode` | `region` | `stripped_and_normalized_ws` | info | 146 | 2090 -> 2090 | Stripped leading/trailing whitespace, collapsed internal spaces, and cleaned unicode chars. | `'North  Area'` -> `'North Area'`; `'East Coast  '` -> `'East Coast'`; `'Central Hub  '` -> `'Central Hub'` |
| `clean_whitespace_unicode` | `membership` | `stripped_and_normalized_ws` | info | 123 | 2090 -> 2090 | Stripped leading/trailing whitespace, collapsed internal spaces, and cleaned unicode chars. | `'  Basic'` -> `'Basic'`; `'  Gold'` -> `'Gold'`; `'  Silver'` -> `'Silver'` |
| `normalize_missing_tokens` | `income` | `converted_to_NaN` | info | 126 | 2090 -> 2090 | Replaced placeholder missing token(s) ('-': 39, '?': 36, 'N/A': 26, 'null': 25) with NaN. | `N/A` -> `NaN`; `N/A` -> `NaN`; `-` -> `NaN` |
| `normalize_missing_tokens` | `region` | `converted_to_NaN` | info | 83 | 2090 -> 2090 | Replaced placeholder missing token(s) ('Unknown': 83) with NaN. | `Unknown` -> `NaN`; `Unknown` -> `NaN`; `Unknown` -> `NaN` |
| `standardize_categories` | `gender` | `merged_case_variants` | info | 226 | 2090 -> 2090 | Merged 5 case-only variant spelling(s) into dominant form. | `female` -> `Female`; `MALE` -> `Male`; `male` -> `Male` |
| `standardize_categories` | `gender` | `flagged_fuzzy_variants` | warning | 0 | 2090 -> 2090 | Flagged near-duplicate/abbreviation label candidate(s) for human review (not auto-merged): 'M' (28) -> 'Male' (1019) [abbreviation, sim=0.85]; 'F' (35) -> 'Female' (998) [abbreviation, sim=0.85]. | `M` -> `M`; `F` -> `F` |
| `standardize_categories` | `membership` | `merged_case_variants` | info | 20 | 2090 -> 2090 | Merged 3 case-only variant spelling(s) into dominant form. | `SILVER` -> `Silver`; `BASIC` -> `Basic`; `SILVER` -> `Silver` |
| `standardize_categories` | `churned` | `merged_case_variants` | info | 47 | 2090 -> 2090 | Merged 2 case-only variant spelling(s) into dominant form. | `no` -> `No`; `no` -> `No`; `yes` -> `Yes` |
| `standardize_categories` | `churned` | `standardized_binary_tokens` | warning | 59 | 2090 -> 2090 | Standardized mixed boolean tokens in 'churned' into dominant labels ('Yes' / 'No'). | `0` -> `No`; `1` -> `Yes`; `Y` -> `Yes` |
| `convert_types` | `income` | `cast_dtype` | info | 1914 | 2090 -> 2090 | Converted 'income' to float64, stripping numeric formatting on 1914 cell(s). | `$49,691.74` -> `49691.7`; `$41,181.65` -> `41181.7`; `$52,275.29` -> `52275.3` |
| `convert_types` | `tenure_months` | `coerced_to_NaN` | warning | 20 | 2090 -> 2090 | Coerced 20 unparseable numeric token(s) in 'tenure_months' to NaN. | `twelve` -> `NaN`; `twenty` -> `NaN`; `twelve` -> `NaN` |
| `convert_types` | `monthly_spend` | `cast_dtype` | info | 2080 | 2090 -> 2090 | Converted 'monthly_spend' to float64, stripping numeric formatting on 2080 cell(s). | `$149.07` -> `149.07`; `$121.17` -> `121.17`; `$117.31` -> `117.31` |
| `convert_types` | `signup_date` | `coerced_to_NaN` | warning | 21 | 2090 -> 2090 | Coerced 21 unparseable datetime string(s) in 'signup_date' to NaN. | `not_a_valid_date` -> `NaN`; `not_a_valid_date` -> `NaN`; `not_a_valid_date` -> `NaN` |
| `convert_types` | `signup_date` | `standardized_datetime` | info | 1374 | 2090 -> 2090 | Standardized 1374 date cell(s) in 'signup_date' to ISO format (%Y-%m-%d). | `01/10/2023` -> `2023-10-01`; `Mar 22, 2024` -> `2024-03-22`; `18/04/2023` -> `2023-04-18` |
| `apply_validity_rules` | `age` | `invalid_to_NaN` | warning | 21 | 2090 -> 2090 | Set 21 out-of-range cell(s) in 'age' to NaN (rule: min=0.0, max=120.0, allowed=None). | `-7.0` -> `NaN`; `-5.0` -> `NaN`; `-17.0` -> `NaN` |
| `apply_validity_rules` | `tenure_months` | `invalid_to_NaN` | warning | 11 | 2090 -> 2090 | Set 11 out-of-range cell(s) in 'tenure_months' to NaN (rule: min=0.0, max=None, allowed=None). | `-1.0` -> `NaN`; `-7.0` -> `NaN`; `-2.0` -> `NaN` |
| `handle_duplicates` | *(table)* | `dropped_duplicate_rows` | info | 1200 | 2090 -> 2010 | Dropped 80 exact duplicate row(s) (kept first occurrence). | - |
| `structural_drops` | `Unnamed: 0` | `dropped_index_column` | info | 2010 | 2010 -> 2010 | Dropped redundant exported index column 'Unnamed: 0'. | - |
| `structural_drops` | `unused` | `dropped_empty_column` | info | 2010 | 2010 -> 2010 | Dropped fully empty column 'unused'. | - |
| `structural_drops` | *(table)* | `dropped_empty_rows` | info | 130 | 2010 -> 2000 | Dropped 10 fully empty row(s). | - |
| `structural_drops` | `customer_id` | `marked_excluded` | info | 0 | 2000 -> 2000 | Kept column 'customer_id' in data but marked role as id (id_like). | - |
| `structural_drops` | `notes` | `marked_excluded` | info | 0 | 2000 -> 2000 | Kept column 'notes' in data but marked role as excluded (free_text). | - |
| `structural_drops` | `constant_flag` | `marked_excluded` | info | 0 | 2000 -> 2000 | Kept column 'constant_flag' in data but marked role as excluded (constant). | - |
| `handle_missing_values` | `age` | `imputed_median` | info | 140 | 2000 -> 2000 | Imputed 140 missing cell(s) (7.0%) in 'age' with median=42.0 (imputed output only). | `NaN` -> `42.0`; `NaN` -> `42.0`; `NaN` -> `42.0` |
| `handle_missing_values` | `income` | `imputed_median` | info | 160 | 2000 -> 2000 | Imputed 160 missing cell(s) (8.0%) in 'income' with median=52125.75 (imputed output only). | `NaN` -> `52125.75`; `NaN` -> `52125.75`; `NaN` -> `52125.75` |
| `handle_missing_values` | `region` | `imputed_mode` | info | 80 | 2000 -> 2000 | Imputed 80 missing cell(s) (4.0%) in 'region' with mode='North Area' (imputed output only). | `NaN` -> `North Area`; `NaN` -> `North Area`; `NaN` -> `North Area` |
| `handle_missing_values` | `tenure_months` | `imputed_median` | info | 30 | 2000 -> 2000 | Imputed 30 missing cell(s) (1.5%) in 'tenure_months' with median=61.0 (imputed output only). | `NaN` -> `61.0`; `NaN` -> `61.0`; `NaN` -> `61.0` |
| `handle_missing_values` | `signup_date` | `left_datetime_missing` | info | 0 | 2000 -> 2000 | Datetime column 'signup_date' has 20 missing value(s); left un-imputed per policy. | - |
| `handle_missing_values` | `satisfaction` | `imputed_median` | info | 60 | 2000 -> 2000 | Imputed 60 missing cell(s) (3.0%) in 'satisfaction' with median=3 (imputed output only). | `NaN` -> `3`; `NaN` -> `3`; `NaN` -> `3` |
| `handle_outliers` | `age` | `flagged_outliers` | info | 0 | 2000 -> 2000 | Flagged 7 outlier(s) (0.4%) and 0 extreme outlier(s) in 'age' (action=flag; values untouched). | `80` -> `80`; `78` -> `78`; `78` -> `78` |
| `handle_outliers` | `income` | `flagged_outliers` | info | 0 | 2000 -> 2000 | Flagged 97 outlier(s) (5.3%) and 27 extreme outlier(s) in 'income' (action=flag; values untouched). | `131326` -> `131326`; `176550` -> `176550`; `132927` -> `132927` |
| `handle_outliers` | `monthly_spend` | `flagged_outliers` | info | 0 | 2000 -> 2000 | Flagged 90 outlier(s) (4.5%) and 28 extreme outlier(s) in 'monthly_spend' (action=flag; values untouched). | `391.47` -> `391.47`; `406.83` -> `406.83`; `442.51` -> `442.51` |
