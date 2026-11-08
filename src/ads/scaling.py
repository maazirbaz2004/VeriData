"""Scaling and transformation analysis, recommendations, and convenience output (Section 11b)."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

from ads.config import PipelineConfig, load_config
from ads.schemas import (
    ColumnRole,
    ColumnScalingRecommendation,
    ColumnSchemaEntry,
    ScalingReport,
    SemanticType,
)


def render_scaling_report_markdown(report: ScalingReport) -> str:
    """Render scaling_report.md with per-column table and decision paragraph (Section 11b)."""
    lines = [
        f"# Scaling & Transformation Analysis — `{report.dataset_name}`",
        "",
        "## Decision Summary",
        "",
        f"> {report.decision_paragraph}",
        "",
        "## Scale Disparity Across Numeric Features",
        "",
    ]
    if report.scale_disparity_ratio is not None:
        lines.extend(
            [
                f"- **Max standard deviation:** `{report.max_std:.4f}`",
                f"- **Min standard deviation:** `{report.min_std:.4f}`",
                f"- **Scale disparity ratio (`max_std / min_std`):** `{report.scale_disparity_ratio:.2f}x`",
                f"- **Z-score standardization recommended for scale-sensitive models (PCA/L1/L2/KNN):** `{report.recommend_zscore_for_scale_sensitive}`",
                "",
            ]
        )
    else:
        lines.extend(["- Insufficient numeric features to compute scale disparity.", ""])

    lines.extend(
        [
            "## Per-Column Transformation Recommendations",
            "",
            "| Column | Skewness | Kurtosis | Min | Max | Std | Min >= 0 | Recommended Transform | Reason |",
            "| :--- | ---: | ---: | ---: | ---: | ---: | :---: | :--- | :--- |",
        ]
    )

    for c in report.columns:
        lines.append(
            f"| `{c.column}` | {c.skewness:.3f} | {c.kurtosis:.3f} | {c.min_val:g} | "
            f"{c.max_val:g} | {c.std_val:.3f} | {c.min_non_negative} | "
            f"`{c.recommended_transform}` | {c.reason} |"
        )

    if report.scaled_csv_path:
        lines.extend(
            [
                "",
                "## Generated Convenience Artifacts",
                "",
                f"- **Scaled CSV (TA review / downstream modeling copy):** `{report.scaled_csv_path}`",
            ]
        )

    return "\n".join(lines) + "\n"


def analyze_scaling(
    df_clean_conservative: pd.DataFrame,
    schema: dict[str, ColumnSchemaEntry],
    config: PipelineConfig | None = None,
    df_clean_imputed: pd.DataFrame | None = None,
    dataset_name: str | None = None,
    out_dir: Path | str | None = None,
    cleaned_dir: Path | str | None = None,
) -> ScalingReport:
    """Analyze skewness and scale disparity, write scaling_report.md, scaling_params.json, and <name>_scaled.csv."""
    cfg = config or load_config()
    ds_name = dataset_name or cfg.name
    skew_thresh = cfg.scaling.skew_threshold
    disp_thresh = cfg.scaling.scale_disparity_ratio_threshold

    recommendations: list[ColumnScalingRecommendation] = []
    scaling_params: dict[str, dict[str, float]] = {}
    stds: list[float] = []

    for col in df_clean_conservative.columns:
        if col.endswith("__was_missing"):
            continue
        entry = schema.get(col)
        if entry is not None:
            if entry.role in {ColumnRole.ID, ColumnRole.EXCLUDED}:
                continue
            if entry.semantic_type not in {
                SemanticType.NUMERIC_CONTINUOUS,
                SemanticType.NUMERIC_DISCRETE,
            }:
                continue
        else:
            if not pd.api.types.is_numeric_dtype(df_clean_conservative[col].dtype):
                continue

        valid = (
            pd.to_numeric(df_clean_conservative[col], errors="coerce")
            .dropna()
            .astype("float64")
        )
        if len(valid) < 3:
            continue

        min_v = round(float(valid.min()), 6)
        max_v = round(float(valid.max()), 6)
        mean_v = round(float(valid.mean()), 6)
        std_v = round(float(valid.std(ddof=1)), 6) if len(valid) > 1 else 0.0
        min_non_neg = bool(min_v >= 0.0)

        if std_v > 1e-12:
            skew_v = round(float(stats.skew(valid, bias=False)), 6)
            kurt_v = round(float(stats.kurtosis(valid, bias=False)), 6) if len(valid) >= 4 else 0.0
            stds.append(std_v)
        else:
            skew_v = 0.0
            kurt_v = 0.0

        yj_lambda: float | None = None
        if skew_v > skew_thresh and min_non_neg:
            rec_transform = "log1p"
            reason = (
                f"Right-skewed (skew={skew_v:.2f} > {skew_thresh:.1f}) with non-negative domain "
                f"(min={min_v:g}); log1p recommended."
            )
        elif skew_v > skew_thresh and not min_non_neg:
            rec_transform = "yeo-johnson"
            _, lmbda_val = stats.yeojohnson(valid.to_numpy())
            yj_lambda = round(float(lmbda_val), 6)
            reason = (
                f"Right-skewed (skew={skew_v:.2f} > {skew_thresh:.1f}) with negative values "
                f"(min={min_v:g}); Yeo-Johnson (lambda={yj_lambda:.3f}) recommended."
            )
        else:
            rec_transform = "none"
            reason = f"Moderate/low skewness (skew={skew_v:.2f}); no non-linear transform needed."

        recommendations.append(
            ColumnScalingRecommendation(
                column=col,
                skewness=skew_v,
                kurtosis=kurt_v,
                min_val=min_v,
                max_val=max_v,
                std_val=std_v,
                min_non_negative=min_non_neg,
                recommended_transform=rec_transform,
                reason=reason,
            )
        )

        param_entry: dict[str, float] = {
            "mean": mean_v,
            "std": std_v,
            "min": min_v,
            "max": max_v,
            "skewness": skew_v,
        }
        if yj_lambda is not None:
            param_entry["yeojohnson_lambda"] = yj_lambda
        scaling_params[col] = param_entry

    if len(stds) >= 2:
        max_std = round(max(stds), 6)
        min_std = round(min(stds), 6)
        disparity = round(max_std / min_std, 6) if min_std > 1e-12 else None
        rec_z = bool(disparity is not None and disparity > disp_thresh)
    elif len(stds) == 1:
        max_std = round(stds[0], 6)
        min_std = round(stds[0], 6)
        disparity = 1.0
        rec_z = False
    else:
        max_std = min_std = disparity = None
        rec_z = False

    transform_cols = [
        r.column for r in recommendations if r.recommended_transform != "none"
    ]
    cols_str = ", ".join(transform_cols) if transform_cols else "none (no numeric column exceeded skewness threshold)"

    decision_paragraph = (
        "Primary cleaned output is **not** scaled. The Phase 3 test library is rank-based or "
        "scale-invariant (Welch/Mann-Whitney, Spearman, Kruskal, chi-square), so scaling would "
        f"not change results. Log transforms are recommended for columns [{cols_str}] only for "
        "plotting and for parametric/regression use. A scaled copy is provided for TA review and "
        "for any future modeling."
    )

    scaled_csv_str: str | None = None
    if cfg.scaling.generate_scaled_csv and cleaned_dir is not None:
        base_df = (
            df_clean_imputed.copy()
            if df_clean_imputed is not None
            else df_clean_conservative.copy()
        )
        for rec in recommendations:
            col = rec.column
            if col not in base_df.columns:
                continue
            s_num = pd.to_numeric(base_df[col], errors="coerce").astype("float64")
            if rec.recommended_transform == "log1p":
                base_df[f"{col}__log1p"] = np.round(
                    np.log1p(np.maximum(0.0, s_num)), 6
                )
            elif rec.recommended_transform == "yeo-johnson":
                lmb = scaling_params[col].get("yeojohnson_lambda", 1.0)
                non_na = s_num.notna()
                yj_series = pd.Series(np.nan, index=base_df.index, dtype="float64")
                if non_na.any():
                    yj_vals = stats.yeojohnson(s_num[non_na].to_numpy(), lmbda=lmb)
                    yj_series.loc[non_na] = np.round(yj_vals, 6)
                base_df[f"{col}__yeojohnson"] = yj_series

            if rec.std_val > 1e-12:
                mu = scaling_params[col]["mean"]
                sd = scaling_params[col]["std"]
                base_df[f"{col}__z"] = np.round((s_num - mu) / sd, 6)

        c_dir = Path(cleaned_dir)
        c_dir.mkdir(parents=True, exist_ok=True)
        scaled_path = c_dir / f"{ds_name}_scaled.csv"
        base_df.to_csv(scaled_path, index=False, encoding="utf-8", lineterminator="\n")
        scaled_csv_str = str(scaled_path)

    report = ScalingReport(
        dataset_name=ds_name,
        columns=recommendations,
        max_std=max_std,
        min_std=min_std,
        scale_disparity_ratio=disparity,
        recommend_zscore_for_scale_sensitive=rec_z,
        decision_paragraph=decision_paragraph,
        scaling_params=scaling_params,
        scaled_csv_path=scaled_csv_str,
    )

    if out_dir is not None:
        o_dir = Path(out_dir)
        o_dir.mkdir(parents=True, exist_ok=True)
        (o_dir / "scaling_report.md").write_text(
            render_scaling_report_markdown(report), encoding="utf-8"
        )
        (o_dir / "scaling_params.json").write_text(
            json.dumps(scaling_params, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    return report

