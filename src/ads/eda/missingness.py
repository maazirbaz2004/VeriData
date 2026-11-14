"""Missing-value EDA (Section 10.2): bar, heatmap, nullity correlation, concentration note."""

from __future__ import annotations

from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import ListedColormap

from .plots import (
    DIVERGING_CMAP,
    PRIMARY,
    WARN,
    EDASettings,
    FigureSink,
    df_to_markdown,
    short_label,
    sns,
    wrap_title,
)
from .stats import pct, safe_round


def run_missingness(
    df: pd.DataFrame, sink: FigureSink, settings: EDASettings
) -> tuple[dict[str, Any], dict[str, str]]:
    """Plot and summarize missing values in the (conservative) cleaned frame."""
    n_rows, n_cols = df.shape
    miss = df.isna()
    per_col = miss.sum()
    total_cells = int(n_rows * n_cols)
    total_missing = int(per_col.sum())
    row_missing = miss.sum(axis=1)
    rows_any = int((row_missing > 0).sum())

    columns_info = {
        str(c): {"n_missing": int(per_col[c]), "pct_missing": pct(per_col[c], n_rows)}
        for c in df.columns
    }
    cols_with_missing = [c for c in df.columns if per_col[c] > 0]
    cols_with_missing.sort(key=lambda c: (-int(per_col[c]), str(c)))

    headline: dict[str, Any] = {
        "total_cells": total_cells,
        "missing_cells": total_missing,
        "pct_missing_cells": pct(total_missing, total_cells),
        "rows_with_any_missing": rows_any,
        "pct_rows_with_any_missing": pct(rows_any, n_rows),
        "n_columns_with_missing": len(cols_with_missing),
        "columns": columns_info,
        "figures": {},
    }
    tables: dict[str, str] = {}

    if total_missing == 0:
        headline["concentration"] = "none"
        headline["concentration_note"] = "No missing values remain in the cleaned data."
        tables["missing_summary"] = "No missing values remain in the cleaned data, so no missingness charts were drawn.\n"
        return headline, tables

    # Concentration: share of all missing cells held by the 10% of rows with the most missing.
    top_n = max(1, int(np.ceil(0.10 * n_rows)))
    top_share = pct(row_missing.sort_values(ascending=False).head(top_n).sum(), total_missing)
    concentrated = top_share >= 50.0 and rows_any < 0.5 * n_rows
    headline["top10pct_rows_share_of_missing"] = top_share
    headline["concentration"] = "concentrated" if concentrated else "spread"
    headline["concentration_note"] = (
        f"Missing values are concentrated: the 10% of rows with the most gaps hold {top_share}% of all missing cells."
        if concentrated
        else f"Missing values are spread out: the 10% of rows with the most gaps hold {top_share}% of all missing cells."
    )

    # --- missing_bar.png ---------------------------------------------------------------
    show = cols_with_missing[:40]
    vals = [columns_info[str(c)]["pct_missing"] for c in show]
    fig, ax = plt.subplots(figsize=(8, max(2.2, 0.32 * len(show) + 1.2)))
    colors = [WARN if v > 40 else PRIMARY for v in vals]
    ax.barh([short_label(c) for c in show][::-1], vals[::-1], color=colors[::-1])
    for i, v in enumerate(vals[::-1]):
        ax.text(v + 0.5, i, f"{v:.1f}%", va="center", fontsize=8)
    ax.set_xlabel("Missing values (% of rows)")
    ax.set_xlim(0, max(100.0, max(vals) * 1.12) if max(vals) > 90 else max(vals) * 1.18 + 1)
    worst = show[0]
    title = (
        f"{len(cols_with_missing)} of {n_cols} columns have missing values; "
        f"most is '{worst}' ({columns_info[str(worst)]['pct_missing']:.1f}%)"
    )
    ax.set_title(wrap_title(title))
    rec = sink.save(
        fig,
        "missing_bar",
        title,
        "Percent of rows missing per column (only columns with at least one gap). Red bars are above 40%.",
        "missingness",
    )
    headline["figures"]["missing_bar"] = rec["rel_path"]

    # --- missing_heatmap.png -----------------------------------------------------------
    sample = miss
    if n_rows > settings.missing_heatmap_max_rows:
        sample = miss.sample(n=settings.missing_heatmap_max_rows, random_state=settings.random_state)
    order = sample.sum(axis=1).sort_values(ascending=False, kind="mergesort").index
    sample = sample.loc[order]
    heat_cols = list(df.columns) if n_cols <= 60 else cols_with_missing[:60]
    mat = sample[heat_cols].to_numpy(dtype=int)
    fig, ax = plt.subplots(figsize=(max(6, 0.28 * len(heat_cols) + 2), 5))
    ax.imshow(mat, aspect="auto", interpolation="nearest", cmap=ListedColormap(["#EAF0F7", WARN]), vmin=0, vmax=1)
    ax.set_xticks(range(len(heat_cols)))
    ax.set_xticklabels([short_label(c, 18) for c in heat_cols], rotation=60, ha="right", rotation_mode="anchor")
    ax.set_yticks([])
    ax.set_ylabel(f"Rows ({len(sample):,} shown, most gaps at top)")
    ax.grid(False)
    title = headline["concentration_note"]
    ax.set_title(wrap_title(title, 80))
    note = "" if len(sample) == n_rows else f" A random sample of {len(sample):,} of {n_rows:,} rows is shown."
    rec = sink.save(
        fig,
        "missing_heatmap",
        title,
        f"Each red cell is a missing value; rows are sorted by how many gaps they have.{note}",
        "missingness",
    )
    headline["figures"]["missing_heatmap"] = rec["rel_path"]

    # --- missing_correlation.png -------------------------------------------------------
    varying = [c for c in cols_with_missing if 0 < per_col[c] < n_rows]
    if len(varying) >= 2:
        corr = miss[varying].astype(float).corr()
        k = len(varying)
        fig, ax = plt.subplots(figsize=(max(4.5, 0.5 * k + 2.5), max(3.8, 0.45 * k + 2)))
        mask = np.triu(np.ones_like(corr, dtype=bool), k=1)
        sns.heatmap(
            corr,
            mask=mask,
            cmap=DIVERGING_CMAP,
            vmin=-1,
            vmax=1,
            annot=k <= 12,
            fmt=".2f",
            annot_kws={"fontsize": 8},
            square=True,
            linewidths=0.5,
            cbar_kws={"shrink": 0.7, "label": "Correlation of missingness"},
            ax=ax,
            xticklabels=[short_label(c, 18) for c in varying],
            yticklabels=[short_label(c, 18) for c in varying],
        )
        pairs = []
        for i in range(k):
            for j in range(i + 1, k):
                pairs.append((varying[i], varying[j], float(corr.iat[i, j])))
        pairs.sort(key=lambda t: (-abs(t[2]), str(t[0]), str(t[1])))
        a, b, v = pairs[0]
        title = f"Missingness in '{a}' and '{b}' moves together most (r = {v:+.2f})"
        ax.set_title(wrap_title(title, 60))
        rec = sink.save(
            fig,
            "missing_correlation",
            title,
            "Correlation between the missing/not-missing patterns of columns with gaps. "
            "High values mean the gaps tend to occur in the same rows. Descriptive only.",
            "missingness",
        )
        headline["figures"]["missing_correlation"] = rec["rel_path"]
        headline["top_missing_correlation"] = {"a": str(a), "b": str(b), "r": safe_round(v, 3)}

    rows = [
        {"Column": str(c), "Missing": int(per_col[c]), "Missing %": columns_info[str(c)]["pct_missing"]}
        for c in cols_with_missing
    ]
    tables["missing_summary"] = df_to_markdown(rows, ["Column", "Missing", "Missing %"], {"Missing", "Missing %"})
    return headline, tables
