"""Chart generation for individual findings and summary distributions (Phase 5 Section 8)."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")  # Non-interactive background backend
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from veridata.contracts.findings import Finding
from veridata.contracts.hypothesis import RelationshipType
from veridata.reporting.facts import FactRegistry

logger = logging.getLogger("veridata.reporting.charts")

# Colorblind-safe palette (Okabe-Ito friendly)
PALETTE = ["#0072B2", "#D55E00", "#009E73", "#CC79A7", "#F0E442", "#56B4E9"]


def setup_style() -> None:
    plt.rcParams.update({
        "font.size": 10,
        "axes.labelsize": 10,
        "axes.titlesize": 11,
        "xtick.labelsize": 9,
        "ytick.labelsize": 9,
        "figure.titlesize": 12,
        "figure.dpi": 150,
        "axes.spines.top": False,
        "axes.spines.right": False,
    })


def plot_finding(
    finding: Finding,
    df: pd.DataFrame,
    registry: FactRegistry | None = None,
    out_path: Path | str | None = None,
) -> Path:
    """Generate and save an publication-quality, colorblind-safe chart for a Finding."""
    setup_style()
    hid = finding.hypothesis.id
    col_a = finding.hypothesis.column_a
    col_b = finding.hypothesis.column_b
    rel = finding.hypothesis.relationship

    sub = df[[col_a, col_b]].dropna()
    fig, ax = plt.subplots(figsize=(6.5, 4.0))

    try:
        if rel == RelationshipType.NUM_BINARY:
            sns.boxplot(
                data=sub,
                x=col_b,
                y=col_a,
                ax=ax,
                palette=PALETTE[:2],
                width=0.4,
                boxprops=dict(alpha=0.7),
            )
            # Add jittered points
            sns.stripplot(
                data=sub.sample(min(len(sub), 500), random_state=42),
                x=col_b,
                y=col_a,
                ax=ax,
                color="black",
                alpha=0.25,
                size=3,
                jitter=0.2,
            )
            ax.set_title(f"{col_a} by {col_b}")

        elif rel == RelationshipType.NUM_CATEGORICAL:
            order = sub.groupby(col_b)[col_a].median().sort_values(ascending=False).index[:12]
            sub_filtered = sub[sub[col_b].isin(order)]
            sns.boxplot(
                data=sub_filtered,
                x=col_b,
                y=col_a,
                order=order,
                ax=ax,
                palette=PALETTE,
                width=0.5,
            )
            ax.set_title(f"{col_a} across {col_b}")
            ax.tick_params(axis="x", rotation=30)

        elif rel == RelationshipType.NUM_NUM:
            if len(sub) > 3000:
                ax.hexbin(sub[col_a], sub[col_b], gridsize=30, cmap="Blues", mincnt=1)
            else:
                ax.scatter(sub[col_a], sub[col_b], alpha=0.35, color=PALETTE[0], edgecolors="none")
            # Linear trend
            try:
                sns.regplot(
                    data=sub.sample(min(len(sub), 1000), random_state=42),
                    x=col_a,
                    y=col_b,
                    ax=ax,
                    scatter=False,
                    color=PALETTE[1],
                    line_kws={"linewidth": 2},
                )
            except Exception:
                pass
            ax.set_title(f"{col_a} vs {col_b}")

        elif rel == RelationshipType.CAT_CAT:
            ct = pd.crosstab(sub[col_a], sub[col_b], normalize="index")
            ct.plot(kind="bar", stacked=True, ax=ax, colormap="tab10", alpha=0.85)
            ax.set_ylabel("Proportion")
            ax.set_title(f"Distribution of {col_b} across {col_a}")
            ax.tick_params(axis="x", rotation=30)
            ax.legend(title=col_b, bbox_to_anchor=(1.02, 1), loc="upper left")

        else:
            ax.text(0.5, 0.5, f"{col_a} vs {col_b}", ha="center", va="center")

        fig.tight_layout()

        if out_path is None:
            p = Path(f"outputs/figures/{hid}.png")
        else:
            p = Path(out_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(p, dpi=150, metadata={"Software": None})
        return p

    finally:
        plt.close(fig)


def plot_distribution(
    df: pd.DataFrame,
    column: str,
    group_column: str | None = None,
    out_path: Path | str | None = None,
) -> Path:
    """Plot single column distribution, optionally grouped."""
    setup_style()
    fig, ax = plt.subplots(figsize=(6.5, 3.8))

    try:
        sub = df[[column] + ([group_column] if group_column else [])].dropna()
        is_numeric = pd.api.types.is_numeric_dtype(sub[column])

        if is_numeric:
            if group_column:
                sns.histplot(data=sub, x=column, hue=group_column, ax=ax, kde=True, palette=PALETTE)
                ax.set_title(f"Distribution of {column} by {group_column}")
            else:
                sns.histplot(data=sub, x=column, ax=ax, kde=True, color=PALETTE[0])
                ax.set_title(f"Distribution of {column}")
        else:
            counts = sub[column].value_counts().head(15)
            counts.plot(kind="bar", ax=ax, color=PALETTE[0])
            ax.set_title(f"Value Counts of {column}")
            ax.tick_params(axis="x", rotation=30)

        fig.tight_layout()
        p = Path(out_path) if out_path else Path(f"outputs/figures/dist_{column}.png")
        p.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(p, dpi=150, metadata={"Software": None})
        return p
    finally:
        plt.close(fig)
