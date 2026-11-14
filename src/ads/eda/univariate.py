"""Single-column EDA (Sections 10.1, 10.3, 10.4, 10.7)."""

from __future__ import annotations

from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .plots import (
    ACCENT,
    MUTED,
    PRIMARY,
    SECONDARY,
    WARN,
    EDASettings,
    FigureSink,
    chunked,
    df_to_markdown,
    fmt_num,
    fmt_pct,
    grid_shape,
    short_label,
    slugify,
    sns,
    wrap_title,
)
from .stats import (
    as_float,
    as_labels,
    count_histogram_peaks,
    iqr_outlier_mask,
    normalized_entropy,
    pct,
    safe_round,
    value_counts_sorted,
)

# ---------------------------------------------------------------------------------------
# 10.1 Overview
# ---------------------------------------------------------------------------------------


def run_overview(
    df: pd.DataFrame,
    semantic_types: dict[str, str],
    roles: dict[str, str],
    sink: FigureSink,
    extra: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, str]]:
    """Overview table (markdown) and the semantic-type bar chart."""
    n_rows, n_cols = df.shape
    type_counts: dict[str, int] = {}
    for c in df.columns:
        t = semantic_types.get(str(c), "unknown")
        type_counts[t] = type_counts.get(t, 0) + 1
    type_counts = dict(sorted(type_counts.items(), key=lambda kv: (-kv[1], kv[0])))
    missing_cells = int(df.isna().sum().sum())
    memory_mb = round(float(df.memory_usage(deep=True).sum()) / 1_048_576, 3)
    excluded = sorted(str(c) for c in df.columns if roles.get(str(c)) in {"id", "excluded"})

    headline = {
        "n_rows": int(n_rows),
        "n_cols": int(n_cols),
        "memory_mb": memory_mb,
        "missing_cells": missing_cells,
        "pct_missing_cells": pct(missing_cells, n_rows * n_cols),
        "semantic_type_counts": type_counts,
        "excluded_columns": excluded,
        **extra,
        "figures": {},
    }

    rows = [
        {"Item": "Rows (cleaned, conservative)", "Value": f"{n_rows:,}"},
        {"Item": "Columns", "Value": f"{n_cols:,}"},
        {"Item": "Memory", "Value": f"{memory_mb} MB"},
        {"Item": "Missing cells", "Value": f"{missing_cells:,} ({headline['pct_missing_cells']}%)"},
    ]
    if "n_rows_raw" in extra:
        rows.insert(0, {"Item": "Rows (raw file)", "Value": f"{extra['n_rows_raw']:,}"})
    if "duplicate_rows_removed" in extra:
        rows.append({"Item": "Duplicate rows removed", "Value": f"{extra['duplicate_rows_removed']:,}"})
    for t, k in type_counts.items():
        rows.append({"Item": f"Columns typed `{t}`", "Value": str(k)})
    rows.append({"Item": "Columns left out of EDA (ID / excluded)", "Value": ", ".join(excluded) or "none"})
    tables = {"overview": df_to_markdown(rows, ["Item", "Value"])}

    if type_counts:
        labels = list(type_counts.keys())
        vals = list(type_counts.values())
        fig, ax = plt.subplots(figsize=(7, max(2.2, 0.42 * len(labels) + 1.0)))
        ax.barh(labels[::-1], vals[::-1], color=PRIMARY)
        for i, v in enumerate(vals[::-1]):
            ax.text(v + 0.05, i, str(v), va="center", fontsize=8.5)
        ax.set_xlabel("Number of columns")
        ax.set_xlim(0, max(vals) * 1.15 + 0.5)
        title = f"{n_cols} columns; the most common type is {labels[0]} ({vals[0]} columns)"
        ax.set_title(wrap_title(title))
        rec = sink.save(
            fig,
            "dtype_breakdown",
            title,
            "Count of columns by the semantic type the pipeline inferred (after cleaning).",
            "overview",
        )
        headline["figures"]["dtype_breakdown"] = rec["rel_path"]
    return headline, tables


# ---------------------------------------------------------------------------------------
# 10.3 Numeric columns
# ---------------------------------------------------------------------------------------


