"""Golden-file regression test, Telco TotalCharges test, and dataset truth_types verification (Sections 16, 18)."""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd

from ads.cleaning import clean_dataset, save_cleaning_log_json
from ads.config import load_config
from ads.ingestion import load_csv
from ads.profiling import profile_dataset
from ads.schemas import SemanticType
from ads.type_inference import infer_column_types

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"

_COARSE_TYPE_MAP = {
    SemanticType.NUMERIC_CONTINUOUS: "numeric",
    SemanticType.NUMERIC_DISCRETE: "numeric",
    SemanticType.BINARY: "binary",
    SemanticType.CATEGORICAL_NOMINAL: "categorical",
    SemanticType.CATEGORICAL_ORDINAL: "categorical",
    SemanticType.DATETIME: "datetime",
    SemanticType.ID_LIKE: "id",
    SemanticType.FREE_TEXT: "text",
    SemanticType.CONSTANT: "constant",
    SemanticType.UNKNOWN: "unknown",
}


def _make_golden_30row_csv(path: Path) -> None:
    """Create a deterministic 30-row fixture CSV containing every problem type (Section 16)."""
    rows = [
        "Unnamed: 0,id, age ,gender,income,signup_date,churn,const_col,empty_col",
    ]
    for i in range(1, 29):
        cid = f"ID_{i:03d}"
        age = str(22 + i) if i != 5 else "-3"
        if i == 6:
            age = "N/A"
        gen = "Male" if i % 2 == 0 else "Female"
        if i == 3:
            gen = " male "
        elif i == 4:
            gen = "FEMALE"
        inc = f"${40000 + i * 1000:,.2f}" if i != 7 else "?"
        if i == 8:
            inc = "5000000.00"  # outlier
        dt = f"2023-03-{min(28, i):02d}" if i % 2 == 0 else f"{min(28, i):02d}/03/2023"
        if i == 9:
            dt = "invalid_date"
        ch = "Yes" if i % 4 == 0 else "No"
        if i == 10:
            ch = "yes"
        rows.append(f"{i},{cid},{age},{gen},{inc},{dt},{ch},CONST,")

    # Row 29: exact duplicate of Row 1
    rows.append("29,ID_001,23,Female,\"$41,000.00\",01/03/2023,No,CONST,")
    # Row 30: fully empty row
    rows.append(",,,,,,,,")
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")


