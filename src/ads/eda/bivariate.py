"""Two-column EDA, descriptive only (Section 10.6).

Numeric-numeric: Pearson/Spearman heatmaps, top pairs, scatter plots, collinearity list.
Numeric-categorical: eta-squared ranking and grouped box plots.
Categorical-categorical: bias-corrected Cramér's V matrix and proportion bars.
Target vs each feature: one ranked chart and table.
No p-values or hypothesis tests anywhere in this module.
"""

from __future__ import annotations

from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from .plots import (
    ACCENT,
    CATEGORY_COLORS,
    DESCRIPTIVE_NOTE,
    DIVERGING_CMAP,
    PRIMARY,
    SECONDARY,
    SEQUENTIAL_CMAP,
    WARN,
    EDASettings,
    FigureSink,
    df_to_markdown,
    short_label,
    wrap_title,
)
from .stats import as_float, as_labels, cramers_v, eta_squared, safe_round, upper_pairs

# ---------------------------------------------------------------------------------------
# Numeric vs numeric
# ---------------------------------------------------------------------------------------


def run_numeric_numeric(
    df: pd.DataFrame, numeric_cols: list[str], sink: FigureSink, settings: EDASettings
) -> tuple[dict[str, Any], dict[str, str]]:
    headline: dict[str, Any] = {"figures": {}, "top_pairs": [], "collinear_pairs": []}
    tables: dict[str, str] = {}
    num = pd.DataFrame({c: as_float(df[c]) for c in numeric_cols})
    usable = [c for c in numeric_cols if num[c].dropna().nunique() > 1]
    if len(usable) < 2:
        tables["top_correlations"] = "Fewer than two varying numeric columns, so no correlations were computed.\n"
        return headline, tables
    num = num[usable]
    pearson = num.corr(method="pearson")
    spearman = num.corr(method="spearman")

    pairs = []
    sp_lookup = {(a, b): v for a, b, v in upper_pairs(spearman)}
    for a, b, p in upper_pairs(pearson):
        s = sp_lookup.get((a, b))
        if s is None:
            continue
        n_pair = int(num[[a, b]].dropna().shape[0])
        pairs.append({"a": a, "b": b, "pearson": safe_round(p, 3), "spearman": safe_round(s, 3), "n": n_pair})
    pairs.sort(key=lambda d: (-abs(d["spearman"] or 0), -abs(d["pearson"] or 0), d["a"], d["b"]))
    headline["top_pairs"] = pairs[:10]
    headline["n_pairs"] = len(pairs)
    collinear = [d for d in pairs if abs(d["pearson"] or 0) > settings.collinearity_threshold]
    headline["collinear_pairs"] = collinear

    # --- correlation_heatmap.png (Pearson + Spearman) ---------------------------------
    k = len(usable)
    annot = k <= 14
    side = max(4.5, 0.48 * k + 2.2)
    fig, axes = plt.subplots(1, 2, figsize=(2 * side + 1, side + 0.4), layout="constrained")
    mask = np.triu(np.ones((k, k), dtype=bool), k=1)
    ticks = [short_label(c, 16) for c in usable]
    for ax, mat, name in zip(axes, [pearson, spearman], ["Pearson r", "Spearman rho"]):
        sns.heatmap(
            mat,
            mask=mask,
            cmap=DIVERGING_CMAP,
            vmin=-1,
            vmax=1,
            center=0,
            annot=annot,
            fmt=".2f",
            annot_kws={"fontsize": 7},
            square=True,
            linewidths=0.4,
            cbar_kws={"shrink": 0.7},
            xticklabels=ticks,
            yticklabels=ticks,
            ax=ax,
        )
        ax.set_title(name)
    best = pairs[0]
    title = f"Strongest numeric pair: '{best['a']}' vs '{best['b']}' (Spearman {best['spearman']:+.2f}, Pearson {best['pearson']:+.2f})"
    fig.suptitle(wrap_title(title, 100))
    rec = sink.save(
        fig,
        "correlation_heatmap",
        title,
        f"Correlation between numeric columns (lower triangle). Left: Pearson (linear). Right: Spearman (rank-based). {DESCRIPTIVE_NOTE}",
        "relationships",
    )
    headline["figures"]["correlation_heatmap"] = rec["rel_path"]

    # --- top_scatter_pairs.png ---------------------------------------------------------
    top = pairs[: settings.top_bivariate_pairs]
    if top:
        n_p = len(top)
        n_c = min(3, n_p)
        n_r = (n_p + n_c - 1) // n_c
        fig, axes = plt.subplots(n_r, n_c, figsize=(4.6 * n_c, 3.9 * n_r + 0.4), squeeze=False, layout="constrained")
        rng_state = settings.random_state
        for ax, d in zip(axes.flat, top):
            sub = num[[d["a"], d["b"]]].dropna()
            n_all = len(sub)
            if n_all > settings.scatter_max_points:
                sub = sub.sample(n=settings.scatter_max_points, random_state=rng_state)
            alpha = 0.6 if len(sub) < 500 else (0.3 if len(sub) < 3000 else 0.15)
            ax.scatter(sub[d["a"]], sub[d["b"]], s=9, alpha=alpha, color=PRIMARY, edgecolors="none")
            if sub[d["a"]].nunique() > 1:
                slope, intercept = np.polyfit(sub[d["a"]], sub[d["b"]], 1)
                xs = np.linspace(sub[d["a"]].min(), sub[d["a"]].max(), 50)
                ax.plot(xs, slope * xs + intercept, color=SECONDARY, lw=1.6, label="linear fit")
                ax.legend(loc="best", fontsize=7)
            ax.set_xlabel(short_label(d["a"], 30))
            ax.set_ylabel(short_label(d["b"], 30))
            shown = "" if len(sub) == n_all else f", {len(sub):,} of {n_all:,} pts"
            ax.set_title(f"r {d['pearson']:+.2f}, rho {d['spearman']:+.2f}{shown}", fontsize=9)
        for ax in list(axes.flat)[n_p:]:
            ax.set_visible(False)
        title = f"Top {n_p} numeric pairs by |Spearman rho|"
        fig.suptitle(title)
        rec = sink.save(
            fig,
            "top_scatter_pairs",
            title,
            "Scatter plots with a straight-line fit for the most strongly related numeric pairs. "
            f"Large datasets are randomly sampled for plotting. {DESCRIPTIVE_NOTE}",
            "relationships",
        )
        headline["figures"]["top_scatter_pairs"] = rec["rel_path"]

    rows = [
        {"Column A": d["a"], "Column B": d["b"], "Pearson r": d["pearson"], "Spearman rho": d["spearman"], "Rows used": d["n"]}
        for d in pairs[:10]
    ]
    tables["top_correlations"] = (
        df_to_markdown(rows, ["Column A", "Column B", "Pearson r", "Spearman rho", "Rows used"], {"Pearson r", "Spearman rho", "Rows used"})
        + f"\n{DESCRIPTIVE_NOTE}\n"
    )
    if collinear:
        tables["collinear_pairs"] = df_to_markdown(
            [{"Column A": d["a"], "Column B": d["b"], "Pearson r": d["pearson"]} for d in collinear],
            ["Column A", "Column B", "Pearson r"],
            {"Pearson r"},
        )
    else:
        tables["collinear_pairs"] = f"No numeric pairs have |Pearson r| above {settings.collinearity_threshold}.\n"
    return headline, tables


