"""Publication-quality Phase 8 figures using VeriData's Okabe-Ito chart style (150 DPI)."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from veridata.reporting.charts.style import OKABE_ITO, apply_style, save

SHORT_LABELS = {
    "S3_veridata_full": "VeriData (S3)",
    "S2_veridata_nocorrection": "No-Corr (S2)",
    "S1a_summary_standard": "LLM-Sum (Std)",
    "S1a_summary_careful": "LLM-Sum (Care)",
    "S1b_code_standard": "LLM-Code (Std)",
    "S1b_code_careful": "LLM-Code (Care)",
    "A1_bh_only": "BH only",
    "A2_floor_only": "Floor only",
    "A3_assumption_only": "Aware only",
    "A4_naive_tests": "Naive tests",
    "A5_bonferroni": "Bonferroni",
    "A5_holm": "Holm",
    "A5_by": "BY",
    "A6_full_minus_floor": "Full - Floor",
    "A6_full_minus_gates": "Full - Gates",
    "N0_naive_raw": "Naive raw",
}


def _short(name: str) -> str:
    return SHORT_LABELS.get(name, name)


def _save_both(fig: plt.Figure, eval_fig_dir: Path, report_fig_dir: Path, filename: str) -> Path:
    p = save(fig, eval_fig_dir / filename)
    report_fig_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(p, report_fig_dir / filename)
    return p


def generate_all_figures(
    *,
    suite: str = "core60",
    split: str = "dev",
    eval_root: Path = Path("outputs/eval"),
    report_root: Path = Path("final_report"),
) -> dict[str, Path]:
    """Generate all E1-E8 figures into outputs/eval/figures and final_report/figures."""
    apply_style()
    eval_fig_dir = eval_root / "figures"
    report_fig_dir = report_root / "figures"
    out: dict[str, Path] = {}

    e1_dir = eval_root / suite / split / "e1"
    e1_p = e1_dir / "summary.json"
    if e1_p.exists():
        e1 = json.loads(e1_p.read_text(encoding="utf-8"))
        summary = e1.get("summary", {})
        systems = list(summary.keys())

        # Fig 1a: FDR & Recall bars with 95% CIs
        if systems:
            fig, axes = plt.subplots(1, 2, figsize=(9.5, 4.2))
            x = np.arange(len(systems))
            for ax, metric, title in [
                (axes[0], "fdr", "False Discovery Rate (mean FDP)"),
                (axes[1], "recall", "Recall (testable truths)"),
            ]:
                vals = [100.0 * (summary[s]["if_reported"].get(metric) or 0.0) for s in systems]
                lo = [max(0.0, v - 100.0 * (summary[s]["if_reported"].get(f"{metric}_ci_low") or (v / 100.0))) for v, s in zip(vals, systems)]
                hi = [max(0.0, 100.0 * (summary[s]["if_reported"].get(f"{metric}_ci_high") or (v / 100.0)) - v) for v, s in zip(vals, systems)]
                colors = [OKABE_ITO[i % len(OKABE_ITO)] for i in range(len(systems))]
                ax.bar(x, vals, yerr=[lo, hi], capsize=4, color=colors, edgecolor="#333333", linewidth=0.6)
                if metric == "fdr":
                    ax.axhline(5.0, color="#D55E00", linestyle="--", linewidth=1.2, label="5% target")
                    ax.legend(frameon=False)
                ax.set_xticks(x)
                ax.set_xticklabels([_short(s) for s in systems], rotation=20, ha="right")
                ax.set_ylabel(f"{title} (%)")
                ax.set_title(title)
                ax.set_ylim(0, 105)
            fig.suptitle(f"E1 Main Benchmark ({suite}/{split}, n={e1.get('n_datasets')} datasets)")
            fig.tight_layout()
            out["e1_fdr_recall_bars"] = _save_both(fig, eval_fig_dir, report_fig_dir, "fig_e1_fdr_recall_bars.png")

        # Fig 1b: Recall vs effect bin
        strat_bin = e1.get("stratified", {}).get("bin", [])
        if strat_bin:
            df_b = pd.DataFrame(strat_bin)
            bins = [b for b in ("small", "medium", "large") if b in set(df_b["bin"])]
            if bins:
                fig, ax = plt.subplots(figsize=(7.0, 4.2))
                for idx, sys_id in enumerate(systems):
                    sub = df_b[df_b["system"] == sys_id]
                    ys = [100.0 * float(sub[sub["bin"] == b]["recall"].mean()) if len(sub[sub["bin"] == b]) else np.nan for b in bins]
                    ax.plot(bins, ys, marker="o", linewidth=2.0, label=_short(sys_id), color=OKABE_ITO[idx % len(OKABE_ITO)])
                ax.set_ylabel("Recall (%)")
                ax.set_xlabel("Planted effect strength")
                ax.set_title(f"Recall by Effect Strength ({suite}/{split})")
                ax.set_ylim(0, 105)
                ax.legend(frameon=False)
                fig.tight_layout()
                out["e1_recall_by_effect"] = _save_both(fig, eval_fig_dir, report_fig_dir, "fig_e1_recall_by_effect.png")

        # Fig 1c & 1d: FDR vs p and FDR vs n
        per_ds_p = e1_dir / "per_dataset.csv"
        if per_ds_p.exists():
            df_ds = pd.read_csv(per_ds_p)
            df_ds = df_ds[df_ds["direction_mode"] == "if_reported"]
            for col_x, xlabel, fname in [
                ("n_cols", "Number of columns (p)", "fig_e1_fdr_vs_p.png"),
                ("n_rows", "Sample size (n)", "fig_e1_fdr_vs_n.png"),
            ]:
                fig, ax = plt.subplots(figsize=(7.0, 4.2))
                for idx, sys_id in enumerate(systems):
                    sub = df_ds[df_ds["system"] == sys_id].groupby(col_x, as_index=False)["fdp"].mean().sort_values(col_x)
                    if len(sub):
                        ax.plot(sub[col_x].astype(str), 100.0 * sub["fdp"], marker="o", linewidth=2.0, label=_short(sys_id), color=OKABE_ITO[idx % len(OKABE_ITO)])
                ax.axhline(5.0, color="#D55E00", linestyle="--", linewidth=1.1, label="5% target")
                ax.set_xlabel(xlabel)
                ax.set_ylabel("FDR (mean FDP, %)")
                ax.set_title(f"FDR vs {xlabel} ({suite}/{split})")
                ax.set_ylim(0, 105)
                ax.legend(frameon=False)
                fig.tight_layout()
                out[fname.replace(".png", "")] = _save_both(fig, eval_fig_dir, report_fig_dir, fname)

            # Fig 1e: False positives on zero-effect datasets
            zero_df = df_ds[df_ds["zero_planted"] == True]
            if len(zero_df):
                fig, ax = plt.subplots(figsize=(7.2, 4.2))
                data_fp = [zero_df[zero_df["system"] == s]["fp"].to_numpy(dtype=float) for s in systems]
                ax.boxplot(data_fp, tick_labels=[_short(s) for s in systems], showfliers=True)
                for idx, vals in enumerate(data_fp, start=1):
                    jitter = np.linspace(-0.12, 0.12, len(vals)) if len(vals) > 1 else np.array([0.0])
                    ax.scatter(np.full(len(vals), idx) + jitter, vals, alpha=0.7, s=22, color=OKABE_ITO[(idx - 1) % len(OKABE_ITO)])
                ax.set_ylabel("False positives per null dataset")
                ax.set_title(f"Null-Dataset False Positives ({suite}/{split})")
                fig.tight_layout()
                out["e1_null_fp"] = _save_both(fig, eval_fig_dir, report_fig_dir, "fig_e1_null_fp.png")

        # Fig 1f: Alpha trade-off curve
        sweep = e1.get("alpha_sweep", [])
        if sweep:
            df_sw = pd.DataFrame(sweep)
            fig, ax = plt.subplots(figsize=(6.8, 4.4))
            ax.plot(100.0 * df_sw["fdr"], 100.0 * df_sw["recall"], marker="o", linewidth=2.2, color=OKABE_ITO[0], label="VeriData (alpha 0.01..0.20)")
            for _, r in df_sw.iterrows():
                ax.annotate(f"a={r['alpha']:.2f}", (100.0 * r["fdr"] + 0.6, 100.0 * r["recall"] - 1.5), fontsize=8)
            for idx, sys_id in enumerate(systems):
                if sys_id == "S3_veridata_full":
                    continue
                p_m = summary[sys_id]["if_reported"]
                ax.scatter(
                    100.0 * (p_m.get("fdr") or 0.0),
                    100.0 * (p_m.get("recall") or 0.0),
                    s=70,
                    label=_short(sys_id),
                    color=OKABE_ITO[(idx + 1) % len(OKABE_ITO)],
                )
            ax.axvline(5.0, color="#999999", linestyle="--", linewidth=1.0)
            ax.set_xlabel("FDR (%)")
            ax.set_ylabel("Recall (%)")
            ax.set_title(f"Recall-FDR Trade-off Curve ({suite}/{split})")
            ax.legend(frameon=False, fontsize=8)
            fig.tight_layout()
            out["e1_alpha_tradeoff"] = _save_both(fig, eval_fig_dir, report_fig_dir, "fig_e1_alpha_tradeoff.png")

        # Fig 1g: q-value calibration
        qcal = [r for r in e1.get("q_calibration", []) if r.get("n", 0) > 0]
        if qcal:
            df_q = pd.DataFrame(qcal)
            fig, ax = plt.subplots(figsize=(6.8, 4.2))
            labels_q = [f"({r['q_low']:.3f}, {r['q_high']:.3f}]" for r in qcal]
            ax.bar(np.arange(len(qcal)), 100.0 * df_q["false_fraction"], color=OKABE_ITO[0], edgecolor="#333333", linewidth=0.6)
            ax.plot(np.arange(len(qcal)), 100.0 * df_q["q_high"], color="#D55E00", marker="o", linestyle="--", label="Upper q threshold")
            ax.set_xticks(np.arange(len(qcal)))
            ax.set_xticklabels(labels_q, rotation=20, ha="right")
            ax.set_ylabel("Empirical false fraction (%)")
            ax.set_title(f"q-Value Calibration for VeriData S3 ({suite}/{split})")
            ax.legend(frameon=False)
            fig.tight_layout()
            out["e1_q_calibration"] = _save_both(fig, eval_fig_dir, report_fig_dir, "fig_e1_q_calibration.png")

    # Fig 2: E2 Ablation scatter / bars
    e2_p = eval_root / suite / split / "e2" / "summary.json"
    if e2_p.exists():
        e2 = json.loads(e2_p.read_text(encoding="utf-8"))
        df_a = pd.DataFrame(e2.get("ablation_table", []))
        if len(df_a):
            fig, ax = plt.subplots(figsize=(8.2, 4.6))
            y_pos = np.arange(len(df_a))
            ax.barh(y_pos - 0.18, 100.0 * df_a["fdr"].fillna(0.0), height=0.35, color=OKABE_ITO[3], label="FDR (%)")
            ax.barh(y_pos + 0.18, 100.0 * df_a["recall"].fillna(0.0), height=0.35, color=OKABE_ITO[0], label="Recall (%)")
            ax.axvline(5.0, color="#333333", linestyle="--", linewidth=1.0, label="5% FDR target")
            ax.set_yticks(y_pos)
            ax.set_yticklabels([_short(s) for s in df_a["system"]])
            ax.invert_yaxis()
            ax.set_xlabel("Percentage (%)")
            ax.set_title(f"E2 Component Ablation ({suite}/{split})")
            ax.legend(frameon=False)
            fig.tight_layout()
            out["e2_ablation"] = _save_both(fig, eval_fig_dir, report_fig_dir, "fig_e2_ablation.png")

    # Fig 3: E3 Dependence FDR
    e3_dep = eval_root / "e3" / "dependence_summary.csv"
    if e3_dep.exists():
        df_d = pd.read_csv(e3_dep)
        if len(df_d):
            fig, ax = plt.subplots(figsize=(8.0, 4.4))
            methods = [m for m in ("bh", "by", "bonferroni", "holm", "none") if m in set(df_d["method"])]
            scenarios = sorted(df_d["scenario"].unique())
            x = np.arange(len(scenarios))
            w = 0.15
            for idx, m in enumerate(methods):
                sub = df_d[df_d["method"] == m].set_index("scenario")
                vals = [100.0 * float(sub.loc[sc, "mean_fdr"]) if sc in sub.index else 0.0 for sc in scenarios]
                ax.bar(x + (idx - len(methods) / 2) * w, vals, width=w, label=m.upper(), color=OKABE_ITO[idx % len(OKABE_ITO)])
            ax.axhline(5.0, color="#D55E00", linestyle="--", linewidth=1.1)
            ax.set_xticks(x)
            ax.set_xticklabels(scenarios, rotation=20, ha="right")
            ax.set_ylabel("Mean Empirical FDR (%)")
            ax.set_title("E3 FDR Under Correlated Dependence")
            ax.legend(frameon=False, ncol=3)
            fig.tight_layout()
            out["e3_dependence_fdr"] = _save_both(fig, eval_fig_dir, report_fig_dir, "fig_e3_dependence_fdr.png")

    # Fig 5: E5 Real datasets reliability
    e5_p = eval_root / "e5" / "summary.json"
    if e5_p.exists():
        e5 = json.loads(e5_p.read_text(encoding="utf-8"))
        df_r = pd.DataFrame(e5.get("table", []))
        df_r = df_r[df_r["system"].isin(["S3_veridata_full", "S2_veridata_nocorrection"])]
        if len(df_r):
            datasets = list(dict.fromkeys(df_r["dataset"]))
            x = np.arange(len(datasets))
            fig, axes = plt.subplots(1, 2, figsize=(9.2, 4.2))
            for idx, sys_id in enumerate(("S3_veridata_full", "S2_veridata_nocorrection")):
                sub = df_r[df_r["system"] == sys_id].set_index("dataset")
                perm_vals = [float(sub.loc[d, "perm_mean_fp"]) if d in sub.index else 0.0 for d in datasets]
                rep_vals = [100.0 * float(sub.loc[d, "split_strict_rep"] or 0.0) if d in sub.index else 0.0 for d in datasets]
                axes[0].bar(x + (idx - 0.5) * 0.35, perm_vals, width=0.35, label=_short(sys_id), color=OKABE_ITO[idx])
                axes[1].bar(x + (idx - 0.5) * 0.35, rep_vals, width=0.35, label=_short(sys_id), color=OKABE_ITO[idx])
            axes[0].set_title("Mean FP on Permuted Null Columns")
            axes[0].set_ylabel("False discoveries (count)")
            axes[1].set_title("Split-Half Strict Replication Rate")
            axes[1].set_ylabel("Replication (%)")
            axes[1].set_ylim(0, 105)
            for ax in axes:
                ax.set_xticks(x)
                ax.set_xticklabels(datasets, rotation=20, ha="right")
                ax.legend(frameon=False)
            fig.tight_layout()
            out["e5_real_reliability"] = _save_both(fig, eval_fig_dir, report_fig_dir, "fig_e5_real_reliability.png")

    return out
