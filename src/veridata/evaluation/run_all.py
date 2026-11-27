"""Phase 8 evaluation orchestrator: plan, run E1-E8, freeze protocol, write manifest."""

from __future__ import annotations

import json
import platform
import subprocess
from datetime import datetime, timezone
from importlib import metadata as importlib_metadata
from pathlib import Path
from typing import Any

from veridata.agent.llm import get_llm_client
from veridata.benchmark.suites import suite_specs
from veridata.config import PipelineConfig, load_config
from veridata.evaluation.budget import CostTracker
from veridata.evaluation.experiments.e1_main import run_e1
from veridata.evaluation.experiments.e2_ablation import run_e2
from veridata.evaluation.experiments.e3_calibration import run_e3
from veridata.evaluation.experiments.e4_numbers import run_e4
from veridata.evaluation.experiments.e5_real import run_e5
from veridata.evaluation.experiments.e6_selection import run_e6
from veridata.evaluation.experiments.e7_chat import run_e7
from veridata.evaluation.experiments.e8_robustness import run_e8
from veridata.evaluation.figures import generate_all_figures
from veridata.evaluation.tables import generate_all_tables

ALL_EXPERIMENTS = ("e1", "e2", "e3", "e4", "e5", "e6", "e7", "e8")


def _git_sha() -> str:
    try:
        out = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], text=True, timeout=3)
        return out.strip()
    except Exception:  # noqa: BLE001
        return "unknown"


def _pkg_versions() -> dict[str, str]:
    pkgs = ["pandas", "numpy", "scipy", "statsmodels", "pydantic", "langgraph", "httpx", "matplotlib", "streamlit"]
    out: dict[str, str] = {}
    for p in pkgs:
        try:
            out[p] = importlib_metadata.version(p)
        except importlib_metadata.PackageNotFoundError:
            out[p] = "not-installed"
    return out


def plan_evaluation(
    *,
    suite: str = "core60",
    split: str = "dev",
    experiment: str = "all",
    config: PipelineConfig | None = None,
    confirm_final: bool = False,
) -> dict[str, Any]:
    """Compute run plan and estimated LLM cost before executing Phase 8 experiments."""
    cfg = config or load_config()
    n_ds = len(suite_specs(suite, split, confirm_final=confirm_final)) if split == "dev" or confirm_final else 60
    exps = list(ALL_EXPERIMENTS) if experiment == "all" else [e.strip() for e in experiment.split(",")]
    r_syn = int(cfg.eval.repeats_synthetic) + 1
    r_real = int(cfg.eval.repeats_real)

    est_llm_calls = 0
    if "e1" in exps:
        # 2 S1a systems (1 call each) + 2 S1b systems (~3 calls each)
        est_llm_calls += n_ds * r_syn * (2 + 2 * 3)
    if "e5" in exps:
        est_llm_calls += 5 * r_real * (2 + 2 * 3)
    if "e7" in exps:
        est_llm_calls += 15

    # Conservative Gemini 2.5 Flash estimate (~2,500 input tokens, ~500 output tokens per call)
    est_cost_gemini = est_llm_calls * (2500 * 0.15 + 500 * 0.60) / 1_000_000.0
    return {
        "suite": suite,
        "split": split,
        "experiments": exps,
        "n_synthetic_datasets": n_ds,
        "deterministic_variants": 12,
        "llm_model": cfg.llm.model,
        "llm_provider": cfg.llm.provider,
        "estimated_llm_calls": est_llm_calls,
        "estimated_cost_usd_gemini_flash": round(est_cost_gemini, 3),
        "budget_cap_usd": cfg.eval.max_cost_usd,
    }


def write_run_manifest(
    *,
    eval_root: Path = Path("outputs/eval"),
    suite: str,
    split: str,
    experiments: list[str],
    config: PipelineConfig,
    cost_summary: dict[str, Any],
) -> Path:
    """Record reproducibility manifest (commit hash, versions, hardware, config, spend)."""
    eval_root.mkdir(parents=True, exist_ok=True)
    manifest = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "git_commit": _git_sha(),
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "suite": suite,
        "split": split,
        "experiments": experiments,
        "llm_provider": config.llm.provider,
        "llm_model": config.llm.model,
        "packages": _pkg_versions(),
        "cost": cost_summary,
    }
    p = eval_root / "run_manifest.json"
    p.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return p


