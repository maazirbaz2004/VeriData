"""Shared chart style: Okabe-Ito colour-blind-safe palette, fonts >= 10 pt, fixed size, 150 dpi."""

from __future__ import annotations

import textwrap
from dataclasses import dataclass, field
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

OKABE_ITO = ["#0072B2", "#E69F00", "#009E73", "#D55E00", "#56B4E9", "#CC79A7", "#F0E442", "#000000"]
ACCEPT, REJECT, FLOOR, MUTED = "#0072B2", "#999999", "#E69F00", "#BBBBBB"
FIGSIZE = (6.5, 4.2)
DPI = 150


@dataclass
class ChartResult:
    path: Path
    title: str
    texts: list[str] = field(default_factory=list)  # every string drawn on the chart (for the verifier)


def apply_style() -> None:
    plt.rcParams.update({
        "font.size": 10, "axes.titlesize": 11, "axes.labelsize": 10, "xtick.labelsize": 10, "ytick.labelsize": 10,
        "legend.fontsize": 10, "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True,
        "grid.alpha": 0.25, "figure.facecolor": "white", "savefig.facecolor": "white", "axes.prop_cycle": matplotlib.cycler(color=OKABE_ITO),
    })


def wrap(s: str, width: int = 60) -> str:
    return "\n".join(textwrap.wrap(str(s), width)) or str(s)


def short(s: str, n: int = 40) -> str:
    s = str(s)
    return s if len(s) <= n else s[: n - 1] + "…"


def labels(series: pd.Series) -> pd.Series:
    """Group labels as strings, normalising 1.0 -> '1' so they match the test's labels."""
    def f(v: object) -> object:
        if v is None or (isinstance(v, float) and np.isnan(v)):
            return None
        if isinstance(v, float) and v.is_integer():
            return str(int(v))
        return str(v)
    return series.map(f)


def save(fig: plt.Figure, path: Path, dpi: int = DPI) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=dpi, metadata={"Software": None})
    plt.close(fig)
    return path
