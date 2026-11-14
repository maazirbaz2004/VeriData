# Dataset Cards (`docs/datasets.md`)

One card per dataset used in Phase 1 (plan Section 5.3). Raw files live in `data/raw/<name>/`, are never modified, and are git-ignored; download steps are in [`scripts/download_datasets.md`](../scripts/download_datasets.md) and automated via [`scripts/download_datasets.py`](../scripts/download_datasets.py).

| # | Dataset | File | Rows × cols | Target | Owner | SHA-256 recorded |
| :-- | :--- | :--- | :--- | :--- | :--- | :---: |
| 1 | Medical Cost / Insurance | `insurance/insurance.csv` | 1,338 × 7 | `charges` (numeric) | Partner 1 (Maaz) | ✔ |
| 2 | Telco Customer Churn | `telco_churn/WA_Fn-UseC_-Telco-Customer-Churn.csv` | 7,043 × 21 | `Churn` (binary) | Partner 1 (Maaz) | ✔ |
| 3 | Heart Disease | `heart_disease/heart.csv` | 303 × 14 | `target` (binary) | Partner 1 (Maaz) | ✔ |
| 4 | Student Performance (Math) | `student_performance/student-mat.csv` | 395 × 33 | `G3` (numeric) | Partner 2 (Tahreem) | ✔ |
| 5 | Bank Marketing (additional, full) | `bank_marketing/bank-additional-full.csv` | 41,188 × 21 | `y` (binary) | Partner 2 (Tahreem) | ✔ |
| 6 | Messy Synthetic | `data/synthetic/messy_dataset.csv` (generated) | 2,040 × 17 (2,000 base rows + injected defects) | `churned` (binary) | Partner 1 generator / Partner 2 analysis | ✔ |

> **LLM contamination note (plan Section 20, risk 7):** datasets 1–5 are public and an LLM may have seen them during training. The messy synthetic dataset is the contamination-free test for the LLM comparison.

---

## 1. Medical Cost / Insurance (`insurance`)

| Field | Value |
| :--- | :--- |
| Source | Kaggle (`mirichoi0218/insurance`) / Brett Lantz, *Machine Learning with R* — <https://raw.githubusercontent.com/stedy/Machine-Learning-with-R-datasets/master/insurance.csv> |
| License | Open Database License (ODbL) / Educational Public Dataset |
| Downloaded | 2026-11-08 |
| SHA-256 | `505c1cbc2e63d0363bac59501563df2530aadf4cdb9cfee226f4ef32f5468281` |
| Shape | 1,338 raw rows × 7 columns (1,337 cleaned rows × 7 columns after removing 1 exact duplicate row), `,`-delimited, 0 missing cells |
| Target | `charges` — individual medical costs billed by health insurance (USD) |
| Config | [`configs/datasets/insurance.yaml`](../configs/datasets/insurance.yaml) |

**Columns:**

| Column | Description |
| :--- | :--- |
| `age` | Age of primary beneficiary (18–64 years) |
| `sex` | Insurance contractor gender (`female`, `male`) |
| `bmi` | Body mass index ($\text{kg/m}^2$, ideally 18.5 to 24.9; range 15.96–53.13) |
| `children` | Number of children covered by health insurance / number of dependents (0–5) |
| `smoker` | Smoking status (`yes`, `no`) |
| `region` | Beneficiary's residential area in the US (`northeast`, `northwest`, `southeast`, `southwest`) |
| `charges` | Individual medical costs billed by health insurance (`$1,121.87`–`$63,770.43`, target) |

**Quirks noticed while loading**
- Contains 1 exact duplicate row (`age=19, sex=male, bmi=30.59, children=0, smoker=no, region=northwest, charges=1639.5631`), which is detected and removed in Step 7.
- `charges` is strongly right-skewed (`skew = +1.52`) with a pronounced upper tail driven by smokers with high BMI (`bmi >= 30`), where 139 values (~10.4%) exceed the $1.5 \times \text{IQR}$ fence (`$34,524.78`). Kept in conservative output and recommended for `log1p` scaling in parametric models.

---

## 2. Telco Customer Churn (`telco_churn`)

