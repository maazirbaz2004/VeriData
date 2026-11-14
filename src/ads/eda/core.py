"""EDA orchestration without any dependency on the rest of ``ads`` (Section 10).

``run_eda_core`` takes plain inputs (a dataframe, semantic types and roles as strings) and
returns plain dictionaries. ``ads.eda.run_eda`` wraps it to accept the pipeline's pydantic
objects and to return an ``EDAResult``.
"""

from __future__ import annotations

import json
import logging
import traceback
from pathlib import Path
from typing import Any, Callable

import pandas as pd

from .bivariate import (
    run_categorical_categorical,
    run_numeric_categorical,
    run_numeric_numeric,
    run_target_relationships,
)
from .missingness import run_missingness
from .plots import EDASettings, FigureSink, apply_style
from .stats import as_float, as_labels, jsonable, normalized_entropy, value_counts_sorted
from .target import run_target
from .univariate import run_categorical, run_datetime, run_numeric, run_overview

logger = logging.getLogger("ads.eda")

NUMERIC_TYPES = {"numeric_continuous", "numeric_discrete"}
CATEGORICAL_TYPES = {"categorical_nominal", "categorical_ordinal", "binary"}
EXCLUDED_ROLES = {"id", "excluded"}


def _fallback_semantic_type(s: pd.Series) -> str:
    if pd.api.types.is_bool_dtype(s):
        return "binary"
    if pd.api.types.is_numeric_dtype(s):
        n = s.dropna().nunique()
        return "binary" if n == 2 else "numeric_continuous"
    if pd.api.types.is_datetime64_any_dtype(s):
        return "datetime"
    return "categorical_nominal"


def classify_columns(
    df: pd.DataFrame,
    semantic_types: dict[str, str],
    roles: dict[str, str],
    target: str | None,
    settings: EDASettings,
) -> dict[str, Any]:
    """Split columns into numeric / categorical / datetime groups used by the EDA sections."""
    sem = {str(c): semantic_types.get(str(c)) or _fallback_semantic_type(df[c]) for c in df.columns}
    numeric, discrete, categorical, datetimes, skipped = [], set(), [], [], []
    for c in df.columns:
        c = str(c)
        if roles.get(c) in EXCLUDED_ROLES and c != target:
            skipped.append(c)
            continue
        t = sem[c]
        if t in NUMERIC_TYPES:
            if as_float(df[c]).notna().any():
                numeric.append(c)
                if t == "numeric_discrete":
                    discrete.add(c)
            else:
                skipped.append(c)
        elif t in CATEGORICAL_TYPES:
            categorical.append(c)
        elif t == "datetime":
            datetimes.append(c)
        else:
            skipped.append(c)

    notes: list[str] = []
    if len(numeric) > settings.max_numeric_plots:
        var = {c: float(as_float(df[c]).var(skipna=True) or 0.0) for c in numeric}
        keep = sorted(numeric, key=lambda c: (-var[c], c))[: settings.max_numeric_plots]
        if target in numeric and target not in keep:
            keep[-1] = target
        notes.append(
            f"{len(numeric)} numeric columns found; only the {settings.max_numeric_plots} with the highest variance are plotted."
        )
        numeric = [c for c in numeric if c in keep]
    if len(categorical) > settings.max_categorical_plots:
        ent = {c: normalized_entropy(value_counts_sorted(as_labels(df[c])).to_numpy()) for c in categorical}
        keep = sorted(categorical, key=lambda c: (-ent[c], c))[: settings.max_categorical_plots]
        if target in categorical and target not in keep:
            keep[-1] = target
        notes.append(
            f"{len(categorical)} categorical columns found; only the {settings.max_categorical_plots} with the highest entropy are plotted."
        )
        categorical = [c for c in categorical if c in keep]

    target_kind = None
    if target and target in df.columns:
        t = sem[str(target)]
        if t in NUMERIC_TYPES:
            target_kind = "numeric"
        elif t in CATEGORICAL_TYPES:
            target_kind = "categorical"
    return {
        "semantic_types": sem,
        "numeric": numeric,
        "discrete": discrete,
        "categorical": categorical,
        "datetime": datetimes,
        "skipped": skipped,
        "target": target if target_kind else None,
        "target_kind": target_kind,
        "notes": notes,
    }


def _clear_old_figures(fig_dir: Path) -> None:
    if fig_dir.exists():
        for p in fig_dir.glob("*.png"):
            p.unlink()


def run_eda_core(
    df: pd.DataFrame,
    semantic_types: dict[str, str],
    roles: dict[str, str],
    target: str | None,
    settings: EDASettings,
    out_dir: Path | str,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Run every EDA section and write figures, markdown tables and ``eda_summary.json``.

    Returns ``{"figures": [...], "tables": {...}, "headline": {...}}``. A section that
    fails is recorded in ``headline["eda_errors"]`` and the rest still run.
    """
    out_dir = Path(out_dir)
    fig_dir = out_dir / "figures"
    tables_dir = out_dir / "tables"
    _clear_old_figures(fig_dir)
    tables_dir.mkdir(parents=True, exist_ok=True)
    sink = FigureSink(fig_dir, dpi=settings.dpi)
    apply_style()

    groups = classify_columns(df, semantic_types, roles, target, settings)
    headline: dict[str, Any] = {
        "column_groups": {
            "numeric": groups["numeric"],
            "categorical": groups["categorical"],
            "datetime": groups["datetime"],
            "skipped": groups["skipped"],
        },
        "column_roles": {str(c): {"semantic_type": groups["semantic_types"][str(c)], "role": roles.get(str(c), "feature")} for c in df.columns},
        "target": None,
        "notes": list(groups["notes"]),
        "eda_errors": [],
    }
    tables: dict[str, str] = {}

    def section(name: str, fn: Callable[[], tuple[dict[str, Any], dict[str, str]]]) -> None:
        try:
            h, t = fn()
            headline[name] = h
            tables.update(t)
        except Exception as exc:  # keep going; the error is recorded and reported
            logger.warning("EDA section '%s' failed: %s", name, exc)
            logger.debug(traceback.format_exc())
            headline["eda_errors"].append({"section": name, "error": f"{type(exc).__name__}: {exc}"})

    tgt, kind = groups["target"], groups["target_kind"]
    section("overview", lambda: run_overview(df, groups["semantic_types"], roles, sink, extra or {}))
    section("missingness", lambda: run_missingness(df, sink, settings))
    section("numeric", lambda: run_numeric(df, groups["numeric"], groups["discrete"], sink, settings))
    section("categorical", lambda: run_categorical(df, groups["categorical"], sink, settings))
    if tgt:
        section("target", lambda: run_target(df, tgt, kind, groups["categorical"], sink, settings))
    section("numeric_numeric", lambda: run_numeric_numeric(df, groups["numeric"], sink, settings))
    section(
        "numeric_categorical",
        lambda: run_numeric_categorical(df, groups["numeric"], groups["categorical"], sink, settings),
    )
    section("categorical_categorical", lambda: run_categorical_categorical(df, groups["categorical"], sink, settings))
    if tgt:
        section(
            "target_relationships",
            lambda: run_target_relationships(df, tgt, kind, groups["numeric"], groups["categorical"], sink, settings),
        )
    if groups["datetime"]:
        section("datetime", lambda: run_datetime(df, groups["datetime"], sink))

    for name, md in tables.items():
        (tables_dir / f"{name}.md").write_text(md, encoding="utf-8")

    headline = jsonable(headline)
    (out_dir / "eda_summary.json").write_text(
        json.dumps(headline, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return {"figures": sink.records, "tables": tables, "headline": headline}
