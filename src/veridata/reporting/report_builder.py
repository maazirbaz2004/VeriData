"""Findings report builder: Markdown + self-contained HTML, with a final verification gate (Phase 5, Section 9).

Narration is template-only in this version (the optional LLM slot narration, P5-M5, is on the
cut list); ``report_meta.json`` records the narration source of every text.
"""

from __future__ import annotations

import base64
import csv
import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd
from pydantic import BaseModel, Field

import veridata
from veridata.contracts.findings import Finding
from veridata.contracts.validation import RejectionReason
from veridata.errors import ReportingError
from veridata.reporting.charts import (
    plot_bh,
    plot_finding,
    plot_forest,
    plot_rejection_breakdown,
    plot_volcano,
)
from veridata.reporting.charts.summary import REASON_LABELS
from veridata.reporting.facts import (
    FactRegistry,
    build_facts,
    build_method_facts,
    finding_id,
)
from veridata.reporting.language_lint import LintIssue, lint_text
from veridata.reporting.number_verifier import VerificationResult, verify_text
from veridata.reporting.templates import explain_accepted, explain_rejected, how_tested


class Explanation(BaseModel):
    """What Phase 6 chat reuses: a verified explanation of one finding (Section 10)."""

    text: str
    source: str = "template"  # llm | template | template_fallback
    verified: bool
    violations: list[dict[str, Any]] = Field(default_factory=list)
    lint: list[dict[str, Any]] = Field(default_factory=list)
    used_fact_keys: list[str] = Field(default_factory=list)


def explain_finding(finding: Finding, registry: FactRegistry, llm: Any = None, config: Any = None) -> Explanation:
    """Template explanation of one finding, verified against that finding's facts only."""
    fid = finding_id(finding)
    if not registry.has(f"{fid}.col_a"):
        build_facts(finding, registry)
    if not registry.has("method.alpha") and config is not None:
        build_method_facts(registry, config)
    text = explain_accepted(finding, registry).text if finding.decision.accepted else explain_rejected(finding, registry)
    v = verify_text(text, registry, [fid])
    li = lint_text(text, finding, kind="finding" if finding.decision.accepted else "rejected")
    return Explanation(text=text, source="template", verified=v.ok and not li, violations=[x.as_dict() for x in v.violations], lint=[x.as_dict() for x in li], used_fact_keys=[f.key for f in registry.for_finding(fid)])


@dataclass
class ReportArtifacts:
    out_dir: Path
    markdown_path: Path
    html_path: Path | None
    findings_csv: Path
    meta_path: Path
    checks_path: Path
    figures: list[Path] = field(default_factory=list)
    ok: bool = True


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")[:40] or "x"


def _cell(s: Any) -> str:
    return str(s).replace("|", "\\|").replace("\n", " ")


def _disp(reg: FactRegistry, key: str, default: str = "–") -> str:
    return reg.get(key).display if reg.has(key) else default


def _config_hash(config: Any) -> str:
    return hashlib.sha256(json.dumps(config.model_dump(mode="json"), sort_keys=True, default=str).encode()).hexdigest()[:12]


