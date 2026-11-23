"""Batch analysis LangGraph nodes wrapping Phase 1, Phase 2, Phase 3, and reporting functions."""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any

import pandas as pd

from veridata.agent.datastore import GLOBAL_DATASTORE
from veridata.agent.llm import LLMClient, NullLLM
from veridata.agent.state import BatchState
from veridata.cleaning import clean_dataset
from veridata.config import PipelineConfig, load_config
from veridata.contracts.hypothesis import HypothesisSet
from veridata.hypotheses.generator import generate_hypotheses
from veridata.ingestion import load_csv
from veridata.profiling import build_column_schema, profile_dataset
from veridata.reporting.facts import FactRegistry, build_facts
from veridata.reporting.narration import explain_finding
from veridata.schemas import ColumnSchemaEntry
from veridata.stats.runner import run_hypothesis
from veridata.validation.ledger import SessionLedger
from veridata.validation.validator import build_findings, validate

logger = logging.getLogger("veridata.agent.nodes.batch")


def ingest_profile_node(state: BatchState) -> dict[str, Any]:
    """Ingest CSV, compute initial profile, and infer column schemas."""
    t0 = time.perf_counter()
    cfg_dict = state.get("config", {})
    input_path = cfg_dict.get("file") or cfg_dict.get("input_csv")
    ds_name = state.get("dataset_name", "dataset")

    if not input_path or not Path(input_path).exists():
        return {
            "errors": [{"stage": "ingest_profile", "error": f"Input CSV '{input_path}' not found."}],
            "status": "failed",
        }

    cfg = PipelineConfig.model_validate(cfg_dict) if cfg_dict else load_config()
    ing = load_csv(input_path, config=cfg)
    df = ing.df_naive
    dataset_id = GLOBAL_DATASTORE.put(df)
    profile = profile_dataset(ing.df_raw_str, df_naive=ing.df_naive, config=cfg, dataset_name=ds_name)
    schema = build_column_schema(profile, cfg)

    duration = time.perf_counter() - t0
    timings = dict(state.get("stage_timings", {}))
    timings["ingest_profile"] = duration

    return {
        "dataset_id": dataset_id,
        "dataset_sha256": profile.sha256,
        "profile": profile.model_dump(mode="json"),
        "schema": {k: v.model_dump(mode="json") for k, v in schema.items()},
        "stage_timings": timings,
        "status": "running",
        "progress_message": f"Ingested and profiled {len(df):,} rows and {len(df.columns)} columns.",
    }


def clean_node(state: BatchState) -> dict[str, Any]:
    """Execute Phase 1 cleaning rules and store the cleaned DataFrame."""
    t0 = time.perf_counter()
    raw_df = GLOBAL_DATASTORE.get(state["dataset_id"])
    cfg = PipelineConfig.model_validate(state.get("config", {}))
    from veridata.schemas import DataProfile
    profile = DataProfile.model_validate(state["profile"])

    cleaning_result = clean_dataset(raw_df, profile, cfg)
    cleaned_df = cleaning_result.df_clean_conservative
    cleaned_id = GLOBAL_DATASTORE.put(cleaned_df)

    # Re-profile cleaned frame
    schema = {k: ColumnSchemaEntry.model_validate(v) for k, v in state["schema"].items()}

    duration = time.perf_counter() - t0
    timings = dict(state.get("stage_timings", {}))
    timings["clean"] = duration

    return {
        "cleaned_dataset_id": cleaned_id,
        "cleaning_log": [entry.model_dump(mode="json") for entry in cleaning_result.log],
        "stage_timings": timings,
        "progress_message": f"Cleaned dataset: {len(cleaned_df):,} conservative rows retained.",
    }


def hypothesize_node(state: BatchState) -> dict[str, Any]:
    """Generate Phase 2 hypotheses set (exhaustive or target-focused)."""
    t0 = time.perf_counter()
    cleaned_df = GLOBAL_DATASTORE.get(state["cleaned_dataset_id"])
    schema = {k: ColumnSchemaEntry.model_validate(v) for k, v in state["schema"].items()}
    cfg = PipelineConfig.model_validate(state.get("config", {}))

    hyp_set = generate_hypotheses(
        df=cleaned_df,
        schema=schema,
        profile=None,
        config=cfg,
        llm=NullLLM(),
        target=cfg.hypotheses.target,
    )

    duration = time.perf_counter() - t0
    timings = dict(state.get("stage_timings", {}))
    timings["hypothesize"] = duration

    return {
        "hypothesis_set": hyp_set.model_dump(mode="json"),
        "stage_timings": timings,
        "progress_message": f"Generated {len(hyp_set.hypotheses):,} hypotheses in multiple-testing family.",
    }


