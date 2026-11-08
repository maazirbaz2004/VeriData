# Raw Datasets Directory

Place untouched original CSV datasets in subdirectories under `data/raw/<dataset_name>/`:

1. `data/raw/insurance/insurance.csv` — Medical Cost Personal Datasets
2. `data/raw/telco_churn/WA_Fn-UseC_-Telco-Customer-Churn.csv` — Telco Customer Churn
3. `data/raw/heart_disease/heart.csv` — Heart Disease UCI/Kaggle
4. `data/raw/student_performance/student-mat.csv` — Student Performance (UCI)
5. `data/raw/bank_marketing/bank-additional-full.csv` — Bank Marketing (UCI)

> **Important:** Files in `data/raw/` are read-only and never mutated by the pipeline. Exact download URLs, dates, licenses, and SHA-256 checksums are recorded in `docs/datasets.md`.

