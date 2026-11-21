# Phase 2 — Natural-Language Hypothesis Parser Evaluation

- **Gold set:** `tests\gold\nl_hypotheses.jsonl` (`44` labeled sentences, `38` positive `ok` pairs)
- **Mode:** Offline deterministic fuzzy fallback (`llm=None`)
- **Status accuracy:** `97.7%` (43/44)
- **Column identification accuracy (on `ok`):** `97.4%` (37/38)
- **Relationship type accuracy (on `ok`):** `97.4%` (37/38)
- **Direction accuracy (on `ok`):** `94.7%` (36/38)

| ID | Dataset | Sentence | Expected | Got | Cols | Rel | Dir |
| :--- | :--- | :--- | :--- | :--- | :---: | :---: | :---: |
| `nl01` | `insurance` | Do smokers have higher charges? | `ok` | `ok` | PASS | PASS | PASS |
| `nl02` | `insurance` | Is age positively correlated with charges? | `ok` | `ok` | PASS | PASS | PASS |
| `nl03` | `insurance` | Is bmi associated with charges? | `ok` | `ok` | PASS | PASS | PASS |
| `nl04` | `insurance` | Do charges differ across region? | `ok` | `ok` | PASS | PASS | PASS |
| `nl05` | `insurance` | Is sex associated with smoker status? | `ok` | `ok` | PASS | PASS | PASS |
| `nl06` | `insurance` | Do people in the southeast have different bmi? | `ok` | `ok` | PASS | PASS | PASS |
| `nl07` | `insurance` | Does smoking cause higher charges? | `unsupported` | `unsupported` | - | - | - |
| `nl08` | `insurance` | Predict charges using a machine learning model. | `unsupported` | `unsupported` | - | - | - |
| `nl09` | `insurance` | How does credit score relate to salary? | `no_columns_found` | `no_columns_found` | - | - | - |
| `nl10` | `insurance` | Is age related to bmi? | `ok` | `ok` | PASS | PASS | PASS |
| `nl11` | `insurance` | Do male beneficiaries have higher bmi? | `ok` | `ok` | PASS | PASS | PASS |
| `nl12` | `insurance` | Do charges vary by number of children? | `ok` | `ok` | PASS | PASS | PASS |
| `nl13` | `telco_churn` | Is Contract associated with Churn? | `ok` | `ok` | PASS | PASS | PASS |
| `nl14` | `telco_churn` | Do churners have lower tenure? | `ok` | `no_columns_found` | FAIL | FAIL | FAIL |
| `nl15` | `telco_churn` | Is tenure positively associated with TotalCharges? | `ok` | `ok` | PASS | PASS | PASS |
| `nl16` | `telco_churn` | Do customers with higher MonthlyCharges churn more? | `ok` | `ok` | PASS | PASS | PASS |
| `nl17` | `telco_churn` | Is PaymentMethod related to Churn? | `ok` | `ok` | PASS | PASS | PASS |
| `nl18` | `telco_churn` | Is InternetService associated with MonthlyCharges? | `ok` | `ok` | PASS | PASS | PASS |
| `nl19` | `telco_churn` | Is PaperlessBilling associated with Churn? | `ok` | `ok` | PASS | PASS | PASS |
| `nl20` | `telco_churn` | Is Partner associated with Dependents? | `ok` | `ok` | PASS | PASS | PASS |
| `nl21` | `telco_churn` | Does MonthlyCharges cause Churn? | `unsupported` | `unsupported` | - | - | - |
| `nl22` | `telco_churn` | Is SeniorCitizen related to Churn? | `ok` | `ok` | PASS | PASS | PASS |
| `nl23` | `telco_churn` | Test whether TechSupport is associated with OnlineSecurity. | `ok` | `ok` | PASS | PASS | PASS |
| `nl24` | `telco_churn` | Compare tenure between gender groups. | `ok` | `ok` | PASS | PASS | PASS |
| `nl25` | `heart_disease` | Is age associated with chol? | `ok` | `ok` | PASS | PASS | PASS |
| `nl26` | `heart_disease` | Do target groups differ in thalach? | `ok` | `ok` | PASS | PASS | PASS |
| `nl27` | `heart_disease` | Is cp associated with target? | `ok` | `ok` | PASS | PASS | PASS |
| `nl28` | `heart_disease` | Is oldpeak lower in target patients? | `ok` | `ok` | PASS | PASS | PASS |
| `nl29` | `heart_disease` | Is exang associated with target? | `ok` | `ok` | PASS | PASS | PASS |
| `nl30` | `heart_disease` | Is age negatively correlated with thalach? | `ok` | `ok` | PASS | PASS | PASS |
| `nl31` | `heart_disease` | Is trestbps correlated with chol? | `ok` | `ok` | PASS | PASS | PASS |
| `nl32` | `student_performance` | Is G2 positively correlated with G3? | `ok` | `ok` | PASS | PASS | PASS |
| `nl33` | `student_performance` | Is G1 associated with G3? | `ok` | `ok` | PASS | PASS | PASS |
| `nl34` | `student_performance` | Do absences relate to G3? | `ok` | `ok` | PASS | PASS | PASS |
| `nl35` | `student_performance` | Is higher associated with G3? | `ok` | `ok` | PASS | PASS | FAIL |
| `nl36` | `student_performance` | Is internet associated with G3? | `ok` | `ok` | PASS | PASS | PASS |
| `nl37` | `bank_marketing` | Is duration higher for y subscribers? | `ok` | `ok` | PASS | PASS | PASS |
| `nl38` | `bank_marketing` | Is poutcome associated with y? | `ok` | `ok` | PASS | PASS | PASS |
| `nl39` | `bank_marketing` | Is job associated with education? | `ok` | `ok` | PASS | PASS | PASS |
| `nl40` | `bank_marketing` | Forecast y over time using a time series model. | `unsupported` | `unsupported` | - | - | - |
| `nl41` | `messy_synthetic` | Does signup_date relate to churned? | `unsupported` | `unsupported` | - | - | - |
| `nl42` | `messy_synthetic` | Is income associated with monthly_spend? | `ok` | `ok` | PASS | PASS | PASS |
| `nl43` | `messy_synthetic` | Do churned customers have different tenure_months? | `ok` | `ok` | PASS | PASS | PASS |
| `nl44` | `messy_synthetic` | Is region associated with membership? | `ok` | `ok` | PASS | PASS | PASS |