def _numeric_stats(x: pd.Series, discrete: bool) -> dict[str, Any]:
    v = x.dropna()
    n = int(len(v))
    if n == 0:
        return {"count": 0}
    out_mask = iqr_outlier_mask(x, 1.5)
    n_out = int(out_mask.sum())
    n_zero = int((v == 0).sum())
    return {
        "count": n,
        "mean": safe_round(v.mean(), 4),
        "std": safe_round(v.std(ddof=1), 4) if n > 1 else None,
        "min": safe_round(v.min(), 4),
        "q1": safe_round(v.quantile(0.25), 4),
        "median": safe_round(v.median(), 4),
        "q3": safe_round(v.quantile(0.75), 4),
        "max": safe_round(v.max(), 4),
        "skew": safe_round(v.skew(), 3) if n > 2 else None,
        "kurtosis": safe_round(v.kurt(), 3) if n > 3 else None,
        "n_zeros": n_zero,
        "pct_zeros": pct(n_zero, n),
        "n_outliers_iqr": n_out,
        "pct_outliers_iqr": pct(n_out, n),
        "n_unique": int(v.nunique()),
        "n_peaks_heuristic": None if discrete else count_histogram_peaks(v),
    }


def _hist_panel(ax: Any, v: pd.Series, discrete: bool, log1p: bool = False) -> None:
    data = np.log1p(v) if log1p else v
    nunique = int(data.nunique())
    use_discrete = discrete and nunique <= 40 and not log1p
    sns.histplot(
        x=data,
        ax=ax,
        color=PRIMARY,
        kde=(not use_discrete) and nunique > 10,
        discrete=use_discrete,
        bins="auto" if not use_discrete else "auto",
        edgecolor="white",
        linewidth=0.4 if len(data) <= 5000 else 0,
        alpha=0.85,
    )
    mean, median = float(data.mean()), float(data.median())
    ax.axvline(mean, color=SECONDARY, lw=1.6, label=f"mean {fmt_num(mean)}")
    ax.axvline(median, color=ACCENT, lw=1.6, ls="--", label=f"median {fmt_num(median)}")
    ax.legend(loc="upper right", frameon=True, framealpha=0.85)
    ax.set_ylabel("Count")
    ax.set_xlabel("")


def _box_strip(ax: Any, v: pd.Series, log1p: bool = False) -> None:
    data = np.log1p(v) if log1p else v
    ax.boxplot(
        data.to_numpy(),
        vert=False,
        widths=0.6,
        patch_artist=True,
        boxprops={"facecolor": "#D6E2F0", "edgecolor": PRIMARY},
        medianprops={"color": ACCENT, "lw": 1.6},
        flierprops={"marker": "o", "markersize": 2.5, "markerfacecolor": WARN, "markeredgecolor": WARN, "alpha": 0.5},
        whiskerprops={"color": PRIMARY},
        capprops={"color": PRIMARY},
    )
    ax.set_yticks([])
    ax.grid(axis="y", visible=False)