def freeze_eval_protocol(protocol_path: Path = Path("docs/eval_protocol.md")) -> bool:
    """Change 'Status: DRAFT' to 'Status: FROZEN' in docs/eval_protocol.md."""
    text = protocol_path.read_text(encoding="utf-8")
    if "Status: FROZEN" in text:
        return False
    if "Status: DRAFT" not in text:
        raise ValueError(f"Could not find 'Status: DRAFT' in {protocol_path}")
    protocol_path.write_text(text.replace("Status: DRAFT", "Status: FROZEN", 1), encoding="utf-8")
    return True


def run_evaluation(
    *,
    experiment: str = "all",
    suite: str = "core60",
    split: str = "dev",
    eval_root: Path = Path("outputs/eval"),
    bench_root: Path = Path("outputs/benchmark"),
    n_jobs: int = 2,
    confirm_final: bool = False,
    skip_unavailable_llm: bool = True,
    with_llm: bool = True,
    config: PipelineConfig | None = None,
    llm_override: Any = None,
) -> dict[str, Any]:
    """Execute selected Phase 8 experiments with caching, tables, figures, and manifest."""
    cfg = config or load_config()
    exps = list(ALL_EXPERIMENTS) if experiment == "all" else [e.strip().lower() for e in experiment.split(",")]
    cost_tracker = CostTracker(max_cost_usd=cfg.eval.max_cost_usd, log_path=eval_root / "cost_log.jsonl")
    llm = llm_override if llm_override is not None else (
        get_llm_client(cfg.llm, log_path=eval_root / "llm_calls.jsonl") if with_llm else None
    )

    results: dict[str, Any] = {}
    if "e1" in exps:
        results["e1"] = run_e1(
            suite=suite,
            split=split,
            bench_root=bench_root,
            eval_root=eval_root,
            llm=llm,
            skip_unavailable_llm=skip_unavailable_llm,
            cost_tracker=cost_tracker,
            config=cfg,
            n_jobs=n_jobs,
            confirm_final=confirm_final,
            n_resamples=cfg.eval.bootstrap_resamples,
        )
    if "e2" in exps:
        results["e2"] = run_e2(
            suite=suite,
            split=split,
            bench_root=bench_root,
            eval_root=eval_root,
            n_jobs=n_jobs,
            confirm_final=confirm_final,
            n_resamples=cfg.eval.bootstrap_resamples,
        )
    if "e3" in exps:
        results["e3"] = run_e3(cal_root=bench_root / "calibration", eval_root=eval_root)
    if "e4" in exps:
        results["e4"] = run_e4(eval_root=eval_root, suite=suite, split=split)
    if "e5" in exps:
        results["e5"] = run_e5(
            eval_root=eval_root,
            llm=llm,
            skip_unavailable_llm=skip_unavailable_llm,
            cost_tracker=cost_tracker,
            config=cfg,
            n_jobs=n_jobs,
        )
    if "e6" in exps:
        results["e6"] = run_e6(suite=suite, split=split, bench_root=bench_root, eval_root=eval_root, confirm_final=confirm_final)
    if "e7" in exps:
        results["e7"] = run_e7(eval_root=eval_root, llm=llm, cost_tracker=cost_tracker)
    if "e8" in exps:
        results["e8"] = run_e8(bench_root=bench_root, eval_root=eval_root, suite=suite, split=split, confirm_final=confirm_final)

    tables = generate_all_tables(suite=suite, split=split, eval_root=eval_root)
    figures = generate_all_figures(suite=suite, split=split, eval_root=eval_root)
    manifest_p = write_run_manifest(
        eval_root=eval_root,
        suite=suite,
        split=split,
        experiments=exps,
        config=cfg,
        cost_summary=cost_tracker.summary(),
    )
    return {
        "experiments_run": exps,
        "tables": {k: str(v) for k, v in tables.items()},
        "figures": {k: str(v) for k, v in figures.items()},
        "manifest": str(manifest_p),
        "cost": cost_tracker.summary(),
    }