# ---------------------------------------------------------------------------------------
# Numeric vs categorical
# ---------------------------------------------------------------------------------------


def run_numeric_categorical(
    df: pd.DataFrame,
    numeric_cols: list[str],
    categorical_cols: list[str],
    sink: FigureSink,
    settings: EDASettings,
) -> tuple[dict[str, Any], dict[str, str]]:
    headline: dict[str, Any] = {"figures": {}, "top_pairs": []}
    tables: dict[str, str] = {}
    group_cols = []
    for c in categorical_cols:
        n_lvls = int(as_labels(df[c]).nunique())
        if 2 <= n_lvls <= settings.max_group_levels_box:
            group_cols.append(c)
    if not numeric_cols or not group_cols:
        tables["numeric_by_category"] = "No numeric/categorical pairs to compare (need a categorical column with 2-8 levels).\n"
        return headline, tables

    num = {c: as_float(df[c]) for c in numeric_cols}
    labs = {c: as_labels(df[c]) for c in group_cols}
    scored = []
    for n_c in numeric_cols:
        for g_c in group_cols:
            if n_c == g_c:
                continue
            e = eta_squared(num[n_c], labs[g_c])
            if e is not None:
                scored.append({"numeric": n_c, "categorical": g_c, "eta_squared": safe_round(e, 3)})
    scored.sort(key=lambda d: (-(d["eta_squared"] or 0), d["numeric"], d["categorical"]))
    headline["top_pairs"] = scored[:10]
    if not scored:
        tables["numeric_by_category"] = "No numeric/categorical pairs had enough data to compare.\n"
        return headline, tables

    top = scored[: settings.top_bivariate_pairs]
    n_p = len(top)
    n_c = 2 if n_p > 1 else 1
    n_r = (n_p + n_c - 1) // n_c
    fig, axes = plt.subplots(n_r, n_c, figsize=(6.4 * n_c, 3.6 * n_r + 0.5), squeeze=False, layout="constrained")
    for ax, d in zip(axes.flat, top):
        frame = pd.DataFrame({"y": num[d["numeric"]], "g": labs[d["categorical"]]}).dropna()
        order = sorted(frame["g"].unique(), key=str)
        sns.boxplot(
            data=frame,
            x="y",
            y="g",
            order=order,
            ax=ax,
            color="#D6E2F0",
            linecolor=PRIMARY,
            fliersize=2,
            flierprops={"markerfacecolor": WARN, "markeredgecolor": WARN, "alpha": 0.5},
            medianprops={"color": ACCENT, "lw": 1.6},
        )
        ax.set_yticks(range(len(order)))
        ax.set_yticklabels([short_label(o, 18) for o in order])
        ax.set_xlabel(short_label(d["numeric"], 30))
        ax.set_ylabel(short_label(d["categorical"], 24))
        ax.set_title(f"{short_label(d['numeric'], 22)} by {short_label(d['categorical'], 22)}: eta² {d['eta_squared']:.2f}")
    for ax in list(axes.flat)[n_p:]:
        ax.set_visible(False)
    best = top[0]
    title = (
        f"'{best['categorical']}' separates '{best['numeric']}' the most "
        f"(eta² {best['eta_squared']:.2f} = share of its spread explained by the groups)"
    )
    fig.suptitle(wrap_title(title, 90))
    rec = sink.save(
        fig,
        "numeric_by_category",
        title,
        "Box plots of numeric columns split by categorical columns with up to "
        f"{settings.max_group_levels_box} levels, for the pairs with the largest eta-squared. {DESCRIPTIVE_NOTE}",
        "relationships",
    )
    headline["figures"]["numeric_by_category"] = rec["rel_path"]
    rows = [{"Numeric": d["numeric"], "Grouped by": d["categorical"], "eta²": d["eta_squared"]} for d in scored[:10]]
    tables["numeric_by_category"] = df_to_markdown(rows, ["Numeric", "Grouped by", "eta²"], {"eta²"}) + f"\n{DESCRIPTIVE_NOTE}\n"
    return headline, tables


