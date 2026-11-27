"""E3 — Calibration summary (Phase 4 Type-I error, BH-vs-BY under dependence, and power)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from veridata.benchmark import calibration as cal


def run_e3(
    *,
    cal_root: Path = Path("outputs/benchmark/calibration"),
    eval_root: Path = Path("outputs/eval"),
    fast_reps: int = 200,
) -> dict[str, Any]:
    """Summarize existing Phase 4 calibration outputs (or compute fast calibration if missing)."""
    t1_p = cal_root / "type1.csv"
    rerun_p = cal_root / "type1_rerun_outlier_cell.csv"
    dep_p = cal_root / "fdr_dependence.csv"
    pow_p = cal_root / "power.csv"

    if not (t1_p.exists() and dep_p.exists() and pow_p.exists()):
        t1_df = cal.run_type1(reps=fast_reps, n_jobs=1)
        fd_df = cal.run_fdr_dependence(reps=fast_reps, n_jobs=1)
        pw_df = cal.run_power(reps=fast_reps)
        cal.write_outputs(t1_df, fd_df, pw_df, out_dir=cal_root)

    t1 = pd.read_csv(t1_p)
    dep = pd.read_csv(dep_p)
    pw = pd.read_csv(pow_p)

    t1_valid = t1[t1["size"].notna()].copy()
    t1_valid["inside"] = (t1_valid["size"] >= 0.04 - 2 * t1_valid["mc_se"]) & (
        t1_valid["size"] <= 0.06 + 2 * t1_valid["mc_se"]
    )
    t1_summary = (
        t1_valid.groupby(["relationship", "selection"], as_index=False)
        .agg(
            cells=("size", "count"),
            mean_size=("size", "mean"),
            max_size=("size", "max"),
            pct_inside=("inside", "mean"),
        )
        .to_dict("records")
    )

    dep_bh_by = dep[dep["method"].isin(["bh", "by", "bonferroni", "holm", "none"])].copy()
    dep_summary = (
        dep_bh_by.groupby(["scenario", "method"], as_index=False)
        .agg(mean_fdr=("fdr", "mean"), max_fdr=("fdr", "max"), mean_fwer=("fwer", "mean"), mean_power=("power", "mean"))
        .to_dict("records")
    )

    rerun_rows = pd.read_csv(rerun_p).to_dict("records") if rerun_p.exists() else []
    power_rows = pw.to_dict("records")

    aware_valid = t1_valid[t1_valid["selection"] == "assumption_aware"]
    naive_valid = t1_valid[t1_valid["selection"] == "naive"]

    out_dir = eval_root / "e3"
    out_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "n_type1_cells_aware": len(aware_valid),
        "aware_pct_inside_band": float(aware_valid["inside"].mean()) if len(aware_valid) else None,
        "naive_pct_inside_band": float(naive_valid["inside"].mean()) if len(naive_valid) else None,
        "aware_max_size": float(aware_valid["size"].max()) if len(aware_valid) else None,
        "naive_max_size": float(naive_valid["size"].max()) if len(naive_valid) else None,
        "type1_by_relationship": t1_summary,
        "rerun_outlier_cell": rerun_rows,
        "dependence_summary": dep_summary,
        "power_check": power_rows,
        "all_power_within_3se": bool(pw["within_3se"].all()) if "within_3se" in pw.columns and len(pw) else None,
    }
    (out_dir / "summary.json").write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")
    pd.DataFrame(t1_summary).to_csv(out_dir / "type1_summary.csv", index=False)
    pd.DataFrame(dep_summary).to_csv(out_dir / "dependence_summary.csv", index=False)
    return payload
