"""E1 — Main synthetic benchmark experiment (S1a, S1b, S2, S3 on smoke/core60)."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from joblib import Parallel, delayed

from veridata.agent.llm import LLMClient, NullLLM
from veridata.benchmark.matcher import match_findings
from veridata.benchmark.metrics import aggregate, dataset_metrics, q_calibration, stratified_recall
from veridata.benchmark.runner import generate_suite
from veridata.benchmark.suites import suite_hash, suite_specs
from veridata.benchmark.systems import benchmark_config
from veridata.benchmark.truth import GroundTruth, SystemOutput
from veridata.config import PipelineConfig, load_config
from veridata.errors import LLMUnavailable
from veridata.evaluation.budget import BudgetExceededError, CostTracker
from veridata.evaluation.stats_utils import collapse_repeats, paired_wilcoxon
from veridata.evaluation.systems.llm_only import (
    LLM_SYSTEM_IDS,
    run_llm_only_system,
    summarize_llm_error,
)
from veridata.evaluation.systems.veridata_variants import (
    _validate_spec,
    resolve_variant_spec,
    run_phase8_variants_on_csv,
)

logger = logging.getLogger("veridata.eval.e1")

E1_DETERMINISTIC_SYSTEMS = ["S3_veridata_full", "S2_veridata_nocorrection"]


def _cache_system_path(eval_root: Path, suite: str, split: str, system: str, dataset_id: str, repeat_idx: int | None = None) -> Path:
    suffix = f"__r{repeat_idx}" if repeat_idx is not None else ""
    return eval_root / suite / split / "systems" / system / f"{dataset_id}{suffix}.json"


def _load_cached_output(path: Path) -> SystemOutput | None:
    if not path.exists():
        return None
    try:
        return SystemOutput.model_validate_json(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None


def _save_output(path: Path, out: SystemOutput) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(out.model_dump_json(indent=1) + "\n", encoding="utf-8")


def _run_det_one(
    csv_path: Path,
    dataset_id: str,
    missing_systems: list[str],
    eval_root: Path,
    suite: str,
    split: str,
) -> dict[str, SystemOutput]:
    outs = run_phase8_variants_on_csv(csv_path, dataset_id, variants=missing_systems)
    for sys_id, out in outs.items():
        _save_output(_cache_system_path(eval_root, suite, split, sys_id, dataset_id), out)
    return outs


def run_alpha_sweep(
    suite: str,
    split: str,
    *,
    bench_root: Path = Path("outputs/benchmark"),
    eval_root: Path = Path("outputs/eval"),
    alphas: tuple[float, ...] = (0.01, 0.02, 0.05, 0.10, 0.15, 0.20),
    confirm_final: bool = False,
    only: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Compute S3 recall-FDR trade-off across alpha thresholds reusing Stage A results."""
    from veridata.benchmark.systems import findings_to_reported, prepare_dataset, run_stage_a

    specs = [s for s in suite_specs(suite, split, confirm_final=confirm_final) if only is None or s.dataset_id in only]
    base = bench_root / suite / split
    stage_cache_dir = eval_root / suite / split / "stage_a_cache"
    stage_cache_dir.mkdir(parents=True, exist_ok=True)

    cfg_base = benchmark_config(load_config())
    spec_s3 = resolve_variant_spec("S3_veridata_full")

    # Prepare & cache Stage A per dataset once
    loaded: list[tuple[str, Any, Any, list[Any], GroundTruth, dict[str, Any]]] = []
    for ds_spec in specs:
        ds_dir = base / ds_spec.dataset_id
        truth = GroundTruth.load(ds_dir / "truth.json")
        scen = json.loads((ds_dir / "scenario.json").read_text(encoding="utf-8"))["scenario"]
        cache_p = stage_cache_dir / f"{ds_spec.dataset_id}_aware.json"
        if cache_p.exists():
            from veridata.contracts.results import TestResult

            _, hset, _ = prepare_dataset(ds_dir / "data.csv", ds_spec.dataset_id, cfg_base)
            raw = json.loads(cache_p.read_text(encoding="utf-8"))
            results = [TestResult.model_validate(r) for r in raw]
        else:
            df, hset, _ = prepare_dataset(ds_dir / "data.csv", ds_spec.dataset_id, cfg_base)
            results = run_stage_a(hset, df, cfg_base)
            cache_p.write_text(
                json.dumps([r.model_dump(mode="json") for r in results], indent=1) + "\n",
                encoding="utf-8",
            )
        loaded.append((ds_spec.dataset_id, hset, cfg_base, results, truth, scen))

    rows: list[dict[str, Any]] = []
    for alpha in alphas:
        cfg_a = cfg_base.model_copy(deep=True)
        cfg_a.stats.alpha = float(alpha)
        ds_rows = []
        for ds_id, hset, _, results, truth, scen in loaded:
            findings = _validate_spec(results, hset, cfg_a, spec_s3)
            rep = findings_to_reported(findings)
            m = match_findings(rep, truth, "if_reported")
            ds_rows.append(dataset_metrics(m, truth, scen))
        agg = aggregate(ds_rows, n_resamples=500, seed=0)
        rows.append(
            {
                "alpha": alpha,
                "fdr": agg["fdr"],
                "fdr_ci_low": agg.get("fdr_ci_low"),
                "fdr_ci_high": agg.get("fdr_ci_high"),
                "recall": agg["recall"],
                "recall_ci_low": agg.get("recall_ci_low"),
                "recall_ci_high": agg.get("recall_ci_high"),
                "precision": agg["precision"],
                "fwer_null": agg["fwer_null"],
            }
        )
    return rows