| Field | Value |
| :--- | :--- |
| Source | IBM Cognos Analytics Sample Data / Kaggle (`blastchar/telco-customer-churn`) — <https://raw.githubusercontent.com/IBM/telco-customer-churn-on-icp4d/master/data/Telco-Customer-Churn.csv> |
| License | IBM Sample Data License / Apache-2.0 mirror |
| Downloaded | 2026-11-08 |
| SHA-256 | `16320c9c1ec72448db59aa0a26a0b95401046bef5d02fd3aeb906448e3055e91` |
| Shape | 7,043 rows × 21 columns, `,`-delimited, 0 exact duplicate rows |
| Target | `Churn` — whether the customer left within the last month (`No` 5,174 / `Yes` 1,869; 26.54% churn) |
| Config | [`configs/datasets/telco_churn.yaml`](../configs/datasets/telco_churn.yaml) |

**Columns:**

| Column | Description |
| :--- | :--- |
| `customerID` | Unique alphanumeric customer identifier (e.g. `7590-VHVEG`, inferred as `id_like`) |
| `gender` | Customer gender (`Female`, `Male`) |
| `SeniorCitizen` | Whether the customer is a senior citizen (`0`, `1`; forced to `categorical_nominal` in config) |
| `Partner`, `Dependents` | Whether the customer has a partner or dependents (`Yes`, `No`) |
| `tenure` | Number of months the customer has stayed with the company (`0`–`72`) |
| `PhoneService` | Whether the customer has phone service (`Yes`, `No`) |
| `MultipleLines` | Whether the customer has multiple lines (`Yes`, `No`, `No phone service`) |
| `InternetService` | Customer's internet service provider (`DSL`, `Fiber optic`, `No`) |
| `OnlineSecurity`, `OnlineBackup`, `DeviceProtection`, `TechSupport`, `StreamingTV`, `StreamingMovies` | Internet add-on services (`Yes`, `No`, `No internet service`) |
| `Contract` | Contract term (`Month-to-month`, `One year`, `Two year`) |
| `PaperlessBilling` | Whether the customer has paperless billing (`Yes`, `No`) |
| `PaymentMethod` | Payment method (`Electronic check`, `Mailed check`, `Bank transfer (automatic)`, `Credit card (automatic)`) |
| `MonthlyCharges` | Amount charged to the customer monthly (`$18.25`–`$118.75`) |
| `TotalCharges` | Total amount charged to the customer (`$18.80`–`$8,684.80`, stored as string with 11 blank spaces `" "`) |
| `Churn` | Whether the customer churned (`Yes`, `No`, target) |

**Quirks noticed while loading**
- `TotalCharges` is stored as an `object` string column because 11 rows contain a single whitespace character (`" "`). All 11 rows correspond to new subscribers with `tenure == 0`. String-first ingestion strips the whitespace to `""` -> `NaN` and converts the remaining 7,032 rows cleanly to `float64`.
- `SeniorCitizen` is stored as `0`/`1` integers rather than `Yes`/`No` strings.
- Six add-on columns share the level `"No internet service"` (1,526 rows, 21.67%), creating structural Cramér's $V$ associations among internet service columns.

---

## 3. Heart Disease (`heart_disease`)

| Field | Value |
| :--- | :--- |
| Source | UCI Machine Learning Repository (Cleveland Heart Disease, id 45) / Kaggle (`johnsmith88/heart-disease-dataset`) — <https://raw.githubusercontent.com/sharmaroshan/Heart-UCI-Dataset/master/heart.csv> |
| License | Creative Commons Attribution 4.0 International (CC BY 4.0) |
| Downloaded | 2026-11-08 |
| SHA-256 | `7c3014365675306819510a49ff289efbec1d1a6a666a2dc7652f1547b383d859` |
| Shape | 303 raw rows × 14 columns (302 cleaned rows × 14 columns after removing 1 exact duplicate row), `,`-delimited, 0 missing cells |
| Target | `target` — heart disease diagnosis (`1` = 165 rows, `0` = 138 rows in raw) |
| Config | [`configs/datasets/heart_disease.yaml`](../configs/datasets/heart_disease.yaml) |

**Columns:**

| Column | Description |
| :--- | :--- |
| `age` | Patient age in years (29–77) |
| `sex` | Patient sex (`1` = male, `0` = female) |
| `cp` | Chest pain type (`0`: typical angina, `1`: atypical angina, `2`: non-anginal pain, `3`: asymptomatic) |
| `trestbps` | Resting blood pressure in mm Hg on admission (94–200) |
| `chol` | Serum cholesterol in mg/dL (126–564) |
| `fbs` | Fasting blood sugar $> 120\text{ mg/dL}$ (`1` = true, `0` = false) |
| `restecg` | Resting electrocardiographic results (`0`: normal, `1`: ST-T wave abnormality, `2`: left ventricular hypertrophy) |
| `thalach` | Maximum heart rate achieved during exercise testing (71–202 bpm) |
| `exang` | Exercise-induced angina (`1` = yes, `0` = no) |
| `oldpeak` | ST depression induced by exercise relative to rest (`0.0`–`6.2`) |
| `slope` | Slope of the peak exercise ST segment (`0`: upsloping, `1`: flat, `2`: downsloping) |
| `ca` | Number of major vessels (0–4) colored by fluoroscopy |
| `thal` | Thalassemia status (`0`–`3`) |
| `target` | Diagnosis of heart disease (`0` or `1`, target) |

