"""Unit tests for Cleaning Engine Steps 1-8 (Milestone M4, Sections 9.1-9.8)."""

from __future__ import annotations

import unittest

import numpy as np
import pandas as pd

from ads.cleaning import (
    CleaningLog,
    step1_normalize_column_names,
    step2_clean_whitespace_and_unicode,
    step3_normalize_missing_tokens,
    step4_standardize_categories,
    step5_convert_types,
    step6_apply_validity_rules,
    step7_handle_duplicates,
    step8_structural_drops,
)
from ads.config import load_config
from ads.schemas import DroppedColumnRecord, SemanticType


class TestCleaningSteps1To8(unittest.TestCase):
    def test_step1_and_step2_whitespace_and_unicode(self) -> None:
        df = pd.DataFrame(
            {
                " membership ": ["  Gold\u00a0", "Silver\u200b", "Basic  "],
                "region  name": ["North  Area", "South\tBay", "East Coast"],
            }
        )
        log = CleaningLog()
        cfg = load_config()
        df1, name_map = step1_normalize_column_names(df, log, cfg)
        self.assertEqual(list(df1.columns), ["membership", "region name"])
        self.assertEqual(name_map[" membership "], "membership")

        df2 = step2_clean_whitespace_and_unicode(df1, log)
        self.assertEqual(df2["membership"].tolist(), ["Gold", "Silver", "Basic"])
        self.assertEqual(
            df2["region name"].tolist(), ["North Area", "South Bay", "East Coast"]
        )
        self.assertTrue(any(e.step == "clean_whitespace_unicode" for e in log.entries))

    def test_step3_missing_tokens(self) -> None:
        df = pd.DataFrame(
            {
                "income": ["50000", "N/A", "?", "null", "-", ""],
                "region": ["North", "Unknown", "South", "East", "West", "North"],
            }
        )
        log = CleaningLog()
        cfg = load_config(
            cli_overrides={"profiling": {"treat_unknown_as_missing": True}}
        )
        df3 = step3_normalize_missing_tokens(df, log, cfg)
        self.assertEqual(int(df3["income"].isna().sum()), 5)
        self.assertEqual(int(df3["region"].isna().sum()), 1)
        # 4 non-empty placeholder tokens in 6 rows (>10%) -> severity == 'warning'
        inc_logs = [e for e in log.entries if e.column == "income"]
        self.assertEqual(len(inc_logs), 1)
        self.assertEqual(inc_logs[0].severity, "warning")

    def test_step4_category_standardization_and_fuzzy_flagging(self) -> None:
        df = pd.DataFrame(
            {
                "gender": [
                    "Male",
                    "Male",
                    "Male",
                    "male",
                    "MALE",
                    "Female",
                    "Female",
                    "female",
                    "M",
                    "F",
                ],
                "churned": ["Yes", "No", "No", "Yes", "yes", "Y", "1", "0", "No", "Yes"],
            }
        )
        sem = {
            "gender": SemanticType.BINARY,
            "churned": SemanticType.BINARY,
        }
        log = CleaningLog()
        cfg = load_config()
        df4 = step4_standardize_categories(df, sem, log, cfg)

        # Case-only variants ('male', 'MALE', 'female') must merge into 'Male'/'Female',
        # while 'M' and 'F' must stay untouched and be flagged!
        self.assertEqual(
            df4["gender"].tolist(),
            ["Male", "Male", "Male", "Male", "Male", "Female", "Female", "Female", "M", "F"],
        )
        self.assertTrue(
            any(
                e.column == "gender" and e.action == "flagged_fuzzy_variants"
                for e in log.entries
            )
        )

        # Mixed boolean tokens in churned ('yes', 'Y', '1', '0') must standardize into 'Yes'/'No'
        self.assertEqual(set(df4["churned"].unique()), {"Yes", "No"})

    def test_step5_type_conversion_and_coerced_to_nan(self) -> None:
        df = pd.DataFrame(
            {
                "income": ["$1,200.50", "(300.25)", "1.5e3", "12%"],
                "tenure": ["12", "24", "twelve", "36"],
                "signup_date": ["2023-01-15", "15/02/2023", "Mar 20, 2023", "not_a_date"],
            }
        )
        sem = {
            "income": SemanticType.NUMERIC_CONTINUOUS,
            "tenure": SemanticType.NUMERIC_DISCRETE,
            "signup_date": SemanticType.DATETIME,
        }
        log = CleaningLog()
        cfg = load_config()
        df5 = step5_convert_types(df, sem, log, cfg)

        self.assertEqual(str(df5["income"].dtype), "float64")
        self.assertAlmostEqual(df5.loc[0, "income"], 1200.50)
        self.assertAlmostEqual(df5.loc[1, "income"], -300.25)
        # Percentage symbol stripped without dividing by 100 (Section 9.5 DECISION)
        self.assertAlmostEqual(df5.loc[3, "income"], 12.0)

        # tenure -> Int64 with 'twelve' coerced to <NA>
        self.assertEqual(str(df5["tenure"].dtype), "Int64")
        self.assertTrue(pd.isna(df5.loc[2, "tenure"]))
        self.assertEqual(int(df5.loc[0, "tenure"]), 12)

        # signup_date -> ISO YYYY-MM-DD with 'not_a_date' coerced to NaN
        self.assertEqual(df5.loc[0, "signup_date"], "2023-01-15")
        self.assertEqual(df5.loc[1, "signup_date"], "2023-02-15")
        self.assertEqual(df5.loc[2, "signup_date"], "2023-03-20")
        self.assertTrue(pd.isna(df5.loc[3, "signup_date"]))

        coerced_entries = [e for e in log.entries if e.action == "coerced_to_NaN"]
        self.assertEqual(len(coerced_entries), 2)

    def test_step6_validity_rules_and_sanity_checks(self) -> None:
        df = pd.DataFrame(
            {
                "age": pd.Series([25, -5, 140, 40], dtype="Int64"),
                "charges": pd.Series([100.0, -20.0, 300.0, 400.0], dtype="float64"),
            }
        )
        sem = {
            "age": SemanticType.NUMERIC_DISCRETE,
            "charges": SemanticType.NUMERIC_CONTINUOUS,
        }
        log = CleaningLog()
        cfg = load_config(
            cli_overrides={"validity_rules": {"age": {"min": 0, "max": 120}}}
        )
        df6 = step6_apply_validity_rules(df, sem, log, cfg)

        # age violations (-5, 140) set to <NA>
        self.assertTrue(pd.isna(df6.loc[1, "age"]))
        self.assertTrue(pd.isna(df6.loc[2, "age"]))
        self.assertEqual(int(df6.loc[0, "age"]), 25)

        # charges has no configured rule, so negative value (-20.0) is flagged only, not mutated
        self.assertEqual(df6.loc[1, "charges"], -20.0)
        self.assertTrue(
            any(
                e.column == "charges" and e.action == "sanity_check_flag"
                for e in log.entries
            )
        )

    def test_step7_duplicates_auto_policy_and_step8_structural_drops(self) -> None:
        # 1. Small 2-column table with no ID -> auto policy keeps duplicates with warning
        df_small = pd.DataFrame({"a": [1, 1, 2], "b": [10, 10, 20]})
        sem_small = {
            "a": SemanticType.NUMERIC_DISCRETE,
            "b": SemanticType.NUMERIC_DISCRETE,
        }
        log_small = CleaningLog()
        cfg = load_config()
        res_small = step7_handle_duplicates(df_small, sem_small, log_small, cfg)
        self.assertEqual(len(res_small), 3)
        self.assertTrue(
            any(e.action == "kept_duplicates_warning" for e in log_small.entries)
        )

        # 2. Table with ID column, Unnamed: 0, duplicate row, empty row, and empty column 'unused'
        df_full = pd.DataFrame(
            {
                "Unnamed: 0": ["0", "1", "2", "3"],
                "customer_id": ["C1", "C2", "C2", np.nan],
                "val": [10.0, 20.0, 20.0, np.nan],
                "unused": [np.nan, np.nan, np.nan, np.nan],
            }
        )
        sem_full = {
            "Unnamed: 0": SemanticType.ID_LIKE,
            "customer_id": SemanticType.ID_LIKE,
            "val": SemanticType.NUMERIC_CONTINUOUS,
            "unused": SemanticType.CONSTANT,
        }
        log_full = CleaningLog()
        df7 = step7_handle_duplicates(df_full, sem_full, log_full, cfg)
        # Duplicate C2 row removed (3 rows left: C1, C2, and the empty row)
        self.assertEqual(len(df7), 3)

        dropped_cols: list[DroppedColumnRecord] = []
        df8, high_miss = step8_structural_drops(
            df7, sem_full, dropped_cols, log_full, cfg
        )
        # Empty row removed -> 2 rows left; 'Unnamed: 0' and 'unused' columns dropped -> 2 cols left
        self.assertEqual(len(df8), 2)
        self.assertEqual(list(df8.columns), ["customer_id", "val"])
        self.assertEqual(high_miss, [])


if __name__ == "__main__":
    unittest.main()