# ---------------------------------------------------------------------------------------
# Categorical vs categorical
# ---------------------------------------------------------------------------------------


def run_categorical_categorical(
    df: pd.DataFrame, categorical_cols: list[str], sink: FigureSink, settings: EDASettings
) -> tuple[dict[str, Any], dict[str, str]]:
    headline: dict[str, Any] = {"figures": {}, "top_pairs": []}
    tables: dict[str, str] = {}
    labs = {c: as_labels(df[c]) for c in categorical_cols}
    cols = [c for c in categorical_cols if 2 <= labs[c].nunique() <= settings.max_cramers_levels]
    if len(cols) > settings.max_cramers_columns:
        cols = cols[: settings.max_cramers_columns]
        headline["capped_columns"] = True
    if len(cols) < 2:
        tables["categorical_pairs"] = "Fewer than two usable categorical columns, so no Cramér's V matrix was computed.\n"
        return headline, tables

    k = len(cols)
    mat = pd.DataFrame(np.eye(k), index=cols, columns=cols)
    pairs = []
    for i in range(k):
        for j in range(i + 1, k):
            v = cramers_v(labs[cols[i]], labs[cols[j]])
            v = 0.0 if v is None else v
            mat.iat[i, j] = mat.iat[j, i] = v
            pairs.append({"a": cols[i], "b": cols[j], "cramers_v": safe_round(v, 3)})
    pairs.sort(key=lambda d: (-(d["cramers_v"] or 0), d["a"], d["b"]))
    headline["top_pairs"] = pairs[:10]

    side = max(4.5, 0.48 * k + 2.2)
    fig, ax = plt.subplots(figsize=(side + 1, side))
    mask = np.triu(np.ones((k, k), dtype=bool), k=1)
    ticks = [short_label(c, 16) for c in cols]
    sns.heatmap(
        mat,
        mask=mask,
        cmap=SEQUENTIAL_CMAP,
        vmin=0,
        vmax=1,
        annot=k <= 14,
        fmt=".2f",
        annot_kws={"fontsize": 7},
        square=True,
        linewidths=0.4,
        cbar_kws={"shrink": 0.7, "label": "Cramér's V (bias-corrected)"},
        xticklabels=ticks,
        yticklabels=ticks,
        ax=ax,
    )
    best = pairs[0]
    title = f"Strongest categorical pair: '{best['a']}' vs '{best['b']}' (Cramér's V {best['cramers_v']:.2f})"
    ax.set_title(wrap_title(title, 70))
    rec = sink.save(
        fig,
        "cramers_v_heatmap",
        title,
        f"Bias-corrected Cramér's V between categorical/binary columns: 0 = unrelated, 1 = one fully predicts the other. {DESCRIPTIVE_NOTE}",
        "relationships",
    )
    headline["figures"]["cramers_v_heatmap"] = rec["rel_path"]

    # --- categorical_pairs.png: proportion bars for the top 4 pairs --------------------
    top = [d for d in pairs[:4] if labs[d["a"]].nunique() <= 12 and labs[d["b"]].nunique() <= 8]
    if top:
        n_p = len(top)
        n_c = 2 if n_p > 1 else 1
        n_r = (n_p + n_c - 1) // n_c
        fig, axes = plt.subplots(n_r, n_c, figsize=(6.4 * n_c, 3.3 * n_r + 0.4), squeeze=False, layout="constrained")
        for ax, d in zip(axes.flat, top):
            tab = pd.crosstab(labs[d["a"]], labs[d["b"]], normalize="index").sort_index()
            tab = tab.reindex(columns=sorted(tab.columns, key=str))
            left = np.zeros(len(tab))
            for idx, col in enumerate(tab.columns):
                vals = tab[col].to_numpy() * 100
                ax.barh(
                    [short_label(x, 20) for x in tab.index],
                    vals,
                    left=left,
                    color=CATEGORY_COLORS[idx % len(CATEGORY_COLORS)],
                    label=short_label(col, 14),
                )
                left += vals
            ax.set_xlim(0, 100)
            ax.set_xlabel(f"% of rows in level, by {short_label(d['b'], 20)}")
            ax.set_ylabel(short_label(d["a"], 24))
            ax.set_title(f"{short_label(d['a'], 20)} × {short_label(d['b'], 20)} (V {d['cramers_v']:.2f})")
            ax.legend(loc="center left", bbox_to_anchor=(1.01, 0.5), fontsize=7, title=short_label(d["b"], 14), title_fontsize=7)
        for ax in list(axes.flat)[n_p:]:
            ax.set_visible(False)
        title = "Level-by-level mix for the most associated categorical pairs"
        fig.suptitle(title)
        rec = sink.save(
            fig,
            "categorical_pairs",
            title,
            f"For each level of the first column, the share of rows in each level of the second column. {DESCRIPTIVE_NOTE}",
            "relationships",
        )
        headline["figures"]["categorical_pairs"] = rec["rel_path"]

    rows = [{"Column A": d["a"], "Column B": d["b"], "Cramér's V": d["cramers_v"]} for d in pairs[:10]]
    tables["categorical_pairs"] = df_to_markdown(rows, ["Column A", "Column B", "Cramér's V"], {"Cramér's V"}) + f"\n{DESCRIPTIVE_NOTE}\n"
    return headline, tables


