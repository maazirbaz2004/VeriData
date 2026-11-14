# Cleaning Log — `student_performance`

## Summary
2 cleaning step group(s) recorded; 0 column(s) type-converted; 0 cell(s) normalized (whitespace/missing tokens/categories); 0 duplicate row(s) removed; 0 row(s) dropped for structural/missingness rules.

## Step-by-Step Log

| Step | Column | Action | Severity | Cells Affected | Rows (Before -> After) | Reason | Examples (Before -> After) |
| :--- | :--- | :--- | :--- | ---: | ---: | :--- | :--- |
| `standardize_categories` | `guardian` | `flagged_fuzzy_variants` | warning | 0 | 395 -> 395 | Flagged near-duplicate/abbreviation label candidate(s) for human review (not auto-merged): 'other' (32) -> 'mother' (273) [fuzzy, sim=0.91]. | `other` -> `other` |
| `handle_outliers` | `age` | `flagged_outliers` | info | 0 | 395 -> 395 | Flagged 1 outlier(s) (0.3%) and 0 extreme outlier(s) in 'age' (action=flag; values untouched). | `22` -> `22` |
| `handle_outliers` | `Fedu` | `flagged_outliers` | info | 0 | 395 -> 395 | Flagged 2 outlier(s) (0.5%) and 0 extreme outlier(s) in 'Fedu' (action=flag; values untouched). | `0` -> `0`; `0` -> `0` |
| `handle_outliers` | `traveltime` | `flagged_outliers` | info | 0 | 395 -> 395 | Flagged 31 outlier(s) (7.8%) and 0 extreme outlier(s) in 'traveltime' (action=flag; values untouched). | `3` -> `3`; `3` -> `3`; `3` -> `3` |
| `handle_outliers` | `studytime` | `flagged_outliers` | info | 0 | 395 -> 395 | Flagged 27 outlier(s) (6.8%) and 0 extreme outlier(s) in 'studytime' (action=flag; values untouched). | `4` -> `4`; `4` -> `4`; `4` -> `4` |
| `handle_outliers` | `failures` | `flagged_outliers` | info | 0 | 395 -> 395 | Flagged 33 outlier(s) (8.4%) and 0 extreme outlier(s) in 'failures' (action=flag; values untouched). | `3` -> `3`; `3` -> `3`; `2` -> `2` |
| `handle_outliers` | `famrel` | `flagged_outliers` | info | 0 | 395 -> 395 | Flagged 26 outlier(s) (6.6%) and 0 extreme outlier(s) in 'famrel' (action=flag; values untouched). | `1` -> `1`; `2` -> `2`; `2` -> `2` |
| `handle_outliers` | `freetime` | `flagged_outliers` | info | 0 | 395 -> 395 | Flagged 19 outlier(s) (4.8%) and 0 extreme outlier(s) in 'freetime' (action=flag; values untouched). | `1` -> `1`; `1` -> `1`; `1` -> `1` |
| `handle_outliers` | `Dalc` | `flagged_outliers` | info | 0 | 395 -> 395 | Flagged 18 outlier(s) (4.6%) and 0 extreme outlier(s) in 'Dalc' (action=flag; values untouched). | `5` -> `5`; `4` -> `4`; `5` -> `5` |
| `handle_outliers` | `absences` | `flagged_outliers` | info | 0 | 395 -> 395 | Flagged 15 outlier(s) (3.8%) and 5 extreme outlier(s) in 'absences' (action=flag; values untouched). | `25` -> `25`; `54` -> `54`; `26` -> `26` |
| `handle_outliers` | `G2` | `flagged_outliers` | info | 0 | 395 -> 395 | Flagged 13 outlier(s) (3.3%) and 0 extreme outlier(s) in 'G2' (action=flag; values untouched). | `0` -> `0`; `0` -> `0`; `0` -> `0` |