def run_numeric(
    df: pd.DataFrame,
    numeric_cols: list[str],
    discrete_cols: set[str],
    sink: FigureSink,
    settings: EDASettings,
    units: dict[str, str] | None = None,
) -> tuple[dict[str, Any], dict[str, str]]:
    """Distribution panels, per-column detail figures, outlier bar and summary table."""
    units = units or {}
    headline: dict[str, Any] = {"columns": {}, "figures": {}, "batches": []}
    tables: dict[str, str] = {}
    if not numeric_cols:
        tables["numeric_summary"] = "No numeric columns to summarize.\n"
        return headline, tables

    data = {c: as_float(df[c]) for c in numeric_cols}
    stats = {c: _numeric_stats(data[c], c in discrete_cols) for c in numeric_cols}
    for c in numeric_cols:
        headline["columns"][c] = dict(stats[c])

    plot_cols = [c for c in numeric_cols if stats[c]["count"] > 0]

    # --- batched distribution figures --------------------------------------------------
    for b_idx, batch in enumerate(chunked(plot_cols, settings.batch_panel_size), start=1):
        n_rows_grid, n_cols_grid = grid_shape(len(batch), 2)
        fig = plt.figure(figsize=(6.2 * n_cols_grid, 3.5 * n_rows_grid + 0.6), layout="constrained")
        outer = fig.add_gridspec(n_rows_grid, n_cols_grid)
        for i, c in enumerate(batch):
            r, k = divmod(i, n_cols_grid)
            inner = outer[r, k].subgridspec(2, 1, height_ratios=[4, 1])
            ax_h = fig.add_subplot(inner[0])
            ax_b = fig.add_subplot(inner[1], sharex=ax_h)
            v = data[c].dropna()
            _hist_panel(ax_h, v, c in discrete_cols)
            _box_strip(ax_b, v)
            sk = stats[c]["skew"]
            ax_h.set_title(short_label(c, 40) + (f"  (skew {sk:+.2f})" if sk is not None else ""))
            ax_b.set_xlabel(f"{c} ({units[c]})" if c in units else str(c))
            plt.setp(ax_h.get_xticklabels(), visible=False)
        n_total_batches = (len(plot_cols) + settings.batch_panel_size - 1) // settings.batch_panel_size
        most_skewed = max(batch, key=lambda c: abs(stats[c]["skew"] or 0.0))
        sk = stats[most_skewed]["skew"] or 0.0
        title = (
            f"Numeric distributions ({b_idx}/{n_total_batches}): most skewed here is "
            f"'{most_skewed}' (skew {sk:+.2f})"
        )
        fig.suptitle(wrap_title(title, 90))
        rec = sink.save(
            fig,
            f"numeric_distributions_{b_idx}",
            title,
            "Histogram (with a smooth density curve for many-valued columns) and a box plot per column. "
            "Orange line = mean, green dashed line = median; red dots are values beyond 1.5×IQR.",
            "numeric",
        )
        headline["batches"].append(rec["rel_path"])
        for c in batch:
            headline["columns"][c]["figure"] = rec["rel_path"]

    # --- per-column detail figures (skewed or outlier-heavy) ---------------------------
    flagged = [
        c
        for c in plot_cols
        if abs(stats[c]["skew"] or 0.0) > settings.skew_threshold
        or stats[c]["pct_outliers_iqr"] > 100 * settings.outlier_pct_threshold
    ]
    flagged.sort(key=lambda c: (-abs(stats[c]["skew"] or 0.0), str(c)))
    headline["n_detail_flagged"] = len(flagged)
    for c in flagged[: settings.max_detail_figures]:
        v = data[c].dropna()
        sk = stats[c]["skew"] or 0.0
        add_log = sk > settings.skew_threshold and float(v.min()) >= 0
        n_panels = 2 if add_log else 1
        fig = plt.figure(figsize=(6.2 * n_panels, 4.6), layout="constrained")
        gs = fig.add_gridspec(2, n_panels, height_ratios=[4, 1])
        ax_h = fig.add_subplot(gs[0, 0])
        ax_b = fig.add_subplot(gs[1, 0], sharex=ax_h)
        _hist_panel(ax_h, v, c in discrete_cols)
        _box_strip(ax_b, v)
        ax_h.set_title("Raw scale")
        ax_b.set_xlabel(f"{c} ({units[c]})" if c in units else str(c))
        plt.setp(ax_h.get_xticklabels(), visible=False)
        if add_log:
            ax_h2 = fig.add_subplot(gs[0, 1])
            ax_b2 = fig.add_subplot(gs[1, 1], sharex=ax_h2)
            _hist_panel(ax_h2, v, False, log1p=True)
            _box_strip(ax_b2, v, log1p=True)
            log_skew = safe_round(np.log1p(v).skew(), 2)
            ax_h2.set_title(f"log1p scale (skew {log_skew:+.2f})" if log_skew is not None else "log1p scale")
            ax_b2.set_xlabel(f"log1p({c})")
            plt.setp(ax_h2.get_xticklabels(), visible=False)
            headline["columns"][c]["log1p_skew"] = log_skew
        reasons = []
        if abs(sk) > settings.skew_threshold:
            reasons.append(f"{'right' if sk > 0 else 'left'}-skewed (skew {sk:+.2f})")
        if stats[c]["pct_outliers_iqr"] > 100 * settings.outlier_pct_threshold:
            reasons.append(f"{stats[c]['pct_outliers_iqr']:.1f}% IQR outliers")
        if len(reasons) == 2:
            title = f"'{c}' is {reasons[0]} and has {reasons[1]}"
        elif abs(sk) > settings.skew_threshold:
            title = f"'{c}' is {reasons[0]}"
        else:
            title = f"'{c}' has {reasons[0]}"
        fig.suptitle(wrap_title(title, 90))
        rec = sink.save(
            fig,
            f"numeric_detail_{slugify(c)}",
            title,
            "Close-up of a skewed or outlier-heavy column."
            + (" The right panel shows the same values on a log1p scale." if add_log else ""),
            "numeric",
        )
        headline["columns"][c]["detail_figure"] = rec["rel_path"]

    # --- outlier_summary.png ----------------------------------------------------------
    out_rows = sorted(plot_cols, key=lambda c: (-stats[c]["pct_outliers_iqr"], str(c)))
    vals = [stats[c]["pct_outliers_iqr"] for c in out_rows]
    if any(v > 0 for v in vals):
        show = out_rows[:30]
        show_vals = vals[:30]
        fig, ax = plt.subplots(figsize=(8, max(2.2, 0.32 * len(show) + 1.2)))
        thr = 100 * settings.outlier_pct_threshold
        colors = [WARN if v > thr else PRIMARY for v in show_vals]
        ax.barh([short_label(c) for c in show][::-1], show_vals[::-1], color=colors[::-1])
        for i, v in enumerate(show_vals[::-1]):
            ax.text(v + 0.1, i, f"{v:.1f}%", va="center", fontsize=8)
        ax.axvline(thr, color=MUTED, ls=":", lw=1.2, label=f"{thr:.0f}% guide line")
        ax.legend(loc="lower right")
        ax.set_xlabel("Values beyond 1.5×IQR (% of non-missing values)")
        ax.set_xlim(0, max(show_vals) * 1.2 + 0.5)
        title = f"'{show[0]}' has the most IQR outliers ({show_vals[0]:.1f}% of its values)"
        ax.set_title(wrap_title(title))
        rec = sink.save(
            fig,
            "outlier_summary",
            title,
            "Share of each numeric column's values outside 1.5×IQR. Outliers are only flagged, not removed, "
            "in the conservative cleaned data. Red bars are above the guide line.",
            "numeric",
        )
        headline["figures"]["outlier_summary"] = rec["rel_path"]
    else:
        headline["figures"]["outlier_summary"] = None

    # --- numeric_summary.md -----------------------------------------------------------
    rows = []
    for c in numeric_cols:
        s = stats[c]
        rows.append(
            {
                "Column": c,
                "Count": s.get("count"),
                "Mean": s.get("mean"),
                "Std": s.get("std"),
                "Min": s.get("min"),
                "Q1": s.get("q1"),
                "Median": s.get("median"),
                "Q3": s.get("q3"),
                "Max": s.get("max"),
                "Skew": s.get("skew"),
                "Kurtosis": s.get("kurtosis"),
                "% zeros": s.get("pct_zeros"),
                "% outliers (1.5×IQR)": s.get("pct_outliers_iqr"),
            }
        )
    cols = ["Column", "Count", "Mean", "Std", "Min", "Q1", "Median", "Q3", "Max", "Skew", "Kurtosis", "% zeros", "% outliers (1.5×IQR)"]
    tables["numeric_summary"] = df_to_markdown(rows, cols, set(cols[1:]))
    return headline, tables


