"""Shared plotting helpers for the EDA module (Section 10).

Every figure is a static PNG, saved with the non-interactive ``Agg`` backend, using one
consistent seaborn ``whitegrid`` style and one palette. This module has no imports from the
rest of ``ads`` so that the plotting code stays easy to test in isolation.
"""

from __future__ import annotations

import re
import textwrap
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Iterator, Sequence

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import seaborn as sns  # noqa: E402

# One palette for the whole report.
PRIMARY = "#3B6EA8"
SECONDARY = "#E07B39"
ACCENT = "#5A9E6F"
MUTED = "#8C8C8C"
WARN = "#C0392B"
SEQUENTIAL_CMAP = "Blues"
DIVERGING_CMAP = "RdBu_r"
CATEGORY_COLORS = [PRIMARY, SECONDARY, ACCENT, "#8E6BB0", "#C9A227", "#4BA3B8", MUTED, WARN]

DESCRIPTIVE_NOTE = "Descriptive coefficients only; no hypothesis tests were run."


@dataclass
class EDASettings:
    """Plain settings object built from ``EDAConfig`` (+ a few insight thresholds)."""

    dpi: int = 150
    max_numeric_plots: int = 30
    max_categorical_plots: int = 30
    batch_panel_size: int = 6
    top_categories_shown: int = 15
    missing_heatmap_max_rows: int = 500
    scatter_max_points: int = 5000
    top_bivariate_pairs: int = 6
    max_group_levels_box: int = 8
    collinearity_threshold: float = 0.90
    skew_threshold: float = 1.0
    outlier_pct_threshold: float = 0.05
    rare_level_threshold: float = 0.01
    minority_imbalance_threshold: float = 0.10
    max_detail_figures: int = 12
    max_cramers_columns: int = 30
    max_cramers_levels: int = 50
    random_state: int = 0


def apply_style() -> None:
    """Apply the shared figure style (call once before plotting)."""
    sns.set_theme(style="whitegrid", context="notebook", font_scale=0.9)
    plt.rcParams.update(
        {
            "figure.facecolor": "white",
            "axes.titlesize": 10.5,
            "axes.titleweight": "semibold",
            "axes.labelsize": 9.5,
            "xtick.labelsize": 8.5,
            "ytick.labelsize": 8.5,
            "legend.fontsize": 8,
            "figure.titlesize": 12.5,
            "figure.titleweight": "bold",
            "axes.prop_cycle": matplotlib.cycler(color=CATEGORY_COLORS),
            "savefig.facecolor": "white",
        }
    )


_SLUG_RE = re.compile(r"[^a-z0-9]+")


def slugify(name: str, max_len: int = 40) -> str:
    """Turn a column name into a safe, deterministic filename fragment."""
    slug = _SLUG_RE.sub("_", str(name).lower()).strip("_")
    return (slug or "col")[:max_len]


def short_label(value: Any, width: int = 28) -> str:
    """Shorten long category labels so axis text stays readable."""
    text = str(value)
    if len(text) <= width:
        return text
    return text[: width - 1] + "…"


def wrap_title(text: str, width: int = 70) -> str:
    """Wrap a long title onto several lines."""
    return "\n".join(textwrap.wrap(text, width=width)) or text


def chunked(items: Sequence[Any], size: int) -> Iterator[list[Any]]:
    """Yield successive chunks of ``size`` items."""
    size = max(1, int(size))
    for i in range(0, len(items), size):
        yield list(items[i : i + size])


def fmt_num(value: float | int | None, digits: int = 2) -> str:
    """Compact number formatting for labels (thousands separators, fixed decimals)."""
    if value is None:
        return "n/a"
    try:
        v = float(value)
    except (TypeError, ValueError):
        return str(value)
    if v != v:  # NaN
        return "n/a"
    if abs(v) >= 1000 and float(v).is_integer():
        return f"{int(v):,}"
    if abs(v) >= 1000:
        return f"{v:,.{digits}f}"
    if float(v).is_integer():
        return f"{int(v)}"
    return f"{v:.{digits}f}"


def fmt_pct(part: float, whole: float) -> str:
    """Percent label with one decimal; uses two decimals near 0% or 100% so 99.99% never shows as 100.0%."""
    if not whole:
        return "0.0%"
    v = 100.0 * float(part) / float(whole)
    if (0 < v < 0.1) or (99.9 < v < 100):
        return f"{v:.2f}%"
    return f"{v:.1f}%"


def grid_shape(n_panels: int, n_cols: int = 2) -> tuple[int, int]:
    """Rows and columns for a multi-panel figure."""
    n_cols = max(1, min(n_cols, n_panels))
    n_rows = (n_panels + n_cols - 1) // n_cols
    return n_rows, n_cols


def hide_unused(axes: Iterable[Any], n_used: int) -> None:
    """Turn off axes that were not used in a grid."""
    for i, ax in enumerate(axes):
        if i >= n_used:
            ax.set_visible(False)


@dataclass
class FigureSink:
    """Saves figures with deterministic names and records their metadata."""

    fig_dir: Path
    dpi: int = 150
    records: list[dict[str, str]] = field(default_factory=list)
    _used: set[str] = field(default_factory=set)

    def __post_init__(self) -> None:
        self.fig_dir = Path(self.fig_dir)
        self.fig_dir.mkdir(parents=True, exist_ok=True)

    def unique_name(self, stem: str) -> str:
        """Return ``stem.png``, adding ``_2``, ``_3``… if that name was already used."""
        name = f"{stem}.png"
        k = 2
        while name in self._used:
            name = f"{stem}_{k}.png"
            k += 1
        self._used.add(name)
        return name

    def save(self, fig: Any, stem: str, title: str, caption: str, section: str) -> dict[str, str]:
        """Save ``fig`` as PNG, close it, and record its metadata."""
        filename = self.unique_name(stem)
        path = self.fig_dir / filename
        # metadata={"Software": None} keeps the PNG bytes identical between runs.
        fig.savefig(path, dpi=self.dpi, bbox_inches="tight", metadata={"Software": None})
        plt.close(fig)
        record = {
            "filename": filename,
            "path": str(path),
            "rel_path": f"figures/{filename}",
            "title": title,
            "caption": caption,
            "section": section,
        }
        self.records.append(record)
        return record


def df_to_markdown(rows: list[dict[str, Any]], columns: list[str], align_right: set[str] | None = None) -> str:
    """Render a list of dict rows as a GitHub-style markdown table (no extra dependency)."""
    if not rows:
        return "_No rows._\n"
    align_right = align_right or set()

    def cell(v: Any) -> str:
        if v is None:
            return ""
        if isinstance(v, bool):
            return str(v)
        if isinstance(v, int):
            return f"{v:,}"
        if isinstance(v, float):
            if v != v:
                return ""
            if v.is_integer():
                return f"{int(v):,}"
            return f"{v:,.3f}".rstrip("0").rstrip(".")
        return str(v).replace("|", "\\|").replace("\n", " ")

    header = "| " + " | ".join(columns) + " |"
    sep = "| " + " | ".join("---:" if c in align_right else ":---" for c in columns) + " |"
    body = ["| " + " | ".join(cell(r.get(c)) for c in columns) + " |" for r in rows]
    return "\n".join([header, sep, *body]) + "\n"