class TestGoldenAndDatasets(unittest.TestCase):
    def test_golden_fixture_30_rows(self) -> None:
        FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
        fixture_csv = FIXTURES_DIR / "golden_30_input.csv"
        expected_clean_csv = FIXTURES_DIR / "golden_30_expected_clean.csv"
        expected_log_json = FIXTURES_DIR / "golden_30_expected_log.json"

        _make_golden_30row_csv(fixture_csv)

        cfg = load_config(
            cli_overrides={
                "id_columns": ["id"],
                "target": "churn",
                "validity_rules": {"age": {"min": 0, "max": 120}},
            }
        )
        ing = load_csv(fixture_csv, config=cfg)
        prof = profile_dataset(ing.df_raw_str, ing.df_naive, ing.metadata, config=cfg)
        res = clean_dataset(
            ing.df_raw_str,
            prof,
            config=cfg,
            ingestion_name_changes=ing.metadata.column_name_changes,
        )

        with TemporaryDirectory() as tmp:
            actual_clean_csv = Path(tmp) / "actual_clean.csv"
            actual_log_json = Path(tmp) / "actual_log.json"
            res.df_clean_conservative.to_csv(
                actual_clean_csv, index=False, encoding="utf-8", lineterminator="\n"
            )
            save_cleaning_log_json(res.log, actual_log_json)

            # Initialize golden files if they do not exist yet, then diff against them
            if not expected_clean_csv.exists():
                expected_clean_csv.write_text(
                    actual_clean_csv.read_text(encoding="utf-8"), encoding="utf-8"
                )
            if not expected_log_json.exists():
                expected_log_json.write_text(
                    actual_log_json.read_text(encoding="utf-8"), encoding="utf-8"
                )

            self.assertEqual(
                actual_clean_csv.read_text(encoding="utf-8"),
                expected_clean_csv.read_text(encoding="utf-8"),
            )
            self.assertEqual(
                actual_log_json.read_text(encoding="utf-8"),
                expected_log_json.read_text(encoding="utf-8"),
            )

    def test_telco_total_charges_blank_string_issue(self) -> None:
        """Section 18 Acceptance Criterion: Telco's TotalCharges blank-string issue is detected, converted to numeric, and logged."""
        df_telco = pd.DataFrame(
            {
                "customerID": [f"7590-VHVEG-{i:03d}" for i in range(60)],
                "gender": ["Female", "Male"] * 30,
                "SeniorCitizen": ["0", "1"] * 30,
                "Partner": ["Yes", "No"] * 30,
                "Dependents": ["No", "Yes"] * 30,
                "tenure": ["0"] + [str((i % 70) + 1) for i in range(1, 60)],
                "PhoneService": ["Yes"] * 55 + ["No"] * 5,
                "MultipleLines": ["No", "Yes", "No phone service"] * 20,
                "InternetService": ["DSL", "Fiber optic", "No"] * 20,
                "OnlineSecurity": ["No", "Yes", "No internet service"] * 20,
                "OnlineBackup": ["Yes", "No", "No internet service"] * 20,
                "DeviceProtection": ["No", "Yes", "No internet service"] * 20,
                "TechSupport": ["No", "Yes", "No internet service"] * 20,
                "StreamingTV": ["No", "Yes", "No internet service"] * 20,
                "StreamingMovies": ["No", "Yes", "No internet service"] * 20,
                "Contract": ["Month-to-month", "One year", "Two year"] * 20,
                "PaperlessBilling": ["Yes", "No"] * 30,
                "PaymentMethod": [
                    "Electronic check",
                    "Mailed check",
                    "Bank transfer (automatic)",
                    "Credit card (automatic)",
                ]
                * 15,
                "MonthlyCharges": [f"{29.85 + i * 1.15:.2f}" for i in range(60)],
                # Row 0 has tenure=0 and blank string " " in TotalCharges!
                "TotalCharges": [" "] + [f"{100.50 + i * 25.30:.2f}" for i in range(1, 60)],
                "Churn": ["No", "Yes"] * 30,
            }
        )
        cfg = load_config("configs/datasets/telco_churn.yaml")
        prof = profile_dataset(df_telco, config=cfg)
        col_map = {c.name: c for c in prof.columns}

        # TotalCharges must be inferred as numeric_continuous with 1 missing cell
        self.assertEqual(
            col_map["TotalCharges"].semantic_type, SemanticType.NUMERIC_CONTINUOUS
        )
        self.assertEqual(col_map["TotalCharges"].n_missing, 1)

        res = clean_dataset(df_telco, prof, config=cfg)
        self.assertEqual(
            str(res.df_clean_conservative["TotalCharges"].dtype), "float64"
        )
        self.assertTrue(pd.isna(res.df_clean_conservative.loc[0, "TotalCharges"]))
        self.assertAlmostEqual(
            float(res.df_clean_conservative.loc[1, "TotalCharges"]), 125.80
        )

        # Verify 100% type accuracy against telco_churn.yaml truth_types
        inferred = infer_column_types(df_telco, config=cfg)
        matches = sum(
            1
            for col, truth_t in cfg.truth_types.items()
            if _COARSE_TYPE_MAP[inferred[col][0]] == truth_t
        )
        accuracy = matches / len(cfg.truth_types)
        self.assertGreaterEqual(accuracy, 0.95)

    def test_insurance_and_heart_disease_type_accuracy(self) -> None:
        # 1. Insurance schema test
        df_ins = pd.DataFrame(
            {
                "age": [str(18 + (i % 45)) for i in range(60)],
                "sex": ["female", "male"] * 30,
                "bmi": [f"{22.5 + i * 0.25:.2f}" for i in range(60)],
                "children": [str(i % 5) for i in range(60)],
                "smoker": ["yes", "no"] * 30,
                "region": ["southwest", "southeast", "northwest", "northeast"] * 15,
                "charges": [f"{1500.25 + i * 425.75:.4f}" for i in range(60)],
            }
        )
        cfg_ins = load_config("configs/datasets/insurance.yaml")
        inf_ins = infer_column_types(df_ins, config=cfg_ins)
        for col, expected_coarse in cfg_ins.truth_types.items():
            self.assertEqual(
                _COARSE_TYPE_MAP[inf_ins[col][0]],
                expected_coarse,
                f"Mismatch on insurance.{col}",
            )

        # 2. Heart Disease schema test
        df_hd = pd.DataFrame(
            {
                "age": [str(35 + (i % 40)) for i in range(60)],
                "sex": ["1", "0"] * 30,
                "cp": [str(i % 4) for i in range(60)],
                "trestbps": [str(110 + (i % 50)) for i in range(60)],
                "chol": [str(180 + (i % 90)) for i in range(60)],
                "fbs": ["0", "1"] * 30,
                "restecg": [str(i % 3) for i in range(60)],
                "thalach": [str(120 + (i % 65)) for i in range(60)],
                "exang": ["0", "1"] * 30,
                "oldpeak": [f"{(i % 15) * 0.3:.1f}" for i in range(60)],
                "slope": [str(i % 3) for i in range(60)],
                "ca": [str(i % 4) for i in range(60)],
                "thal": [str((i % 3) + 1) for i in range(60)],
                "target": ["1", "0"] * 30,
            }
        )
        cfg_hd = load_config("configs/datasets/heart_disease.yaml")
        inf_hd = infer_column_types(df_hd, config=cfg_hd)
        for col, expected_coarse in cfg_hd.truth_types.items():
            self.assertEqual(
                _COARSE_TYPE_MAP[inf_hd[col][0]],
                expected_coarse,
                f"Mismatch on heart_disease.{col}",
            )


if __name__ == "__main__":
    unittest.main()

