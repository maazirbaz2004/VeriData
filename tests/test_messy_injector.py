"""Unit tests for the messy synthetic dataset generator and manifest (Section 12.3)."""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from ads.ingestion import compute_sha256, load_csv
from ads.profiling import profile_dataset
from ads.synthetic.base_generator import generate_base_truth_metadata, make_clean_base
from ads.synthetic.messy_injector import (
    generate_and_save_messy_dataset,
    inject_problems,
)


class TestMessyInjector(unittest.TestCase):
    def test_base_generator_structure_and_planted_relationships(self) -> None:
        df_clean = make_clean_base(n_rows=500, seed=42)
        self.assertEqual(len(df_clean), 500)
        self.assertEqual(len(df_clean.columns), 13)
        self.assertTrue((df_clean["income"] > 0).all())
        self.assertTrue((df_clean["age"].between(18, 80)).all())
        self.assertEqual(df_clean["constant_flag"].nunique(), 1)

        meta = generate_base_truth_metadata(df_clean, seed=42)
        rels = { tuple(r["pair"]): r for r in meta["planted_relationships"] }
        self.assertGreater(rels[("income", "monthly_spend")]["pearson_r"], 0.70)
        self.assertLess(rels[("tenure_months", "churned")]["point_biserial_r"], -0.10)
        self.assertLess(rels[("satisfaction", "churned")]["point_biserial_r"], -0.15)

    def test_all_18_problems_injected_and_manifest_counts_match(self) -> None:
        df_clean = make_clean_base(n_rows=400, seed=99)
        df_messy, manifest, index_map = inject_problems(df_clean, seed=99)

        expected_problem_ids = {
            "ws_leading_trailing",
            "ws_internal",
            "case_variants",
            "missing_tokens",
            "real_nan",
            "numeric_as_string",
            "mixed_types",
            "date_formats",
            "duplicates_exact",
            "duplicates_formatting",
            "outliers_numeric",
            "impossible_values",
            "constant_column",
            "id_column",
            "empty_rows",
            "empty_column",
            "column_name_issues",
            "binary_encoding_mix",
        }
        by_id = {e.problem_id: e for e in manifest.entries}
        self.assertEqual(set(by_id.keys()), expected_problem_ids)

        # Verify row count matches: 400 clean + 3% exact dups (12) + 1% fmt dups (4) + 10 empty = 426
        n_dup_exact = by_id["duplicates_exact"].n_rows
        n_dup_fmt = by_id["duplicates_formatting"].n_rows
        n_empty = by_id["empty_rows"].n_rows
        self.assertEqual(
            len(df_messy),
            len(df_clean) + n_dup_exact + n_dup_fmt + n_empty,
        )

        # Verify column count matches: 13 clean + 1 'unused' + 1 'Unnamed: 0' = 15
        self.assertEqual(len(df_messy.columns), 15)
        self.assertIn("Unnamed: 0", df_messy.columns)
        self.assertIn("unused", df_messy.columns)
        self.assertIn("membership ", df_messy.columns)
        self.assertNotIn("_row_uid", df_messy.columns)

        # Verify manifest counts against actual differences on primary rows (0..399)
        primary = df_messy.iloc[:400]

        # real_nan in age and satisfaction
        age_empty = int((primary["age"] == "").sum())
        sat_empty = int((primary["satisfaction"] == "").sum())
        self.assertEqual(by_id["real_nan"].n_cells, age_empty + sat_empty)

        # missing_tokens in region ('Unknown')
        reg_unk = int((primary["region"].str.strip() == "Unknown").sum())
        self.assertEqual(
            len(by_id["missing_tokens"].details["region_unknown_rows"]), reg_unk
        )

        # mixed_types in tenure_months ('twelve' / 'twenty')
        ten_words = int(primary["tenure_months"].isin(["twelve", "twenty"]).sum())
        self.assertEqual(by_id["mixed_types"].n_cells, ten_words)

        # index_map integrity
        self.assertEqual(len(index_map["messy_rows"]), len(df_messy))
        self.assertEqual(len(index_map["customer_id_to_truth_row"]), 400)

    def test_reproducibility_hash_equality_and_profiler_integration(self) -> None:
        with TemporaryDirectory() as tmp1, TemporaryDirectory() as tmp2:
            paths1 = generate_and_save_messy_dataset(out_dir=tmp1, n_rows=300, seed=42)
            paths2 = generate_and_save_messy_dataset(out_dir=tmp2, n_rows=300, seed=42)

            for key in ["messy_csv", "manifest_json", "truth_csv", "index_json", "base_truth_json"]:
                self.assertEqual(
                    compute_sha256(paths1[key]),
                    compute_sha256(paths2[key]),
                    f"Hash mismatch on {key}",
                )

            # Verify ingestion + profiling works on the generated messy CSV
            ing = load_csv(paths1["messy_csv"])
            prof = profile_dataset(ing.df_raw_str, ing.df_naive, ing.metadata)
            self.assertEqual(prof.n_fully_empty_rows, 10)
            self.assertGreaterEqual(prof.n_fully_empty_cols, 1)
            self.assertGreater(prof.n_duplicate_rows, prof.n_duplicate_rows_raw)


if __name__ == "__main__":
    unittest.main()