def _summary_facts(reg: FactRegistry, findings: list[Finding], df: pd.DataFrame, alpha: float, manifest: dict[str, Any], profile: dict[str, Any], cleaning_log: list[dict[str, Any]]) -> None:
    tested = [f for f in findings if f.decision.p_raw is not None]
    reg.num("summary", "n_hypotheses", len(findings), "count", "len(findings)")
    reg.num("summary", "n_tests", len(tested), "count", "findings with a p-value (the correction family)")
    reg.num("summary", "n_raw_sig", sum(1 for f in tested if (f.decision.p_raw or 1) < alpha), "count", "findings with raw p < alpha")
    reg.num("summary", "n_accepted", sum(1 for f in findings if f.decision.accepted), "count", "findings with decision.accepted")
    reg.num("summary", "n_rejected", sum(1 for f in findings if not f.decision.accepted), "count", "findings not accepted")
    reg.num("summary", "n_not_tested", len(findings) - len(tested), "count", "hypotheses without a p-value")
    counts: dict[str, int] = {}
    for f in findings:
        for r in f.decision.reasons:
            counts[r.value] = counts.get(r.value, 0) + 1
    for code, n in sorted(counts.items()):
        reg.num("summary", f"reason_{code}", n, "count", f"count of RejectionReason.{code}")
    reg.num("summary", "n_rows", len(df), "count", "cleaned dataframe rows")
    reg.num("summary", "n_cols", df.shape[1], "count", "cleaned dataframe columns")
    for k in ("n_columns_total", "n_columns_eligible", "n_candidate_hypotheses", "n_infeasible", "n_in_family_planned"):
        if isinstance(manifest.get(k), int):
            reg.num("summary", k, manifest[k], "count", f"HypothesisManifest.{k}")
    if isinstance(profile.get("n_rows"), int):
        reg.num("summary", "n_rows_raw", profile["n_rows"], "count", "DataProfile.n_rows")
        reg.num("summary", "n_cols_raw", profile["n_cols"], "count", "DataProfile.n_cols")
    mms = profile.get("missing_matrix_summary") or {}
    if "pct_missing_cells" in mms:
        reg.num("summary", "pct_missing_raw", 100 * float(mms["pct_missing_cells"]), "pct", "100 * DataProfile.missing_matrix_summary.pct_missing_cells")
    dup = sum(int(e.get("n_rows_affected", 0)) for e in cleaning_log if e.get("action") == "dropped_duplicate_rows")
    reg.num("summary", "n_duplicates_removed", dup, "count", "cleaning log: dropped_duplicate_rows")
    reg.num("summary", "n_cleaning_changes", len(cleaning_log), "count", "len(cleaning log)")
    reg.num("summary", "n_cells_changed", sum(int(e.get("n_cells_affected", 0)) for e in cleaning_log), "count", "sum of cleaning log n_cells_affected")


def _stats_table(f: Finding, reg: FactRegistry) -> str:
    fid = finding_id(f)
    rows = [("Test used", _disp(reg, f"{fid}.test_name"))]
    if reg.has(f"{fid}.statistic"):
        rows.append(("Test statistic", _disp(reg, f"{fid}.statistic")))
    if reg.has(f"{fid}.df"):
        rows.append(("Degrees of freedom", _disp(reg, f"{fid}.df")))
    elif reg.has(f"{fid}.df1"):
        rows.append(("Degrees of freedom", _disp(reg, f"{fid}.df1") + " and " + _disp(reg, f"{fid}.df2")))
    rows.append(("Raw p-value", _disp(reg, f"{fid}.p_raw")))
    rows.append(("Adjusted p-value (q)", _disp(reg, f"{fid}.q_value")))
    if reg.has(f"{fid}.effect_value"):
        ci = f" (95% CI {_disp(reg, f'{fid}.ci_low')} to {_disp(reg, f'{fid}.ci_high')})" if reg.has(f"{fid}.ci_low") else ""
        rows.append(("Effect size", f"{_disp(reg, f'{fid}.effect_name')} = {_disp(reg, f'{fid}.effect_value')}{ci}, {_disp(reg, f'{fid}.magnitude_label')}"))
    rows.append(("Records used", _disp(reg, f"{fid}.n_used")))
    if f.decision.flags:
        rows.append(("Flags", ", ".join(x.replace("_", " ") for x in f.decision.flags)))
    return "| | |\n| :--- | :--- |\n" + "\n".join(f"| {a} | {_cell(b)} |" for a, b in rows) + "\n"


LIMITATIONS_STATIC = [
    "**Association, not causation.** Every finding describes how columns move together in this data. None of them shows that a column is the reason for another.",
    "**Rows are assumed independent.** The tests assume each row is a separate, unrelated record. Repeated measurements of the same person, place or time period break this assumption and make the results look more reliable than they are.",
    "**Pairwise only.** Each test looks at a single pair of columns. Interactions between several columns and confounding by a third column are not controlled for.",
    "**Correction under dependence.** The Benjamini-Hochberg correction assumes the tests are independent or positively dependent. Tests that share columns are dependent. In the planted-truth calibration it still kept the false discovery rate near the target with strongly correlated columns, but unusual (negative) dependence is not covered; the Benjamini-Yekutieli option (`stats.correction: by`) is the safer choice then.",
    "**Adjusted p-values are not per-finding error chances.** The correction controls the share of false findings across the whole list. A finding whose adjusted p-value is close to the cut-off is more likely to be a false lead than a finding far below it.",
    "**Effects of selected findings are optimistic.** Effect sizes and confidence intervals are reported for the findings that passed the checks, so they tend to be somewhat larger than the true effects. The intervals are not adjusted for this selection.",
    "**Missing data.** Each test uses the rows where both columns are present (pairwise deletion). If values are missing for a reason related to the columns, results can be biased.",
    "**Cleaning choices matter.** The results depend on the cleaning steps listed in the data quality section, such as removing duplicates and turning placeholder text into missing values.",
    "**Role of the language model.** No language model produced or changed any number in this report. The explanations are filled from fixed templates and every number is checked against the computed results.",
]