# ---------------------------------------------------------------------------------------
# Target vs every feature
# ---------------------------------------------------------------------------------------


def run_target_relationships(
    df: pd.DataFrame,
    target: str,
    target_kind: str,
    numeric_cols: list[str],
    categorical_cols: list[str],
    sink: FigureSink,
    settings: EDASettings,
) -> tuple[dict[str, Any], dict[str, str]]:
    """Rank every feature by a descriptive association with the target.

    Categorical target: numeric feature -> eta² (feature split by target class);
    categorical feature -> Cramér's V. Numeric target: numeric feature -> Spearman rho
    (ranked by absolute value); categorical feature -> eta² (target split by feature levels).
    """
    headline: dict[str, Any] = {"target": target, "figures": {}, "features": []}
    tables: dict[str, str] = {}
    rows = []
    tgt = df[target]
    if target_kind == "numeric":
        t_num = as_float(tgt)
        for c in numeric_cols:
            if c == target:
                continue
            pair = pd.DataFrame({"x": as_float(df[c]), "y": t_num}).dropna()
            if len(pair) < 3 or pair["x"].nunique() < 2 or pair["y"].nunique() < 2:
                continue
            rho = pair["x"].corr(pair["y"], method="spearman")
            rows.append({"feature": c, "measure": "Spearman rho", "value": safe_round(rho, 3), "strength": safe_round(abs(rho), 3)})
        for c in categorical_cols:
            if c == target or as_labels(df[c]).nunique() > settings.max_cramers_levels:
                continue
            e = eta_squared(t_num, df[c])
            if e is not None:
                rows.append({"feature": c, "measure": "eta²", "value": safe_round(e, 3), "strength": safe_round(e, 3)})
    else:
        for c in numeric_cols:
            if c == target:
                continue
            e = eta_squared(df[c], tgt)
            if e is not None:
                rows.append({"feature": c, "measure": "eta²", "value": safe_round(e, 3), "strength": safe_round(e, 3)})
        for c in categorical_cols:
            if c == target or as_labels(df[c]).nunique() > settings.max_cramers_levels:
                continue
            v = cramers_v(df[c], tgt)
            if v is not None:
                rows.append({"feature": c, "measure": "Cramér's V", "value": safe_round(v, 3), "strength": safe_round(v, 3)})

    rows = [r for r in rows if r["strength"] is not None]
    rows.sort(key=lambda r: (-r["strength"], r["feature"]))
    headline["features"] = rows
    if not rows:
        tables["target_relationships"] = f"No features could be compared with '{target}'.\n"
        return headline, tables

    show = rows[:25]
    color_map = {"Spearman rho": PRIMARY, "eta²": SECONDARY, "Cramér's V": ACCENT}
    fig, ax = plt.subplots(figsize=(8.5, max(2.4, 0.32 * len(show) + 1.4)))
    labels = [short_label(r["feature"], 26) for r in show][::-1]
    vals = [r["strength"] for r in show][::-1]
    cols = [color_map[r["measure"]] for r in show][::-1]
    ax.barh(labels, vals, color=cols)
    for i, r in enumerate(show[::-1]):
        shown_val = r["value"]
        ax.text(r["strength"] + 0.005, i, f"{shown_val:+.2f}" if r["measure"] == "Spearman rho" else f"{shown_val:.2f}", va="center", fontsize=7.5)
    ax.set_xlim(0, min(1.05, max(vals) * 1.2 + 0.03))
    ax.set_xlabel("Association strength (|rho|, eta² or Cramér's V; 0 = none, 1 = perfect)")
    handles = [plt.Rectangle((0, 0), 1, 1, color=color_map[m]) for m in color_map if any(r["measure"] == m for r in show)]
    names = [m for m in color_map if any(r["measure"] == m for r in show)]
    ax.legend(handles, names, loc="lower right", fontsize=8)
    best = rows[0]
    title = f"'{best['feature']}' has the strongest association with '{target}' ({best['measure']} {best['value']:.2f})"
    ax.set_title(wrap_title(title, 80))
    rec = sink.save(
        fig,
        "target_relationships",
        title,
        "Every feature ranked by a descriptive association with the target. Different measures are used for "
        f"different column types, so compare bars of the same colour most directly. {DESCRIPTIVE_NOTE}",
        "relationships",
    )
    headline["figures"]["target_relationships"] = rec["rel_path"]
    table_rows = [{"Feature": r["feature"], "Measure": r["measure"], "Value": r["value"]} for r in rows]
    tables["target_relationships"] = df_to_markdown(table_rows, ["Feature", "Measure", "Value"], {"Value"}) + f"\n{DESCRIPTIVE_NOTE}\n"
    return headline, tables
