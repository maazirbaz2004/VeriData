"""Target / class balance EDA (Section 10.5)."""

from __future__ import annotations

from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .plots import (
    CATEGORY_COLORS,
    DESCRIPTIVE_NOTE,
    PRIMARY,
    SECONDARY,
    EDASettings,
    FigureSink,
    df_to_markdown,
    fmt_num,
    short_label,
    wrap_title,
)
from .stats import as_float, as_labels, cramers_v, imbalance_label, pct, safe_round, value_counts_sorted
from .univariate import _box_strip, _hist_panel


def run_target(
    df: pd.DataFrame,
    target: str,
    target_kind: str,
    categorical_cols: list[str],
    sink: FigureSink,
    settings: EDASettings,
) -> tuple[dict[str, Any], dict[str, str]]:
    """Class balance (categorical target) or distribution (numeric target)."""
    headline: dict[str, Any] = {"name": target, "kind": target_kind, "figures": {}}
    tables: dict[str, str] = {}

    if target_kind == "numeric":
        v = as_float(df[target]).dropna()
        headline["n_missing"] = int(df[target].isna().sum())
        if len(v) == 0:
            return headline, tables
        n_zero = int((v == 0).sum())
        headline.update(
            {
                "count": int(len(v)),
                "mean": safe_round(v.mean(), 4),
                "median": safe_round(v.median(), 4),
                "std": safe_round(v.std(ddof=1), 4) if len(v) > 1 else None,
                "min": safe_round(v.min(), 4),
                "max": safe_round(v.max(), 4),
                "skew": safe_round(v.skew(), 3) if len(v) > 2 else None,
                "n_zeros": n_zero,
                "pct_zeros": pct(n_zero, len(v)),
            }
        )
        fig = plt.figure(figsize=(8, 4.6), layout="constrained")
        gs = fig.add_gridspec(2, 1, height_ratios=[4, 1])
        ax_h = fig.add_subplot(gs[0])
        ax_b = fig.add_subplot(gs[1], sharex=ax_h)
        _hist_panel(ax_h, v, discrete=bool((v % 1 == 0).all() and v.nunique() <= 40))
        _box_strip(ax_b, v)
        ax_b.set_xlabel(str(target))
        plt.setp(ax_h.get_xticklabels(), visible=False)
        title = (
            f"Target '{target}' ranges from {fmt_num(headline['min'])} to {fmt_num(headline['max'])} "
            f"(median {fmt_num(headline['median'])}, skew {headline['skew']:+.2f})"
            if headline["skew"] is not None
            else f"Target '{target}' distribution"
        )
        ax_h.set_title(wrap_title(title, 80))
        rec = sink.save(fig, "target_distribution", title, "Distribution of the target column.", "target")
        headline["figures"]["target"] = rec["rel_path"]
        return headline, tables

    # ---- categorical / binary target -------------------------------------------------
    labels = as_labels(df[target])
    vc = value_counts_sorted(labels)
    headline["n_missing"] = int(labels.isna().sum())
    n = int(vc.sum())
    if n == 0 or len(vc) == 0:
        return headline, tables
    classes = [{"label": str(k), "count": int(c), "pct": pct(c, n)} for k, c in vc.items()]
    majority, minority = classes[0], classes[-1]
    ratio = round(majority["count"] / max(1, minority["count"]), 2)
    label = imbalance_label(minority["count"] / n, ratio, settings.minority_imbalance_threshold)
    headline.update(
        {
            "n_classes": len(classes),
            "classes": classes,
            "majority_class": majority["label"],
            "majority_pct": majority["pct"],
            "minority_class": minority["label"],
            "minority_pct": minority["pct"],
            "imbalance_ratio": ratio,
            "balance_label": label,
        }
    )
    tables["target_balance"] = df_to_markdown(
        [{"Class": c["label"], "Count": c["count"], "%": c["pct"]} for c in classes], ["Class", "Count", "%"], {"Count", "%"}
    ) + f"\nImbalance ratio (largest/smallest class) = {ratio}: **{label}**.\n"

    shown = classes[:20]
    fig, ax = plt.subplots(figsize=(max(5.5, 0.6 * len(shown) + 3), 4))
    colors = [PRIMARY] * len(shown)
    colors[-1] = SECONDARY
    ax.bar([short_label(c["label"], 16) for c in shown], [c["count"] for c in shown], color=colors)
    top = max(c["count"] for c in shown)
    for i, c in enumerate(shown):
        ax.text(i, c["count"] + top * 0.01, f"{c['count']:,}\n({c['pct']:.1f}%)", ha="center", va="bottom", fontsize=8)
    ax.set_ylim(0, top * 1.22)
    ax.set_ylabel("Rows")
    ax.set_xlabel(str(target))
    if len(shown) > 6:
        plt.setp(ax.get_xticklabels(), rotation=35, ha="right", rotation_mode="anchor")
    title = (
        f"Target '{target}' is {label}: smallest class '{minority['label']}' is "
        f"{minority['pct']:.1f}% of rows (ratio {ratio}:1)"
    )
    ax.set_title(wrap_title(title, 70))
    rec = sink.save(
        fig,
        "target_balance",
        title,
        "Rows per target class. The orange bar is the smallest class. Highly imbalanced = smallest class under "
        f"{100 * settings.minority_imbalance_threshold:.0f}% of rows; mildly = largest/smallest ratio of 1.5 or more.",
        "target",
    )
    headline["figures"]["target"] = rec["rel_path"]

    # ---- target mix across the most associated categorical features ------------------
    if len(classes) <= 8:
        scored = []
        for c in categorical_cols:
            if c == target:
                continue
            n_lvls = int(as_labels(df[c]).nunique())
            if n_lvls < 2 or n_lvls > 12:
                continue
            v = cramers_v(df[c], df[target])
            if v is not None:
                scored.append((c, v))
        scored.sort(key=lambda t: (-t[1], str(t[0])))
        top_feats = scored[: settings.top_bivariate_pairs]
        if top_feats:
            n_p = len(top_feats)
            n_c = 2 if n_p > 1 else 1
            n_r = (n_p + n_c - 1) // n_c
            fig, axes = plt.subplots(n_r, n_c, figsize=(6.4 * n_c, 3.2 * n_r + 0.5), squeeze=False, layout="constrained")
            class_order = [c["label"] for c in classes]
            for ax, (feat, v) in zip(axes.flat, top_feats):
                tab = pd.crosstab(as_labels(df[feat]), labels, normalize="index")
                tab = tab.reindex(columns=[c for c in class_order if c in tab.columns])
                tab = tab.sort_index()
                left = np.zeros(len(tab))
                for k, cls in enumerate(tab.columns):
                    vals = tab[cls].to_numpy() * 100
                    ax.barh(
                        [short_label(x, 20) for x in tab.index],
                        vals,
                        left=left,
                        color=CATEGORY_COLORS[k % len(CATEGORY_COLORS)],
                        label=short_label(cls, 14),
                    )
                    left += vals
                ax.set_xlim(0, 100)
                ax.set_xlabel(f"% of rows in level, by {target}")
                ax.set_title(f"{short_label(feat, 28)} (Cramér's V {v:.2f})")
            for ax in list(axes.flat)[n_p:]:
                ax.set_visible(False)
            handles, leg_labels = axes.flat[0].get_legend_handles_labels()
            fig.legend(handles, leg_labels, loc="outside upper center", ncol=min(8, len(leg_labels)), title=str(target), fontsize=8)
            best, best_v = top_feats[0]
            title = f"The '{target}' mix changes most across levels of '{best}' (Cramér's V {best_v:.2f})"
            fig.suptitle(wrap_title(title, 90))
            rec = sink.save(
                fig,
                "target_by_categorical",
                title,
                "Share of each target class within each level of the categorical features most associated with the "
                f"target (bias-corrected Cramér's V). {DESCRIPTIVE_NOTE}",
                "target",
            )
            headline["figures"]["target_by_categorical"] = rec["rel_path"]
            headline["top_categorical_by_cramers_v"] = [
                {"feature": f, "cramers_v": safe_round(v, 3)} for f, v in top_feats
            ]
    return headline, tables
