"""End-to-end pipeline, determinism, manual-section preservation, and no-LLM-import tests (Sections 14, 16, 18)."""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from ads.config import load_config
from ads.ingestion import compute_sha256
from ads.pipeline import run_phase1
from ads.synthetic.messy_injector import generate_and_save_messy_dataset


class TestPipelineEndToEnd(unittest.TestCase):
    def test_end_to_end_determinism_and_manual_insights_preservation(self) -> None:
        with TemporaryDirectory() as tmp:
            syn_dir = Path(tmp) / "syn"
            paths = generate_and_save_messy_dataset(out_dir=syn_dir, n_rows=200, seed=42)
            raw_sha_before = compute_sha256(paths["messy_csv"])

            cfg = load_config("configs/datasets/messy_synthetic.yaml")
            out1 = Path(tmp) / "out1"
            clean1 = Path(tmp) / "clean1"
            res1 = run_phase1(
                input_csv=paths["messy_csv"],
                dataset_name="messy_synthetic",
                out_dir=out1,
                config=cfg,
                cleaned_dir=clean1,
            )

            # Raw file must never be mutated (Section 2 Principle 4 & Section 18)
            self.assertEqual(compute_sha256(paths["messy_csv"]), raw_sha_before)

            # All required artifacts must exist
            self.assertTrue(res1.cleaned_conservative_csv.exists())
            self.assertTrue(res1.cleaned_imputed_csv.exists())
            self.assertTrue(res1.scaled_csv is not None and res1.scaled_csv.exists())
            self.assertTrue(res1.profile_json.exists())
            self.assertTrue(res1.column_schema_json.exists())
            self.assertTrue(res1.cleaning_log_json.exists())
            self.assertTrue((out1 / "cleaning_log.md").exists())
            self.assertTrue((out1 / "scaling_report.md").exists())
            self.assertTrue((out1 / "insights.md").exists())
            self.assertTrue((out1 / "report.md").exists())
            self.assertTrue((out1 / "run_meta.json").exists())

            # Determinism test: second run into out2/clean2 must produce identical artifact hashes
            out2 = Path(tmp) / "out2"
            clean2 = Path(tmp) / "clean2"
            res2 = run_phase1(
                input_csv=paths["messy_csv"],
                dataset_name="messy_synthetic",
                out_dir=out2,
                config=cfg,
                cleaned_dir=clean2,
            )

            self.assertEqual(
                compute_sha256(res1.cleaned_conservative_csv),
                compute_sha256(res2.cleaned_conservative_csv),
            )
            self.assertEqual(
                compute_sha256(res1.cleaned_imputed_csv),
                compute_sha256(res2.cleaned_imputed_csv),
            )
            self.assertEqual(
                compute_sha256(res1.profile_json),
                compute_sha256(res2.profile_json),
            )
            self.assertEqual(
                compute_sha256(res1.column_schema_json),
                compute_sha256(res2.column_schema_json),
            )
            self.assertEqual(
                compute_sha256(res1.cleaning_log_json),
                compute_sha256(res2.cleaning_log_json),
            )

            # Test manual section preservation on re-run (Section 11 & Section 20 Risk 11)
            ins_md = out1 / "insights.md"
            custom_note = (
                "<!-- MANUAL:START -->\n"
                "- **Custom Analyst Finding:** Smoker x BMI interaction is strong.\n"
                "<!-- MANUAL:END -->"
            )
            text_with_custom = ins_md.read_text(encoding="utf-8").replace(
                ins_md.read_text(encoding="utf-8")[
                    ins_md.read_text(encoding="utf-8").find("<!-- MANUAL:START -->") :
                ],
                custom_note + "\n",
            )
            ins_md.write_text(text_with_custom, encoding="utf-8")

            # Re-run on out1 -> custom_note must be preserved!
            run_phase1(
                input_csv=paths["messy_csv"],
                dataset_name="messy_synthetic",
                out_dir=out1,
                config=cfg,
                cleaned_dir=clean1,
            )
            self.assertIn(
                "**Custom Analyst Finding:** Smoker x BMI interaction is strong.",
                ins_md.read_text(encoding="utf-8"),
            )

    def test_no_pipeline_module_imports_llm_sdk(self) -> None:
        # Section 18 Acceptance Criteria: No pipeline module imports an LLM SDK
        src_root = Path(__file__).resolve().parents[1] / "src" / "ads"
        for py_file in src_root.rglob("*.py"):
            if "baselines" in py_file.parts:
                continue
            code = py_file.read_text(encoding="utf-8")
            self.assertNotIn(
                "import anthropic",
                code,
                f"Forbidden LLM import in pipeline module {py_file}",
            )
            self.assertNotIn(
                "from anthropic",
                code,
                f"Forbidden LLM import in pipeline module {py_file}",
            )


if __name__ == "__main__":
    unittest.main()

