"""E8 — Robustness on messy inputs, clean-vs-messy synthetic pairs, and size/width edge cases."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from veridata.benchmark.generator import Scenario, make_dataset, save_dataset
from veridata.benchmark.matcher import match_findings
from veridata.benchmark.metrics import aggregate, dataset_metrics
from veridata.benchmark.suites import suite_specs
from veridata.benchmark.truth import GroundTruth, pair_key
from veridata.config import load_config
from veridata.evaluation.systems.veridata_variants import run_phase8_variants_on_csv


def _corrupt_clean_csv(in_csv: Path, out_csv: Path, seed: int) -> None:
    """Inject realistic formatting defects (whitespace, case, missing tokens, duplicates, outliers)."""
    rng = np.random.default_rng(seed)
    df = pd.read_csv(in_csv)
    obj_cols = [c for c in df.columns if df[c].dtype == object or str(df[c].dtype) == "string"]
    num_cols = [c for c in df.columns if c not in obj_cols]

    df_str = df.copy()
    for c in obj_cols[:2]:
        mask = rng.random(len(df_str)) < 0.10
        df_str[c] = df_str[c].astype(str)
        df_str.loc[mask, c] = "  " + df_str.loc[mask, c].str.lower() + "  "

    if num_cols:
        nc = num_cols[0]
        vals = df_str[nc].astype(object)
        miss_mask = rng.random(len(df_str)) < 0.04
        vals.loc[miss_mask] = rng.choice(["N/A", "?", ""], size=int(miss_mask.sum()))
        fmt_mask = (~miss_mask) & (rng.random(len(df_str)) < 0.15)
        vals.loc[fmt_mask] = [f"${float(v):,.2f}" for v in df.loc[fmt_mask, nc]]
        df_str[nc] = vals

    # Append 3% exact duplicate rows + 1 fully empty row
    n_dup = max(1, int(0.03 * len(df_str)))
    dups = df_str.iloc[rng.choice(len(df_str), size=n_dup, replace=False)]
    df_str = pd.concat([df_str, dups], ignore_index=True)
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    df_str.to_csv(out_csv, index=False)


def _norm_col(name: str) -> str:
    return name.strip().lower().replace(" ", "_")


def run_e8(
    *,
    synthetic_dir: Path = Path("data/synthetic"),
    bench_root: Path = Path("outputs/benchmark"),
    eval_root: Path = Path("outputs/eval"),
    suite: str = "core60",
    split: str = "dev",
    confirm_final: bool = False,
) -> dict[str, Any]:
    """Evaluate full pipeline robustness on Phase 1 messy variants, corrupted core subset, and edge cases."""
    out_dir = eval_root / "e8"
    out_dir.mkdir(parents=True, exist_ok=True)

    # 1. Phase 1 messy synthetic variants vs base_truth.json
    base_truth_p = synthetic_dir / "base_truth.json"
    messy_rows: list[dict[str, Any]] = []
    if base_truth_p.exists():
        bt = json.loads(base_truth_p.read_text(encoding="utf-8"))
        planted = {pair_key(p["pair"][0], p["pair"][1]) for p in bt.get("planted_relationships", [])}
        messy_cfg_p = Path("configs/datasets/messy_synthetic.yaml")
        messy_cfg = load_config(dataset_config_path=messy_cfg_p if messy_cfg_p.exists() else None)
        variants = [
            ("clean_truth", synthetic_dir / "messy_clean_truth.csv"),
            ("messy_light", synthetic_dir / "messy_light_dataset.csv"),
            ("messy_default", synthetic_dir / "messy_dataset.csv"),
            ("messy_heavy", synthetic_dir / "messy_heavy_dataset.csv"),
        ]
        for label, csv_p in variants:
            if not csv_p.exists():
                continue
            outs = run_phase8_variants_on_csv(
                csv_p, f"e8_{label}", variants=["S3_veridata_full", "S2_veridata_nocorrection"], base_cfg=messy_cfg
            )
            for sys_id, out in outs.items():
                rep_pairs = {pair_key(_norm_col(f.col_a), _norm_col(f.col_b)) for f in out.findings}
                tp = len(rep_pairs & planted)
                fp = len(rep_pairs - planted)
                messy_rows.append(
                    {
                        "variant": label,
                        "system": sys_id,
                        "n_reported": len(rep_pairs),
                        "planted_recall": float(tp / len(planted)) if planted else None,
                        "fdp_vs_planted": float(fp / len(rep_pairs)) if rep_pairs else 0.0,
                        "runtime_s": out.runtime_s,
                    }
                )

    # 2. Corrupted core subset vs clean counterparts (up to 8 datasets with n<=1000, p<=30)
    specs = [
        s
        for s in suite_specs(suite, split, confirm_final=confirm_final)
        if (bench_root / suite / split / s.dataset_id / "data.csv").exists()
        and s.scenario.n_rows <= 1000
        and s.scenario.n_cols <= 30
    ][:8]
    clean_rows: list[dict[str, Any]] = []
    corrupt_rows: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="vd_e8_") as tmpdir:
        tmp_p = Path(tmpdir)
        for i, sp in enumerate(specs):
            ds_dir = bench_root / suite / split / sp.dataset_id
            truth = GroundTruth.load(ds_dir / "truth.json")
            scen = json.loads((ds_dir / "scenario.json").read_text(encoding="utf-8"))["scenario"]
            clean_out = run_phase8_variants_on_csv(ds_dir / "data.csv", sp.dataset_id, variants=["S3_veridata_full"])["S3_veridata_full"]
            m_c = match_findings(clean_out.findings, truth, "if_reported")
            clean_rows.append(dataset_metrics(m_c, truth, scen))

            corrupt_csv = tmp_p / f"{sp.dataset_id}_messy.csv"
            _corrupt_clean_csv(ds_dir / "data.csv", corrupt_csv, seed=500 + i)
            messy_out = run_phase8_variants_on_csv(corrupt_csv, f"{sp.dataset_id}_messy", variants=["S3_veridata_full"])["S3_veridata_full"]
            m_m = match_findings(messy_out.findings, truth, "if_reported")
            corrupt_rows.append(dataset_metrics(m_m, truth, scen))

    clean_agg = aggregate(clean_rows, n_resamples=400, seed=0) if clean_rows else {}
    corrupt_agg = aggregate(corrupt_rows, n_resamples=400, seed=0) if corrupt_rows else {}

    # 3. Small (n=40, p=10) & Wide (n=500, p=60) edge cases
    edge_rows: list[dict[str, Any]] = []
    edge_scenarios = [
        Scenario(scenario_id="edge_small_n40_p10", n_rows=40, n_cols=10, n_effects=2, effect_strength="large"),
        Scenario(scenario_id="edge_wide_n300_p40", n_rows=300, n_cols=40, n_effects=5, effect_strength="medium"),
    ]
    with tempfile.TemporaryDirectory(prefix="vd_e8_edge_") as tmpdir:
        for idx, sc in enumerate(edge_scenarios):
            df_e, truth_e, struct_e = make_dataset(sc, seed=600 + idx)
            d_e = Path(tmpdir) / sc.scenario_id
            save_dataset(d_e, df_e, truth_e, sc, struct_e)
            outs_e = run_phase8_variants_on_csv(d_e / "data.csv", sc.scenario_id, variants=["S3_veridata_full"])
            out_e = outs_e["S3_veridata_full"]
            m_e = match_findings(out_e.findings, truth_e, "if_reported")
            dm = dataset_metrics(m_e, truth_e, sc.model_dump())
            edge_rows.append(
                {
                    "scenario_id": sc.scenario_id,
                    "n_rows": sc.n_rows,
                    "n_cols": sc.n_cols,
                    "n_hypotheses": out_e.meta.get("n_hypotheses"),
                    "n_infeasible": out_e.meta.get("n_infeasible"),
                    "fdp": dm["fdp"],
                    "recall": dm["recall"],
                    "runtime_s": out_e.runtime_s,
                }
            )

    payload = {
        "messy_synthetic_variants": messy_rows,
        "core_subset_n": len(clean_rows),
        "core_clean": clean_agg,
        "core_corrupted": corrupt_agg,
        "edge_cases": edge_rows,
    }
    (out_dir / "summary.json").write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")
    pd.DataFrame(messy_rows).to_csv(out_dir / "robustness_table.csv", index=False)
    return payload
