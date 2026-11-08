# Dataset Download Instructions

This guide provides instructions for downloading the 5 real datasets required for Phase 1.

You can either:
1. Run the automated Python downloader script: [`scripts/download_datasets.py`](./download_datasets.py)
2. Or download the files manually from the direct URLs or Kaggle links below into `data/raw/`.

---

## Method 1: Automated Script

Run the download script in your terminal (ensure you have an internet connection):

```bash
# Download Partner 1 datasets (Insurance, Telco Churn, Heart Disease)
python scripts/download_datasets.py --datasets partner1

# Download Partner 2 datasets (Student Performance, Bank Marketing)
python scripts/download_datasets.py --datasets partner2

# Download all datasets
python scripts/download_datasets.py --datasets all
```

---

## Method 2: Manual Download (Direct URLs & Destinations)

Place untouched CSV files into the exact destinations expected by `configs/datasets/*.yaml`:

### 1. Medical Cost / Insurance (Partner 1)
- **Destination:** `data/raw/insurance/insurance.csv`
- **Rows/Cols:** ~1,338 rows, 7 cols
- **Direct Link:** [GitHub Raw Mirror (insurance.csv)](https://raw.githubusercontent.com/stedy/Machine-Learning-with-R-datasets/master/insurance.csv)
- **Kaggle Link:** [Kaggle - Medical Cost Personal Datasets](https://www.kaggle.com/datasets/mirichoi0218/insurance)

### 2. Telco Customer Churn (Partner 1)
- **Destination:** `data/raw/telco_churn/WA_Fn-UseC_-Telco-Customer-Churn.csv`
- **Rows/Cols:** ~7,043 rows, 21 cols
- **Direct Link:** [IBM GitHub Mirror (Telco-Customer-Churn.csv)](https://raw.githubusercontent.com/IBM/telco-customer-churn-on-icp4d/master/data/Telco-Customer-Churn.csv) *(Save as `WA_Fn-UseC_-Telco-Customer-Churn.csv`)*
- **Kaggle Link:** [Kaggle - Telco Customer Churn](https://www.kaggle.com/datasets/blastchar/telco-customer-churn)

### 3. Heart Disease (Partner 1)
- **Destination:** `data/raw/heart_disease/heart.csv`
- **Rows/Cols:** ~303 rows, 14 cols
- **Direct Link:** [GitHub Raw Mirror (heart.csv)](https://raw.githubusercontent.com/sharmaroshan/Heart-UCI-Dataset/master/heart.csv)
- **Kaggle Link:** [Kaggle - Heart Disease Dataset](https://www.kaggle.com/datasets/johnsmith88/heart-disease-dataset)
- **UCI Link:** [UCI Machine Learning Repository - Heart Disease](https://archive.ics.uci.edu/dataset/45/heart+disease)

### 4. Student Performance (Partner 2)
- **Destination:** `data/raw/student_performance/student-mat.csv`
- **Rows/Cols:** ~395 rows, 33 cols (semicolon-delimited `;`)
- **Direct Link:** [GitHub Raw Mirror (student-mat.csv)](https://raw.githubusercontent.com/guipsamora/pandas_exercises/master/04_Apply/Students_Alcohol_Consumption/student-mat.csv)
- **UCI Link:** [UCI Student Performance Zip](https://archive.ics.uci.edu/static/public/320/student+performance.zip)

### 5. Bank Marketing (Partner 2)
- **Destination:** `data/raw/bank_marketing/bank-additional-full.csv`
- **Rows/Cols:** ~41,188 rows, 21 cols (semicolon-delimited `;`)
- **UCI Link:** [UCI Bank Marketing Zip](https://archive.ics.uci.edu/static/public/222/bank+marketing.zip)
  *(Extract `bank-additional/bank-additional-full.csv` into `data/raw/bank_marketing/`)*

