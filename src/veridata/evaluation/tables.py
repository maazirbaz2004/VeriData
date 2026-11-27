"""Auto-generated Markdown, CSV, and LaTeX tables from cached Phase 8 evaluation outputs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd


def _fmt_pct(val: float | None) -> str:
    return "–" if val is None else f"{100.0 * val:.1f}%"


def _fmt_ci(s: dict[str, Any], key: str, pct: bool = True) -> str:
    val = s.get(key)
    lo = s.get(f"{key}_ci_low")
    hi = s.get(f"{key}_ci_high")
    if val is None:
        return "–"
    fmt = _fmt_pct if pct else (lambda x: f"{x:.3f}" if x is not None else "–")
    if lo is None or hi is None:
        return fmt(val)
    return f"{fmt(val)} [{fmt(lo)}, {fmt(hi)}]"


def _to_latex(df: pd.DataFrame, caption: str, label: str) -> str:
    cols = " & ".join(str(c).replace("_", "\\_") for c in df.columns) + " \\\\"
    align = "l" + "r" * (len(df.columns) - 1)
    rows = []
    for _, r in df.iterrows():
        cells = [str(v).replace("_", "\\_").replace("%", "\\%") for v in r.tolist()]
        rows.append(" & ".join(cells) + " \\\\")
    return "\n".join(
        [
            "\\begin{table}[htbp]",
            "\\centering",
            f"\\caption{{{caption}}}",
            f"\\label{{{label}}}",
            f"\\begin{{tabular}}{{{align}}}",
            "\\toprule",
            cols,
            "\\midrule",
            *rows,
            "\\bottomrule",
            "\\end{tabular}",
            "\\end{table}",
            "",
        ]
    )


def _write_table_bundle(out_dir: Path, stem: str, df: pd.DataFrame, caption: str) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    md_p = out_dir / f"{stem}.md"
    csv_p = out_dir / f"{stem}.csv"
    tex_p = out_dir / f"{stem}.tex"
    df.to_csv(csv_p, index=False)
    headers = "| " + " | ".join(str(c) for c in df.columns) + " |"
    sep = "| " + " | ".join("---" for _ in df.columns) + " |"
    lines = [headers, sep]
    for _, row in df.iterrows():
        lines.append("| " + " | ".join(str(v) for v in row.tolist()) + " |")
    md_p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    tex_p.write_text(_to_latex(df, caption, f"tab:{stem}"), encoding="utf-8")
    return md_p


def generate_all_tables(
    *,
    suite: str = "core60",
    split: str = "dev",
    eval_root: Path = Path("outputs/eval"),
) -> dict[str, Path]:
    """Build all evaluation tables from cached E1-E8 JSON outputs."""
    tables_dir = eval_root / "tables"
    generated: dict[str, Path] = {}

    # E1 Main Table
    e1_p = eval_root / suite / split / "e1" / "summary.json"
    if e1_p.exists():
        e1 = json.loads(e1_p.read_text(encoding="utf-8"))
        rows = []
        for sys_id, rec in e1.get("summary", {}).items():
            p = rec["if_reported"]
            rows.append(
                {
                    "System": sys_id,
                    "Datasets": rec.get("n_datasets_evaluated", p.get("n_datasets")),
                    "FDR [95% CI]": _fmt_ci(p, "fdr"),
                    "Recall [95% CI]": _fmt_ci(p, "recall"),
                    "Precision [95% CI]": _fmt_ci(p, "precision"),
                    "FWER (Null)": _fmt_ci(p, "fwer_null"),
                    "Mean Reported": f"{p['mean_reported']:.2f}" if p.get("mean_reported") is not None else "–",
                    "Mean FP": f"{p['mean_fp']:.2f}" if p.get("mean_fp") is not None else "–",
                }
            )
        if rows:
            generated["e1_main"] = _write_table_bundle(
                tables_dir, "table_e1_main", pd.DataFrame(rows), f"Main benchmark results ({suite}/{split})."
            )

    # E2 Ablation Table
    e2_p = eval_root / suite / split / "e2" / "summary.json"
    if e2_p.exists():
        e2 = json.loads(e2_p.read_text(encoding="utf-8"))
        rows = []
        for r in e2.get("ablation_table", []):
            rows.append(
                {
                    "System": r["system"],
                    "FDR [95% CI]": _fmt_ci(r, "fdr"),
                    "Recall [95% CI]": _fmt_ci(r, "recall"),
                    "Precision": _fmt_pct(r.get("precision")),
                    "FWER (Null)": _fmt_pct(r.get("fwer_null")),
                    "Mean FP": f"{r['mean_fp']:.2f}" if r.get("mean_fp") is not None else "–",
                    "dFDR vs S3": f"{100 * r['delta_fdr_vs_s3']:+.1f}pp" if r.get("delta_fdr_vs_s3") is not None else "–",
                    "dRecall vs S3": f"{100 * r['delta_recall_vs_s3']:+.1f}pp" if r.get("delta_recall_vs_s3") is not None else "–",
                }
            )
        if rows:
            generated["e2_ablation"] = _write_table_bundle(
                tables_dir, "table_e2_ablation", pd.DataFrame(rows), f"Component ablation results ({suite}/{split})."
            )

    # E3 Calibration Table
    e3_p = eval_root / "e3" / "summary.json"
    if e3_p.exists():
        e3 = json.loads(e3_p.read_text(encoding="utf-8"))
        rows = [
            {
                "Relationship": r["relationship"],
                "Selection": r["selection"],
                "Cells": int(r["cells"]),
                "Mean Size": f"{r['mean_size']:.4f}",
                "Max Size": f"{r['max_size']:.4f}",
                "Inside Band": _fmt_pct(r["pct_inside"]),
            }
            for r in e3.get("type1_by_relationship", [])
        ]
        if rows:
            generated["e3_calibration"] = _write_table_bundle(
                tables_dir, "table_e3_calibration", pd.DataFrame(rows), "Type-I error calibration across relationships."
            )

    # E4 Number Verification Table
    e4_p = eval_root / "e4" / "summary.json"
    if e4_p.exists():
        e4 = json.loads(e4_p.read_text(encoding="utf-8"))
        rows = [
            {
                "System": "VeriData (Phase 5 Verifier)",
                "Items Checked": e4.get("veridata_n_narrations_checked", 0),
                "Verified Rate": _fmt_pct(e4.get("veridata_phase5_verified_rate")),
                "Fabricated Rate": _fmt_pct(1.0 - e4["veridata_phase5_verified_rate"]) if e4.get("veridata_phase5_verified_rate") is not None else "–",
                "Hallucinated Cols": 0,
            },
            {
                "System": "VeriData (Independent Recompute)",
                "Items Checked": e4.get("veridata_n_findings_recomputed", 0),
                "Verified Rate": _fmt_pct(e4.get("veridata_independent_verified_rate")),
                "Fabricated Rate": _fmt_pct(1.0 - e4["veridata_independent_verified_rate"]) if e4.get("veridata_independent_verified_rate") is not None else "–",
                "Hallucinated Cols": 0,
            },
        ]
        for sys_name, info in e4.get("llm_baselines", {}).items():
            rows.append(
                {
                    "System": sys_name,
                    "Items Checked": info.get("checkable_claims", 0),
                    "Verified Rate": _fmt_pct(info.get("verified_rate")),
                    "Fabricated Rate": _fmt_pct(info.get("fabricated_rate")),
                    "Hallucinated Cols": info.get("hallucinated_column_count", 0),
                }
            )
        generated["e4_numbers"] = _write_table_bundle(
            tables_dir, "table_e4_numbers", pd.DataFrame(rows), "Number correctness and independent verification."
        )

    # E5 Real Datasets Table
    e5_p = eval_root / "e5" / "summary.json"
    if e5_p.exists():
        e5 = json.loads(e5_p.read_text(encoding="utf-8"))
        rows = [
            {
                "Dataset": r["dataset"],
                "System": r["system"],
                "Reported": f"{r['n_reported']:.1f}" if isinstance(r["n_reported"], float) else r["n_reported"],
                "Ref Recovery": f"{_fmt_pct(r['ref_recovery_rate'])} ({r['ref_hits']})",
                "Permuted Null FP": f"{r['perm_mean_fp']:.2f}" if r.get("perm_mean_fp") is not None else "–",
                "Noise Col FP": f"{r['noise_mean_fp']:.2f}" if r.get("noise_mean_fp") is not None else "–",
                "Split-Half (Strict)": _fmt_pct(r.get("split_strict_rep")),
                "Bootstrap Jaccard": f"{r['bootstrap_jaccard']:.3f}" if r.get("bootstrap_jaccard") is not None else "–",
            }
            for r in e5.get("table", [])
        ]
        if rows:
            generated["e5_real"] = _write_table_bundle(
                tables_dir, "table_e5_real", pd.DataFrame(rows), "Real-dataset reliability and recovery summary."
            )

    # E6 Selection Table
    e6_p = eval_root / suite / split / "e6" / "summary.json"
    if e6_p.exists():
        e6 = json.loads(e6_p.read_text(encoding="utf-8"))
        rows = [
            {
                "Relationship": r["relationship"],
                "Hypotheses": int(r["n"]),
                "VeriData Aware": _fmt_pct(r["aware_acc"]),
                "Always Parametric": _fmt_pct(r["naive_acc"]),
                "Always Nonparametric": _fmt_pct(r["nonparam_acc"]),
            }
            for r in e6.get("by_relationship", [])
        ]
        if rows:
            generated["e6_selection"] = _write_table_bundle(
                tables_dir, "table_e6_selection", pd.DataFrame(rows), "Test-selection oracle accuracy."
            )

    # E7 Chat Table
    e7_p = eval_root / "e7" / "summary.json"
    if e7_p.exists():
        e7 = json.loads(e7_p.read_text(encoding="utf-8"))
        rows = [
            {"Metric": "Single-turn Intent Accuracy", "Value": _fmt_pct(e7.get("single_intent_accuracy"))},
            {"Metric": "Single-turn Argument Accuracy", "Value": _fmt_pct(e7.get("single_arg_accuracy"))},
            {"Metric": "Multi-turn Intent Accuracy", "Value": _fmt_pct(e7.get("multi_intent_accuracy"))},
            {"Metric": "Independent Statistical Answer Correctness", "Value": _fmt_pct(e7.get("answer_numeric_correctness"))},
            {"Metric": "Verified-Number Rate", "Value": _fmt_pct(e7.get("verified_number_rate"))},
            {"Metric": "Causal-Language Violations", "Value": str(e7.get("causal_language_violations", 0))},
            {"Metric": "Out-of-Scope & Injection Refusal Rate", "Value": _fmt_pct(e7.get("out_of_scope_refusal_rate"))},
            {"Metric": "Ambiguous Query Clarification Rate", "Value": _fmt_pct(e7.get("clarification_rate"))},
            {"Metric": "Duplicate-Test Suppression Rate", "Value": _fmt_pct(e7.get("duplicate_suppression_rate"))},
            {"Metric": "Follow-up Executability Rate", "Value": _fmt_pct(e7.get("followup_executability_rate"))},
            {"Metric": "Mean Turn Latency (ms)", "Value": f"{e7['mean_latency_ms']:.1f}" if e7.get("mean_latency_ms") is not None else "–"},
        ]
        generated["e7_chat"] = _write_table_bundle(
            tables_dir, "table_e7_chat", pd.DataFrame(rows), "Chat evaluation summary across single- and multi-turn benchmarks."
        )

    # E8 Robustness Table
    e8_p = eval_root / "e8" / "summary.json"
    if e8_p.exists():
        e8 = json.loads(e8_p.read_text(encoding="utf-8"))
        rows = [
            {
                "Variant": r["variant"],
                "System": r["system"],
                "Reported": r["n_reported"],
                "Planted Recall": _fmt_pct(r.get("planted_recall")),
                "FDP vs Planted": _fmt_pct(r.get("fdp_vs_planted")),
                "Runtime (s)": f"{r['runtime_s']:.2f}",
            }
            for r in e8.get("messy_synthetic_variants", [])
        ]
        if rows:
            generated["e8_robustness"] = _write_table_bundle(
                tables_dir, "table_e8_robustness", pd.DataFrame(rows), "Pipeline robustness on messy synthetic datasets."
            )

    return generated
