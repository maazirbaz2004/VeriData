"""Unit tests for Milestone M5: Outliers, Imputation, Invariants, Idempotence, and Messy Benchmark."""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np
import pandas as pd

from ads.cleaning import (
    CleaningInvariantError,
    CleaningLog,
    clean_dataset,
    step11_validate_invariants,
)
from ads.config import load_config
from ads.ingestion import load_csv
from ads.profiling import profile_dataset
from ads.schemas import SemanticType
from ads.synthetic.base_generator import make_clean_base
from ads.synthetic.messy_injector import inject_problems


class TestOutliersAndFullCleaning(unittest.TestCase):
    def test_outlier_flag_cap_and_remove_modes(self) -> None:
        # 25 rows with 1 extreme outlier at index 0 (1 / 25 = 4% <= 5% removal limit)
        vals = ["5000.0"] + [str(100.0 + i) for i in range(24)]
        df = pd.DataFrame(
            {
                "id": [f"ID_{i:03d}" for i in range(25)],
                "amount": vals,
            }
        )

        # 1. Default mode: flag
        cfg_flag = load_config()
        prof = profile_dataset(df, config=cfg_flag)
        res_flag = clean_dataset(df, prof, config=cfg_flag)
        self.assertEqual(res_flag.outlier_report["amount"].n_flagged, 1)
        self.assertEqual(res_flag.df_clean_conservative.loc[0, "amount"], 5000.0)
        self.assertEqual(res_flag.df_clean_imputed.loc[0, "amount"], 5000.0)

        # 2. Cap mode: winsorizes in imputed output only, leaves conservative untouched
        cfg_cap = load_config(cli_overrides={"cleaning": {"outlier_action": "cap"}})
        res_cap = clean_dataset(df, prof, config=cfg_cap)
        self.assertEqual(res_cap.df_clean_conservative.loc[0, "amount"], 5000.0)
        upper_fence = res_cap.outlier_report["amount"].iqr_1_5_upper or 200.0
        self.assertAlmostEqual(
            float(res_cap.df_clean_imputed.loc[0, "amount"]), upper_fence, places=4
        )

        # 3. Remove mode (<= 5% of rows): drops outlier row in imputed output only
        cfg_rem = load_config(cli_overrides={"cleaning": {"outlier_action": "remove"}})
        res_rem = clean_dataset(df, prof, config=cfg_rem)
        self.assertEqual(len(res_rem.df_clean_conservative), 25)
        self.assertEqual(len(res_rem.df_clean_imputed), 24)

        # 4. Remove mode (> 5% of rows): refuses removal and logs warning
        cfg_refuse = load_config(
            cli_overrides={
                "cleaning": {
                    "outlier_action": "remove",
                    "outlier_remove_max_row_fraction": 0.02,
                }
            }
        )
        res_refuse = clean_dataset(df, prof, config=cfg_refuse)
        self.assertEqual(len(res_refuse.df_clean_imputed), 25)
        self.assertTrue(
            any(e.action == "refused_outlier_removal" for e in res_refuse.log)
        )

    def test_step9_missing_imputation_and_indicators(self) -> None:
        # 20 rows, staggered missingness so no single row exceeds 50% row_drop_threshold:
        # - 'num_col': 2 missing at rows 0, 1 (10% >= 5%) -> median imputed + num_col__was_missing
        # - 'cat_high_miss': 2 missing at rows 2, 3 (10% >= 5%) -> 'Missing' level + cat_high_miss__was_missing
        # - 'mostly_empty': 18 missing (90% > 80%) -> kept in conservative, dropped in imputed
        # - 'target_col': 1 missing at row 19 -> kept as NaN in conservative, row dropped in imputed
        df = pd.DataFrame(
            {
                "id": [f"C{i:03d}" for i in range(20)],
                "num_col": ["N/A", "?"] + ["10.0"] * 9 + ["20.0"] * 9,
                "cat_high_miss": ["Red", "Red", "", "null"] + ["Red"] * 10 + ["Blue"] * 6,
                "mostly_empty": ["val"] * 2 + [""] * 18,
                "target_col": ["Yes"] * 10 + ["No"] * 9 + [""],
            }
        )
        cfg = load_config(cli_overrides={"target": "target_col", "id_columns": ["id"]})
        prof = profile_dataset(df, config=cfg)
        res = clean_dataset(df, prof, config=cfg)

        df_cons = res.df_clean_conservative
        df_imp = res.df_clean_imputed

        # Conservative keeps mostly_empty and all 20 rows, with NaNs intact
        self.assertEqual(len(df_cons), 20)
        self.assertIn("mostly_empty", df_cons.columns)
        self.assertEqual(int(df_cons["num_col"].isna().sum()), 2)

        # Imputed drops 'mostly_empty' column and drops 1 row where target_col was missing -> 19 rows
        self.assertEqual(len(df_imp), 19)
        self.assertNotIn("mostly_empty", df_imp.columns)
        self.assertEqual(int(df_imp["num_col"].isna().sum()), 0)
        self.assertIn("num_col__was_missing", df_imp.columns)
        self.assertIn("cat_high_miss__was_missing", df_imp.columns)
        self.assertIn("Missing", df_imp["cat_high_miss"].astype(str).values)

    def test_step11_invariant_error_when_violated(self) -> None:
        df_bad = pd.DataFrame({"a": [" unstripped "], "b": ["clean"]})
        log = CleaningLog()
        cfg = load_config()
        sem = {"a": SemanticType.CATEGORICAL_NOMINAL, "b": SemanticType.CATEGORICAL_NOMINAL}
        with self.assertRaises(CleaningInvariantError):
            step11_validate_invariants(df_bad, df_bad, 1, sem, log, cfg)

    def test_idempotence_requirement(self) -> None:
        df_clean_base = make_clean_base(n_rows=150, seed=7)
        df_messy, _, _ = inject_problems(df_clean_base, seed=7)
        cfg = load_config("configs/datasets/messy_synthetic.yaml")

        prof1 = profile_dataset(df_messy, config=cfg)
        res1 = clean_dataset(df_messy, prof1, config=cfg)

        # Save conservative output to CSV, reload via load_csv, profile, and clean again
        with TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "cleaned.csv"
            res1.df_clean_conservative.to_csv(csv_path, index=False, encoding="utf-8")
            ing2 = load_csv(csv_path, config=cfg)
            prof2 = profile_dataset(ing2.df_raw_str, ing2.df_naive, ing2.metadata, config=cfg)
            res2 = clean_dataset(ing2.df_raw_str, prof2, config=cfg)

            # Check that no cells or rows were modified on the second pass
            log_check = CleaningLog()
            log_check.entries = res2.log
            self.assertFalse(
                log_check.has_meaningful_changes(),
                f"Expected idempotent second pass, but got changes: {[e.model_dump() for e in res2.log if e.n_cells_affected > 0 or e.rows_before != e.rows_after]}",
            )
            self.assertEqual(
                len(res1.df_clean_conservative), len(res2.df_clean_conservative)
            )

    def test_messy_synthetic_benchmark_fidelity_and_zero_damage(self) -> None:
        df_truth = make_clean_base(n_rows=500, seed=42)
        df_messy, manifest, _ = inject_problems(df_truth, seed=42)
        cfg = load_config("configs/datasets/messy_synthetic.yaml")

        prof = profile_dataset(df_messy, config=cfg)
        res = clean_dataset(df_messy, prof, config=cfg)
        df_cons = res.df_clean_conservative

        # 1. Exact row recovery: 500 primary rows (all duplicates and empty rows removed)
        self.assertEqual(len(df_cons), 500)
        # 2. Exact column recovery: 13 original columns ('Unnamed: 0' and 'unused' removed; 'membership ' normalized)
        self.assertEqual(list(df_cons.columns), list(df_truth.columns))

        # 3. Verify 100% of untouched cells in primary rows have zero damage
        by_id = {e.problem_id: e for e in manifest.entries}

        # Check gender: case_only_auto_fixed_rows must match truth 100%;
        # abbreviation_flagged_only_rows ('M'/'F') must remain untouched ('M'/'F')
        case_auto_rows = by_id["case_variants"].details["case_only_auto_fixed_rows"]
        abbrev_rows = set(by_id["case_variants"].details["abbreviation_flagged_only_rows"])
        for r_i in case_auto_rows:
            self.assertEqual(
                str(df_cons.loc[r_i, "gender"]),
                str(df_truth.loc[r_i, "gender"]),
            )
        for r_i in abbrev_rows:
            self.assertIn(str(df_cons.loc[r_i, "gender"]), {"M", "F"})

        # Check churned: 100% of binary_encoding_mix rows restored to exact truth ('Yes'/'No')
        for r_i in range(500):
            self.assertEqual(
                str(df_cons.loc[r_i, "churned"]),
                str(df_truth.loc[r_i, "churned"]),
            )

        # Check signup_date: 100% of non-garbage dates match exact ISO YYYY-MM-DD truth
        garbage_date_rows = set(by_id["date_formats"].details["garbage_date_rows"])
        for r_i in range(500):
            if r_i in garbage_date_rows:
                self.assertTrue(pd.isna(df_cons.loc[r_i, "signup_date"]))
            else:
                self.assertEqual(
                    str(df_cons.loc[r_i, "signup_date"]),
                    str(df_truth.loc[r_i, "signup_date"]),
                )

        # Check income: all non-missing, non-outlier rows match truth within 0.5% (scientific notation rounding)
        miss_inc_rows = set(by_id["missing_tokens"].details["income_rows"])
        out_inc_rows = set(by_id["outliers_numeric"].details["income_rows"])
        for r_i in range(500):
            if r_i in miss_inc_rows:
                self.assertTrue(pd.isna(df_cons.loc[r_i, "income"]))
            elif r_i not in out_inc_rows:
                val_clean = float(df_cons.loc[r_i, "income"])
                val_truth = float(df_truth.loc[r_i, "income"])
                self.assertLess(abs(val_clean - val_truth) / val_truth, 0.005)

        # Check outliers in income and monthly_spend were flagged and left untouched
        self.assertGreater(res.outlier_report["income"].n_flagged, 0)
        self.assertGreater(res.outlier_report["monthly_spend"].n_flagged, 0)


if __name__ == "__main__":
    unittest.main()
