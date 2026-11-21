"""One chart per finding, chosen by the test that ran (Phase 5, Section 8)."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from veridata.contracts.findings import Finding
from veridata.contracts.hypothesis import Direction
from veridata.reporting.charts.style import (
    FIGSIZE,
    OKABE_ITO,
    ChartResult,
    apply_style,
    labels,
    save,
    short,
    wrap,
)
from veridata.reporting.facts import FactRegistry, finding_id

MAX_POINTS_PER_GROUP = 800
MAX_GROUPS = 12


def _r(reg: FactRegistry, fid: str, template: str) -> str:
    return reg.render(template, fid)


def _annot(ax: plt.Axes, text: str) -> None:
    ax.text(0.99, 0.98, text, transform=ax.transAxes, ha="right", va="top", fontsize=10, bbox={"boxstyle": "round", "fc": "white", "ec": "#cccccc"})


def _q_phrase(reg: FactRegistry, fid: str) -> str:
    if not reg.has(f"{fid}.q_value"):
        return ""
    d = reg.get(f"{fid}.q_value").display
    return "adjusted p " + (d if d.startswith("<") else "= " + d)


def _group_chart(f: Finding, df: pd.DataFrame, reg: FactRegistry, out_path: Path) -> ChartResult:
    fid = finding_id(f)
    a, b = f.hypothesis.column_a, f.hypothesis.column_b
    sub = pd.DataFrame({"y": pd.to_numeric(df[a], errors="coerce"), "g": labels(df[b])}).dropna()
    desc = f.test.descriptives
    order = [str(x) for x in desc.get("group_order", [])] or sorted(sub["g"].unique())
    order = [g for g in order if g in set(sub["g"])]
    tn = f.test.test_name
    stat = "median" if tn in {"mann_whitney_u", "kruskal_wallis"} else "mean"
    if len(order) > 2:  # order by the plotted statistic, highest first
        order = sorted(order, key=lambda g: -float(getattr(sub.loc[sub["g"] == g, "y"], stat)()))
    other = []
    if len(order) > MAX_GROUPS:
        other = order[MAX_GROUPS - 1 :]
        order = order[: MAX_GROUPS - 1]
    data = [sub.loc[sub["g"] == g, "y"].to_numpy() for g in order]
    tick = []
    texts = []
    pos_of = {str(x): i + 1 for i, x in enumerate(desc.get("group_order", []))}
    for g in order:
        key = f"{fid}.n_g{pos_of[g]}" if g in pos_of else None
        n_txt = reg.get(key).display if key and reg.has(key) else None
        lbl = short(g, 18) + (f"\n(n = {n_txt})" if n_txt else "")
        tick.append(lbl)
        texts.append(lbl)
    if other:
        data.append(sub.loc[sub["g"].isin(other), "y"].to_numpy())
        tick.append("Other\n(display only)")
        texts.append(tick[-1])
    apply_style()
    fig, ax = plt.subplots(figsize=(max(FIGSIZE[0], 0.7 * len(tick) + 2), FIGSIZE[1]), layout="constrained")
    ax.boxplot(data, widths=0.55, showfliers=False, patch_artist=True, boxprops={"facecolor": "#DCE9F5", "edgecolor": OKABE_ITO[0]}, medianprops={"color": OKABE_ITO[3], "lw": 1.8})
    rng = np.random.default_rng(0)
    for i, arr in enumerate(data, start=1):
        pts = arr if len(arr) <= MAX_POINTS_PER_GROUP else rng.choice(arr, MAX_POINTS_PER_GROUP, replace=False)
        ax.scatter(i + rng.uniform(-0.18, 0.18, len(pts)), pts, s=7, alpha=0.35 if len(pts) > 200 else 0.6, color=OKABE_ITO[0], edgecolors="none", zorder=2)
        if stat == "mean" and len(arr) > 1:
            m, se = float(np.mean(arr)), float(np.std(arr, ddof=1) / np.sqrt(len(arr)))
            ax.errorbar(i + 0.3, m, yerr=1.96 * se, fmt="D", color=OKABE_ITO[1], ms=5, capsize=3, zorder=3)
    ax.set_xticks(range(1, len(tick) + 1))
    ax.set_xticklabels(tick)
    ax.set_xlabel(short(b))
    ax.set_ylabel(short(a))
    top = desc.get("higher_group") or desc.get("highest_group")
    if top is not None:
        title = _r(reg, fid, "{.col_a} is higher on average for {.col_b} = {." + ("higher_group" if "higher_group" in desc else "highest_group") + "}") if stat == "mean" else _r(reg, fid, "{.col_a} tends to be higher for {.col_b} = {." + ("higher_group" if "higher_group" in desc else "highest_group") + "}")
    else:
        title = _r(reg, fid, "{.col_a} by {.col_b}")
    ax.set_title(wrap(title))
    annot = ""
    if reg.has(f"{fid}.effect_value"):
        annot = _r(reg, fid, "{.effect_name} = {.effect_value}") + ("\n" + _q_phrase(reg, fid) if _q_phrase(reg, fid) else "")
        _annot(ax, annot)
    if stat == "mean":
        ax.plot([], [], "D", color=OKABE_ITO[1], label="mean with 95% CI")
        ax.legend(loc="lower right", fontsize=9)
        texts.append("mean with 95% CI")
    return ChartResult(save(fig, out_path), title, [title, annot, *texts])


def _scatter_chart(f: Finding, df: pd.DataFrame, reg: FactRegistry, out_path: Path) -> ChartResult:
    fid = finding_id(f)
    a, b = f.hypothesis.column_a, f.hypothesis.column_b
    sub = pd.DataFrame({"x": pd.to_numeric(df[a], errors="coerce"), "y": pd.to_numeric(df[b], errors="coerce")}).dropna()
    apply_style()
    fig, ax = plt.subplots(figsize=FIGSIZE, layout="constrained")
    if len(sub) > 3000:
        hb = ax.hexbin(sub["x"], sub["y"], gridsize=40, cmap="Blues", mincnt=1, linewidths=0, bins="log")
        fig.colorbar(hb, ax=ax, label="records (log scale)")
    else:
        ax.scatter(sub["x"], sub["y"], s=10, alpha=0.5, color=OKABE_ITO[0], edgecolors="none")
    xs = np.linspace(sub["x"].min(), sub["x"].max(), 100)
    legend = ""
    if f.test.test_name == "pearson" and sub["x"].nunique() > 1:
        slope, intercept = np.polyfit(sub["x"], sub["y"], 1)
        resid = sub["y"] - (slope * sub["x"] + intercept)
        s = float(np.sqrt((resid**2).sum() / max(1, len(sub) - 2)))
        xm, sxx = float(sub["x"].mean()), float(((sub["x"] - sub["x"].mean()) ** 2).sum())
        band = 1.96 * s * np.sqrt(1 / len(sub) + (xs - xm) ** 2 / sxx)
        ax.plot(xs, slope * xs + intercept, color=OKABE_ITO[3], lw=2)
        ax.fill_between(xs, slope * xs + intercept - band, slope * xs + intercept + band, color=OKABE_ITO[3], alpha=0.2)
        legend = "straight-line fit with 95% band"
    elif sub["x"].nunique() > 3:
        from statsmodels.nonparametric.smoothers_lowess import lowess

        sm = lowess(sub["y"], sub["x"], frac=0.5, it=1, return_sorted=True)
        ax.plot(sm[:, 0], sm[:, 1], color=OKABE_ITO[3], lw=2)
        legend = "smoothed trend (LOWESS)"
    if legend:
        ax.plot([], [], color=OKABE_ITO[3], lw=2, label=legend)
        ax.legend(loc="lower right", fontsize=9)
    ax.set_xlabel(short(a))
    ax.set_ylabel(short(b))
    word = "positively" if f.test.direction_observed == Direction.POSITIVE else ("negatively" if f.test.direction_observed == Direction.NEGATIVE else "")
    title = _r(reg, fid, "{.col_a} and {.col_b} are " + word + " associated").replace("are  associated", "are associated")
    ax.set_title(wrap(title))
    annot = _r(reg, fid, "{.effect_name} = {.effect_value}\nn = {.n_used}") if reg.has(f"{fid}.effect_value") and reg.has(f"{fid}.n_used") else ""
    if annot:
        _annot(ax, annot)
    return ChartResult(save(fig, out_path), title, [title, annot, legend, "records (log scale)"])


def _categorical_chart(f: Finding, df: pd.DataFrame, reg: FactRegistry, out_path: Path) -> ChartResult:
    fid = finding_id(f)
    a, b = f.hypothesis.column_a, f.hypothesis.column_b
    sub = pd.DataFrame({"a": labels(df[a]), "b": labels(df[b])}).dropna()
    desc = f.test.descriptives
    rows = [str(x) for x in desc.get("row_labels", [])] or sorted(sub["a"].unique())
    cols = [str(x) for x in desc.get("col_labels", [])] or sorted(sub["b"].unique())
    sub = sub[sub["a"].isin(rows) & sub["b"].isin(cols)]
    if len(rows) > MAX_GROUPS:
        keep = sub["a"].value_counts().index[: MAX_GROUPS - 1].tolist()
        sub.loc[~sub["a"].isin(keep), "a"] = "Other (display only)"
        rows = [r for r in rows if r in keep] + ["Other (display only)"]
    if len(cols) > 8:
        keep = sub["b"].value_counts().index[:7].tolist()
        sub.loc[~sub["b"].isin(keep), "b"] = "Other (display only)"
        cols = [c for c in cols if c in keep] + ["Other (display only)"]
    tab = pd.crosstab(sub["a"], sub["b"]).reindex(index=rows, columns=cols, fill_value=0)
    prop = tab.div(tab.sum(axis=1).replace(0, np.nan), axis=0).fillna(0) * 100
    n = tab.to_numpy().sum()
    exp = np.outer(tab.sum(1), tab.sum(0)) / max(n, 1)
    rp, cp = tab.sum(1).to_numpy() / max(n, 1), tab.sum(0).to_numpy() / max(n, 1)
    with np.errstate(divide="ignore", invalid="ignore"):
        resid = (tab.to_numpy() - exp) / np.sqrt(exp * np.outer(1 - rp, 1 - cp))
    resid = np.nan_to_num(resid)
    apply_style()
    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(FIGSIZE[0] + 3.0, FIGSIZE[1]), gridspec_kw={"width_ratios": [3, 2]}, layout="constrained")
    left = np.zeros(len(rows))
    texts = []
    for i, c in enumerate(cols):
        vals = prop[c].to_numpy()
        ax.barh([short(r, 18) for r in rows], vals, left=left, color=OKABE_ITO[i % len(OKABE_ITO)], label=short(c, 16))
        left += vals
        texts.append(short(c, 16))
    texts += [short(r, 18) for r in rows]
    ax.set_xlim(0, 100)
    ax.set_xlabel(wrap(f"% of each {short(a, 24)} level, by {short(b, 24)}", 45))
    ax.set_ylabel(short(a))
    ax.invert_yaxis()
    ax.legend(title=short(b, 20), loc="center left", bbox_to_anchor=(1.0, 0.5), fontsize=9, title_fontsize=9)
    lim = max(2.0, float(np.abs(resid).max()))
    im = ax2.imshow(resid, cmap="RdBu_r", vmin=-lim, vmax=lim, aspect="auto")
    ax2.set_xticks(range(len(cols)))
    ax2.set_xticklabels([short(c, 10) for c in cols], rotation=45, ha="right", rotation_mode="anchor")
    ax2.set_yticks(range(len(rows)))
    ax2.set_yticklabels([short(r, 12) for r in rows])
    ax2.grid(False)
    ax2.set_title("more (red) or fewer (blue)\nthan expected", fontsize=10)
    fig.colorbar(im, ax=ax2, shrink=0.8, label="standardized residual")
    title = _r(reg, fid, "{.col_a} and {.col_b} are associated")
    annot = _r(reg, fid, "Cramér's V = {.effect_value},  n = {.n_used}") if reg.has(f"{fid}.effect_value") and reg.has(f"{fid}.n_used") else ""
    fig.suptitle(wrap(title, 80) + ("\n" + annot if annot else ""))
    texts += [short(c, 10) for c in cols] + [short(r, 12) for r in rows]
    return ChartResult(save(fig, out_path), title, [title, annot, *texts, "more (red) or fewer (blue)\nthan expected", "standardized residual"])


def plot_finding(f: Finding, df: pd.DataFrame, reg: FactRegistry, out_path: Path | str) -> ChartResult:
    """Pick the chart for the test that ran; uses only ``df`` (cleaned data) and the Finding."""
    out = Path(out_path)
    tn = f.test.test_name
    if tn in {"welch_t", "mann_whitney_u", "welch_anova", "kruskal_wallis"}:
        return _group_chart(f, df, reg, out)
    if tn in {"pearson", "spearman"}:
        return _scatter_chart(f, df, reg, out)
    return _categorical_chart(f, df, reg, out)
