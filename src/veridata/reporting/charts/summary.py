"""Summary charts: rejection breakdown, BH plot, forest plot, volcano (Phase 5, Section 8)."""

from __future__ import annotations

import math
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from veridata.contracts.findings import Finding
from veridata.contracts.validation import RejectionReason
from veridata.reporting.charts.style import (
    ACCEPT,
    FIGSIZE,
    FLOOR,
    OKABE_ITO,
    REJECT,
    ChartResult,
    apply_style,
    save,
    short,
    wrap,
)
from veridata.reporting.facts import FactRegistry

REASON_LABELS = {
    RejectionReason.NOT_SIGNIFICANT_AFTER_CORRECTION.value: "not supported after correction",
    RejectionReason.EFFECT_BELOW_THRESHOLD.value: "effect too small",
    RejectionReason.ASSUMPTION_VIOLATED.value: "assumptions not met",
    RejectionReason.INSUFFICIENT_DATA.value: "not enough data",
    RejectionReason.DEGENERATE_DATA.value: "no variation",
    RejectionReason.TEST_ERROR.value: "test error",
    RejectionReason.TRIVIAL_RELATIONSHIP.value: "derived / duplicate columns",
    RejectionReason.UNSTABLE_CI.value: "unstable direction",
}


def plot_rejection_breakdown(reg: FactRegistry, out_path: Path | str) -> ChartResult:
    """Headline 'naive vs validated' chart; every bar label is a summary fact."""
    bars = [("tests run", "summary.n_tests", REJECT), ("raw p below alpha", "summary.n_raw_sig", FLOOR), ("validated findings", "summary.n_accepted", ACCEPT)]
    reasons = sorted(k.split("reason_", 1)[1] for k in (f.key for f in reg.all()) if k.startswith("summary.reason_"))
    apply_style()
    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(FIGSIZE[0] + 3.5, FIGSIZE[1]), gridspec_kw={"width_ratios": [2, 3]}, layout="constrained")
    texts = []
    for i, (lbl, key, col) in enumerate(bars):
        v = float(reg.get(key).value)
        ax.bar(i, v, color=col)
        ax.text(i, v, reg.get(key).display, ha="center", va="bottom", fontsize=10)
        texts += [lbl, reg.get(key).display]
    ax.set_xticks(range(len(bars)))
    ax.set_xticklabels([wrap(b[0], 12) for b in bars])
    ax.set_ylabel("number of tests")
    ax.set_title("What the checks removed")
    names = [REASON_LABELS.get(r, r) for r in reasons]
    vals = [float(reg.get(f"summary.reason_{r}").value) for r in reasons]
    ax2.barh(names[::-1], vals[::-1], color=OKABE_ITO[3])
    for y, r in enumerate(reasons[::-1]):
        d = reg.get(f"summary.reason_{r}").display
        ax2.text(float(reg.get(f"summary.reason_{r}").value), y, " " + d, va="center", fontsize=10)
        texts.append(d)
    ax2.set_xlabel("rejected tests (a test can have several reasons)")
    ax2.set_title("Why tests were rejected")
    texts += names + ["What the checks removed", "Why tests were rejected", "number of tests", "rejected tests (a test can have several reasons)"]
    title = reg.render("{summary.n_accepted} validated findings out of {summary.n_tests} tests")
    fig.suptitle(title)
    return ChartResult(save(fig, Path(out_path)), title, [title, *texts])


def plot_bh(findings: list[Finding], reg: FactRegistry, out_path: Path | str, alpha: float) -> ChartResult:
    """Sorted p-values vs the BH line (i/m)·alpha; accepted, floor-rejected and other points."""
    tested = sorted([f for f in findings if f.decision.p_raw is not None], key=lambda f: f.decision.p_raw or 1.0)
    m = len(tested)
    apply_style()
    fig, ax = plt.subplots(figsize=FIGSIZE, layout="constrained")
    if m:
        ranks = np.arange(1, m + 1)
        p = np.array([max(f.decision.p_raw or 1.0, 1e-300) for f in tested])
        acc = np.array([f.decision.accepted for f in tested])
        floor = np.array([RejectionReason.EFFECT_BELOW_THRESHOLD in f.decision.reasons and RejectionReason.NOT_SIGNIFICANT_AFTER_CORRECTION not in f.decision.reasons for f in tested])
        other = ~acc & ~floor
        ax.scatter(ranks[other], p[other], s=14, color=REJECT, label="rejected")
        ax.scatter(ranks[floor], p[floor], s=18, color=FLOOR, marker="s", label="rejected: effect too small")
        ax.scatter(ranks[acc], p[acc], s=18, color=ACCEPT, label="validated")
        ax.plot(ranks, ranks / m * alpha, color=OKABE_ITO[3], lw=1.5, label="Benjamini-Hochberg line")
        ax.set_yscale("log")
        ax.legend(fontsize=9, loc="lower right")
    ax.set_xlabel("tests sorted by raw p-value")
    ax.set_ylabel("raw p-value (log scale)")
    title = reg.render("Correcting for {summary.n_tests} tests: points under the line pass")
    ax.set_title(wrap(title))
    return ChartResult(save(fig, Path(out_path)), title, [title, "rejected", "rejected: effect too small", "validated", "Benjamini-Hochberg line", "tests sorted by raw p-value", "raw p-value (log scale)"])