def test_node(state: BatchState) -> dict[str, Any]:
    """Execute fixed statistical tests for all planned hypotheses."""
    t0 = time.perf_counter()
    cleaned_df = GLOBAL_DATASTORE.get(state["cleaned_dataset_id"])
    cfg = PipelineConfig.model_validate(state.get("config", {}))
    hyp_set = HypothesisSet.model_validate(state["hypothesis_set"])

    ledger = SessionLedger(
        dataset_sha256=state.get("dataset_sha256", "sha"),
        alpha=getattr(cfg.stats, "alpha", 0.05) if hasattr(cfg, "stats") else 0.05,
    )
    results = []

    for hyp in hyp_set.hypotheses:
        res = run_hypothesis(hyp, cleaned_df, cfg, stage="A")
        ledger.add(res, stage="batch")
        results.append(res)

    GLOBAL_DATASTORE.put_artifact(f"ledger_{state.get('run_id')}", ledger)
    GLOBAL_DATASTORE.put_artifact(f"results_{state.get('run_id')}", results)

    duration = time.perf_counter() - t0
    timings = dict(state.get("stage_timings", {}))
    timings["test"] = duration

    return {
        "stage_timings": timings,
        "progress_message": f"Completed statistical testing for {len(results):,} hypotheses.",
    }


def validate_node(state: BatchState) -> dict[str, Any]:
    """Apply Benjamini-Hochberg FDR control and effect-size floor validation."""
    t0 = time.perf_counter()
    cfg = PipelineConfig.model_validate(state.get("config", {}))
    hyp_set = HypothesisSet.model_validate(state["hypothesis_set"])
    results = GLOBAL_DATASTORE.get_artifact(f"results_{state.get('run_id')}")

    hyp_map = {h.id: h for h in hyp_set.hypotheses}
    decisions = validate(results, hyp_map, cfg, family_id="batch")
    findings = build_findings(hyp_map, results, decisions)

    GLOBAL_DATASTORE.put_artifact(f"findings_{state.get('run_id')}", findings)

    accepted_count = sum(1 for d in decisions if d.accepted)
    duration = time.perf_counter() - t0
    timings = dict(state.get("stage_timings", {}))
    timings["validate"] = duration

    return {
        "decisions": [d.model_dump(mode="json") for d in decisions],
        "stage_timings": timings,
        "progress_message": f"Validation complete: {accepted_count} hypotheses validated out of {len(decisions)}.",
    }


def report_node(state: BatchState) -> dict[str, Any]:
    """Assemble final findings report and figures."""
    t0 = time.perf_counter()
    findings = GLOBAL_DATASTORE.get_artifact(f"findings_{state.get('run_id')}") or []
    cleaned_df = GLOBAL_DATASTORE.get(state["cleaned_dataset_id"])

    out_dir = Path("outputs") / state.get("dataset_name", "batch_run")
    fig_dir = out_dir / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)

    report_md_path = out_dir / "report.md"
    lines = [
        f"# VeriData Analysis Report — `{state.get('dataset_name')}`",
        "",
        f"- **Multiple-testing family size:** {len(state.get('decisions', []))}",
        f"- **Validated discoveries:** {sum(1 for d in state.get('decisions', []) if d.get('accepted'))}",
        "",
        "## Validated Findings",
        "",
    ]

    for f in findings:
        if f.decision.accepted:
            reg = FactRegistry()
            reg.add_many(build_facts(f), finding_id=f.hypothesis.id)
            exp = explain_finding(f, registry=reg)
            lines.append(f"### {f.hypothesis.column_a} vs {f.hypothesis.column_b}")
            lines.append(f"- **Explanation:** {exp.text}")
            lines.append(f"- **P-value:** {f.test.p_value:.3e} (FDR adjusted q: {f.decision.q_value:.3e})")
            lines.append("")

    report_md_path.write_text("\n".join(lines), encoding="utf-8")

    duration = time.perf_counter() - t0
    timings = dict(state.get("stage_timings", {}))
    timings["report"] = duration

    return {
        "report_paths": {"report.md": str(report_md_path)},
        "stage_timings": timings,
        "status": "done",
        "progress_message": f"Analysis complete. Report written to {report_md_path}.",
    }


def handle_error_node(state: BatchState) -> dict[str, Any]:
    """Handle fatal pipeline errors gracefully."""
    logger.error("Batch graph error handler invoked with errors: %s", state.get("errors"))
    return {
        "status": "failed",
        "progress_message": "Analysis failed due to errors.",
    }
