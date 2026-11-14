# VeriData — Agentic Data Scientist (Phase 1: Deterministic Ingestion, Cleaning, EDA & Insights)

**VeriData (Phase 1)** is an automated, deterministic data engineering and exploratory data analysis (EDA) pipeline developed for the **Agentic Data Scientist** system. Given any raw CSV dataset, the pipeline performs fault-tolerant CSV ingestion, 10-class semantic type inference, comprehensive statistical profiling, conservative and imputed 12-step data cleaning with full cell-level audit logs, scaling/transformation analysis, publication-ready 150-DPI visualizations, and rule-based traceable insights.

---

## 1. Problem Statement

Real-world tabular datasets rarely arrive ready for statistical testing or machine learning. They suffer from inconsistent encodings and delimiters, numeric columns corrupted by currency symbols or whitespace blanks (`" "` in Telco `TotalCharges`), placeholder missing tokens (`"?"`, `"unknown"`, `"N/A"`), mixed date formats, inconsistent category capitalization and typos, duplicate records, extreme outliers, and severe skewness or class imbalance.

At the same time, relying on an ungrounded Large Language Model (LLM) to clean or summarize raw CSV files risks **silent data corruption, hallucinated statistics, and irreproducible preprocessing decisions**, while aggressive manual cleaning (such as blindly dropping outliers or imputing missing values before exploratory analysis) can distort distributions and fabricate false positives in downstream hypothesis testing.

**Phase 1 solves this problem by building:**
1. **A reusable, 100% deterministic Python library (`ads`)** where every number, cleaning action, chart, and insight is produced by tested code—never guessed by an LLM—and where raw data is never mutated.
2. **A dual-output conservative cleaning architecture** that produces both a **Conservative Cleaned Dataset** (`<name>_cleaned.csv`, preserving true `NaN` values and flagging outliers without deleting valid extremes) for unbiased statistical analysis in Phases 2–3, and an **Imputed Cleaned Dataset** (`<name>_cleaned_imputed.csv`, with median/mode imputation and explicit `<col>__was_missing` indicator flags) plus a **Scaled Dataset** (`<name>_scaled.csv`) for downstream modeling.
3. **A documented multi-dataset benchmark study** across **5 real-world datasets + 1 synthetic messy benchmark** with 18 injected defect categories, complete with executed Jupyter notebooks, self-contained HTML/Markdown reports, and an objective ground-truth answer key.

---

## 2. Dataset Details & Download Links

We evaluate the Phase 1 pipeline across **5 real public datasets** spanning healthcare, telecommunications, education, and banking, plus **1 synthetic messy benchmark** generated with a cell-level ground-truth manifest.