# ---------------------------------------------------------------------------------------
# 10.4 Categorical / binary columns
# ---------------------------------------------------------------------------------------


def run_categorical(
    df: pd.DataFrame, categorical_cols: list[str], sink: FigureSink, settings: EDASettings
) -> tuple[dict[str, Any], dict[str, str]]:
    """Value-count bars, cardinality bar and categorical summary table."""
    headline: dict[str, Any] = {"columns": {}, "figures": {}, "batches": []}
    tables: dict[str, str] = {}
    if not categorical_cols:
        tables["categorical_summary"] = "No categorical or binary columns to summarize.\n"
        return headline, tables

    counts: dict[str, pd.Series] = {}
    for c in categorical_cols:
        labels = as_labels(df[c])
        vc = value_counts_sorted(labels)
        counts[c] = vc
        n = int(vc.sum())
        if n == 0:
            headline["columns"][c] = {"n_unique": 0, "count": 0}
            continue
        rare_cut = settings.rare_level_threshold * len(df)
        rare = [(str(k), int(v)) for k, v in vc.items() if v < rare_cut]
        rarest_label = str(vc.index[-1])
        headline["columns"][c] = {
            "count": n,
            "n_unique": int(len(vc)),
            "mode": str(vc.index[0]),
            "mode_count": int(vc.iloc[0]),
            "mode_pct": pct(vc.iloc[0], n),
            "rarest_level": rarest_label,
            "rarest_count": int(vc.iloc[-1]),
            "rarest_pct": pct(vc.iloc[-1], n),
            "entropy_norm": safe_round(normalized_entropy(vc.to_numpy()), 3),
            "n_rare_levels": len(rare),
            "rare_levels": [{"level": k, "count": v, "pct_of_rows": pct(v, len(df))} for k, v in rare[:20]],
            "smallest_group_n": int(vc.iloc[-1]),
        }

    plot_cols = [c for c in categorical_cols if headline["columns"][c].get("count", 0) > 0]
    top_k = settings.top_categories_shown
    for b_idx, batch in enumerate(chunked(plot_cols, settings.batch_panel_size), start=1):
        n_rows_grid, n_cols_grid = grid_shape(len(batch), 2)
        heights = []
        for c in batch:
            heights.append(min(len(counts[c]), top_k + 1))
        row_h = [max(heights[i : i + n_cols_grid]) for i in range(0, len(heights), n_cols_grid)]
        fig, axes = plt.subplots(
            n_rows_grid,
            n_cols_grid,
            figsize=(6.4 * n_cols_grid, sum(max(2.0, 0.3 * h + 1.1) for h in row_h) + 0.6),
            squeeze=False,
            gridspec_kw={"height_ratios": [max(2.0, 0.3 * h + 1.1) for h in row_h]},
            layout="constrained",
        )
        flat = list(axes.flat)
        for ax, c in zip(flat, batch):
            vc = counts[c]
            n = int(vc.sum())
            shown = vc.head(top_k)
            labels = [short_label(x) for x in shown.index]
            vals = list(shown.to_numpy())
            if len(vc) > top_k:
                labels.append(f"Other ({len(vc) - top_k} levels)")
                vals.append(int(vc.iloc[top_k:].sum()))
            pcts = [100.0 * v / n for v in vals]
            colors = [PRIMARY] * len(vals)
            if len(vc) <= top_k:
                colors[-1] = SECONDARY  # mark the minority level
            ax.barh(labels[::-1], pcts[::-1], color=colors[::-1])
            for i, (p, v) in enumerate(zip(pcts[::-1], vals[::-1])):
                ax.text(p + 0.4, i, fmt_pct(v, n), va="center", fontsize=7.5)
            ax.set_xlim(0, max(pcts) * 1.2 + 1)
            ax.set_xlabel("% of non-missing rows")
            h = headline["columns"][c]
            ax.set_title(
                f"{short_label(c, 30)}: mode '{short_label(h['mode'], 18)}' {fmt_pct(vc.iloc[0], n)}; "
                f"rarest {fmt_pct(vc.iloc[-1], n)}"
            )
        for ax in flat[len(batch) :]:
            ax.set_visible(False)
        n_total_batches = (len(plot_cols) + settings.batch_panel_size - 1) // settings.batch_panel_size
        most_dominated = max(batch, key=lambda c: (headline["columns"][c]["mode_pct"], str(c)))
        md = headline["columns"][most_dominated]
        title = (
            f"Categorical distributions ({b_idx}/{n_total_batches}): most lopsided here is "
            f"'{most_dominated}' (top level {fmt_pct(md['mode_count'], md['count'])})"
        )
        fig.suptitle(wrap_title(title, 90))
        rec = sink.save(
            fig,
            f"categorical_distributions_{b_idx}",
            title,
            f"Share of rows per level (top {top_k} levels; the rest are grouped as 'Other'). "
            "The orange bar marks the smallest (minority) level.",
            "categorical",
        )
        headline["batches"].append(rec["rel_path"])
        for c in batch:
            headline["columns"][c]["figure"] = rec["rel_path"]

    # --- cardinality_bar.png ----------------------------------------------------------
    card = sorted(plot_cols, key=lambda c: (-headline["columns"][c]["n_unique"], str(c)))
    vals = [headline["columns"][c]["n_unique"] for c in card]
    if card:
        show, show_vals = card[:30], vals[:30]
        fig, ax = plt.subplots(figsize=(8, max(2.2, 0.32 * len(show) + 1.2)))
        ax.barh([short_label(c) for c in show][::-1], show_vals[::-1], color=PRIMARY)
        for i, v in enumerate(show_vals[::-1]):
            ax.text(v * 1.03 + 0.05, i, str(v), va="center", fontsize=8)
        wide = max(show_vals) / max(1, min(show_vals)) >= 20
        if wide:
            ax.set_xscale("log")
        ax.set_xlabel("Number of distinct levels" + (" (log scale)" if wide else ""))
        title = f"'{show[0]}' has the most levels ({show_vals[0]})"
        ax.set_title(wrap_title(title))
        rec = sink.save(
            fig,
            "cardinality_bar",
            title,
            "Number of distinct values in each categorical or binary column.",
            "categorical",
        )
        headline["figures"]["cardinality_bar"] = rec["rel_path"]

    rows = []
    for c in categorical_cols:
        h = headline["columns"][c]
        if not h.get("count"):
            rows.append({"Column": c, "Levels": 0})
            continue
        rows.append(
            {
                "Column": c,
                "Levels": h["n_unique"],
                "Mode": short_label(h["mode"], 24),
                "Mode %": h["mode_pct"],
                "Entropy (0-1)": h["entropy_norm"],
                "Rarest level": short_label(h["rarest_level"], 24),
                "Rarest %": h["rarest_pct"],
                "Levels under 1% of rows": h["n_rare_levels"],
            }
        )
    cols = ["Column", "Levels", "Mode", "Mode %", "Entropy (0-1)", "Rarest level", "Rarest %", "Levels under 1% of rows"]
    tables["categorical_summary"] = df_to_markdown(rows, cols, {"Levels", "Mode %", "Entropy (0-1)", "Rarest %", "Levels under 1% of rows"})
    return headline, tables


