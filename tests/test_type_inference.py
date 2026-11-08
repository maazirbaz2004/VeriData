"""Unit tests for semantic column type inference (Section 7.2, Section 16)."""

from __future__ import annotations

import unittest

import pandas as pd

from ads.config import load_config
from ads.schemas import SemanticType
from ads.type_inference import infer_column_types, infer_column_types_detailed


class TestTypeInference(unittest.TestCase):
    def test_constant_and_empty_columns(self) -> None:
        df = pd.DataFrame(
            {
                "all_empty": ["", " ", "N/A", "?", "null"],
                "single_val": ["A", "A", " A ", "N/A", ""],
            }
        )
        inferred = infer_column_types(df)
        self.assertEqual(inferred["all_empty"][0], SemanticType.CONSTANT)
        self.assertIn("all missing", inferred["all_empty"][1])
        self.assertEqual(inferred["single_val"][0], SemanticType.CONSTANT)
        self.assertIn("1 unique", inferred["single_val"][1])

    def test_numeric_continuous_and_adversarial_formatting(self) -> None:
        # 20 rows: currency, commas, parentheses negatives, scientific notation, percentages, plus 1 unparseable (<5%)
        vals = [
            "$1,234.50",
            "(1,234.5)",
            "$ 12",
            "1e3",
            "12%",
            "45.67",
            "89.01",
            "102.3",
            "550.25",
            "$9,999.99",
            "0.125",
            "-42.8",
            "300.1",
            "412.9",
            "77.7",
            "64.2",
            "19.8",
            "811.4",
            "205.6",
            "twelve",  # 1/20 = 5% unparseable -> 95% valid
        ]
        df = pd.DataFrame(
            {
                "formatted_amount": vals,
                "unique_floats": [f"{i + 0.1234:.4f}" for i in range(20)],
            }
        )
        detailed = infer_column_types_detailed(df)
        self.assertEqual(
            detailed["formatted_amount"].semantic_type, SemanticType.NUMERIC_CONTINUOUS
        )
        self.assertTrue(detailed["formatted_amount"].looks_numeric_but_object)
        self.assertTrue(detailed["formatted_amount"].mixed_types)
        self.assertEqual(detailed["formatted_amount"].n_unparseable_numeric, 1)

        self.assertEqual(
            detailed["unique_floats"].semantic_type, SemanticType.NUMERIC_CONTINUOUS
        )
        self.assertFalse(detailed["unique_floats"].mixed_types)

    def test_non_ascii_digits_do_not_crash(self) -> None:
        # Arabic-Indic digits '١٢' should not crash and should not be treated as standard ASCII floats
        df = pd.DataFrame({"arabic_digits": ["١٢", "٣٤", "٥٦", "٧٨", "٩٠"] * 4})
        inferred = infer_column_types(df)
        self.assertIn(
            inferred["arabic_digits"][0],
            {SemanticType.CATEGORICAL_NOMINAL, SemanticType.UNKNOWN},
        )

    def test_numeric_discrete_and_years(self) -> None:
        df = pd.DataFrame(
            {
                "satisfaction": ["1", "2", "3", "4", "5"] * 6,
                "year": ["2019", "2020", "2021", "2022", "2023"] * 6,
            }
        )
        inferred = infer_column_types(df)
        self.assertEqual(inferred["satisfaction"][0], SemanticType.NUMERIC_DISCRETE)
        self.assertEqual(inferred["year"][0], SemanticType.NUMERIC_DISCRETE)

    def test_binary_encodings(self) -> None:
        df = pd.DataFrame(
            {
                "bin_int": ["0", "1", "1", "0", "N/A"] * 4,
                "bin_float": ["0.0", "1.0", "0.0", "1.0", ""] * 4,
                "bin_str": ["Yes", "No", "yes", "NO", " "] * 4,
                "bin_mix": ["Yes", "No", "yes", "Y", "1", "0", "No", "Yes", "0", "1"] * 2,
            }
        )
        inferred = infer_column_types(df)
        self.assertEqual(inferred["bin_int"][0], SemanticType.BINARY)
        self.assertEqual(inferred["bin_float"][0], SemanticType.BINARY)
        self.assertEqual(inferred["bin_str"][0], SemanticType.BINARY)
        self.assertEqual(inferred["bin_mix"][0], SemanticType.BINARY)

    def test_id_like_and_zip_codes(self) -> None:
        n = 60
        df = pd.DataFrame(
            {
                "customer_id": [f"C{i:05d}" for i in range(n)],
                "row_id": [str(i) for i in range(1, n + 1)],
                "zip_code": ["90210", "10001", "60601", "02138", "30301"] * 12,
                "zero_padded": [f"{i:05d}" for i in range(1, 11)] * 6,
            }
        )
        inferred = infer_column_types(df)
        self.assertEqual(inferred["customer_id"][0], SemanticType.ID_LIKE)
        self.assertEqual(inferred["row_id"][0], SemanticType.ID_LIKE)
        # ZIP codes and zero-padded codes must NEVER be numeric_continuous
        self.assertEqual(inferred["zip_code"][0], SemanticType.CATEGORICAL_NOMINAL)
        self.assertEqual(inferred["zero_padded"][0], SemanticType.CATEGORICAL_NOMINAL)

    def test_datetime_and_ambiguity_warning(self) -> None:
        df = pd.DataFrame(
            {
                "iso_date": [f"2023-05-{d:02d}" for d in range(1, 21)],
                "mixed_date": (
                    ["2023-01-15", "15/02/2023", "Mar 20, 2023", "2023-04-10"] * 5
                ),
                "ambiguous_slash": ["01/02/2022", "03/04/2022", "05/06/2022", "07/08/2022"] * 5,
            }
        )
        detailed = infer_column_types_detailed(df)
        self.assertEqual(detailed["iso_date"].semantic_type, SemanticType.DATETIME)
        self.assertIsNone(detailed["iso_date"].ambiguous_date_warning)

        self.assertEqual(detailed["mixed_date"].semantic_type, SemanticType.DATETIME)

        self.assertEqual(detailed["ambiguous_slash"].semantic_type, SemanticType.DATETIME)
        self.assertIsNotNone(detailed["ambiguous_slash"].ambiguous_date_warning)
        self.assertIn("ambiguous day/month order", detailed["ambiguous_slash"].reason)

    def test_free_text_and_categorical_and_ordinal(self) -> None:
        notes = [
            f"Customer called support regarding billing issue number {i} and requested a full refund on their account"
            for i in range(20)
        ]
        df = pd.DataFrame(
            {
                "notes": notes,
                "region": ["North", "South", "East", "West"] * 5,
                "membership": ["Basic", "Silver", "Gold", "Basic"] * 5,
            }
        )
        inferred = infer_column_types(df)
        self.assertEqual(inferred["notes"][0], SemanticType.FREE_TEXT)
        self.assertEqual(inferred["region"][0], SemanticType.CATEGORICAL_NOMINAL)
        self.assertEqual(inferred["membership"][0], SemanticType.CATEGORICAL_ORDINAL)

    def test_forced_types_override(self) -> None:
        df = pd.DataFrame({"SeniorCitizen": ["0", "1", "0", "1"] * 5})
        cfg = load_config(
            cli_overrides={
                "forced_types": {"SeniorCitizen": SemanticType.CATEGORICAL_NOMINAL}
            }
        )
        detailed = infer_column_types_detailed(df, config=cfg)
        self.assertEqual(
            detailed["SeniorCitizen"].semantic_type, SemanticType.CATEGORICAL_NOMINAL
        )
        self.assertTrue(detailed["SeniorCitizen"].override_applied)
        self.assertIn("config override", detailed["SeniorCitizen"].reason)


if __name__ == "__main__":
    unittest.main()