> **Automated Download:** Run `python scripts/download_datasets.py --datasets all` to automatically download and verify all 5 real datasets into `data/raw/<dataset>/`, and `python scripts/make_messy_dataset.py --seed 42 --variants` to generate the synthetic datasets in `data/synthetic/`. Full dataset cards are in [`docs/datasets.md`](file:///c:/Users/Mr%20Laptop%20point/OneDrive/Desktop/VeriData/docs/datasets.md).

### Summary Table

| # | Dataset Name (`id`) | Source & Direct Download Link | Raw Shape (Rows × Cols) | Cleaned Shape (Conservative) | Target Variable |
| :-- | :--- | :--- | :--- | :--- | :--- |
| **1** | **Medical Cost / Insurance** (`insurance`) | [Kaggle](https://www.kaggle.com/datasets/mirichoi0218/insurance) · [Direct CSV](https://raw.githubusercontent.com/stedy/Machine-Learning-with-R-datasets/master/insurance.csv) | 1,338 × 7 | 1,337 × 7 | `charges` (Continuous USD, `$1,121.87`–`$63,770.43`) |
| **2** | **Telco Customer Churn** (`telco_churn`) | [Kaggle](https://www.kaggle.com/datasets/blastchar/telco-customer-churn) · [Direct CSV](https://raw.githubusercontent.com/IBM/telco-customer-churn-on-icp4d/master/data/Telco-Customer-Churn.csv) | 7,043 × 21 | 7,043 × 21 | `Churn` (Binary: `Yes` 26.5% / `No` 73.5%) |
| **3** | **Heart Disease (UCI)** (`heart_disease`) | [UCI ID 45](https://archive.ics.uci.edu/dataset/45/heart+disease) · [Direct CSV](https://raw.githubusercontent.com/sharmaroshan/Heart-UCI-Dataset/master/heart.csv) | 303 × 14 | 302 × 14 | `target` (Binary: `1` 54.3% / `0` 45.7%) |
| **4** | **Student Performance (Math)** (`student_performance`) | [UCI ID 320](https://archive.ics.uci.edu/dataset/320/student+performance) · [Direct CSV](https://raw.githubusercontent.com/guipsamora/pandas_exercises/master/04_Apply/Students_Alcohol_Consumption/student-mat.csv) | 395 × 33 | 395 × 33 | `G3` (Discrete grade `0`–`20`) |
| **5** | **Bank Marketing (Full)** (`bank_marketing`) | [UCI ID 222](https://archive.ics.uci.edu/dataset/222/bank+marketing) · [Direct ZIP](https://archive.ics.uci.edu/static/public/222/bank+marketing.zip) | 41,188 × 21 | 41,176 × 21 | `y` (Binary term deposit: `yes` 11.3% / `no` 88.7%) |
| **6** | **Messy Synthetic Benchmark** (`messy_synthetic`) | Generated locally via `ads make-messy --seed 42` ([`src/ads/synthetic/`](file:///c:/Users/Mr%20Laptop%20point/OneDrive/Desktop/VeriData/src/ads/synthetic)) | 2,040 × 17 | 2,000 × 15 | `churned` (Binary: `0` / `1`) |

### Features & Domain Overview per Dataset

1. **Medical Cost / Insurance (`insurance`)**
   - **Features (7):** `age` (beneficiary age, 18–64), `sex` (`female`/`male`), `bmi` (body mass index, 15.96–53.13), `children` (number of dependents, 0–5), `smoker` (`yes`/`no`), `region` (`northeast`, `northwest`, `southeast`, `southwest`), and **Target:** `charges` (billed medical costs).
   - **Cleaned Files:** [`data/cleaned/insurance_cleaned.csv`](file:///c:/Users/Mr%20Laptop%20point/OneDrive/Desktop/VeriData/data/cleaned/insurance_cleaned.csv), [`insurance_cleaned_imputed.csv`](file:///c:/Users/Mr%20Laptop%20point/OneDrive/Desktop/VeriData/data/cleaned/insurance_cleaned_imputed.csv), [`insurance_scaled.csv`](file:///c:/Users/Mr%20Laptop%20point/OneDrive/Desktop/VeriData/data/cleaned/insurance_scaled.csv).

2. **Telco Customer Churn (`telco_churn`)**
   - **Features (21):** `customerID` (unique ID), demographics (`gender`, `SeniorCitizen` [0/1], `Partner`, `Dependents`), account info (`tenure` [0–72 months], `Contract`, `PaperlessBilling`, `PaymentMethod`, `MonthlyCharges`, `TotalCharges`), phone/internet services (`PhoneService`, `MultipleLines`, `InternetService`, `OnlineSecurity`, `OnlineBackup`, `DeviceProtection`, `TechSupport`, `StreamingTV`, `StreamingMovies`), and **Target:** `Churn` (`Yes`/`No`).
   - **Cleaned Files:** [`data/cleaned/telco_churn_cleaned.csv`](file:///c:/Users/Mr%20Laptop%20point/OneDrive/Desktop/VeriData/data/cleaned/telco_churn_cleaned.csv), [`telco_churn_cleaned_imputed.csv`](file:///c:/Users/Mr%20Laptop%20point/OneDrive/Desktop/VeriData/data/cleaned/telco_churn_cleaned_imputed.csv), [`telco_churn_scaled.csv`](file:///c:/Users/Mr%20Laptop%20point/OneDrive/Desktop/VeriData/data/cleaned/telco_churn_scaled.csv).

3. **Heart Disease (`heart_disease`)**
   - **Features (14):** `age` (29–77), `sex` (0/1), `cp` (chest pain type, 0–3), `trestbps` (resting blood pressure, mm Hg), `chol` (serum cholesterol, mg/dL), `fbs` (fasting blood sugar $>120$ mg/dL, 0/1), `restecg` (resting ECG, 0–2), `thalach` (max heart rate achieved), `exang` (exercise-induced angina, 0/1), `oldpeak` (ST depression induced by exercise), `slope` (peak exercise ST slope, 0–2), `ca` (major vessels colored by fluoroscopy, 0–4), `thal` (thalassemia code, 0–3), and **Target:** `target` (0/1).
   - **Cleaned Files:** [`data/cleaned/heart_disease_cleaned.csv`](file:///c:/Users/Mr%20Laptop%20point/OneDrive/Desktop/VeriData/data/cleaned/heart_disease_cleaned.csv), [`heart_disease_cleaned_imputed.csv`](file:///c:/Users/Mr%20Laptop%20point/OneDrive/Desktop/VeriData/data/cleaned/heart_disease_cleaned_imputed.csv), [`heart_disease_scaled.csv`](file:///c:/Users/Mr%20Laptop%20point/OneDrive/Desktop/VeriData/data/cleaned/heart_disease_scaled.csv).

4. **Student Performance — Math (`student_performance`)**
   - **Features (33):** School & demographics (`school`, `sex`, `age`, `address`, `famsize`, `Pstatus`), parental background (`Medu`, `Fedu`, `Mjob`, `Fjob`, `guardian`), study habits & lifestyle (`reason`, `traveltime`, `studytime`, `failures`, `schoolsup`, `famsup`, `paid`, `activities`, `nursery`, `higher`, `internet`, `romantic`, `famrel`, `freetime`, `goout`, `Dalc`, `Walc`, `health`, `absences`), prior period grades (`G1`, `G2`), and **Target:** `G3` (final math grade, 0–20).
   - **Cleaned Files:** [`data/cleaned/student_performance_cleaned.csv`](file:///c:/Users/Mr%20Laptop%20point/OneDrive/Desktop/VeriData/data/cleaned/student_performance_cleaned.csv), [`student_performance_cleaned_imputed.csv`](file:///c:/Users/Mr%20Laptop%20point/OneDrive/Desktop/VeriData/data/cleaned/student_performance_cleaned_imputed.csv), [`student_performance_scaled.csv`](file:///c:/Users/Mr%20Laptop%20point/OneDrive/Desktop/VeriData/data/cleaned/student_performance_scaled.csv).

5. **Bank Marketing (`bank_marketing`)**
   - **Features (21):** Client profile (`age`, `job`, `marital`, `education`, `default`, `housing`, `loan`), campaign contact attributes (`contact`, `month`, `day_of_week`, `duration`, `campaign`, `pdays`, `previous`, `poutcome`), macroeconomic indicators (`emp.var.rate`, `cons.price.idx`, `cons.conf.idx`, `euribor3m`, `nr.employed`), and **Target:** `y` (subscribed term deposit: `yes`/`no`).
   - **Cleaned Files:** [`data/cleaned/bank_marketing_cleaned.csv`](file:///c:/Users/Mr%20Laptop%20point/OneDrive/Desktop/VeriData/data/cleaned/bank_marketing_cleaned.csv), [`bank_marketing_cleaned_imputed.csv`](file:///c:/Users/Mr%20Laptop%20point/OneDrive/Desktop/VeriData/data/cleaned/bank_marketing_cleaned_imputed.csv), [`bank_marketing_scaled.csv`](file:///c:/Users/Mr%20Laptop%20point/OneDrive/Desktop/VeriData/data/cleaned/bank_marketing_scaled.csv).

6. **Messy Synthetic Benchmark (`messy_synthetic`)**
   - **Features (17 raw → 15 cleaned):** `Unnamed: 0` (exported index), `customer_id`, `age`, `tenure_months`, `monthly_spend`, `total_spend`, `satisfaction_score`, `support_tickets`, `discount_rate`, `signup_date`, `plan_tier`, `region`, `payment_method`, `is_active`, `notes`, `constant_col`, `all_null_col`, and **Target:** `churned` (`0`/`1`).
   - **Cleaned Files:** [`data/cleaned/messy_synthetic_cleaned.csv`](file:///c:/Users/Mr%20Laptop%20point/OneDrive/Desktop/VeriData/data/cleaned/messy_synthetic_cleaned.csv), [`messy_synthetic_cleaned_imputed.csv`](file:///c:/Users/Mr%20Laptop%20point/OneDrive/Desktop/VeriData/data/cleaned/messy_synthetic_cleaned_imputed.csv), [`messy_synthetic_scaled.csv`](file:///c:/Users/Mr%20Laptop%20point/OneDrive/Desktop/VeriData/data/cleaned/messy_synthetic_scaled.csv).

---

## 3. Summary of Data Cleaning & Preprocessing Steps

Our cleaning engine ([`src/ads/cleaning/`](file:///c:/Users/Mr%20Laptop%20point/OneDrive/Desktop/VeriData/src/ads/cleaning)) executes **12 deterministic steps in strict order**, recording every change in `outputs/<dataset>/cleaning_log.md` and `cleaning_log.json`:

| Step | Module / Function | What It Does & Why |
| :-- | :--- | :--- |
| **0. String-First Ingestion** | `ads.ingestion.load_csv` | Detects encoding (`UTF-8` / `UTF-8-SIG` BOM / `Latin-1` fallback) and delimiter (`,`, `;`, `\t`, `\|`), skips malformed ragged rows safely, and loads all cells as raw strings (`dtype=str, keep_default_na=False`) so pandas never silently coerces formatting quirks. |
| **1. Column Name Normalization** | `normalize_column_names` | Strips leading/trailing whitespace and invisible BOM characters from headers; deduplicates repeated column names (`col`, `col.1`). |
| **2. Whitespace & Unicode Normalization** | `clean_whitespace_unicode` | Strips leading/trailing spaces, collapses internal multiple spaces, and removes zero-width Unicode characters (`\u200b`, `\ufeff`) and non-breaking spaces (`\u00a0`). Turns whitespace-only strings (`"   "`) into `""`. |
| **3. Missing-Token Normalization** | `normalize_missing_tokens` | Replaces placeholder tokens (`""`, `"na"`, `"n/a"`, `"null"`, `"none"`, `"nan"`, `"?"`, `"--"`, `"-999"`, `"missing"`, plus `"unknown"` when configured as in `bank_marketing`) with true `np.nan`. |
| **4. Category Standardization** | `standardize_categories` | Merges case/whitespace/punctuation variants (e.g., `"North"` / `"north"` / `"NORTH "` → majority form `"North"`). Flags near-duplicate fuzzy typos (e.g., `"Nroth"` vs `"North"`, sequence similarity $\ge 0.88$) in the audit log without aggressively merging distinct codes. |
| **5. Type Conversion & Coercion** | `convert_types` | Parses numeric strings with currency symbols (`$`), thousands commas (`,`), percentages (`%`), and accounting parentheses (`(1,234.5)` → `-1234.5`). Standardizes dates to ISO `YYYY-MM-DD`, flagging ambiguous `DD/MM` vs `MM/DD` dates. Casts clean integer columns to nullable `Int64`. |
| **6. Domain Validity Rules** | `apply_validity_rules` | Enforces domain range rules from config (e.g., `age in [0, 120]`, `tenure >= 0`, `satisfaction_score in [1, 5]`). Out-of-range values (such as negative ages `-5` or impossible `999`) are set to `NaN` and logged. |
| **7. Duplicate Row Handling** | `handle_duplicates` | Detects exact duplicates on a normalized copy. Under `drop_duplicates: auto`, drops exact duplicates while keeping the first occurrence (`1` removed in `insurance`, `1` in `heart_disease`, `12` in `bank_marketing`, `40` in `messy_synthetic`). Also checks for duplicate `id_like` keys. |
| **8. Structural Drops** | `structural_drops` | Drops 100% empty rows, 100% `NaN` columns (`all_null_col`), and redundant exported row-index columns (`Unnamed: 0`). Marks constant and ID columns as `excluded`/`id` in `column_schema.json`. |
| **9. Missing Value Handling (Dual Output)** | `handle_missing_values` | Produces **two cleaned DataFrames**: (1) **Conservative (`_cleaned.csv`)** keeping `NaN` intact for unbiased statistical testing; (2) **Imputed (`_cleaned_imputed.csv`)** dropping columns with $>80\%$ missingness, imputing numeric columns with the **median** and categorical/binary columns with the **mode**, and adding `<col>__was_missing` (`0`/`1`) indicator columns. |
| **10. Outlier Detection & Policy** | `handle_outliers` | Computes both $1.5 \times \text{IQR}$ / $3.0 \times \text{IQR}$ fences and Modified Z-scores ($0.6745 \times |x - \text{median}| / \text{MAD}$, guarded when $\text{MAD}=0$). Default policy is **`flag`** (records exact counts and bounds in `cleaning_log.json` and `report.md` without deleting valid extreme observations). |
| **11. Scaling & Transformation Analysis** | `analyze_scaling` | Evaluates skewness and cross-column scale disparity ($\max \sigma / \min \sigma$). Recommends `log1p` for right-skewed positive columns (`skew > 1.0`), `yeo_johnson` when negatives exist, and `zscore` for scale-sensitive models, saving `<name>_scaled.csv` and `scaling_report.md`. |
| **12. Post-Condition & Idempotence Verification** | `clean_dataset` | Asserts row-count reconciliation (`rows_raw - rows_dropped == rows_cleaned`), zero remaining placeholder strings or unstripped whitespace, and **idempotence** (re-running `clean_dataset` on `df_clean_conservative` produces 0 further changes). |

---

## 4. Key Findings Across Datasets

Every dataset's full narrative, tables, and charts are available in `outputs/<dataset>/report.md` (and `report.html`) and in `notebooks/<dataset>_phase1.ipynb`. Below is a synthesis of the primary findings:

### 1. Medical Cost / Insurance (`insurance`)
- **Data Cleaning:** Removed `1` exact duplicate row (`1,338 → 1,337` rows); `0` missing values; `139` rows (`10.40%`) in `charges` flagged above the $1.5 \times \text{IQR}$ fence (`$34,524.78`).
- **Dominant Driver (`smoker → charges`):** Smoking status explains **$62.0\%$ of the variance** in medical charges ($\eta^2 = 0.62$, Spearman $\rho$ equivalent). Smokers average **`$32,050`** in billed charges compared to **`$8,441`** for non-smokers.
- **Synergistic Interaction (`smoker × bmi → charges`):** While BMI has a moderate overall correlation with charges (Pearson $r = +0.20$, Spearman $\rho = +0.12$), scatter and subgroup plots reveal a sharp interaction: obese smokers ($\text{BMI} \ge 30$) cluster in a high-cost tier (`$35,000–$63,770`), whereas non-smokers increase gradually with age.
- **Age Progression (`age → charges`):** Charges rise monotonically with beneficiary age (Spearman $\rho = +0.53$, Pearson $r = +0.30$) along three parallel cost bands.
- **Scaling Decision:** `charges` is strongly right-skewed (`skew = +1.52`); `log1p` transformation is applied in `insurance_scaled.csv` for parametric modeling, while rank-based tests are recommended for Phase 3.

### 2. Telco Customer Churn (`telco_churn`)
- **Data Cleaning:** Detected and fixed **11 whitespace-only cells (`" "`)** in `TotalCharges`, converting them to `NaN` in the conservative output and casting the remaining `7,032` values from `object` to `float64`. In the imputed output, `TotalCharges` is median-imputed alongside a `TotalCharges__was_missing` indicator column.
- **Structural Missingness Discovery:** All 11 missing `TotalCharges` records belong to customers with **`tenure == 0`** (newly onboarded customers who have not completed their first billing cycle), proving the missingness is structurally **MAR** rather than random corruption.
- **Contract Type & Early-Tenure Churn:** `Contract` is the strongest categorical predictor of `Churn` (bias-corrected Cramér's $V = 0.41$): customers on **Month-to-month** contracts churn at **`42.7%`**, compared to **`11.3%`** for one-year and **`2.8%`** for two-year contracts. `tenure` is strongly negatively associated with churn (Spearman $\rho = -0.37$; median tenure is `10` months for churners vs. `38` months for retained customers).
- **Pricing & Service Collinearity:** `TotalCharges` and `tenure` are strongly collinear (Pearson $r = +0.83$, Spearman $\rho = +0.89$). Six internet add-on columns (`OnlineSecurity`, `TechSupport`, etc.) share the `"No internet service"` category (`21.7%` of rows), producing Cramér's $V \ge 0.50$ across add-on pairs.

### 3. Heart Disease (`heart_disease`)
- **Data Cleaning:** Removed `1` exact duplicate patient record (`303 → 302` rows). Four integer-encoded clinical codes (`cp`, `restecg`, `slope`, `thal`) were configured as `categorical_nominal` so they are analyzed via group comparisons ($\eta^2$ / Cramér's $V$) rather than spurious linear correlations.
- **Key Clinical Associations with `target`:** The strongest categorical associations with diagnosis (`target`) are **thalassemia (`thal`, Cramér's $V = 0.52$)**, **chest pain type (`cp`, Cramér's $V = 0.51$)**, and **exercise-induced angina (`exang`, Cramér's $V = 0.43$)**. Among numeric features, **ST depression (`oldpeak`, Spearman $\rho = -0.43$)**, **maximum heart rate (`thalach`, Spearman $\rho = +0.43$)**, and **major vessels (`ca`, Spearman $\rho = -0.46$)** show the largest separation between classes.
- **Distributional Quirks:** `oldpeak` is both right-skewed (`skew = +1.27`) and **zero-inflated (`32.8%` exact zeros)**, and `chol` contains a extreme clinically plausible outlier (`564 mg/dL`). Non-parametric rank tests are recommended.

### 4. Student Performance — Math (`student_performance`)
- **Data Cleaning:** Semicolon-delimited (`;`) CSV with `395` rows and `33` columns; stripped quotes from string-formatted integer grades (`G1`, `G2`); `0` missing values and `0` duplicates.
- **Longitudinal Grade Collinearity (`G1`, `G2` → `G3`):** Second-period grade `G2` (Spearman $\rho = +0.96$, Pearson $r = +0.90$) and first-period grade `G1` (Spearman $\rho = +0.88$, Pearson $r = +0.80$) strongly determine final grade `G3`. Excluding prior grades, **past class failures (`failures`, Spearman $\rho = -0.36$)**, **mother's education (`Medu`, $\rho = +0.23$)**, and **higher-education ambition (`higher`, Cramér's $V = 0.18$)** are the top behavioral/demographic predictors.
- **Zero-Inflation in Final Grade (`G3 = 0`):** `38` students (`9.6%`) have `G3 = 0` despite positive `G1`/`G2` scores and `0` recorded absences—representing exam non-attendance/dropouts rather than continuous grade outcomes.
- **Skewed Lifestyle Features:** `absences` (`skew = +3.67`), `failures` (`skew = +2.39`), and `Dalc` (`skew = +2.19`) are heavily right-skewed and zero-inflated (`78.7%` of students have `failures == 0`).

### 5. Bank Marketing (`bank_marketing`)
- **Data Cleaning:** Semicolon-delimited (`;`) dataset with `41,188` raw rows. Normalized **`12,718` `"unknown"` placeholder cells** across 6 columns (`default`: `8,597` [20.9%], `education`: `1,731` [4.2%], `housing`: `990` [2.4%], `loan`: `990` [2.4%], `job`: `330`, `marital`: `80`) to `NaN`, and removed **`12` exact duplicate rows** (`41,188 → 41,176` rows).
- **Target Imbalance & Leakage Warning:** Only **`11.27%`** of calls result in a term deposit subscription (`y = yes`, imbalance ratio `7.87 : 1`). Call `duration` has the strongest association with `y` (Spearman $\rho = +0.35$), but `duration` is only known *after* the call ends (target leakage for pre-call prediction).
- **Macroeconomic Collinearity & Sentinel Values:** Three macroeconomic indicators—`euribor3m`, `emp.var.rate`, and `nr.employed`—are nearly collinear (Pearson $r = +0.94$ to $+0.97$). Meanwhile, `pdays = 999` (`96.3%` of rows) is a sentinel code for *"client never previously contacted"*, which aligns with `poutcome = nonexistent` ($\eta^2 = 0.90$).

### 6. Messy Synthetic Benchmark (`messy_synthetic`)
- **Ground-Truth Defect Recovery:** Across `2,040` raw rows and `17` columns with **18 injected defect categories**, the pipeline automatically:
  1. Dropped the redundant exported index (`Unnamed: 0`) and 100% empty column (`all_null_col`), reducing `17 → 15` columns, and flagged `constant_col` (`role = excluded`).
  2. Removed all **`40` injected duplicate rows** (`2,040 → 2,000` clean rows).
  3. Stripped whitespace/Unicode oddities (`233` cells), normalized `569` placeholder missing tokens across 8 columns, merged `200` case/punctuation variants in `region`, flagged `32` fuzzy typo cells (`"Nroth"`), parsed currency/accounting strings in `monthly_spend` (`$1,234.50`), parsed percentage strings in `discount_rate` (`15%`), standardized mixed date formats in `signup_date`, and set `39` out-of-range values (`age < 0`, `age > 120`, `satisfaction_score > 5`) to `NaN`—achieving **zero cell damage** on clean reference cells.

---

## 5. Graphs & Visualizations

For every dataset, the pipeline generates **10 to 13 high-resolution (150 DPI) static PNG visualizations** in `outputs/<dataset>/figures/`, accompanied by descriptive captions in `outputs/<dataset>/report.md`, `outputs/<dataset>/report.html`, and inside the Jupyter notebooks:

1. **Missingness Bar Chart & Co-Missingness Heatmap (`missing_bar.png`, `missing_heatmap.png`):** Shows the exact percentage of missing cells per column and whether missing values co-occur across rows.
2. **Numeric Distributions (`numeric_distributions_1.png`, `numeric_detail_<col>.png`):** Histograms + KDE curves with vertical mean and median markers, highlighting skewness, multimodality, and zero-inflation.
3. **Numeric Boxplots & Outlier Summary (`numeric_boxplots_1.png`, `outlier_summary.png`):** Displays medians, interquartile ranges, and $1.5 \times \text{IQR}$ / $3.0 \times \text{IQR}$ outlier flags.
4. **Categorical Frequency & Cardinality Panels (`categorical_bars_1.png`, `cardinality_bar.png`):** Horizontal bar charts of category proportions and unique-level counts, highlighting rare levels ($<1\%$).
5. **Target Distribution / Class Balance (`target_distribution.png`):** Shows class balance ratios for classification targets (`Churn`, `target`, `y`, `churned`) or histogram/boxplot + log-scale view for continuous targets (`charges`, `G3`).
6. **Correlation & Association Heatmaps (`correlation_heatmap.png`, `cramers_v_heatmap.png`):** Side-by-side Pearson $r$ and Spearman $\rho$ heatmaps for numeric features, plus bias-corrected Cramér's $V$ heatmaps for categorical pairs.
7. **Top Bivariate Scatter Pairs & Grouped Boxplots (`top_scatter_pairs.png`, `numeric_by_category.png`, `target_relationships.png`):** Visualizes the strongest numeric-numeric pairs, numeric-by-category $\eta^2$ breakdowns, and top features ranked by association with the target variable.

---

## 6. How to Run the Notebooks & Pipeline

### Step 1: Install Requirements
```bash
# Install all dependencies
python -m pip install -r requirements.txt

# Install the `ads` package in editable mode
python -m pip install -e .
```

### Step 2: Download Datasets & Run the Pipeline (Optional — Pre-Generated Outputs Are Already Included!)
Cleaned datasets (`data/cleaned/*.csv`), EDA figures (`outputs/<dataset>/figures/*.png`), and executed notebooks (`notebooks/*.ipynb`) are **already generated and saved** in this repository. To regenerate everything from scratch:

```bash
# 1. Download all 5 real datasets into data/raw/
python scripts/download_datasets.py --datasets all

# 2. Generate the messy synthetic dataset + ground-truth manifest in data/synthetic/
python scripts/make_messy_dataset.py --seed 42 --variants

# 3. Run the Phase 1 pipeline on all 6 datasets
python scripts/run_all.py

# Or run on a single CSV file:
python -m ads.cli run --input data/raw/insurance/insurance.csv --name insurance
```

### Step 3: Open and Run the Jupyter Notebooks
All notebooks are located in [`notebooks/`](file:///c:/Users/Mr%20Laptop%20point/OneDrive/Desktop/VeriData/notebooks) and have **all cells pre-executed so outputs, tables, and embedded charts are immediately visible** on GitHub or in VS Code / Jupyter:

- [`notebooks/00_overview.ipynb`](file:///c:/Users/Mr%20Laptop%20point/OneDrive/Desktop/VeriData/notebooks/00_overview.ipynb) — Cross-dataset summary table, cleaning metrics, and comparison across all 6 datasets.
- [`notebooks/insurance_phase1.ipynb`](file:///c:/Users/Mr%20Laptop%20point/OneDrive/Desktop/VeriData/notebooks/insurance_phase1.ipynb) — Cleaning, EDA, visualizations, scaling, and insights for **Medical Cost / Insurance**.
- [`notebooks/telco_churn_phase1.ipynb`](file:///c:/Users/Mr%20Laptop%20point/OneDrive/Desktop/VeriData/notebooks/telco_churn_phase1.ipynb) — Cleaning, EDA, visualizations, scaling, and insights for **Telco Customer Churn**.
- [`notebooks/heart_disease_phase1.ipynb`](file:///c:/Users/Mr%20Laptop%20point/OneDrive/Desktop/VeriData/notebooks/heart_disease_phase1.ipynb) — Cleaning, EDA, visualizations, scaling, and insights for **Heart Disease**.
- [`notebooks/student_performance_phase1.ipynb`](file:///c:/Users/Mr%20Laptop%20point/OneDrive/Desktop/VeriData/notebooks/student_performance_phase1.ipynb) — Cleaning, EDA, visualizations, scaling, and insights for **Student Performance (Math)**.
- [`notebooks/bank_marketing_phase1.ipynb`](file:///c:/Users/Mr%20Laptop%20point/OneDrive/Desktop/VeriData/notebooks/bank_marketing_phase1.ipynb) — Cleaning, EDA, visualizations, scaling, and insights for **Bank Marketing**.
- [`notebooks/messy_synthetic_phase1.ipynb`](file:///c:/Users/Mr%20Laptop%20point/OneDrive/Desktop/VeriData/notebooks/messy_synthetic_phase1.ipynb) — Cleaning, EDA, visualizations, and ground-truth defect recovery for **Messy Synthetic Benchmark**.

To launch Jupyter interactively from the repository root:
```bash
jupyter notebook notebooks/
```
*(Or open any `.ipynb` file directly in VS Code / Cursor and click **Run All**.)*

---

## 7. Repository Structure & Output Guide

```text
VeriData/
├── README.md                           # Project overview, dataset details, cleaning summary & findings
├── requirements.txt                    # Python dependencies
├── pyproject.toml                      # Package configuration (`ads` CLI)
├── configs/
│   ├── default.yaml                    # Global thresholds (missingness, IQR, skew, cardinality)
│   └── datasets/*.yaml                 # Per-dataset config overrides & human-verified truth_types
├── data/
│   ├── raw/                            # Raw CSVs (downloaded via scripts/download_datasets.py)
│   ├── cleaned/                        # Cleaned, imputed & scaled CSVs for all 6 datasets
│   └── synthetic/                      # Messy synthetic CSVs + ground-truth manifest JSON
├── notebooks/                          # Executed Jupyter notebooks (.ipynb) with visible outputs & plots
├── outputs/
│   └── <dataset>/
│       ├── report.md                   # Complete Markdown dataset report
│       ├── report.html                 # Self-contained HTML dataset report
│       ├── profile.json                # Raw dataset profile (schema_version="1.0")
│       ├── column_schema.json          # Phase 2 handoff schema
│       ├── cleaning_log.md / .json     # Step-by-step cleaning audit log with before/after examples
│       ├── eda_summary.json            # Computed descriptive statistics & bivariate effect sizes
│       ├── insights.md / .json         # Automated rule-based + analyst manual insights
│       ├── scaling_report.md           # Skewness analysis & transformation decisions
│       ├── figures/*.png               # 150-DPI static PNG visualizations
│       └── tables/*.md                 # Markdown summary tables
├── scripts/
│   ├── download_datasets.py            # Automated dataset downloader
│   ├── make_messy_dataset.py           # Synthetic messy dataset generator
│   └── run_all.py                      # Batch runner for all configured datasets
├── src/ads/                            # Core Python library (ingestion, profiling, cleaning, eda, insights)
├── docs/                               # Dataset cards (datasets.md), contract.md, decisions.md
└── tests/                              # Unit, golden-file, determinism & integration tests
```
