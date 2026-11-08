"""End-to-end Phase 1 pipeline orchestrator (Section 14.1)."""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path

from ads.cleaning import (
    clean_dataset,
    save_cleaning_log_json,
    save_cleaning_log_markdown,
)
from ads.config import PipelineConfig, dump_resolved_config, load_config
from ads.ingestion import load_csv
from ads.profiling import (
    build_column_schema,
    profile_dataset,
    save_column_schema_json,
    save_profile_json,
)
from ads.scaling import analyze_scaling
from ads.schemas import (
    CleaningResult,
    ColumnSchemaEntry,
    DataProfile,
    EDAResult,
    InsightsReport,
    Phase1Result,
    ScalingReport,
)

logger = logging.getLogger("ads.pipeline")

_MANUAL_START = "<!-- MANUAL:START -->"
_MANUAL_END = "<!-- MANUAL:END -->"
_DEFAULT_MANUAL_TEMPLATE = f"""{_MANUAL_START}
- **What surprised you?** *(Analyst to fill in)*
- **Which relationships look real vs. likely spurious?** *(Analyst to fill in)*
- **Anything suspicious about data collection or missingness?** *(Analyst to fill in)*
- **Known domain relationships present or absent?** *(Analyst to fill in)*
- **Target findings for Phase 5 benchmark recovery:** *(Analyst to fill in)*
{_MANUAL_END}"""


def _extract_existing_manual_block(md_path: Path) -> str:
    """Preserve human-written content between <!-- MANUAL:START --> and <!-- MANUAL:END --> (Section 11)."""
    if not md_path.exists():
        return _DEFAULT_MANUAL_TEMPLATE
    content = md_path.read_text(encoding="utf-8")
    start_idx = content.find(_MANUAL_START)
    end_idx = content.find(_MANUAL_END)
    if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
        return content[start_idx : end_idx + len(_MANUAL_END)]
    return _DEFAULT_MANUAL_TEMPLATE


def _write_fallback_insights_and_report(
    dataset_name: str,
    raw_profile: DataProfile,
    cleaning_res: CleaningResult,
    scaling_report: ScalingReport,
    out_dir: Path,
) -> tuple[Path, Path]:
    """Write deterministic fallback insights and report artifacts if Partner 2's modules are not yet merged."""
    insights_json_path = out_dir / "insights.json"
    insights_md_path = out_dir / "insights.md"
    report_md_path = out_dir / "report.md"
    report_html_path = out_dir / "report.html"

    manual_block = _extract_existing_manual_block(insights_md_path)
    if not insights_json_path.exists():
        insights_json_path.write_text("[]\n", encoding="utf-8")

    insights_md = "\n".join(
        [
            f"# Dataset Insights — `{dataset_name}`",
            "",
            "## Automated insights",
            "",
            f"- Dataset contains `{raw_profile.n_rows}` raw rows and `{raw_profile.n_cols}` columns (`{len(cleaning_res.df_clean_conservative)}` cleaned rows).",
            f"- Duplicate rows detected (normalized): `{raw_profile.n_duplicate_rows}`.",
            "",
            "## Manual insights (written by the analyst)",
            "",
            manual_block,
            "",
        ]
    )
    insights_md_path.write_text(insights_md, encoding="utf-8")

    report_md = "\n".join(
        [
            f"# Phase 1 Dataset Report — `{dataset_name}`",
            "",
            "## 1. Overview",
            f"- **Source file:** `{raw_profile.source_file}`",
            f"- **SHA-256:** `{raw_profile.sha256}`",
            f"- **Raw shape:** `{raw_profile.n_rows}` rows x `{raw_profile.n_cols}` columns",
            f"- **Cleaned shape (conservative):** `{len(cleaning_res.df_clean_conservative)}` rows x `{len(cleaning_res.df_clean_conservative.columns)}` columns",
            f"- **Cleaned shape (imputed):** `{len(cleaning_res.df_clean_imputed)}` rows x `{len(cleaning_res.df_clean_imputed.columns)}` columns",
            "",
            "## 2. Column Profile Summary",
            "",
            "| Column | Raw Dtype | Semantic Type | Missing % | Unique | Reason |",
            "| :--- | :--- | :--- | ---: | ---: | :--- |",
        ]
        + [
            f"| `{c.name}` | `{c.raw_dtype}` | `{c.semantic_type.value}` | {c.pct_missing:.1%} | {c.n_unique} | {c.semantic_type_reason} |"
            for c in raw_profile.columns
        ]
        + [
            "",
            "## 3. Scaling Decision",
            "",
            f"> {scaling_report.decision_paragraph}",
            "",
        ]
    )
    report_md_path.write_text(report_md, encoding="utf-8")

    html_body = (
        "<!DOCTYPE html>\n<html><head><meta charset='utf-8'>"
        f"<title>Phase 1 Report - {dataset_name}</title></head><body>"
        f"<pre>{report_md}</pre></body></html>\n"
    )
    report_html_path.write_text(html_body, encoding="utf-8")

    return insights_json_path, report_md_path