# ---------------------------------------------------------------------------------------
# 10.7 Datetime columns
# ---------------------------------------------------------------------------------------


def run_datetime(
    df: pd.DataFrame, datetime_cols: list[str], sink: FigureSink
) -> tuple[dict[str, Any], dict[str, str]]:
    """Counts over time, date range and the largest gap for each datetime column."""
    headline: dict[str, Any] = {"columns": {}, "figures": {}}
    tables: dict[str, str] = {}
    rows = []
    for c in datetime_cols:
        s = pd.to_datetime(df[c], errors="coerce")
        v = s.dropna().sort_values()
        if len(v) < 2:
            continue
        span_days = (v.iloc[-1] - v.iloc[0]).days
        if span_days <= 92:
            rule, unit = "D", "day"
        elif span_days <= 730:
            rule, unit = "W", "week"
        else:
            rule, unit = "MS", "month"
        counts = v.to_frame(name="t").set_index("t").assign(n=1)["n"].resample(rule).sum()
        gaps = v.diff().dropna()
        max_gap = int(gaps.max().days) if len(gaps) else 0
        info = {
            "count": int(len(v)),
            "min_date": v.iloc[0].isoformat(),
            "max_date": v.iloc[-1].isoformat(),
            "span_days": int(span_days),
            "resample_unit": unit,
            "largest_gap_days": max_gap,
            "busiest_period": counts.idxmax().isoformat() if len(counts) else None,
        }
        fig, ax = plt.subplots(figsize=(9, 3.4))
        ax.plot(counts.index, counts.to_numpy(), color=PRIMARY, lw=1.6)
        ax.fill_between(counts.index, counts.to_numpy(), color=PRIMARY, alpha=0.15)
        ax.set_ylabel(f"Rows per {unit}")
        ax.set_xlabel(str(c))
        title = (
            f"'{c}' runs from {v.iloc[0].date()} to {v.iloc[-1].date()}; "
            f"largest gap between records is {max_gap} days"
        )
        ax.set_title(wrap_title(title, 90))
        rec = sink.save(fig, f"datetime_{slugify(c)}", title, f"Number of rows per {unit} for '{c}'.", "datetime")
        info["figure"] = rec["rel_path"]
        headline["columns"][c] = info
        rows.append(
            {"Column": c, "First": info["min_date"][:10], "Last": info["max_date"][:10], "Span (days)": span_days, "Largest gap (days)": max_gap}
        )
    if rows:
        tables["datetime_summary"] = df_to_markdown(rows, ["Column", "First", "Last", "Span (days)", "Largest gap (days)"], {"Span (days)", "Largest gap (days)"})
    return headline, tables
