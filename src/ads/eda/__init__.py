"""Automated EDA for Phase 1 (Section 10).

Entry point used by ``ads.pipeline.run_phase1``::

    run_eda(df_clean_conservative, profile, schema, config, out_dir) -> EDAResult

Writes PNG figures to ``<out_dir>/figures/``, markdown tables to ``<out_dir>/tables/`` and a
machine-readable ``<out_dir>/eda_summary.json`` with every headline number. All statistics
are descriptive; no p-values are computed.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from ads.config import PipelineConfig
from ads.schemas import ColumnSchemaEntry, DataProfile, EDAResult, FigureArtifact

from .core import classify_columns, run_eda_core
from .plots import EDASettings

__all__ = ["run_eda", "settings_from_config", "classify_columns", "run_eda_core", "EDASettings"]


def settings_from_config(config: PipelineConfig) -> EDASettings:
    """Build plain EDA settings from the merged pipeline config."""
    e = config.eda
    return EDASettings(
        dpi=e.dpi,
        max_numeric_plots=e.max_numeric_plots,
        max_categorical_plots=e.max_categorical_plots,
        batch_panel_size=e.batch_panel_size,
        top_categories_shown=e.top_categories_shown,
        missing_heatmap_max_rows=e.missing_heatmap_max_rows,
        scatter_max_points=e.scatter_max_points,
        top_bivariate_pairs=e.top_bivariate_pairs,
        max_group_levels_box=e.max_group_levels_box,
        collinearity_threshold=e.collinearity_threshold,
        skew_threshold=config.scaling.skew_threshold,
        outlier_pct_threshold=config.insights.outlier_pct_threshold,
        rare_level_threshold=config.insights.rare_level_threshold,
        minority_imbalance_threshold=config.profiling.minority_imbalance_threshold,
    )


def _resolve_target(target: str | None, columns: list[str]) -> str | None:
    if not target:
        return None
    if target in columns:
        return target
    stripped = " ".join(str(target).split())
    return stripped if stripped in columns else None


def run_eda(
    df: pd.DataFrame,
    profile: DataProfile,
    schema: dict[str, ColumnSchemaEntry],
    config: PipelineConfig,
    out_dir: Path | str,
) -> EDAResult:
    """Run the full automated EDA on the conservative cleaned frame."""
    semantic_types = {str(k): v.semantic_type.value for k, v in schema.items()}
    roles = {str(k): v.role.value for k, v in schema.items()}
    target = _resolve_target(config.target, [str(c) for c in df.columns])
    extra: dict[str, Any] = {
        "dataset_name": profile.dataset_name,
        "n_rows_raw": int(profile.n_rows),
        "n_cols_raw": int(profile.n_cols),
        "n_duplicate_rows_detected": int(profile.n_duplicate_rows),
    }
    result = run_eda_core(df, semantic_types, roles, target, settings_from_config(config), out_dir, extra)
    figures = [
        FigureArtifact(
            filename=r["filename"],
            path=r["path"],
            title=r["title"],
            caption=r["caption"],
            section=r["section"],
        )
        for r in result["figures"]
    ]
    return EDAResult(figures=figures, tables_markdown=result["tables"], headline_numbers=result["headline"])
