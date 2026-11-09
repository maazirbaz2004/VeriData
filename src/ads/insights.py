"""Rule-based, deterministic insight generator (Section 11).

Entry point used by ``ads.pipeline.run_phase1``::

    generate_insights(profile, cleaning_result, eda_result, scaling_report, config, out_dir) -> InsightsReport

Writes ``insights.json`` (a list of records) and ``insights.md`` (automated section + the
analyst's MANUAL section, which is never overwritten on re-runs). No LLM is used.
"""

from __future__ import annotations

import json
from pathlib import Path

from ads.config import PipelineConfig
from ads.insight_rules import build_insights, extract_manual_block, render_insights_markdown
from ads.schemas import CleaningResult, DataProfile, EDAResult, InsightRecord, InsightsReport, ScalingReport

__all__ = ["generate_insights", "thresholds_from_config"]


def thresholds_from_config(config: PipelineConfig) -> dict[str, float]:
    """Map config thresholds (fractions) to the percent-based thresholds used in the rules."""
    ins, prof = config.insights, config.profiling
    return {
        "high_missing_pct": 100 * prof.high_missing_warning_threshold,
        "skew": config.scaling.skew_threshold,
        "zero_inflation_pct": 100 * ins.zero_inflation_threshold,
        "outlier_pct": 100 * ins.outlier_pct_threshold,
        "rare_level_pct": 100 * ins.rare_level_threshold,
        "small_n_dataset": ins.small_n_dataset_threshold,
        "small_n_group": ins.small_n_group_threshold,
        "collinearity": config.eda.collinearity_threshold,
    }


def generate_insights(
    profile: DataProfile,
    cleaning_result: CleaningResult,
    eda_result: EDAResult,
    scaling_report: ScalingReport | None,
    config: PipelineConfig,
    out_dir: Path | str,
) -> InsightsReport:
    """Build insights from computed values only and write insights.json / insights.md."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    items = build_insights(
        profile=profile.model_dump(mode="json"),
        log=[e.model_dump(mode="json") for e in cleaning_result.log],
        headline=eda_result.headline_numbers or {},
        scaling=scaling_report.model_dump(mode="json") if scaling_report is not None else {},
        dropped_columns=[d.model_dump(mode="json") for d in cleaning_result.dropped_columns],
        name_map=dict(cleaning_result.name_map),
        thresholds=thresholds_from_config(config),
    )
    records = [InsightRecord(**i) for i in items]

    json_path = out / "insights.json"
    json_path.write_text(
        json.dumps([r.model_dump(mode="json") for r in records], indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    md_path = out / "insights.md"
    existing = md_path.read_text(encoding="utf-8") if md_path.exists() else None
    manual = extract_manual_block(existing)
    md_path.write_text(render_insights_markdown(profile.dataset_name, items, manual), encoding="utf-8")

    return InsightsReport(
        dataset_name=profile.dataset_name,
        insights=records,
        markdown_path=str(md_path),
        json_path=str(json_path),
    )
