"""Unit tests for dataset profiling and column schema generation (Section 8, Section 16)."""

from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd

from ads.config import load_config
from ads.profiling import (
    build_column_schema,
    compute_outlier_counts,
    profile_dataset,
    save_column_schema_json,
    save_profile_json,
)
from ads.schemas import ColumnRole, SemanticType


class TestProfiling(unittest.TestCase):
    def test_profile_does_not_mutate_input_and_counts_missing_and_duplicates(self) -> None:
        df = pd.DataFrame(
            {
                "id": ["C001", "C002", "C002", "C003", "C004", ""],
                "gender": ["Male", "Female", " female ", "MALE", "unknown", ""],
                "income": ["$50,000", "60000", "60000", "N/A", "?", ""],
                "constant_col": ["X", "X", "X", "X", "X", ""],
                "empty_col": ["", " ", "N/A", "?", "null", ""],
            }
        )
        df_copy = df.copy(deep=True)
        cfg = load_config(cli_overrides={"target": "income", "id_columns": ["id"]})
        profile = profile_dataset(df, config=cfg, dataset_name="test_ds")

        # Input must not be mutated
        pd.testing.assert_frame_equal(df, df_copy)

        self.assertEqual(profile.n_rows, 6)
        self.assertEqual(profile.n_cols, 5)
        self.assertEqual(profile.n_fully_empty_rows, 1)
        self.assertEqual(profile.n_fully_empty_cols, 1)

        # Row 1 and Row 2 differ only by 'Female' vs ' female ' -> 0 raw dups, 1 normalized dup
        self.assertEqual(profile.n_duplicate_rows_raw, 0)
        self.assertEqual(profile.n_duplicate_rows, 1)
        self.assertTrue(
            any("additional duplicate row" in w for w in profile.warnings)
        )

        # Check column profiles by name
        col_map = {c.name: c for c in profile.columns}

        # income: 3 valid numbers, 2 missing tokens ('N/A', '?'), 1 empty string -> 3 missing total
        inc = col_map["income"]
        self.assertEqual(inc.semantic_type, SemanticType.NUMERIC_CONTINUOUS)
        self.assertEqual(inc.n_missing, 3)
        self.assertEqual(inc.n_missing_token_cells, 2)
        self.assertEqual(inc.missing_tokens_found, {"N/A": 1, "?": 1})
        self.assertTrue(inc.looks_numeric_but_object)
        self.assertAlmostEqual(inc.min or 0.0, 50000.0)
        self.assertAlmostEqual(inc.max or 0.0, 60000.0)

        # gender: 'unknown' should be flagged as candidate missing token by default, not missing
        gen = col_map["gender"]
        self.assertEqual(gen.n_missing, 1)  # only the empty row
        self.assertTrue(gen.has_leading_trailing_ws)
        self.assertTrue(gen.has_mixed_case_variants)
        self.assertIn("male", gen.case_variant_groups)
        self.assertTrue(
            any("candidate missing token 'unknown'" in w for w in profile.warnings)
        )

        # When treat_unknown_as_missing is enabled, 'unknown' becomes missing
        cfg_unk = load_config(
            cli_overrides={"profiling": {"treat_unknown_as_missing": True}}
        )
        prof_unk = profile_dataset(df, config=cfg_unk)
        gen_unk = {c.name: c for c in prof_unk.columns}["gender"]
        self.assertEqual(gen_unk.n_missing, 2)

    def test_outliers_and_mad_zero_guard(self) -> None:
        # > 50% identical values -> MAD = 0, plus 1 extreme outlier
        s = pd.Series([10.0] * 15 + [11.0, 12.0, 500.0])
        n_iqr_1_5, n_iqr_3_0, n_modz, q1, q3, iqr = compute_outlier_counts(s)
        self.assertGreaterEqual(n_modz, 1)
        self.assertEqual(q1, 10.0)

        # Normal distribution with clear extreme outlier
        s2 = pd.Series([10.0, 11.0, 12.0, 13.0, 14.0, 15.0, 16.0, 17.0, 18.0, 200.0])
        n15, n30, nmz, _, _, _ = compute_outlier_counts(s2)
        self.assertEqual(n15, 1)
        self.assertEqual(n30, 1)
        self.assertEqual(nmz, 1)

    def test_string_quality_unicode_and_fuzzy_near_duplicates(self) -> None:
        # Include non-breaking space \u00a0, internal double space, and fuzzy typo 'California' vs 'Calfornia'
        vals = (
            ["California"] * 10
            + ["Calfornia"] * 2
            + ["New  York"] * 5
            + ["Texas\u00a0"] * 5
            + ["Cat"] * 4
            + ["Car"] * 4  # < 4 chars -> must be skipped by fuzzy matcher
        )
        df = pd.DataFrame({"state": vals})
        profile = profile_dataset(df)
        col = profile.columns[0]

        self.assertTrue(col.has_unicode_oddities)
        self.assertEqual(col.n_unicode_oddities, 5)
        self.assertTrue(col.has_leading_trailing_ws)
        self.assertTrue(col.has_internal_multi_ws)
        self.assertEqual(col.n_internal_multi_ws, 5)

        # Near duplicate should catch California vs Calfornia, but skip Cat vs Car (< 4 chars)
        self.assertEqual(len(col.near_duplicate_labels), 1)
        pair = col.near_duplicate_labels[0]
        self.assertEqual({pair.label_a, pair.label_b}, {"California", "Calfornia"})
        self.assertGreaterEqual(pair.similarity, 0.90)

    def test_column_schema_and_deterministic_json(self) -> None:
        n = 60
        df = pd.DataFrame(
            {
                "cust_id": [f"ID_{i:04d}" for i in range(n)],
                "age": [str(20 + (i % 40)) for i in range(n)],
                "const": ["same"] * n,
                "mostly_nan": ["1.0"] * 5 + [""] * (n - 5),
                "churn": ["Yes" if i % 4 == 0 else "No" for i in range(n)],
            }
        )
        cfg = load_config(cli_overrides={"target": "churn"})
        prof1 = profile_dataset(df, config=cfg)
        # Shuffled copy must produce identical column profile stats (Section 16 property)
        df_shuffled = df.sample(frac=1.0, random_state=42).reset_index(drop=True)
        prof2 = profile_dataset(df_shuffled, config=cfg)

        schema = build_column_schema(prof1, config=cfg)
        self.assertEqual(schema["cust_id"].role, ColumnRole.ID)
        self.assertEqual(schema["age"].role, ColumnRole.FEATURE)
        self.assertEqual(schema["const"].role, ColumnRole.EXCLUDED)
        self.assertEqual(schema["mostly_nan"].role, ColumnRole.EXCLUDED)
        self.assertEqual(schema["churn"].role, ColumnRole.TARGET_CANDIDATE)

        with TemporaryDirectory() as tmp:
            p1 = save_profile_json(prof1, Path(tmp) / "p1.json")
            p2 = save_profile_json(prof2, Path(tmp) / "p2.json")
            s1 = save_column_schema_json(schema, Path(tmp) / "schema.json")
            self.assertEqual(p1.read_text(encoding="utf-8"), p2.read_text(encoding="utf-8"))
            loaded_schema = json.loads(s1.read_text(encoding="utf-8"))
            self.assertEqual(loaded_schema["churn"]["role"], "target_candidate")


if __name__ == "__main__":
    unittest.main()