def _figure_md(chart_title: str, rel_path: str) -> str:
    return f"![{chart_title}]({rel_path})\n"


def build_report(
    findings: list[Finding],
    hypothesis_manifest: dict[str, Any] | Any,
    cleaning_log: list[dict[str, Any]],
    profile: dict[str, Any] | Any,
    df: pd.DataFrame,
    config: Any,
    llm: Any = None,
    out_dir: Path | str = "outputs/report",
    *,
    dataset_name: str | None = None,
    report_date: str = "",
    max_findings: int | None = None,
    formats: tuple[str, ...] = ("md", "html"),
    allow_violations: bool = False,
) -> ReportArtifacts:
    out = Path(out_dir)
    fig_dir = out / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)
    for old in fig_dir.glob("*.png"):
        old.unlink()
    manifest = hypothesis_manifest.model_dump(mode="json") if hasattr(hypothesis_manifest, "model_dump") else dict(hypothesis_manifest or {})
    prof = profile.model_dump(mode="json") if hasattr(profile, "model_dump") else dict(profile or {})
    name = dataset_name or prof.get("dataset_name") or manifest.get("dataset_name") or "dataset"
    alpha = float(config.stats.alpha)
    cap = max_findings or int(config.reporting.max_findings_in_report)

    reg = FactRegistry()
    build_method_facts(reg, config)
    for f in findings:
        build_facts(f, reg)
        f.facts = reg.for_finding(finding_id(f))
    _summary_facts(reg, findings, df, alpha, manifest, prof, cleaning_log)
    reg.text("report", "dataset_name", name, "dataset name")
    reg.text("report", "version", veridata.__version__, "veridata.__version__")
    reg.text("report", "config_hash", _config_hash(config), "sha256 of the resolved config")
    if prof.get("sha256"):
        reg.text("report", "sha256", prof["sha256"], "DataProfile.sha256")
        reg.text("report", "sha_label", "SHA-256", "name of the checksum algorithm")
    if report_date:
        reg.text("report", "date", report_date, "report date")
    for c in df.columns:
        reg.text("report", f"col_{_slug(str(c))}", str(c), "cleaned dataframe column")

    accepted = sorted([f for f in findings if f.decision.accepted], key=lambda f: -(f.test.effect.comparable_value if f.test.effect and f.test.effect.comparable_value is not None else 0.0))
    shown, overflow = accepted[:cap], accepted[cap:]
    explanations: dict[str, Explanation] = {}
    chart_texts: list[str] = []
    figures: list[Path] = []
    md: list[str] = []

    # ---- 1. title + executive summary ---------------------------------------------------
    md.append(reg.render("# VeriData findings report — `{report.dataset_name}`") + "\n")
    meta_line = reg.render("{summary.n_rows} rows × {summary.n_cols} columns after cleaning · VeriData {report.version} · config `{report.config_hash}`")
    if report_date:
        meta_line += reg.render(" · generated {report.date}")
    md.append(meta_line + "\n")
    md.append("## 1. Executive summary\n")
    md.append(reg.render(
        "VeriData tested {summary.n_tests} column pairs. {summary.n_raw_sig} of them had a raw p-value below {method.alpha}, the usual threshold. "
        "After correcting for the number of tests ({method.correction_name} method) and requiring an effect that is not negligible, "
        "{summary.n_accepted} remain as validated findings. The others were rejected for the reasons shown below. "
        "Every finding is an association, not evidence of cause and effect.") + "\n")
    md.append(reg.render("- Tests run: {summary.n_tests}\n- Raw p below {method.alpha}: {summary.n_raw_sig}\n- Validated findings: {summary.n_accepted}"))
    for k in sorted(x.key for x in reg.all() if x.key.startswith("summary.reason_")):
        code = k.split("reason_", 1)[1]
        md.append(f"- Rejected — {REASON_LABELS.get(code, code)}: {reg.get(k).display}")
    md.append("\n_A rejected test can have more than a single reason, so these counts can add up to more than the number of rejected tests._\n")
    cr = plot_rejection_breakdown(reg, fig_dir / "summary_rejections.png")
    figures.append(cr.path)
    chart_texts += cr.texts
    md.append(_figure_md(cr.title, "figures/summary_rejections.png"))
    if shown:
        md.append("**Highlights** (largest effects):\n")
        for f in shown[:3]:
            fid = finding_id(f)
            md.append(reg.render("- `{.col_a}` ↔ `{.col_b}`: {.magnitude_label} ({.effect_name} = {.effect_value})", fid))
        md.append("")

    # ---- 2. validated findings -------------------------------------------------------------
    md.append("## 2. Validated findings\n")
    if not shown:
        md.append("No pattern passed every check. This is a valid result: it means none of the tested relationships is strong and reliable enough to report.\n")
    for i, f in enumerate(shown, start=1):
        fid = finding_id(f)
        ex = explain_finding(f, reg, llm, config)
        explanations[fid] = ex
        md.append(reg.render("### 2." + str(i) + " `{.col_a}` ↔ `{.col_b}`", fid) + "\n")
        md.append(ex.text + "\n")
        rel = f"figures/f{i:02d}_{_slug(f.hypothesis.column_a)}__{_slug(f.hypothesis.column_b)}.png"
        try:
            ch = plot_finding(f, df, reg, out / rel)
            figures.append(ch.path)
            chart_texts += ch.texts
            md.append(_figure_md(ch.title, rel))
        except Exception as exc:  # noqa: BLE001 — a chart must never break the report
            md.append(f"_Chart not available ({type(exc).__name__})._\n")
        md.append(_stats_table(f, reg))
        md.append('<details markdown="1">\n<summary>How was this tested?</summary>\n\n' + how_tested(f) + "\n\n</details>\n")
        md.append('<details markdown="1">\n<summary>Where do the numbers come from?</summary>\n\n' + reg.facts_table_md(fid) + "\n</details>\n")
    if overflow:
        md.append("**Further validated findings** (not shown in full):\n")
        md.append("| Columns | Test | Effect | Adjusted p |\n| :--- | :--- | :--- | :--- |")
        for f in overflow:
            fid = finding_id(f)
            explanations[fid] = explain_finding(f, reg, llm, config)
            md.append(reg.render("| `{.col_a}` ↔ `{.col_b}` | {.test_name} | {.effect_name} = {.effect_value} | {.q_value} |", fid))
        md.append("")
    if accepted:
        cf = plot_forest(findings, reg, fig_dir / "summary_forest.png")
        figures.append(cf.path)
        chart_texts += cf.texts
        md.append(_figure_md(cf.title, "figures/summary_forest.png"))

    # ---- 3. rejected patterns -----------------------------------------------------------------
    md.append("## 3. Patterns that looked interesting but were rejected\n")
    md.append(reg.render("These patterns had the lowest raw p-values among the rejected tests. Each of them would look like a discovery to a naive analysis that tests {summary.n_tests} pairs without correction.") + "\n")
    rejected = sorted([f for f in findings if not f.decision.accepted and f.decision.p_raw is not None and RejectionReason.TRIVIAL_RELATIONSHIP not in f.decision.reasons], key=lambda f: f.decision.p_raw or 1.0)[:10]
    if rejected:
        md.append("| Columns | Test | Raw p | Adjusted p | Effect | Why it was rejected |\n| :--- | :--- | :--- | :--- | :--- | :--- |")
        for f in rejected:
            fid = finding_id(f)
            ex = explain_finding(f, reg, llm, config)
            explanations[fid] = ex
            eff = reg.render("{.effect_name} = {.effect_value}", fid) if reg.has(f"{fid}.effect_value") else "–"
            md.append(reg.render("| `{.col_a}` ↔ `{.col_b}` | {.test_name} | ", fid) + f"{_disp(reg, f'{fid}.p_raw')} | {_disp(reg, f'{fid}.q_value')} | {_cell(eff)} | {_cell(ex.text)} |")
        md.append("")
    else:
        md.append("No tested pattern was rejected.\n")
    cb = plot_bh(findings, reg, fig_dir / "summary_bh.png", alpha)
    cv = plot_volcano(findings, reg, fig_dir / "summary_volcano.png", alpha)
    figures += [cb.path, cv.path]
    chart_texts += cb.texts + cv.texts
    md.append(_figure_md(cb.title, "figures/summary_bh.png"))
    md.append(_figure_md(cv.title, "figures/summary_volcano.png"))

    # ---- 4. derived columns -----------------------------------------------------------------
    md.append("## 4. Likely derived or duplicated columns\n")
    trivial = [f for f in findings if RejectionReason.TRIVIAL_RELATIONSHIP in f.decision.reasons]
    if trivial:
        for f in trivial:
            fid = finding_id(f)
            ex = explain_finding(f, reg, llm, config)
            explanations[fid] = ex
            md.append(reg.render("- `{.col_a}` ↔ `{.col_b}`: ", fid) + ex.text)
        md.append("")
    else:
        md.append("None found.\n")

    # ---- 5. data quality --------------------------------------------------------------------
    md.append("## 5. Data quality summary\n")
    dq = []
    if reg.has("summary.n_rows_raw"):
        dq.append(reg.render("- Raw file: {summary.n_rows_raw} rows × {summary.n_cols_raw} columns; after cleaning: {summary.n_rows} rows × {summary.n_cols} columns."))
    if reg.has("summary.pct_missing_raw"):
        dq.append(reg.render("- Missing cells in the raw file: {summary.pct_missing_raw}."))
    dq.append(reg.render("- Exact duplicate rows removed: {summary.n_duplicates_removed}."))
    dq.append(reg.render("- Logged cleaning changes: {summary.n_cleaning_changes}, touching {summary.n_cells_changed} cells (see the cleaning log)."))
    md.append("\n".join(dq) + "\n")

    # ---- 6. methods -------------------------------------------------------------------------------
    md.append("## 6. Methods\n")
    mode = str(manifest.get("effective_mode", manifest.get("mode", "exhaustive"))).replace("_", " ")
    mtxt = [f"**Hypotheses.** Hypotheses were generated in {mode} mode from the column types only, before any test was run."]
    if reg.has("summary.n_columns_eligible") and reg.has("summary.n_columns_total"):
        mtxt.append(reg.render("{summary.n_columns_eligible} of {summary.n_columns_total} columns were eligible and {summary.n_tests} pairs were tested."))
    mtxt.append("A language model was not used to choose or change the tests." if not manifest.get("llm_used") else "A language model only suggested which pairs to look at; it never saw test results or produced numbers.")
    md.append(" ".join(mtxt) + "\n")
    md.append("**Tests.** Each pair is tested with a fixed, unit-tested test chosen by rules that check the data's shape first:\n")
    md.append("| Relationship | Default test | Fallback when assumptions fail |\n| :--- | :--- | :--- |\n| numeric vs a binary column | Welch's t-test | Mann-Whitney U test |\n| numeric vs several groups | Welch's ANOVA | Kruskal-Wallis test |\n| numeric vs numeric | Pearson correlation | Spearman rank correlation |\n| category vs category | chi-square test | Fisher's exact test or a Monte Carlo (permutation) chi-square test |\n")
    md.append(reg.render(
        "Groups with fewer than {method.min_group_n} records are left out, and a pair needs at least {method.min_n_pairwise} complete records. "
        "Groups of at least {method.large_n_clt} records may use the parametric test when skewness stays below {method.extreme_skew}. "
        "Confidence intervals use {method.bootstrap_resamples} bootstrap resamples; permutation tests use {method.permutation_resamples} resamples.") + "\n")
    md.append(reg.render("**Correction.** All tests form a single family. The {method.correction_name} method controls the false discovery rate at {method.alpha_pct}: on average, at most this share of the reported findings should be false.") + "\n")
    md.append("**Effect-size floors.** A result must also have an effect that is not negligible:\n")
    md.append(reg.render(
        "| Effect measure | Smallest effect reported |\n| :--- | :--- |\n| Hedges' g (binary groups) | {method.floor_cohens_d} |\n| rank-biserial correlation | {method.floor_rank_biserial} |\n"
        "| Pearson r / Spearman rho | {method.floor_correlation} |\n| eta squared | {method.floor_eta_squared} |\n| epsilon squared | {method.floor_epsilon_squared} |\n| Cramér's V (comparable scale) | {method.floor_cramers_v_df1} |") + "\n")
    md.append("**What 'validated' means.** A finding is validated when its adjusted p-value is below the false discovery rate, its effect is above the floor, and its test's assumptions were met or a suitable fallback test was used.\n")

    # ---- 7. limitations -------------------------------------------------------------------------
    md.append("## 7. Limitations\n")
    lim = list(LIMITATIONS_STATIC)
    if len(df) < 200:
        lim.append(reg.render("**Small dataset.** With {summary.n_rows} rows, effect estimates are uncertain and smaller real effects can be missed."))
    if reg.has("summary.pct_missing_raw") and float(reg.get("summary.pct_missing_raw").value) > 20:
        lim.append(reg.render("**Heavy missingness.** {summary.pct_missing_raw} of the raw cells were missing, so some tests used far fewer rows than the file has."))
    md.append("\n".join(f"- {x}" for x in lim) + "\n")

    # ---- 8. appendix -------------------------------------------------------------------------------
    md.append("## 8. Appendix\n")
    md.append("### All results\n")
    md.append("| Columns | Test | Raw p | Adjusted p | Effect | Decision |\n| :--- | :--- | :--- | :--- | :--- | :--- |")
    for f in sorted(findings, key=lambda f: (not f.decision.accepted, f.decision.p_raw if f.decision.p_raw is not None else 2.0, finding_id(f))):
        fid = finding_id(f)
        eff = reg.render("{.effect_name} = {.effect_value}", fid) if reg.has(f"{fid}.effect_value") else "–"
        dec = "validated" if f.decision.accepted else "rejected: " + ", ".join(REASON_LABELS.get(r.value, r.value) for r in f.decision.reasons)
        md.append(reg.render("| `{.col_a}` ↔ `{.col_b}` | {.test_name} | ", fid) + f"{_disp(reg, f'{fid}.p_raw')} | {_disp(reg, f'{fid}.q_value')} | {_cell(eff)} | {dec} |")
    md.append("")
    md.append("### Reproducibility\n")
    repro = [reg.render("- VeriData version: {report.version}; resolved config hash: `{report.config_hash}`.")]
    if reg.has("report.sha256"):
        repro.append(reg.render("- Dataset {report.sha_label}: `{report.sha256}`."))
    repro.append("- Narration: deterministic templates (no language model).")
    md.append("\n".join(repro) + "\n")

    markdown = "\n".join(md).rstrip() + "\n"

    # ---- final gate ---------------------------------------------------------------------------
    sources = sorted({f.source for f in reg.all()}, key=len, reverse=True)
    report_v: VerificationResult = verify_text(markdown, reg, extra_strings=sources)
    chart_v = [verify_text(t, reg) for t in chart_texts if t]
    report_lint: list[LintIssue] = lint_text(markdown, None, kind="report")
    missing_images = [p for p in re.findall(r"!\[[^\]]*\]\(([^)]+)\)", markdown) if not (out / p).exists()]
    expl_bad = {k: e.model_dump() for k, e in explanations.items() if not e.verified}
    checks = {
        "verifier": {"ok": report_v.ok, "n_numbers_checked": len(report_v.extracted), "violations": [v.as_dict() for v in report_v.violations]},
        "chart_text": {"ok": all(v.ok for v in chart_v), "n_texts": len(chart_v), "violations": [v.as_dict() for cv_ in chart_v for v in cv_.violations]},
        "lint": {"ok": not report_lint, "issues": [i.as_dict() for i in report_lint]},
        "explanations": {"n": len(explanations), "n_failed": len(expl_bad), "failed": expl_bad},
        "required_sections": {"limitations": "## 7. Limitations" in markdown, "independence_note": "assumed independent" in markdown, "rejected_section": "## 3. Patterns that looked interesting" in markdown},
        "images": {"ok": not missing_images, "missing": missing_images},
    }
    ok = (report_v.ok and checks["chart_text"]["ok"] and not report_lint and not missing_images and not expl_bad and all(checks["required_sections"].values()))
    checks["ok"] = ok

    md_path = out / "report.md"
    md_path.write_text(markdown, encoding="utf-8")
    (out / "report_checks.json").write_text(json.dumps(checks, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    meta = {
        "dataset": name,
        "veridata_version": veridata.__version__,
        "config_hash": _config_hash(config),
        "narration": {fid: e.source for fid, e in sorted(explanations.items())},
        "verifier_stats": {"n_texts": len(explanations) + len(chart_texts) + 1, "n_violations": len(report_v.violations) + sum(len(v.violations) for v in chart_v), "n_retries": 0},
        "llm": {"model": None, "prompt_version": None, "token_cost_usd": 0.0},
        "n_findings": len(findings),
        "n_validated": len(accepted),
        "n_figures": len(figures),
    }
    meta_path = out / "report_meta.json"
    meta_path.write_text(json.dumps(meta, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    csv_path = out / "findings_summary.csv"
    _write_findings_csv(findings, csv_path)
    html_path = None
    if "html" in formats:
        html_path = out / "report.html"
        html_path.write_text(markdown_to_html(markdown, out, f"VeriData findings report — {name}"), encoding="utf-8")
    if not ok and not allow_violations:
        raise ReportingError(f"report gate failed; see {out / 'report_checks.json'}")
    return ReportArtifacts(out, md_path, html_path, csv_path, meta_path, out / "report_checks.json", figures, ok)


def _write_findings_csv(findings: list[Finding], path: Path) -> None:
    cols = ["hypothesis_id", "column_a", "column_b", "relationship", "test", "n_used", "statistic", "p_raw", "q_value", "effect_name", "effect_value", "ci_low", "ci_high", "magnitude", "accepted", "reasons", "flags"]
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for f in findings:
            e = f.test.effect
            w.writerow({
                "hypothesis_id": f.hypothesis.id, "column_a": f.hypothesis.column_a, "column_b": f.hypothesis.column_b, "relationship": f.hypothesis.relationship.value,
                "test": f.test.test_name, "n_used": f.test.n_used, "statistic": f.test.statistic, "p_raw": f.decision.p_raw, "q_value": f.decision.q_value,
                "effect_name": e.name if e else "", "effect_value": e.value if e else "", "ci_low": e.ci_low if e else "", "ci_high": e.ci_high if e else "",
                "magnitude": e.magnitude if e else "", "accepted": f.decision.accepted, "reasons": ";".join(r.value for r in f.decision.reasons), "flags": ";".join(f.decision.flags),
            })


HTML_CSS = """
body{font-family:-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;color:#1f2933;background:#f5f7fa;margin:0}
main{max-width:1000px;margin:0 auto;background:#fff;padding:28px 32px 60px}
h1{font-size:1.6rem;border-bottom:3px solid #0072B2;padding-bottom:6px}h2{font-size:1.3rem;margin-top:2em;border-bottom:1px solid #d9e2ec}
h3{font-size:1.08rem;margin-top:1.6em}table{border-collapse:collapse;margin:10px 0 16px;font-size:.88rem;display:block;overflow-x:auto}
th,td{border:1px solid #d9e2ec;padding:4px 8px;vertical-align:top;text-align:left}th{background:#eef2f7}
code{background:#eef2f7;padding:1px 4px;border-radius:3px}img{max-width:100%;border:1px solid #e4e7eb;border-radius:4px;margin:8px 0}
details{margin:6px 0 12px;background:#f8fafc;border:1px solid #e4e7eb;border-radius:4px;padding:6px 10px}summary{cursor:pointer;font-weight:600}
@media print{body{background:#fff}main{padding:0}details{display:block}img{page-break-inside:avoid}}
"""


def markdown_to_html(markdown_text: str, base_dir: Path, title: str) -> str:
    """Self-contained HTML: inline CSS and base64-embedded PNGs (no external assets)."""
    import html as _html

    import markdown as md_lib

    body = md_lib.markdown(markdown_text, extensions=["tables", "fenced_code", "md_in_html"])

    def embed(m: re.Match[str]) -> str:
        src = m.group(1)
        p = base_dir / src
        if p.exists():
            data = base64.b64encode(p.read_bytes()).decode()
            return f'src="data:image/png;base64,{data}"'
        return m.group(0)

    body = re.sub(r'src="([^"]+\.png)"', embed, body)
    return f'<!DOCTYPE html>\n<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>{_html.escape(title)}</title><style>{HTML_CSS}</style></head><body><main>\n{body}\n</main></body></html>\n'
