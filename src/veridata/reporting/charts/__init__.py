"""Phase 5 charts (Section 8). Every chart uses only the cleaned dataframe and the Finding; every
number printed on a chart (title, annotation, tick label) comes from the fact registry and is
returned in ``ChartResult.texts`` so the report gate can verify it."""

from veridata.reporting.charts.findings import ChartResult, plot_distribution, plot_finding
from veridata.reporting.charts.style import OKABE_ITO as PALETTE
from veridata.reporting.charts.style import apply_style as setup_style
from veridata.reporting.charts.summary import (
    plot_bh,
    plot_forest,
    plot_rejection_breakdown,
    plot_volcano,
)

__all__ = [
    "ChartResult",
    "PALETTE",
    "setup_style",
    "plot_bh",
    "plot_distribution",
    "plot_finding",
    "plot_forest",
    "plot_rejection_breakdown",
    "plot_volcano",
]
