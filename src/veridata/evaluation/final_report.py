"""Final paper/report assembly directly from cached Phase 8 numbers (no stale hand-typed stats)."""

from __future__ import annotations

import base64
import json
import re
from pathlib import Path
from typing import Any

import markdown


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _pct(val: float | None) -> str:
    return "N/A" if val is None else f"{100.0 * val:.1f}%"


def _embed_figures_html(html_body: str, base_dir: Path) -> str:
    def _repl(match: re.Match[str]) -> str:
        alt, src = match.group(1), match.group(2)
        p = (base_dir / src).resolve()
        if not p.exists():
            return match.group(0)
        b64 = base64.b64encode(p.read_bytes()).decode("ascii")
        return f'<img alt="{alt}" src="data:image/png;base64,{b64}" style="max-width:100%;height:auto;" />'

    return re.sub(r'<img[^>]+alt="([^"]*)"[^>]+src="([^"]+)"[^>]*/?>', _repl, html_body)


def build_final_report(
    *,
    suite: str = "core60",
    split: str = "dev",
    eval_root: Path = Path("outputs/eval"),
    report_root: Path = Path("final_report"),
) -> dict[str, Path]:
    """Assemble final_report/numbers.json, FINAL_REPORT.md, and self-contained FINAL_REPORT.html."""
    report_root.mkdir(parents=True, exist_ok=True)
    e1 = _load_json(eval_root / suite / split / "e1" / "summary.json")
    e2 = _load_json(eval_root / suite / split / "e2" / "summary.json")
    e3 = _load_json(eval_root / "e3" / "summary.json")
    e4 = _load_json(eval_root / "e4" / "summary.json")
    e5 = _load_json(eval_root / "e5" / "summary.json")
    e6 = _load_json(eval_root / suite / split / "e6" / "summary.json")
    e7 = _load_json(eval_root / "e7" / "summary.json")
    e8 = _load_json(eval_root / "e8" / "summary.json")
    manifest = _load_json(eval_root / "run_manifest.json")

    numbers = {
        "suite": suite,
        "split": split,
        "manifest": manifest,
        "e1": e1.get("summary", {}),
        "e1_verdict": e1.get("verdict", {}),
        "e1_paired": e1.get("paired_comparisons", []),
        "e2_ablation": e2.get("ablation_table", []),
        "e3": e3,
        "e4": e4,
        "e5_table": e5.get("table", []),
        "e6": e6,
        "e7": e7,
        "e8": e8,
    }
    numbers_p = report_root / "numbers.json"
    numbers_p.write_text(json.dumps(numbers, indent=2, default=str) + "\n", encoding="utf-8")

    s3 = e1.get("summary", {}).get("S3_veridata_full", {}).get("if_reported", {})
    s2 = e1.get("summary", {}).get("S2_veridata_nocorrection", {}).get("if_reported", {})
    verdict = e1.get("verdict", {})
    llm_included = verdict.get("llm_baselines_included", [])
    split_banner = (
        "**FINAL TEST-SPLIT EVALUATION (Protocol Frozen)**"
        if split == "test"
        else f"**DEVELOPMENT-SPLIT PRELIMINARY REPORT (`{suite}/{split}` — protocol still DRAFT; live Gemini/test-split runs pending API key)**"
    )

    def _read_table(name: str) -> str:
        tp = eval_root / "tables" / name
        return tp.read_text(encoding="utf-8").strip() if tp.exists() else "_Table not generated yet._"

    md_parts = [
        "# VeriData: Validated Agentic Data Science with Controlled False Discovery Rate",
        "",
        f"> {split_banner}",
        "",
        "## Abstract",
        "",
        (
            "Automated data science agents and LLM-only analysts routinely evaluate hundreds of candidate "
            "relationships and report chance correlations as discoveries. **VeriData** addresses this by "
            "combining deterministic Phase 1 cleaning, outcome-blind hypothesis enumeration (no peeking), "
            "a fixed assumption-aware statistical tool library, session-wide Benjamini-Hochberg (BH) "
            "False Discovery Rate (FDR) control with a practical effect-size floor, and strict "
            "FactRegistry-backed number verification. "
            f"On the `{suite}/{split}` planted-truth benchmark (`n={e1.get('n_datasets', 'N/A')}` datasets), "
            f"full VeriData (`S3`) achieved an FDR of **{_pct(s3.get('fdr'))}** "
            f"(95% CI [{_pct(s3.get('fdr_ci_low'))}, {_pct(s3.get('fdr_ci_high'))}]) with "
            f"**{_pct(s3.get('recall'))}** overall testable recall "
            f"(and **{_pct(verdict.get('s3_med_large_n300_recall'))}** recall on medium/large effects at `n >= 300`), "
            f"compared to **{_pct(s2.get('fdr'))}** FDR without correction (`S2`). "
            f"Machine-verified number correctness reached **{_pct(e4.get('veridata_phase5_verified_rate'))}** "
            f"on Phase 5 narration and **{_pct(e4.get('veridata_independent_verified_rate'))}** under independent recomputation."
        ),
        "",
        "---",
        "",
        "## 1. Introduction",
        "",
        (
            "Modern LLM coding assistants can load a CSV, compute correlations, and write persuasive summaries in seconds. "
            "However, exploratory analysis over `p` columns tests `p(p-1)/2` pairs simultaneously. Without multiple-testing "
            "correction, assumption-aware test selection, and programmatic number grounding, both naive scripts and LLM analysts "
            "suffer severe false-discovery inflation and occasional numeric hallucinations."
        ),
        "",
        "**Contributions:**",
        "1. **Zero-peeking hypothesis family & session ledger:** Hypotheses are enumerated from univariate metadata only; every test that produces a p-value in batch or chat enters a unified append-only BH ledger.",
        "2. **Deterministic statistical tool library:** Fixed implementations of Welch's *t*, Mann-Whitney *U*, Welch ANOVA, Kruskal-Wallis, Pearson *r*, Spearman *rho*, Pearson chi-square, Fisher's exact, and Monte Carlo chi-square with bias-corrected effect sizes and bootstrap CIs.",
        "3. **FactRegistry & machine verification:** Every numeric token in reports and chat responses traces to a registered `Fact`; causal phrasing is blocked by an automated linter.",
        "4. **Comprehensive evaluation (E1–E8):** Planted-truth synthetic suites, component ablations, calibration simulations, independent recomputation, real-dataset reliability stress tests, chat evaluation, and messy-input robustness.",
        "",
        "## 2. Related Work",
        "",
        (
            "Multiple-testing control builds on Benjamini & Hochberg (1995) for FDR control and Benjamini & Yekutieli (2001) "
            "for arbitrary dependence. Group and association tests follow Welch (1947, 1951), Mann & Whitney (1947), and "
            "Kruskal & Wallis (1952). Effect sizes follow Cohen (1988), Hedges & Olkin (1985), Cramér (1946), and Bergsma (2013) "
            "for bias-corrected Cramér's *V*."
        ),
        "",
        "## 3. System Design & Principles (P1–P10)",
        "",
        (
            "VeriData enforces ten non-negotiable invariants across Phases 1–7 (see `docs/architecture.md` and `plans/00_MASTER_PLAN.md`): "
            "numbers always originate from deterministic tools (`P1`), hypothesis generation never peeks at test outcomes (`P2`), "
            "every executed test is counted in the BH family (`P3`), the core pipeline runs 100% offline (`P4`), reports state association "
            "rather than causation (`P5`), the product LLM never runs arbitrary code (`P6`), CSV values are sanitized as untrusted input (`P7`), "
            "all runs are seeded and logged (`P8`), defaults are conservative (`P9`), and rejected hypotheses receive explicit reason codes (`P10`)."
        ),
        "",
        "## 4. Methods",
        "",
        "- **Phase 1 (Ingestion & Cleaning):** Two-pass string-safe ingestion, 10-class semantic type inference, and conservative cleaning (`NaN` preserved, outliers flagged).",
        "- **Phase 2 (Hypothesis Enumeration):** Exhaustive pairwise enumeration over feasible columns plus optional outcome-blind LLM proposals.",
        "- **Phase 3 (Testing & Validation):** Two-stage execution (Stage A p-values & effects; Stage B bootstrap CIs & sensitivity checks), BH adjustment at `q <= 0.05`, Cohen 'small' effect floor, assumption gate, and derived-column (`|r| >= 0.999`) trivial gate.",
        "- **Phase 5–7 (Reporting, LangGraph Agent & UI):** Deterministic `FactRegistry`, number verifier, language linter, LangGraph batch/chat orchestration with SQLite checkpointing, and multi-tab Streamlit dashboard.",
        "",
        "## 5. Evaluation Setup",
        "",
        f"- **Protocol:** `docs/eval_protocol.md` (Suite: `{suite}`, Split: `{split}`, Git commit: `{manifest.get('git_commit', 'N/A')}`).",
        f"- **LLM Baselines status:** `{verdict.get('llm_status', 'N/A')}` (Included systems: `{', '.join(llm_included) if llm_included else 'deterministic systems only'}`).",
        "",
        "## 6. Results (E1–E8)",
        "",
        "### E1 — Main Benchmark",
        "",
        _read_table("table_e1_main.md"),
        "",
        "![E1 Main Benchmark FDR and Recall](figures/fig_e1_fdr_recall_bars.png)",
        "",
        "![E1 Recall-FDR Alpha Trade-off](figures/fig_e1_alpha_tradeoff.png)",
        "",
        "![E1 Null Dataset False Positives](figures/fig_e1_null_fp.png)",
        "",
        "![E1 q-Value Calibration](figures/fig_e1_q_calibration.png)",
        "",
        "### E2 — Component Ablation",
        "",
        _read_table("table_e2_ablation.md"),
        "",
        "![E2 Component Ablation](figures/fig_e2_ablation.png)",
        "",
        "### E3 — Calibration Summary",
        "",
        f"- Assumption-aware Type-I error cells inside band: **{_pct(e3.get('aware_pct_inside_band'))}** vs naive **{_pct(e3.get('naive_pct_inside_band'))}**.",
        f"- Power sanity checks within 3 Monte Carlo SE: **{e3.get('all_power_within_3se')}**.",
        "",
        _read_table("table_e3_calibration.md"),
        "",
        "![E3 FDR Under Dependence](figures/fig_e3_dependence_fdr.png)",
        "",
        "### E4 — Number Correctness",
        "",
        _read_table("table_e4_numbers.md"),
        "",
        "### E5 — Real Datasets",
        "",
        _read_table("table_e5_real.md"),
        "",
        "![E5 Real Dataset Reliability](figures/fig_e5_real_reliability.png)",
        "",
        "### E6 — Test-Selection Accuracy",
        "",
        (
            f"- Overall acceptable-set accuracy: VeriData assumption-aware **{_pct(e6.get('overall_aware_accuracy'))}**, "
            f"always-parametric **{_pct(e6.get('overall_naive_accuracy'))}**, always-nonparametric **{_pct(e6.get('overall_nonparam_accuracy'))}**."
        ),
        "",
        _read_table("table_e6_selection.md"),
        "",
        "### E7 — Chat Evaluation",
        "",
        _read_table("table_e7_chat.md"),
        "",
        "### E8 — Robustness on Messy Inputs",
        "",
        _read_table("table_e8_robustness.md"),
        "",
        "## 7. Discussion & Negative / Nuanced Findings",
        "",
        "- **Correction drives FDR control:** Removing BH correction (`S2` / `A2`) raises FDR dramatically on multi-column and pure-null datasets.",
        "- **Borderline q-values carry higher empirical false fractions:** As shown in `fig_e1_q_calibration.png`, BH controls the average FDP across the reported set rather than guaranteeing per-item posterior error < 5% near the 0.05 boundary.",
        "- **Small effects at small n (`n=100`) are intentionally missed:** The practical effect floor + BH sacrifice low-power small effects to protect precision.",
        "",
        "## 8. Limitations, Ethics & Threats to Validity",
        "",
        "1. **Synthetic generator coupling:** Synthetic scenarios cannot replicate every real-world dependency or clustering artifact; mitigated via E5 real-dataset checks.",
        "2. **Observational association only:** VeriData tests statistical association, never causal claims; residual confounding remains possible.",
        "3. **Independence of rows:** Repeated-measures / clustered observations violate i.i.d. test assumptions.",
        "4. **Multiple-testing dependence:** Default BH assumes PRDS; BY is provided as a conservative fallback.",
        "5. **Public dataset contamination:** Kaggle/UCI datasets may appear in LLM pretraining corpora, potentially inflating LLM baselines on E5.",
        "6. **Single-split / dev-vs-test discipline:** All protocol edits freeze before executing the one-time `test` split.",
        "",
        "## 9. Conclusion & Future Work",
        "",
        (
            "VeriData demonstrates that pairing deterministic statistical tools with outcome-blind hypothesis generation, "
            "session-wide BH correction, effect-size floors, and strict FactRegistry verification delivers trustworthy automated "
            "data analysis. Future extensions include covariate-adjusted regression tools, interaction screening, time-series "
            "dependence modeling, and online FDR control."
        ),
        "",
        "## References",
        "",
        "- Benjamini, Y., & Hochberg, Y. (1995). Controlling the false discovery rate: a practical and powerful approach to multiple testing. *JRSS-B*, 57(1), 289-300.",
        "- Benjamini, Y., & Yekutieli, D. (2001). The control of the false discovery rate in multiple testing under dependency. *Annals of Statistics*, 29(4), 1165-1188.",
        "- Bergsma, W. (2013). A bias-correction for Cramér's V and Tschuprow's T. *Journal of the Korean Statistical Society*, 42(3), 323-328.",
        "- Cohen, J. (1988). *Statistical Power Analysis for the Behavioral Sciences* (2nd ed.). Lawrence Erlbaum.",
        "- Cramér, H. (1946). *Mathematical Methods of Statistics*. Princeton University Press.",
        "- Hedges, L. V., & Olkin, I. (1985). *Statistical Methods for Meta-Analysis*. Academic Press.",
        "- Kruskal, W. H., & Wallis, W. A. (1952). Use of ranks in one-criterion variance analysis. *JASA*, 47(260), 583-621.",
        "- Mann, H. B., & Whitney, D. R. (1947). On a test of whether one of two random variables is stochastically larger than the other. *Annals of Mathematical Statistics*, 18(1), 50-60.",
        "- Welch, B. L. (1947). The generalization of 'Student's' problem when several different population variances are involved. *Biometrika*, 34(1-2), 28-35.",
        "- Welch, B. L. (1951). On the comparison of several mean values: an alternative approach. *Biometrika*, 38(3-4), 330-336.",
        "",
    ]

    md_text = "\n".join(md_parts)
    md_p = report_root / "FINAL_REPORT.md"
    md_p.write_text(md_text, encoding="utf-8")

    body_html = markdown.markdown(md_text, extensions=["tables", "fenced_code"])
    body_html = _embed_figures_html(body_html, report_root)
    html_doc = (
        "<!DOCTYPE html><html lang='en'><head><meta charset='utf-8'/>"
        "<title>VeriData Final Report</title>"
        "<style>body{font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;max-width:980px;margin:2rem auto;padding:0 1.25rem;line-height:1.55;color:#1f2937;}"
        "table{border-collapse:collapse;width:100%;margin:1rem 0;font-size:0.9rem;}"
        "th,td{border:1px solid #d1d5db;padding:0.45rem 0.6rem;text-align:left;}"
        "th{background:#f3f4f6;}blockquote{border-left:4px solid #0072B2;padding:0.5rem 1rem;background:#f0f7fc;margin:1rem 0;}"
        "code{background:#f3f4f6;padding:0.1rem 0.3rem;border-radius:3px;}h1,h2,h3{color:#0f172a;}</style>"
        f"</head><body>{body_html}</body></html>\n"
    )
    html_p = report_root / "FINAL_REPORT.html"
    html_p.write_text(html_doc, encoding="utf-8")
    return {"numbers": numbers_p, "markdown": md_p, "html": html_p}