def _comparable_ci(f: Finding) -> tuple[float, float | None, float | None]:
    e = f.test.effect
    assert e is not None
    comp = e.comparable_value if e.comparable_value is not None else abs(e.value)
    if e.ci_low is None or e.ci_high is None or e.value == 0:
        return comp, None, None
    k = comp / e.value
    lo, hi = sorted((e.ci_low * k, e.ci_high * k))
    return comp, lo, hi


def plot_forest(findings: list[Finding], reg: FactRegistry, out_path: Path | str) -> ChartResult:
    acc = [f for f in findings if f.decision.accepted and f.test.effect is not None]
    acc.sort(key=lambda f: (f.hypothesis.relationship.value, -_comparable_ci(f)[0]))
    apply_style()
    fig, ax = plt.subplots(figsize=(FIGSIZE[0] + 1.5, max(2.5, 0.32 * len(acc) + 1.2)), layout="constrained")
    names = []
    for i, f in enumerate(acc):
        c, lo, hi = _comparable_ci(f)
        color = OKABE_ITO[["numeric_vs_binary", "numeric_vs_categorical", "numeric_vs_numeric", "categorical_vs_categorical", "numeric_vs_numeric_nonlinear"].index(f.hypothesis.relationship.value) % len(OKABE_ITO)]
        ax.errorbar(c, i, xerr=None if lo is None else [[c - lo], [hi - c]], fmt="o", color=color, capsize=3)
        names.append(short(f"{f.hypothesis.column_a} ↔ {f.hypothesis.column_b}", 38))
    ax.set_yticks(range(len(acc)))
    ax.set_yticklabels(names)
    ax.invert_yaxis()
    ax.axvline(0, color="#666666", lw=0.8)
    rel_names = ["numeric_vs_binary", "numeric_vs_categorical", "numeric_vs_numeric", "categorical_vs_categorical", "numeric_vs_numeric_nonlinear"]
    present = sorted({f.hypothesis.relationship.value for f in acc}, key=rel_names.index)
    legend_txt = [r.replace("_vs_", " vs ").replace("_", " ") for r in present]
    for r, lbl in zip(present, legend_txt):
        ax.errorbar([], [], fmt="o", color=OKABE_ITO[rel_names.index(r) % len(OKABE_ITO)], label=lbl)
    if present:
        ax.legend(fontsize=9, loc="lower right")
    ax.set_xlabel("effect size on a comparable scale (with 95% CI)")
    title = reg.render("Effect sizes of the {summary.n_accepted} validated findings")
    ax.set_title(wrap(title))
    return ChartResult(save(fig, Path(out_path)), title, [title, "effect size on a comparable scale (with 95% CI)", *names, *legend_txt])


def plot_volcano(findings: list[Finding], reg: FactRegistry, out_path: Path | str, alpha: float) -> ChartResult:
    pts = [f for f in findings if f.test.effect is not None and f.decision.q_value is not None]
    apply_style()
    fig, ax = plt.subplots(figsize=FIGSIZE, layout="constrained")
    for kind, color, lbl in (("acc", ACCEPT, "validated"), ("floor", FLOOR, "detectable but trivial"), ("ns", REJECT, "not supported")):
        xs, ys = [], []
        for f in pts:
            k = "acc" if f.decision.accepted else ("floor" if (f.decision.q_value or 1) <= alpha else "ns")
            if k != kind:
                continue
            xs.append(_comparable_ci(f)[0])
            ys.append(-math.log10(max(f.decision.q_value or 1.0, 1e-300)))
        ax.scatter(xs, ys, s=16, color=color, label=lbl)
    ax.axhline(-math.log10(alpha), color=OKABE_ITO[3], lw=1.2, ls="--", label="adjusted p = alpha")
    ax.set_xlabel("effect size (comparable scale)")
    ax.set_ylabel("-log10(adjusted p)")
    ax.legend(fontsize=9, loc="upper left")
    title = "Effect size vs evidence: validated findings need both"
    ax.set_title(title)
    return ChartResult(save(fig, Path(out_path)), title, [title, "validated", "detectable but trivial", "not supported", "adjusted p = alpha", "effect size (comparable scale)", "-log10(adjusted p)"])
