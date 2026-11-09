"""Per-dataset report rendering (Jinja2): ``report.md`` and ``report.html``.

Entry point used by ``ads.pipeline.run_phase1``::

    render_dataset_report(profile, cleaning_result, eda_result, scaling_report, out_dir) -> Path

``cleaning_log.md`` is already written by ``ads.cleaning.save_cleaning_log_markdown``; the
report links to it. Insights are read from the ``insights`` argument when given, otherwise
from ``<out_dir>/insights.json`` (written earlier in the pipeline by ``generate_insights``).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ads.insight_rules import extract_manual_block
from ads.report_render import build_context, render_html, render_markdown
from ads.schemas import CleaningResult, DataProfile, EDAResult, InsightsReport, ScalingReport

__all__ = ["render_dataset_report"]

_OUTPUT_DESCRIPTIONS = [
    ("profile.json", "full profile of the raw file"),
    ("profile_cleaned.json", "profile of the cleaned file"),
    ("column_schema.json", "Phase 2 handoff: type and role of every column"),
    ("cleaning_log.json", "every cleaning change (machine-readable)"),
    ("cleaning_log.md", "every cleaning change (readable)"),
    ("scaling_report.md", "scaling and transform decisions"),
    ("scaling_params.json", "fitted scaling parameters"),
    ("eda_summary.json", "every EDA number used by the insights"),
    ("insights.json", "automated insights with evidence"),
    ("insights.md", "automated + manual insights"),
    ("report.md", "this report (markdown)"),
    ("report.html", "this report (HTML)"),
    ("config_resolved.yaml", "the exact settings used for this run"),
]


def _display_path(p: str | None) -> str | None:
    """Short, machine-independent path for the report: relative to the project folder when
    possible, otherwise just the file name (so reports never contain temp or user folders)."""
    if not p:
        return None
    path = Path(p)
    try:
        return path.resolve().relative_to(Path.cwd().resolve()).as_posix()
    except ValueError:
        return path.name if path.is_absolute() else path.as_posix()


def _load_insights(insights: InsightsReport | None, out_dir: Path) -> list[dict[str, Any]]:
    if insights is not None:
        return [r.model_dump(mode="json") for r in insights.insights]
    p = out_dir / "insights.json"
    if p.exists():
        data = json.loads(p.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return data
    return []


def render_dataset_report(
    profile: DataProfile,
    cleaning_result: CleaningResult,
    eda_result: EDAResult,
    scaling_report: ScalingReport | None,
    out_dir: Path | str,
    insights: InsightsReport | None = None,
) -> Path:
    """Render report.md and report.html for one dataset; return the report.md path."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    name = profile.dataset_name
    ins = _load_insights(insights, out)
    md_existing = (out / "insights.md").read_text(encoding="utf-8") if (out / "insights.md").exists() else None
    manual_block = extract_manual_block(md_existing)

    scaling = scaling_report.model_dump(mode="json") if scaling_report is not None else {}
    scaling["scaled_csv_path"] = _display_path(scaling.get("scaled_csv_path"))
    outputs = [f"[{fn}]({fn}): {desc}" for fn, desc in _OUTPUT_DESCRIPTIONS if (out / fn).exists() or fn.startswith("report.")]
    outputs.append(f"`figures/`: {len(eda_result.figures)} PNG figures; `tables/`: EDA tables as markdown")
    outputs.append(f"`data/cleaned/{name}_cleaned.csv`: conservative cleaned data (primary, NaN kept)")
    outputs.append(f"`data/cleaned/{name}_cleaned_imputed.csv`: imputed cleaned data (secondary, with `__was_missing` flags)")
    if scaling.get("scaled_csv_path"):
        outputs.append(f"`{scaling['scaled_csv_path']}`: scaled convenience copy")

    ctx = build_context(
        name=name,
        profile=profile.model_dump(mode="json"),
        log=[e.model_dump(mode="json") for e in cleaning_result.log],
        cleaning_summary=dict(cleaning_result.summary),
        dropped_columns=[d.model_dump(mode="json") for d in cleaning_result.dropped_columns],
        outlier_report={k: v.model_dump(mode="json") for k, v in cleaning_result.outlier_report.items()},
        shapes={
            "raw": (int(profile.n_rows), int(profile.n_cols)),
            "conservative": tuple(int(x) for x in cleaning_result.df_clean_conservative.shape),  # type: ignore[dict-item]
            "imputed": tuple(int(x) for x in cleaning_result.df_clean_imputed.shape),  # type: ignore[dict-item]
        },
        figures=[{**f.model_dump(mode="json"), "rel_path": f"figures/{f.filename}"} for f in eda_result.figures],
        tables=dict(eda_result.tables_markdown),
        headline=dict(eda_result.headline_numbers),
        scaling=scaling,
        insights=ins,
        manual_block=manual_block,
        output_files=outputs,
    )
    md = render_markdown(ctx)
    md_path = out / "report.md"
    md_path.write_text(md, encoding="utf-8")
    (out / "report.html").write_text(render_html(md, f"Phase 1 Report — {name}"), encoding="utf-8")
    return md_path
