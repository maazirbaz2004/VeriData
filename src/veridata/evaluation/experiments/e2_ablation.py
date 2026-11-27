"""E2 — Component ablation study (S3, S2, A1-A6, N0) on smoke/core60."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
from joblib import Parallel, delayed

from veridata.benchmark.matcher import match_findings
from veridata.benchmark.metrics import aggregate, dataset_metrics
from veridata.benchmark.runner import generate_suite
from veridata.benchmark.suites import suite_specs
from veridata.benchmark.truth import GroundTruth, SystemOutput
from veridata.evaluation.systems.veridata_variants import (
    DEFAULT_PHASE8_VARIANT_IDS,
    run_phase8_variants_on_csv,
)


def _cache_path(eval_root: Path, suite: str, split: str, sys_id: str, ds_id: str) -> Path:
    return eval_root / suite / split / "systems" / sys_id / f"{ds_id}.json"


def _run_ds_missing(csv_path: Path, ds_id: str, missing: list[str], eval_root: Path, suite: str, split: str) -> dict[str, SystemOutput]:
    outs = run_phase8_variants_on_csv(csv_path, ds_id, variants=missing)
    for sys_id, out in outs.items():
        p = _cache_path(eval_root, suite, split, sys_id, ds_id)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(out.model_dump_json(indent=1) + "\n", encoding="utf-8")
    return outs


def run_e2(
    *,
    suite: str = "core60",
    split: str = "dev",
    bench_root: Path = Path("outputs/benchmark"),
    eval_root: Path = Path("outputs/eval"),
    systems: list[str] | None = None,
    n_jobs: int = 2,
    confirm_final: bool = False,
    only: list[str] | None = None,
    n_resamples: int = 2000,
) -> dict[str, Any]:
    """Run ablation variants and compute marginal FDR/recall contributions vs S3."""
    chosen = systems or list(DEFAULT_PHASE8_VARIANT_IDS)
    specs = [s for s in suite_specs(suite, split, confirm_final=confirm_final) if only is None or s.dataset_id in only]
    base = bench_root / suite / split

    missing_data = [s.dataset_id for s in specs if not (base / s.dataset_id / "data.csv").exists()]
    if missing_data:
        generate_suite(suite, split, out_root=bench_root, n_jobs=n_jobs, confirm_final=confirm_final, only=missing_data)

    by_sys: dict[str, dict[str, SystemOutput]] = {s: {} for s in chosen}
    todo: list[tuple[str, Path, list[str]]] = []
    for sp in specs:
        need = []
        for sys_id in chosen:
            cp = _cache_path(eval_root, suite, split, sys_id, sp.dataset_id)
            if cp.exists():
                try:
                    out = SystemOutput.model_validate_json(cp.read_text(encoding="utf-8"))
                    if not out.error:
                        by_sys[sys_id][sp.dataset_id] = out
                        continue
                except (OSError, ValueError) as exc:
                    need_msg = f"Cache miss for {cp}: {exc}"
                    _ = need_msg
            need.append(sys_id)
        if need:
            todo.append((sp.dataset_id, base / sp.dataset_id / "data.csv", need))

    if todo:
        res_list = Parallel(n_jobs=n_jobs)(
            delayed(_run_ds_missing)(csv_p, ds_id, need, eval_root, suite, split)
            for ds_id, csv_p, need in todo
        )
        for (ds_id, _, _), outs in zip(todo, res_list):
            for sys_id, out in outs.items():
                by_sys[sys_id][ds_id] = out

    truths = {s.dataset_id: GroundTruth.load(base / s.dataset_id / "truth.json") for s in specs}
    scen_map = {
        s.dataset_id: json.loads((base / s.dataset_id / "scenario.json").read_text(encoding="utf-8"))["scenario"]
        for s in specs
    }

    summary: dict[str, Any] = {}
    strata_rows: list[dict[str, Any]] = []
    for sys_id in chosen:
        ds_rows = []
        for sp in specs:
            m = match_findings(by_sys[sys_id][sp.dataset_id].findings, truths[sp.dataset_id], "if_reported")
            row = dataset_metrics(m, truths[sp.dataset_id], scen_map[sp.dataset_id])
            row["system"] = sys_id
            ds_rows.append(row)
        summary[sys_id] = aggregate(ds_rows, n_resamples=n_resamples, seed=0)

        # Targeted strata: n==5000 (effect floor) & non-normal (assumption selection)
        n5000 = [r for r in ds_rows if r["n_rows"] == 5000]
        skewed = [r for r in ds_rows if r["dist"] in {"lognormal", "t3", "zero_inflated"}]
        if n5000:
            s5 = aggregate(n5000, n_resamples=400, seed=0)
            strata_rows.append({"system": sys_id, "stratum": "n_5000", "fdr": s5["fdr"], "recall": s5["recall"], "mean_reported": s5["mean_reported"]})
        if skewed:
            ss = aggregate(skewed, n_resamples=400, seed=0)
            strata_rows.append({"system": sys_id, "stratum": "non_normal", "fdr": ss["fdr"], "recall": ss["recall"], "mean_reported": ss["mean_reported"]})

    ref = summary.get("S3_veridata_full", {})
    table_rows = []
    for sys_id in chosen:
        s = summary[sys_id]
        table_rows.append(
            {
                "system": sys_id,
                "fdr": s["fdr"],
                "fdr_ci_low": s.get("fdr_ci_low"),
                "fdr_ci_high": s.get("fdr_ci_high"),
                "recall": s["recall"],
                "recall_ci_low": s.get("recall_ci_low"),
                "recall_ci_high": s.get("recall_ci_high"),
                "precision": s["precision"],
                "fwer_null": s["fwer_null"],
                "mean_reported": s["mean_reported"],
                "mean_fp": s["mean_fp"],
                "delta_fdr_vs_s3": (s["fdr"] - ref["fdr"]) if (s["fdr"] is not None and ref.get("fdr") is not None) else None,
                "delta_recall_vs_s3": (s["recall"] - ref["recall"]) if (s["recall"] is not None and ref.get("recall") is not None) else None,
            }
        )

    out_dir = eval_root / suite / split / "e2"
    out_dir.mkdir(parents=True, exist_ok=True)
    payload = {"suite": suite, "split": split, "ablation_table": table_rows, "targeted_strata": strata_rows}
    (out_dir / "summary.json").write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")
    pd.DataFrame(table_rows).to_csv(out_dir / "ablation_table.csv", index=False)
    pd.DataFrame(strata_rows).to_csv(out_dir / "targeted_strata.csv", index=False)
    return payload
