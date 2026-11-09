"""Partner 2 modules (EDA, insights, reports) running inside the full Phase 1 pipeline."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from ads.config import load_config
from ads.ingestion import compute_sha256
from ads.pipeline import run_phase1
from ads.schemas import InsightRecord, SemanticType
from ads.synthetic.messy_injector import generate_and_save_messy_dataset

REPO = Path(__file__).resolve().parents[1]
COARSE = {
    SemanticType.NUMERIC_CONTINUOUS.value: "numeric",
    SemanticType.NUMERIC_DISCRETE.value: "numeric",
    SemanticType.BINARY.value: "binary",
    SemanticType.CATEGORICAL_NOMINAL.value: "categorical",
    SemanticType.CATEGORICAL_ORDINAL.value: "categorical",
    SemanticType.DATETIME.value: "datetime",
    SemanticType.ID_LIKE.value: "id",
    SemanticType.FREE_TEXT.value: "text",
    SemanticType.CONSTANT.value: "constant",
    SemanticType.UNKNOWN.value: "unknown",
}
MY_ARTIFACTS = ["report.md", "report.html", "insights.json", "insights.md", "eda_summary.json"]


def _messy(tmp_path: Path) -> Path:
    paths = generate_and_save_messy_dataset(out_dir=tmp_path / "syn", n_rows=200, seed=42)
    return Path(paths["messy_csv"])


def _run(csv: Path, name: str, root: Path, cfg_name: str) -> Path:
    cfg = load_config(REPO / "configs" / "datasets" / f"{cfg_name}.yaml")
    run_phase1(input_csv=csv, dataset_name=name, out_dir=root / "out", config=cfg, cleaned_dir=root / "clean")
    return root / "out"


def _check_outputs(out: Path, target: str | None) -> None:
    summary = json.loads((out / "eda_summary.json").read_text(encoding="utf-8"))
    assert summary["eda_errors"] == []
    if target:
        assert summary["target"]["name"] == target
    figs = sorted((out / "figures").glob("*.png"))
    assert 8 <= len(figs) <= 40
    ins = json.loads((out / "insights.json").read_text(encoding="utf-8"))
    assert isinstance(ins, list) and len(ins) > 0
    for rec in ins:
        InsightRecord(**rec)  # schema-valid
        if rec["figure_ref"]:
            assert (out / rec["figure_ref"]).exists(), rec["figure_ref"]
    md = (out / "report.md").read_text(encoding="utf-8")
    for heading in ["## 3. Data cleaning", "## 4. Exploratory data analysis", "## 5. Insights", "## 6. Normalization / scaling"]:
        assert heading in md
    for rel in re.findall(r"\]\((figures/[^)]+)\)", md):
        assert (out / rel).exists(), rel
    html = (out / "report.html").read_text(encoding="utf-8")
    assert html.count("<img ") == len(re.findall(r"^!\[", md, flags=re.M))
    for text in (md, (out / "insights.md").read_text(encoding="utf-8")):
        low = text.lower()
        assert "significant" not in low and "p-value" not in low


def test_pipeline_uses_partner2_modules_on_messy_data(tmp_path: Path) -> None:
    out = _run(_messy(tmp_path), "messy_synthetic", tmp_path, "messy_synthetic")
    _check_outputs(out, "churned")
    md = (out / "report.md").read_text(encoding="utf-8")
    assert "### What the TA asked for" in md  # the full Partner 2 report, not the pipeline's fallback page


def test_partner2_outputs_are_deterministic(tmp_path: Path) -> None:
    csv = _messy(tmp_path)
    a = _run(csv, "messy_synthetic", tmp_path / "a", "messy_synthetic")
    b = _run(csv, "messy_synthetic", tmp_path / "b", "messy_synthetic")
    for name in MY_ARTIFACTS:
        assert compute_sha256(a / name) == compute_sha256(b / name), name
    pngs = sorted(p.name for p in (a / "figures").glob("*.png"))
    assert pngs == sorted(p.name for p in (b / "figures").glob("*.png"))
    for name in pngs:
        assert compute_sha256(a / "figures" / name) == compute_sha256(b / "figures" / name), name


@pytest.mark.parametrize("name", ["student_performance", "bank_marketing"])
def test_partner2_real_datasets(tmp_path: Path, name: str) -> None:
    cfg = load_config(REPO / "configs" / "datasets" / f"{name}.yaml")
    csv = REPO / str(cfg.file)
    if not csv.exists():
        pytest.skip(f"{csv} not downloaded (see scripts/download_datasets.md)")
    sha_before = compute_sha256(csv)
    out = _run(csv, name, tmp_path, name)
    assert compute_sha256(csv) == sha_before  # raw file untouched
    _check_outputs(out, cfg.target)

    # Type-inference accuracy against the human truth types (plan Section 18: >= 95%)
    profile = json.loads((out / "profile.json").read_text(encoding="utf-8"))
    inferred = {c["name"]: COARSE[c["semantic_type"]] for c in profile["columns"]}
    wrong = {c: (inferred.get(c), t) for c, t in cfg.truth_types.items() if inferred.get(c) != t}
    accuracy = 1 - len(wrong) / len(cfg.truth_types)
    assert accuracy >= 0.95, f"type accuracy {accuracy:.1%}; mismatches (inferred, truth): {wrong}"