def run_phase1(
    input_csv: Path | str,
    dataset_name: str,
    out_dir: Path | str | None = None,
    config: PipelineConfig | None = None,
    cleaned_dir: Path | str = Path("data/cleaned"),
) -> Phase1Result:
    """Execute the full Phase 1 pipeline for a single CSV dataset (Section 14.1)."""
    t0 = time.perf_counter()
    cfg = (config or load_config()).model_copy(deep=True)
    cfg.name = dataset_name
    cfg.file = str(input_csv)

    target_out_dir = Path(out_dir) if out_dir is not None else Path("outputs") / dataset_name
    target_out_dir.mkdir(parents=True, exist_ok=True)
    (target_out_dir / "figures").mkdir(parents=True, exist_ok=True)

    target_cleaned_dir = Path(cleaned_dir)
    target_cleaned_dir.mkdir(parents=True, exist_ok=True)

    dump_resolved_config(cfg, target_out_dir / "config_resolved.yaml")

    # 1. Load CSV (raw strings + naive parse)
    ing = load_csv(input_csv, config=cfg)

    # 2. Profile raw dataset
    raw_profile = profile_dataset(
        ing.df_raw_str,
        df_naive=ing.df_naive,
        ingestion_meta=ing.metadata,
        config=cfg,
        dataset_name=dataset_name,
    )

    # 3. Clean dataset (Steps 1-11)
    cleaning_res = clean_dataset(
        ing.df_raw_str,
        raw_profile,
        config=cfg,
        ingestion_name_changes=ing.metadata.column_name_changes,
    )

    # 4. Write cleaned CSVs (conservative and imputed)
    cons_csv_path = target_cleaned_dir / f"{dataset_name}_cleaned.csv"
    imp_csv_path = target_cleaned_dir / f"{dataset_name}_cleaned_imputed.csv"
    cleaning_res.df_clean_conservative.to_csv(
        cons_csv_path, index=False, encoding="utf-8", lineterminator="\n"
    )
    cleaning_res.df_clean_imputed.to_csv(
        imp_csv_path, index=False, encoding="utf-8", lineterminator="\n"
    )

    # 5. Profile cleaned dataset & build Phase 2 handoff schema
    # Preserve semantic types inferred on raw data for surviving columns so post-cleaning schema stays consistent
    raw_sem_map = {
        cleaning_res.name_map.get(c.name, c.name): c.semantic_type
        for c in raw_profile.columns
    }
    cfg_for_clean_prof = cfg.model_copy(deep=True)
    for col_c in cleaning_res.df_clean_conservative.columns:
        if col_c in raw_sem_map and col_c not in cfg_for_clean_prof.forced_types:
            cfg_for_clean_prof.forced_types[col_c] = raw_sem_map[col_c]

    cleaned_profile = profile_dataset(
        cleaning_res.df_clean_conservative.astype("string").fillna("").astype(str),
        df_naive=cleaning_res.df_clean_conservative,
        ingestion_meta=ing.metadata,
        config=cfg_for_clean_prof,
        dataset_name=dataset_name,
    )
    schema: dict[str, ColumnSchemaEntry] = build_column_schema(cleaned_profile, config=cfg)

    profile_json_path = save_profile_json(raw_profile, target_out_dir / "profile.json")
    save_profile_json(cleaned_profile, target_out_dir / "profile_cleaned.json")
    schema_json_path = save_column_schema_json(
        schema, target_out_dir / "column_schema.json"
    )

    # 6. Save cleaning logs
    cleaning_log_json_path = save_cleaning_log_json(
        cleaning_res.log, target_out_dir / "cleaning_log.json"
    )
    save_cleaning_log_markdown(
        cleaning_res.log,
        target_out_dir / "cleaning_log.md",
        dataset_name=dataset_name,
    )

    # 7. Scaling & transformation analysis + <name>_scaled.csv
    scaling_report = analyze_scaling(
        cleaning_res.df_clean_conservative,
        schema=schema,
        config=cfg,
        df_clean_imputed=cleaning_res.df_clean_imputed,
        dataset_name=dataset_name,
        out_dir=target_out_dir,
        cleaned_dir=target_cleaned_dir,
    )

    # 8. Optional integration with Partner 2's EDA, Insights, and Reporting modules
    eda_result = EDAResult()
    try:
        from ads.eda import run_eda  # type: ignore[import-not-found]

        eda_result = run_eda(
            cleaning_res.df_clean_conservative,
            raw_profile,
            schema,
            cfg,
            target_out_dir,
        )
    except ImportError:
        logger.debug("Partner 2 module ads.eda not yet present; skipping plot generation.")

    insights_json_path: Path | None = None
    report_md_path: Path | None = None
    try:
        from ads.insights import generate_insights  # type: ignore[import-not-found]

        ins_rep: InsightsReport = generate_insights(
            raw_profile, cleaning_res, eda_result, scaling_report, cfg, target_out_dir
        )
        if ins_rep.json_path:
            insights_json_path = Path(ins_rep.json_path)
    except ImportError:
        pass

    try:
        from ads.reporting import render_dataset_report  # type: ignore[import-not-found]

        report_md_path = render_dataset_report(
            raw_profile,
            cleaning_res,
            eda_result,
            scaling_report,
            target_out_dir,
        )
    except ImportError:
        fb_ins, fb_rep = _write_fallback_insights_and_report(
            dataset_name, raw_profile, cleaning_res, scaling_report, target_out_dir
        )
        if insights_json_path is None:
            insights_json_path = fb_ins
        report_md_path = fb_rep

    # 9. Write run_meta.json (stores wall-clock timestamps separately from deterministic artifacts per Section 16)
    elapsed_sec = round(time.perf_counter() - t0, 4)
    run_meta = {
        "dataset_name": dataset_name,
        "source_file": str(input_csv),
        "sha256": ing.metadata.sha256,
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "elapsed_seconds": elapsed_sec,
        "n_rows_raw": raw_profile.n_rows,
        "n_cols_raw": raw_profile.n_cols,
        "n_rows_cleaned_conservative": int(len(cleaning_res.df_clean_conservative)),
        "n_cols_cleaned_conservative": int(len(cleaning_res.df_clean_conservative.columns)),
        "n_rows_cleaned_imputed": int(len(cleaning_res.df_clean_imputed)),
        "n_cols_cleaned_imputed": int(len(cleaning_res.df_clean_imputed.columns)),
    }
    (target_out_dir / "run_meta.json").write_text(
        json.dumps(run_meta, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    logger.info(
        "Completed Phase 1 pipeline for '%s' in %.2fs -> %s",
        dataset_name,
        elapsed_sec,
        target_out_dir,
    )

    return Phase1Result(
        dataset_name=dataset_name,
        out_dir=target_out_dir,
        cleaned_conservative_csv=cons_csv_path,
        cleaned_imputed_csv=imp_csv_path,
        scaled_csv=Path(scaling_report.scaled_csv_path)
        if scaling_report.scaled_csv_path
        else None,
        profile_json=profile_json_path,
        column_schema_json=schema_json_path,
        cleaning_log_json=cleaning_log_json_path,
        insights_json=insights_json_path,
        report_md=report_md_path,
    )

