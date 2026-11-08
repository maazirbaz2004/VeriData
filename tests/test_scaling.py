"""Unit tests for scaling and transformation analysis (Milestone M7a, Section 11b)."""

from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np
import pandas as pd

from ads.config import load_config
from ads.scaling import analyze_scaling
from ads.schemas import ColumnRole, ColumnSchemaEntry, SemanticType


class TestScaling(unittest.TestCase):
    def test_scaling_recommendations_log1p_yeojohnson_and_none(self) -> None:
        rng = np.random.default_rng(42)
        n = 200
        # 1. Right-skewed non-negative -> log1p
        pos_skew = np.exp(rng.normal(2.0, 1.2, size=n))
        # 2. Right-skewed with negative values -> yeo-johnson
        neg_skew = np.exp(rng.normal(2.0, 1.2, size=n)) - 50.0
        # 3. Symmetric normal with tiny std -> none (creates high scale disparity vs pos_skew)
        sym_norm = rng.normal(0.0, 0.01, size=n)

        df = pd.DataFrame(
            {
                "cust_id": [f"C{i:04d}" for i in range(n)],
                "pos_skew": pos_skew,
                "neg_skew": neg_skew,
                "sym_norm": sym_norm,
            }
        )
        schema = {
            "cust_id": ColumnSchemaEntry(
                semantic_type=SemanticType.ID_LIKE,
                role=ColumnRole.ID,
                n_unique=n,
                pct_missing=0.0,
            ),
            "pos_skew": ColumnSchemaEntry(
                semantic_type=SemanticType.NUMERIC_CONTINUOUS,
                role=ColumnRole.FEATURE,
                n_unique=n,
                pct_missing=0.0,
            ),
            "neg_skew": ColumnSchemaEntry(
                semantic_type=SemanticType.NUMERIC_CONTINUOUS,
                role=ColumnRole.FEATURE,
                n_unique=n,
                pct_missing=0.0,
            ),
            "sym_norm": ColumnSchemaEntry(
                semantic_type=SemanticType.NUMERIC_CONTINUOUS,
                role=ColumnRole.FEATURE,
                n_unique=n,
                pct_missing=0.0,
            ),
        }

        with TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "out"
            clean_dir = Path(tmp) / "cleaned"
            cfg = load_config()
            rep = analyze_scaling(
                df,
                schema=schema,
                config=cfg,
                df_clean_imputed=df,
                dataset_name="scale_test",
                out_dir=out_dir,
                cleaned_dir=clean_dir,
            )

            rec_map = {r.column: r for r in rep.columns}
            self.assertNotIn("cust_id", rec_map)
            self.assertEqual(rec_map["pos_skew"].recommended_transform, "log1p")
            self.assertEqual(rec_map["neg_skew"].recommended_transform, "yeo-johnson")
            self.assertEqual(rec_map["sym_norm"].recommended_transform, "none")

            self.assertTrue(rep.recommend_zscore_for_scale_sensitive)
            self.assertGreater(rep.scale_disparity_ratio or 0.0, 10.0)

            scaled_csv = clean_dir / "scale_test_scaled.csv"
            self.assertTrue(scaled_csv.exists())
            df_scaled = pd.read_csv(scaled_csv)
            self.assertIn("pos_skew__log1p", df_scaled.columns)
            self.assertIn("neg_skew__yeojohnson", df_scaled.columns)
            self.assertIn("pos_skew__z", df_scaled.columns)
            self.assertIn("sym_norm__z", df_scaled.columns)

            params_json = out_dir / "scaling_params.json"
            self.assertTrue(params_json.exists())
            params = json.loads(params_json.read_text(encoding="utf-8"))
            self.assertIn("yeojohnson_lambda", params["neg_skew"])
            self.assertTrue((out_dir / "scaling_report.md").exists())


if __name__ == "__main__":
    unittest.main()

