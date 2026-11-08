"""Unit tests for M0: Skeleton, Config Loading, Schemas, and CLI stub."""

from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd

from ads.cli import main
from ads.config import dump_resolved_config, load_config
from ads.schemas import (
    CleaningLogEntry,
    CleaningResult,
    ColumnProfile,
    ColumnRole,
    ColumnSchemaEntry,
    DataProfile,
    MissingMatrixSummary,
    SemanticType,
)


class TestM0Skeleton(unittest.TestCase):
    def test_load_default_config(self) -> None:
        cfg = load_config()
        self.assertEqual(cfg.ingestion.max_file_size_mb, 200.0)
        self.assertEqual(cfg.type_inference.numeric_parse_threshold, 0.95)
        self.assertEqual(cfg.cleaning.outlier_action, "flag")
        self.assertIn("N/A", cfg.effective_missing_tokens())
        self.assertNotIn("unknown", cfg.effective_missing_tokens())

    def test_config_precedence_and_merge(self) -> None:
        with TemporaryDirectory() as tmp:
            ds_yaml = Path(tmp) / "telco.yaml"
            ds_yaml.write_text(
                "name: telco_churn\n"
                "target: Churn\n"
                "forced_types:\n"
                "  SeniorCitizen: categorical_nominal\n"
                "missing_tokens_extra:\n"
                "  - 'BLANK'\n"
                "profiling:\n"
                "  treat_unknown_as_missing: true\n",
                encoding="utf-8",
            )
            cfg = load_config(
                dataset_config_path=ds_yaml,
                cli_overrides={"cleaning": {"outlier_action": "cap"}},
            )
            self.assertEqual(cfg.name, "telco_churn")
            self.assertEqual(cfg.target, "Churn")
            self.assertEqual(
                cfg.forced_types["SeniorCitizen"], SemanticType.CATEGORICAL_NOMINAL
            )
            self.assertEqual(cfg.cleaning.outlier_action, "cap")
            # Default values untouched by override must remain intact
            self.assertEqual(cfg.cleaning.column_drop_threshold, 0.80)
            tokens = cfg.effective_missing_tokens()
            self.assertIn("BLANK", tokens)
            self.assertIn("unknown", tokens)

            resolved_path = Path(tmp) / "config_resolved.yaml"
            dump_resolved_config(cfg, resolved_path)
            self.assertTrue(resolved_path.exists())

    def test_schemas_serialization(self) -> None:
        col_prof = ColumnProfile(
            name="charges",
            raw_dtype="float64",
            semantic_type=SemanticType.NUMERIC_CONTINUOUS,
            semantic_type_reason="float values with high cardinality",
            n_total=100,
            n_missing=2,
            pct_missing=0.02,
            n_unique=98,
            pct_unique=1.0,
            min=100.0,
            max=50000.0,
            mean=13270.4,
            median=9382.0,
            std=12110.0,
        )
        profile = DataProfile(
            dataset_name="insurance",
            source_file="data/raw/insurance/insurance.csv",
            sha256="abc123",
            n_rows=100,
            n_cols=1,
            memory_mb=0.01,
            columns=[col_prof],
            missing_matrix_summary=MissingMatrixSummary(
                total_cells=100,
                total_missing_cells=2,
                pct_missing_cells=0.02,
                rows_with_any_missing=2,
                pct_rows_with_any_missing=0.02,
                rows_with_gt_half_missing=0,
                pct_rows_with_gt_half_missing=0.0,
            ),
            warnings=[],
        )
        raw_json = profile.model_dump_json(indent=2)
        parsed = json.loads(raw_json)
        self.assertEqual(parsed["schema_version"], "1.0")
        self.assertEqual(parsed["columns"][0]["semantic_type"], "numeric_continuous")

        schema_entry = ColumnSchemaEntry(
            semantic_type=SemanticType.NUMERIC_CONTINUOUS,
            role=ColumnRole.TARGET_CANDIDATE,
            n_unique=98,
            pct_missing=0.02,
        )
        self.assertEqual(schema_entry.model_dump()["role"], "target_candidate")

    def test_cleaning_result_with_dataframes(self) -> None:
        df = pd.DataFrame({"a": [1, 2, 3]})
        log_entry = CleaningLogEntry(
            step="strip_whitespace",
            column="a",
            action="none",
            rows_before=3,
            rows_after=3,
            reason="already clean",
        )
        res = CleaningResult(
            df_clean_conservative=df,
            df_clean_imputed=df.copy(),
            log=[log_entry],
        )
        self.assertEqual(len(res.df_clean_conservative), 3)
        self.assertEqual(res.log[0].step, "strip_whitespace")

    def test_cli_run_stub(self) -> None:
        with TemporaryDirectory() as tmp:
            dummy_csv = Path(tmp) / "dummy.csv"
            dummy_csv.write_text("a,b\n1,x\n2,y\n3,z\n", encoding="utf-8")
            out_dir = Path(tmp) / "out_test"
            clean_dir = Path(tmp) / "cleaned"
            exit_code = main(
                [
                    "run",
                    "--input",
                    str(dummy_csv),
                    "--name",
                    "test_ds",
                    "--out",
                    str(out_dir),
                    "--cleaned-dir",
                    str(clean_dir),
                ]
            )
            self.assertEqual(exit_code, 0)
            self.assertTrue((out_dir / "config_resolved.yaml").exists())
            self.assertTrue((out_dir / "run.log").exists())
            self.assertTrue((out_dir / "profile.json").exists())


if __name__ == "__main__":
    unittest.main()

