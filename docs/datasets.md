# Dataset Cards (`docs/datasets.md`)

One card per dataset used in Phase 1 (plan Section 5.3). Raw files live in `data/raw/<name>/`, are never modified, and are git-ignored; download steps are in [`scripts/download_datasets.md`](../scripts/download_datasets.md).

| # | Dataset | File | Rows × cols | Target | Owner | SHA-256 recorded |
| :-- | :--- | :--- | :--- | :--- | :--- | :---: |
| 1 | Medical Cost / Insurance | `insurance/insurance.csv` | ~1,338 × 7 | `charges` (numeric) | Partner 1 (Maaz) | ☐ |
| 2 | Telco Customer Churn | `telco_churn/WA_Fn-UseC_-Telco-Customer-Churn.csv` | ~7,043 × 21 | `Churn` (binary) | Partner 1 (Maaz) | ☐ |
| 3 | Heart Disease | `heart_disease/heart.csv` | ~300–1,000 × 14 | `target` (binary) | Partner 1 (Maaz) | ☐ |
| 4 | Student Performance (Math) | `student_performance/student-mat.csv` | 395 × 33 | `G3` (numeric) | Partner 2 (Ghazanfar) | ✔ |
| 5 | Bank Marketing (additional, full) | `bank_marketing/bank-additional-full.csv` | 41,188 × 21 | `y` (binary) | Partner 2 (Ghazanfar) | ✔ |
| 6 | Messy Synthetic | `data/synthetic/messy_dataset.csv` (generated) | 2,000 base rows + injected problems | `churned` (binary) | Partner 1 generator / Partner 2 analysis | generated |

> **LLM contamination note (plan Section 20, risk 7):** datasets 1–5 are public and an LLM may have seen them during training. The messy synthetic dataset is the contamination-free test for the LLM comparison.

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

## 1. Medical Cost / Insurance *(Partner 1 — to be completed by Maaz)*

| Field | Value |
| :--- | :--- |
| Source | Kaggle `mirichoi0218/insurance` (mirror used in `scripts/download_datasets.md`: `stedy/Machine-Learning-with-R-datasets`) |
| License | *to fill: check the Kaggle page* |
| Downloaded / SHA-256 | *to fill from `outputs/insurance/profile.json` after the first run* |
| Target | `charges` |
| Columns | `age`, `sex`, `bmi`, `children` (number of dependants), `smoker`, `region` (4 US regions), `charges` (medical costs billed) |
| Quirks | *to fill* |

## 2. Telco Customer Churn *(Partner 1 — to be completed by Maaz)*

| Field | Value |
| :--- | :--- |
| Source | IBM sample data, Kaggle `blastchar/telco-customer-churn` |
| License | *to fill* |
| Downloaded / SHA-256 | *to fill* |
| Target | `Churn` |
| Columns | `customerID`; demographics (`gender`, `SeniorCitizen`, `Partner`, `Dependents`); `tenure`; services (`PhoneService`, `MultipleLines`, `InternetService`, `OnlineSecurity`, `OnlineBackup`, `DeviceProtection`, `TechSupport`, `StreamingTV`, `StreamingMovies`); account (`Contract`, `PaperlessBilling`, `PaymentMethod`, `MonthlyCharges`, `TotalCharges`); `Churn` |
| Quirks | `TotalCharges` is stored as text with blank strings for new customers (plan acceptance criterion); `SeniorCitizen` is 0/1 but categorical. |

## 3. Heart Disease *(Partner 1 — to be completed by Maaz)*

| Field | Value |
| :--- | :--- |
| Source | UCI Heart Disease (Kaggle version) |
| License | *to fill* |
| Downloaded / SHA-256 | *to fill* |
| Target | `target` (disease yes/no) |
| Columns | `age`, `sex`, `cp` (chest pain type), `trestbps` (resting blood pressure), `chol`, `fbs` (fasting blood sugar > 120), `restecg`, `thalach` (max heart rate), `exang` (exercise angina), `oldpeak`, `slope`, `ca` (major vessels 0–3), `thal`, `target` |
| Quirks | Categorical codes stored as integers (`cp`, `restecg`, `slope`, `thal` forced to categorical in the config); `?` placeholders in some versions. |

## 6. Messy Synthetic Benchmark

| Field | Value |
| :--- | :--- |
| Source | Generated by `src/ads/synthetic/` (`ads make-messy --seed 42`): a clean 2,000-row base with planted relationships, then 18 types of injected defects |
| Answer key | `data/synthetic/messy_manifest.json`, `messy_clean_truth.csv`, `messy_to_truth_index.json` |
| Target | `churned` |
| Why | Real datasets don't list their own problems; this one does, so issue detection and cleaning quality can be scored objectively (plan Section 12–13). |