**Quirks noticed while loading**
- Raw CSV rows are ordered by `chol` across substantial segments; type inference requires contiguous 0/1-based step-1 indices before labeling an unnamed integer column as `id_like`, avoiding false ID classification on `chol`.
- Categorical medical codes (`cp`, `restecg`, `slope`, `thal`) are encoded as small integers (`0–3`) and configured via `forced_types: categorical_nominal`.
- Contains 1 exact duplicate row (`age=38, sex=1, cp=2, trestbps=138, chol=175, ...`), which is removed during deduplication (303 → 302 rows).
- `oldpeak` is zero-inflated (32.8% zeros) and right-skewed (`skew = +1.27`).

---

## 4. Student Performance — Math course

| Field | Value |
| :--- | :--- |
| Source | UCI Machine Learning Repository, dataset 320 — <https://archive.ics.uci.edu/dataset/320/student+performance> |
| Citation | P. Cortez and A. Silva (2008), *Using Data Mining to Predict Secondary School Student Performance*. |
| License | Creative Commons Attribution 4.0 International (CC BY 4.0) |
| File used | `student-mat.csv` from `student+performance.zip` → `student.zip` (the UCI page's "649 instances" refers to the Portuguese file `student-por.csv`, which is **not** used) |
| Downloaded | 2026-11-09 |
| SHA-256 | `e47f9ee225e1ee6e69b7564e6dac7123e80b8486677fe111f351964cef5dec80` |
| Shape | 395 rows × 33 columns, `;`-delimited, no missing values, no duplicate rows |
| Target | `G3` — final grade, 0–20 |
| Config | [`configs/datasets/student_performance.yaml`](../configs/datasets/student_performance.yaml) |

**Columns** (from the source's `student.txt`):

| Column | Description |
| :--- | :--- |
| `school` | Student's school: GP (Gabriel Pereira) or MS (Mousinho da Silveira) |
| `sex` | F or M |
| `age` | Age in years, 15–22 |
| `address` | Home address type: U (urban) or R (rural) |
| `famsize` | Family size: LE3 (≤ 3) or GT3 (> 3) |
| `Pstatus` | Parents living together (T) or apart (A) |
| `Medu`, `Fedu` | Mother's / father's education, 0 (none) to 4 (higher education) |
| `Mjob`, `Fjob` | Mother's / father's job: teacher, health, services, at_home, other |
| `reason` | Reason for choosing the school: home, reputation, course, other |
| `guardian` | Student's guardian: mother, father, other |
| `traveltime` | Home-to-school travel time, 1 (< 15 min) to 4 (> 1 hour) |
| `studytime` | Weekly study time, 1 (< 2 h) to 4 (> 10 h) |
| `failures` | Number of past class failures (n if 1 ≤ n < 3, else 4) |
| `schoolsup`, `famsup`, `paid` | Extra school support / family support / extra paid classes (yes/no) |
| `activities`, `nursery`, `higher` | Extra-curricular activities / attended nursery / wants higher education (yes/no) |
| `internet`, `romantic` | Internet at home / in a romantic relationship (yes/no) |
| `famrel`, `freetime`, `goout` | Family relationship quality, free time, going out with friends (1 very low – 5 very high) |
| `Dalc`, `Walc` | Workday / weekend alcohol consumption (1 very low – 5 very high) |
| `health` | Current health status (1 very bad – 5 very good) |
| `absences` | Number of school absences, 0–93 |
| `G1`, `G2` | First- and second-period grades, 0–20 |
| `G3` | Final grade, 0–20 (target) |

**Quirks noticed while loading**
- `G1` and `G2` are written as quoted strings (`"5"`) while `G3` is not; the pipeline's string-first loading and type inference handle this.
- 38 students have `G3 = 0` while most have non-zero `G1`/`G2`; these zeros probably mark students who dropped out or missed the final exam, not a real grade of zero. Kept as-is and flagged for the manual insights.
- `G1` and `G2` are earlier grades of the same course, so they almost determine `G3` (Spearman rho about 0.96 for `G2`). Any later "what predicts the final grade" finding should be reported with and without them.
- The ordinal 1–5 / 0–4 scales are stored as integers and treated as `numeric` in `truth_types` (same convention as `ca` in the heart-disease config).
- Small dataset (395 rows): some levels (e.g. `higher = no`, 20 rows) are too small for stable group comparisons.

---

## 5. Bank Marketing — `bank-additional-full`

| Field | Value |
| :--- | :--- |
| Source | UCI Machine Learning Repository, dataset 222 — <https://archive.ics.uci.edu/dataset/222/bank+marketing> |
| Citation | S. Moro, P. Cortez and P. Rita (2014), *A Data-Driven Approach to Predict the Success of Bank Telemarketing*, Decision Support Systems. |
| License | Creative Commons Attribution 4.0 International (CC BY 4.0) |
| File used | `bank-additional/bank-additional-full.csv` from `bank+marketing.zip` → `bank-additional.zip` (the UCI page's "45,211 instances" refers to the older `bank-full.csv`, which is **not** used) |
| Downloaded | 2026-11-09 |
| SHA-256 | `74adfc578bf77a7ff4bb1ba4a9f8709d9e3c6907342959c2c8416847e0afb4d8` |
| Shape | 41,188 rows × 21 columns, `;`-delimited, ordered by date (May 2008 – Nov 2010) |
| Target | `y` — did the client subscribe a term deposit (no 36,548 / yes 4,640) |
| Config | [`configs/datasets/bank_marketing.yaml`](../configs/datasets/bank_marketing.yaml) |

**Columns** (from the source's `bank-additional-names.txt`):

| Column | Description |
| :--- | :--- |
| `age` | Client age |
| `job` | Type of job (12 levels incl. `unknown`) |
| `marital` | Marital status: divorced (incl. widowed), married, single, unknown |
| `education` | Education level (8 levels incl. `unknown`) |
| `default` | Has credit in default? no / yes / unknown |
| `housing` | Has a housing loan? no / yes / unknown |
| `loan` | Has a personal loan? no / yes / unknown |
| `contact` | Contact type: cellular or telephone |
| `month`, `day_of_week` | Month and weekday of the last contact |
| `duration` | Last contact duration in seconds (known only after the call — see quirks) |
| `campaign` | Contacts during this campaign for this client (includes the last one) |
| `pdays` | Days since the client was last contacted in a previous campaign (999 = never contacted) |
| `previous` | Contacts before this campaign for this client |
| `poutcome` | Outcome of the previous campaign: failure, nonexistent, success |
| `emp.var.rate` | Employment variation rate (quarterly indicator) |
| `cons.price.idx` | Consumer price index (monthly) |
| `cons.conf.idx` | Consumer confidence index (monthly) |
| `euribor3m` | Euribor 3-month rate (daily) |
| `nr.employed` | Number of employees (quarterly indicator) |
| `y` | Subscribed a term deposit? yes / no (target) |

**Quirks noticed while loading**
- Missing values are coded as the text `unknown` in six columns: `default` 8,597, `education` 1,731, `housing` 990, `loan` 990, `job` 330, `marital` 80. The config sets `treat_unknown_as_missing: true` (plan Section 8 decision).
- `pdays = 999` means "never contacted before" for 39,673 rows (96.32%). It is a sentinel, not a missing value, and is left unchanged; it makes `pdays` look extremely left-skewed and ties it to `poutcome = nonexistent`.
- `duration` is only known after the call ends, and `duration = 0` always means `y = no` (4 rows). The source says it should be dropped for realistic prediction; it is kept for EDA and flagged as leakage in the manual insights.
- 12 exact duplicate rows.
- The five economic indicators move together (`emp.var.rate`, `euribor3m`, `nr.employed` have Pearson r of 0.9 or more), so they carry largely the same information.
- Target is imbalanced: `yes` is 11.27% of rows.

---

## 6. Messy Synthetic Benchmark

| Field | Value |
| :--- | :--- |
| Source | Generated by `src/ads/synthetic/` (`ads make-messy --seed 42`): a clean 2,000-row base with planted relationships, then 18 types of injected defects |
| Answer key | `data/synthetic/messy_manifest.json`, `messy_clean_truth.csv`, `messy_to_truth_index.json` |
| Target | `churned` |
| Why | Real datasets don't list their own problems; this one does, so issue detection and cleaning quality can be scored objectively (plan Section 12–13). |
