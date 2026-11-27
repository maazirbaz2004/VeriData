"""End-to-end smoke test for Phase 8 evaluation pipeline (E1/E2/E6/tables/figures/report)."""

from __future__ import annotations

from pathlib import Path

from veridata.agent.fake_llm import FakeLLM
from veridata.config import load_config
from veridata.contracts.hypothesis import RelationshipType
from veridata.evaluation.experiments.e1_main import run_e1
from veridata.evaluation.experiments.e2_ablation import run_e2
from veridata.evaluation.experiments.e6_selection import oracle_acceptable_tests
from veridata.evaluation.figures import generate_all_figures
from veridata.evaluation.final_report import build_final_report
from veridata.evaluation.run_all import plan_evaluation
from veridata.evaluation.tables import generate_all_tables


def test_oracle_acceptable_tests_rules() -> None:
    assert oracle_acceptable_tests(RelationshipType.NUM_BINARY, n_total=40, group_sizes=[20, 20], all_normal=True) == {"welch_t"}
    assert oracle_acceptable_tests(RelationshipType.NUM_BINARY, n_total=40, group_sizes=[20, 20], all_normal=False) == {"mann_whitney_u"}
    assert oracle_acceptable_tests(RelationshipType.NUM_NUM, n_total=25, max_ties=0.0) == {"spearman"}
    assert oracle_acceptable_tests(RelationshipType.CAT_CAT, n_total=30, is_2x2=True, chi2_eligible=False) == {"fisher_exact"}


def test_e1_e2_smoke_with_fakellm_and_outputs(tmp_path: Path) -> None:
    bench_root = tmp_path / "bench"
    eval_root = tmp_path / "eval"
    rep_root = tmp_path / "report"

    cfg = load_config()
    cfg.eval.repeats_synthetic = 1

    fake = FakeLLM({"LLMFindingsPayload": {"findings": []}})
    only_ds = ["smoke_null_n200_p12__seed0", "smoke_linear_n300_p12__seed10"]

    e1 = run_e1(
        suite="smoke",
        split="dev",
        bench_root=bench_root,
        eval_root=eval_root,
        llm=fake,
        llm_systems=["S1a_summary_standard"],
        config=cfg,
        n_jobs=1,
        only=only_ds,
        n_resamples=100,
    )
    assert e1["n_datasets"] == 2
    assert "S3_veridata_full" in e1["summary"]
    assert "S1a_summary_standard" in e1["summary"]

    e2 = run_e2(
        suite="smoke",
        split="dev",
        bench_root=bench_root,
        eval_root=eval_root,
        systems=["S3_veridata_full", "S2_veridata_nocorrection", "A6_full_minus_gates"],
        n_jobs=1,
        only=only_ds,
        n_resamples=100,
    )
    assert len(e2["ablation_table"]) == 3

    tables = generate_all_tables(suite="smoke", split="dev", eval_root=eval_root)
    assert "e1_main" in tables and tables["e1_main"].exists()
    assert "e2_ablation" in tables and tables["e2_ablation"].exists()

    figs = generate_all_figures(suite="smoke", split="dev", eval_root=eval_root, report_root=rep_root)
    assert "e1_fdr_recall_bars" in figs and figs["e1_fdr_recall_bars"].exists()

    rep = build_final_report(suite="smoke", split="dev", eval_root=eval_root, report_root=rep_root)
    assert rep["markdown"].exists() and rep["html"].exists() and rep["numbers"].exists()

    plan = plan_evaluation(suite="smoke", split="dev", experiment="e1")
    assert plan["n_synthetic_datasets"] == 12
