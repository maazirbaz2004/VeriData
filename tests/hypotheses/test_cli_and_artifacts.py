"""CLI and artifact-serialization integration tests for Phase 2."""

from __future__ import annotations

import json
from pathlib import Path

from veridata.cli import main
from veridata.contracts.hypothesis import Hypothesis, HypothesisManifest, NLParseOutcome


def test_cli_hypotheses_offline_and_artifacts(tmp_path: Path) -> None:
    out_dir = tmp_path / "insurance_out"
    rc = main(["hypotheses", "--dataset", "insurance", "--no-llm", "--out", str(out_dir)])
    assert rc == 0

    hyps_path = out_dir / "hypotheses.json"
    manifest_path = out_dir / "hypothesis_manifest.json"
    md_path = out_dir / "hypotheses.md"

    assert hyps_path.exists()
    assert manifest_path.exists()
    assert md_path.exists()

    hyps = [Hypothesis.model_validate(x) for x in json.loads(hyps_path.read_text(encoding="utf-8"))]
    manifest = HypothesisManifest.model_validate(
        json.loads(manifest_path.read_text(encoding="utf-8"))
    )

    assert manifest.dataset_name == "insurance"
    assert manifest.n_in_family_planned == 21
    assert len(hyps) == 21
    assert manifest.llm_used is False
    assert "# Phase 2 Hypothesis Set" in md_path.read_text(encoding="utf-8")


def test_cli_parse_hypothesis_offline(capsys) -> None:
    rc = main(
        [
            "parse-hypothesis",
            "--dataset",
            "insurance",
            "--text",
            "Do smokers have higher charges?",
            "--no-llm",
        ]
    )
    assert rc == 0
    captured = capsys.readouterr().out
    outcome = NLParseOutcome.model_validate(json.loads(captured))
    assert outcome.status == "ok"
    assert outcome.hypothesis is not None
    assert outcome.hypothesis.column_a == "charges"
    assert outcome.hypothesis.column_b == "smoker"