def run_e1(
    *,
    suite: str = "core60",
    split: str = "dev",
    bench_root: Path = Path("outputs/benchmark"),
    eval_root: Path = Path("outputs/eval"),
    llm: LLMClient | None = None,
    llm_systems: list[str] | None = None,
    skip_unavailable_llm: bool = True,
    cost_tracker: CostTracker | None = None,
    config: PipelineConfig | None = None,
    n_jobs: int = 2,
    confirm_final: bool = False,
    only: list[str] | None = None,
    n_resamples: int = 2000,
) -> dict[str, Any]:
    """Run E1 Main Benchmark: deterministic S3/S2 + cached/live S1a/S1b with CIs & Wilcoxon."""
    cfg = config or load_config()
    specs = [s for s in suite_specs(suite, split, confirm_final=confirm_final) if only is None or s.dataset_id in only]
    base = bench_root / suite / split

    # Ensure dataset files exist
    missing_data = [s.dataset_id for s in specs if not (base / s.dataset_id / "data.csv").exists()]
    if missing_data:
        generate_suite(suite, split, out_root=bench_root, n_jobs=n_jobs, confirm_final=confirm_final, only=missing_data)

    # 1. Deterministic systems S3 & S2
    todo_det: list[tuple[str, Path, list[str]]] = []
    det_outputs: dict[str, dict[str, SystemOutput]] = {s: {} for s in E1_DETERMINISTIC_SYSTEMS}
    for sp in specs:
        need = []
        for sys_id in E1_DETERMINISTIC_SYSTEMS:
            cp = _cache_system_path(eval_root, suite, split, sys_id, sp.dataset_id)
            cached = _load_cached_output(cp)
            if cached is not None and not cached.error:
                det_outputs[sys_id][sp.dataset_id] = cached
            else:
                need.append(sys_id)
        if need:
            todo_det.append((sp.dataset_id, base / sp.dataset_id / "data.csv", need))

    if todo_det:
        res_list = Parallel(n_jobs=n_jobs)(
            delayed(_run_det_one)(csv_p, ds_id, need, eval_root, suite, split)
            for ds_id, csv_p, need in todo_det
        )
        for (ds_id, _, _), outs in zip(todo_det, res_list):
            for sys_id, out in outs.items():
                det_outputs[sys_id][ds_id] = out

    # 2. LLM-only systems (cached or live if LLM available)
    chosen_llm_systems = llm_systems if llm_systems is not None else list(LLM_SYSTEM_IDS)
    n_repeats = int(cfg.eval.repeats_synthetic)
    temp_rep = float(cfg.eval.repeat_temperature)
    llm_outputs: dict[str, dict[str, list[SystemOutput]]] = {s: {} for s in chosen_llm_systems}
    llm_status = "completed" if (llm is not None and not isinstance(llm, NullLLM)) else "skipped_no_api_key"
    budget_stopped = False

    for sys_id in chosen_llm_systems:
        for sp in specs:
            runs: list[SystemOutput] = []
            for r in range(n_repeats + 1):  # 0..R-1 at T=0.7, R at T=0.0
                t_val = 0.0 if r == n_repeats else temp_rep
                cp = _cache_system_path(eval_root, suite, split, sys_id, sp.dataset_id, repeat_idx=r)
                cached = _load_cached_output(cp)
                if cached is not None and not cached.error:
                    runs.append(cached)
                    continue
                if llm is None or isinstance(llm, NullLLM):
                    if not skip_unavailable_llm:
                        raise LLMUnavailable(f"LLM unavailable for {sys_id}.")
                    continue
                if budget_stopped:
                    continue
                try:
                    out = run_llm_only_system(
                        sys_id,
                        base / sp.dataset_id / "data.csv",
                        sp.dataset_id,
                        llm=llm,
                        temperature=t_val,
                        repeat_idx=r,
                        max_turns=int(cfg.eval.code_sandbox_max_turns),
                        sandbox_timeout_s=float(cfg.eval.code_sandbox_timeout_s),
                        cost_tracker=cost_tracker,
                    )
                    _save_output(cp, out)
                    runs.append(out)
                except BudgetExceededError as exc:
                    logger.warning("Budget cap reached during E1: %s", exc)
                    budget_stopped = True
                    llm_status = "budget_stopped"
                    break
                except Exception as exc:  # noqa: BLE001
                    err_out = summarize_llm_error(sys_id, sp.dataset_id, exc)
                    _save_output(cp, err_out)
            if runs:
                llm_outputs[sys_id][sp.dataset_id] = runs

    # 3. Score all systems
    truths = {s.dataset_id: GroundTruth.load(base / s.dataset_id / "truth.json") for s in specs}
    scen_map = {
        s.dataset_id: json.loads((base / s.dataset_id / "scenario.json").read_text(encoding="utf-8"))["scenario"]
        for s in specs
    }

    summary: dict[str, Any] = {}
    all_dataset_rows: list[dict[str, Any]] = []
    pair_rows: list[dict[str, Any]] = []
    finding_rows: list[dict[str, Any]] = []
    collapsed_by_sys: dict[str, dict[str, dict[str, Any]]] = {}

    for sys_id in E1_DETERMINISTIC_SYSTEMS:
        per_mode: dict[str, list[dict[str, Any]]] = {"if_reported": [], "ignore": []}
        collapsed_by_sys[sys_id] = {}
        for sp in specs:
            out = det_outputs[sys_id][sp.dataset_id]
            truth = truths[sp.dataset_id]
            for mode in ("if_reported", "ignore"):
                m = match_findings(out.findings, truth, mode)  # type: ignore[arg-type]
                row = dataset_metrics(m, truth, scen_map[sp.dataset_id])
                row.update({"system": sys_id, "direction_mode": mode, "runtime_s": out.runtime_s, "n_repeats": 1})
                per_mode[mode].append(row)
                all_dataset_rows.append(row)
                if mode == "if_reported":
                    collapsed_by_sys[sys_id][sp.dataset_id] = row
                    sc = scen_map[sp.dataset_id]
                    for t in m.truths:
                        pair_rows.append({**t.model_dump(), "system": sys_id, "dataset_id": sp.dataset_id, "n_rows": truth.n_rows, "n_cols": len(truth.columns), "dist": sc.get("dist")})
                    for fm in m.findings:
                        finding_rows.append({**fm.model_dump(), "system": sys_id, "dataset_id": sp.dataset_id})
        summary[sys_id] = {
            "if_reported": aggregate(per_mode["if_reported"], n_resamples=n_resamples, seed=0),
            "ignore": aggregate(per_mode["ignore"], n_resamples=n_resamples, seed=0),
            "n_datasets_evaluated": len(per_mode["if_reported"]),
            "is_llm": False,
        }

    for sys_id in chosen_llm_systems:
        if not llm_outputs[sys_id]:
            continue
        per_mode_runs: dict[str, list[dict[str, Any]]] = {"if_reported": [], "ignore": []}
        hallucinated_total = 0
        total_cost = 0.0
        for sp in specs:
            runs = llm_outputs[sys_id].get(sp.dataset_id, [])
            truth = truths[sp.dataset_id]
            for out in runs:
                hallucinated_total += int(out.meta.get("n_hallucinated_columns", 0))
                total_cost += float(out.cost_usd or 0.0)
                for mode in ("if_reported", "ignore"):
                    m = match_findings(out.findings, truth, mode)  # type: ignore[arg-type]
                    row = dataset_metrics(m, truth, scen_map[sp.dataset_id])
                    row.update({"system": sys_id, "direction_mode": mode, "repeat_idx": out.meta.get("repeat_idx", 0), "runtime_s": out.runtime_s})
                    per_mode_runs[mode].append(row)
                    if mode == "if_reported":
                        sc = scen_map[sp.dataset_id]
                        for t in m.truths:
                            pair_rows.append({**t.model_dump(), "system": sys_id, "dataset_id": sp.dataset_id, "n_rows": truth.n_rows, "n_cols": len(truth.columns), "dist": sc.get("dist")})

        # Collapse repeats per dataset BEFORE bootstrap CIs & paired comparisons
        collapsed_primary = collapse_repeats(per_mode_runs["if_reported"])
        collapsed_ignore = collapse_repeats(per_mode_runs["ignore"])
        for row in collapsed_primary:
            row["system"] = sys_id
            row["direction_mode"] = "if_reported"
            all_dataset_rows.append(row)
        collapsed_by_sys[sys_id] = {r["dataset_id"]: r for r in collapsed_primary}
        summary[sys_id] = {
            "if_reported": aggregate(collapsed_primary, n_resamples=n_resamples, seed=0),
            "ignore": aggregate(collapsed_ignore, n_resamples=n_resamples, seed=0),
            "n_datasets_evaluated": len(collapsed_primary),
            "hallucinated_columns_total": hallucinated_total,
            "total_cost_usd": round(total_cost, 6),
            "is_llm": True,
        }

    # 4. Paired Wilcoxon tests vs S3
    paired_rows: list[dict[str, Any]] = []
    s3_map = collapsed_by_sys["S3_veridata_full"]
    s3_fdp = {k: v["fdp"] for k, v in s3_map.items()}
    s3_rec = {k: v["recall"] for k, v in s3_map.items() if v["recall"] is not None}
    for sys_id, ds_map in collapsed_by_sys.items():
        if sys_id == "S3_veridata_full":
            continue
        other_fdp = {k: v["fdp"] for k, v in ds_map.items()}
        other_rec = {k: v["recall"] for k, v in ds_map.items() if v["recall"] is not None}
        w_fdp = paired_wilcoxon(s3_fdp, other_fdp, n_resamples=n_resamples, seed=0)
        w_rec = paired_wilcoxon(s3_rec, other_rec, n_resamples=n_resamples, seed=0)
        paired_rows.append({"comparison": f"S3_vs_{sys_id}", "metric": "fdp", **w_fdp})
        paired_rows.append({"comparison": f"S3_vs_{sys_id}", "metric": "recall", **w_rec})

    # 5. Stratifications, Alpha Sweep & Primary Hypothesis Verdict
    strat = {
        name: stratified_recall(pair_rows, cols)
        for name, cols in {
            "form": ["system", "form"],
            "bin": ["system", "form", "bin"],
            "n": ["system", "n_rows"],
            "p": ["system", "n_cols"],
            "dist": ["system", "dist"],
            "power": ["system", "form", "n_rows", "bin"],
        }.items()
    }
    alpha_sweep = run_alpha_sweep(suite, split, bench_root=bench_root, eval_root=eval_root, confirm_final=confirm_final, only=only)
    qcal = q_calibration([f for f in finding_rows if f["system"] == "S3_veridata_full"])

    s3_fdr = summary["S3_veridata_full"]["if_reported"]["fdr"]
    s2_fdr = summary["S2_veridata_nocorrection"]["if_reported"]["fdr"]
    s3_med_large = [
        bool(r["found"])
        for r in pair_rows
        if r["system"] == "S3_veridata_full" and r["detectable"] and r["testable"] and r["n_rows"] >= 300 and r["bin"] in {"medium", "large"}
    ]
    s2_med_large = [
        bool(r["found"])
        for r in pair_rows
        if r["system"] == "S2_veridata_nocorrection" and r["detectable"] and r["testable"] and r["n_rows"] >= 300 and r["bin"] in {"medium", "large"}
    ]
    s3_ml_rec = float(sum(s3_med_large) / len(s3_med_large)) if s3_med_large else 0.0
    s2_ml_rec = float(sum(s2_med_large) / len(s2_med_large)) if s2_med_large else 0.0

    verdict_ok = (
        s3_fdr is not None
        and s3_fdr <= 0.06
        and s2_fdr is not None
        and s3_fdr < s2_fdr
        and s3_ml_rec >= 0.80 * s2_ml_rec
    )
    verdict = {
        "verdict": "supported" if verdict_ok else "not_supported",
        "s3_fdr": s3_fdr,
        "s2_fdr": s2_fdr,
        "s3_med_large_n300_recall": round(s3_ml_rec, 4),
        "s2_med_large_n300_recall": round(s2_ml_rec, 4),
        "llm_baselines_included": [s for s in chosen_llm_systems if s in summary],
        "llm_status": llm_status,
    }

    out_dir = eval_root / suite / split / "e1"
    out_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "suite": suite,
        "split": split,
        "suite_hash": suite_hash(suite),
        "n_datasets": len(specs),
        "summary": summary,
        "paired_comparisons": paired_rows,
        "alpha_sweep": alpha_sweep,
        "q_calibration": qcal,
        "stratified": strat,
        "verdict": verdict,
    }
    (out_dir / "summary.json").write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")

    import pandas as pd

    pd.DataFrame(all_dataset_rows).to_csv(out_dir / "per_dataset.csv", index=False)
    pd.DataFrame(paired_rows).to_csv(out_dir / "paired_comparisons.csv", index=False)
    pd.DataFrame(alpha_sweep).to_csv(out_dir / "alpha_sweep.csv", index=False)
    pd.DataFrame(qcal).to_csv(out_dir / "q_calibration.csv", index=False)
    return payload
