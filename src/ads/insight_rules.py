"""Rule-based insight templates (Section 11), written as pure functions on plain dicts.

No LLM and no imports from the rest of ``ads``: ``ads.insights`` converts the pipeline's
pydantic objects to dicts, calls :func:`build_insights`, and turns the result back into
``InsightRecord`` objects.

Traceability rule: every number in a statement is copied from the insight's ``evidence``
dict, already rounded to the precision that is printed. The claim checker (M9) relies on this.
"""

from __future__ import annotations

import math
import re
from typing import Any

CATEGORY_ORDER = [
    "data_quality",
    "distributions",
    "class_balance",
    "relationships",
    "cardinality_structure",
    "scaling",
    "modeling_testing_implications",
]
CATEGORY_TITLES = {
    "data_quality": "Data quality",
    "distributions": "Distributions",
    "class_balance": "Class balance",
    "relationships": "Relationships (descriptive)",
    "cardinality_structure": "Cardinality and structure",
    "scaling": "Scaling notes",
    "modeling_testing_implications": "Implications for later testing",
}
SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2, "info": 3}

DEFAULT_THRESHOLDS: dict[str, float] = {
    "high_missing_pct": 40.0,
    "medium_missing_pct": 5.0,
    "skew": 1.0,
    "zero_inflation_pct": 30.0,
    "outlier_pct": 5.0,
    "rare_level_pct": 1.0,
    "small_n_dataset": 200,
    "small_n_group": 20,
    "high_cardinality": 20,
    "corr_report_min": 0.30,
    "cramers_report_min": 0.30,
    "eta_report_min": 0.10,
    "collinearity": 0.90,
    "unbalanced_mode_pct": 90.0,
}


# ---------------------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------------------


def r2(v: Any) -> float | None:
    """Round to 2 decimals (the precision used in statements)."""
    if v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return round(f, 2) if math.isfinite(f) else None


def fmt(v: Any) -> str:
    """Print a number exactly as stored in evidence (thousands separators for big integers)."""
    if isinstance(v, bool):
        return str(v)
    if isinstance(v, int):
        return f"{v:,}"
    if isinstance(v, float):
        if v.is_integer() and abs(v) < 1e15:
            return f"{int(v):,}"
        text = f"{v:,.2f}".rstrip("0").rstrip(".")
        return text
    return str(v)


def signed(v: float) -> str:
    """Print a coefficient with an explicit sign (+0.42 / -0.36)."""
    return ("+" if v > 0 else "") + fmt(v)


_ID_RE = re.compile(r"[^a-z0-9]+")


def _slug(text: str) -> str:
    return _ID_RE.sub("_", str(text).lower()).strip("_")[:40] or "x"


class _Builder:
    def __init__(self) -> None:
        self.items: list[dict[str, Any]] = []
        self._ids: set[str] = set()

    def add(
        self,
        rule: str,
        category: str,
        severity: str,
        statement: str,
        evidence: dict[str, Any],
        figure_ref: str | None = None,
        key: str = "",
    ) -> None:
        base = f"{rule}_{_slug(key)}" if key else rule
        iid, k = base, 2
        while iid in self._ids:
            iid, k = f"{base}_{k}", k + 1
        self._ids.add(iid)
        self.items.append(
            {
                "id": iid,
                "category": category,
                "severity": severity,
                "statement": statement,
                "evidence": evidence,
                "figure_ref": figure_ref,
            }
        )


def _fig(headline: dict[str, Any], *path: str) -> str | None:
    cur: Any = headline
    for p in path:
        if not isinstance(cur, dict) or p not in cur:
            return None
        cur = cur[p]
    return cur if isinstance(cur, str) else None


# ---------------------------------------------------------------------------------------
# rules
# ---------------------------------------------------------------------------------------


def _data_quality(b: _Builder, ctx: dict[str, Any], t: dict[str, float]) -> None:
    hl = ctx["headline"]
    n_rows = int(hl.get("overview", {}).get("n_rows", 0))
    miss_cols = hl.get("missingness", {}).get("columns", {})
    miss_fig = _fig(hl, "missingness", "figures", "missing_bar")
    for col, info in sorted(miss_cols.items(), key=lambda kv: (-kv[1]["pct_missing"], kv[0])):
        n_m, p_m = int(info["n_missing"]), r2(info["pct_missing"])
        if n_m == 0:
            continue
        sev = "high" if p_m > t["high_missing_pct"] else ("medium" if p_m > t["medium_missing_pct"] else "low")
        b.add(
            "dq_missing",
            "data_quality",
            sev,
            f"Column '{col}' has {fmt(p_m)}% missing values (n = {fmt(n_m)} of {fmt(n_rows)} rows).",
            {"column": col, "n_missing": n_m, "pct_missing": p_m, "n_rows": n_rows},
            miss_fig,
            key=col,
        )

    log = ctx["log"]
    dup_entries = [e for e in log if e.get("step") == "handle_duplicates"]
    dropped = [e for e in dup_entries if e.get("action") == "dropped_duplicate_rows"]
    kept = [e for e in dup_entries if e.get("action") == "kept_duplicates_warning"]
    if dropped:
        n = int(sum(e.get("n_rows_affected", 0) for e in dropped))
        b.add(
            "dq_duplicates_removed",
            "data_quality",
            "medium",
            f"{fmt(n)} exact duplicate rows were removed (the first copy of each was kept).",
            {"n_duplicate_rows_removed": n},
        )
    elif kept:
        n = int(sum(e.get("n_rows_affected", 0) for e in kept))
        b.add(
            "dq_duplicates_kept",
            "data_quality",
            "medium",
            f"{fmt(n)} exact duplicate rows were found but kept, because they may be legitimate repeats (no ID column); review them by hand.",
            {"n_duplicate_rows_kept": n},
        )
    else:
        b.add("dq_no_duplicates", "data_quality", "info", "No exact duplicate rows were found.", {"n_duplicate_rows_removed": 0})

    name_map = ctx.get("name_map", {})
    for col in ctx["profile"].get("columns", []):
        raw_name = col.get("name")
        name = name_map.get(raw_name, raw_name)
        tokens = {str(k): int(v) for k, v in (col.get("missing_tokens_found") or {}).items() if int(v) > 0}
        tokens.pop("", None)
        if tokens:
            n_cells = int(sum(tokens.values()))
            listed = ", ".join(f"'{k}' ({fmt(v)})" for k, v in sorted(tokens.items(), key=lambda kv: (-kv[1], kv[0]))[:4])
            b.add(
                "dq_placeholder_tokens",
                "data_quality",
                "medium" if n_cells > 0.05 * max(1, n_rows) else "low",
                f"Column '{name}' used placeholder text for missing values: {listed}; {fmt(n_cells)} cells were turned into real missing values.",
                {"column": name, "tokens": tokens, "n_cells": n_cells},
                key=name,
            )

    for e in log:
        step, action, col = e.get("step"), e.get("action"), e.get("column")
        n = int(e.get("n_cells_affected", 0))
        if not col or n <= 0:
            continue
        if step == "convert_types" and action == "cast_dtype":
            b.add(
                "dq_numeric_as_text",
                "data_quality",
                "medium",
                f"Column '{col}' was stored as text with number formatting; {fmt(n)} cells were converted to numbers.",
                {"column": col, "n_cells_converted": n},
                key=col,
            )
        elif step == "convert_types" and action == "coerced_to_NaN":
            b.add(
                "dq_unparseable",
                "data_quality",
                "medium",
                f"Column '{col}' had {fmt(n)} values that could not be read as its type; they were set to missing.",
                {"column": col, "n_cells_coerced": n},
                key=col,
            )
        elif action == "invalid_to_NaN":
            b.add(
                "dq_invalid_values",
                "data_quality",
                "medium",
                f"Column '{col}' had {fmt(n)} values outside its allowed range; they were set to missing.",
                {"column": col, "n_cells_invalid": n, "rule": e.get("parameters", {})},
                key=col,
            )
        elif action == "merged_case_variants":
            b.add(
                "dq_case_variants",
                "data_quality",
                "low",
                f"Column '{col}' had labels that differed only by capitals or spaces; {fmt(n)} cells were merged into one spelling.",
                {"column": col, "n_cells_merged": n},
                key=col,
            )
        elif action == "flagged_fuzzy_variants":
            b.add(
                "dq_fuzzy_variants",
                "data_quality",
                "low",
                f"Column '{col}' has labels with near-identical spellings ({fmt(n)} cells); they were flagged for review, not changed.",
                {"column": col, "n_cells_flagged": n},
                key=col,
            )

    for col, info in sorted(hl.get("column_roles", {}).items()):
        role, sem = info.get("role"), info.get("semantic_type")
        if role in {"id", "excluded"}:
            kind = {"id_like": "ID-like", "constant": "constant", "free_text": "free text"}.get(sem, sem)
            b.add(
                "dq_excluded",
                "data_quality",
                "info",
                f"Column '{col}' is {kind} and is left out of the analysis (kept in the cleaned file).",
                {"column": col, "semantic_type": sem, "role": role},
                key=col,
            )
    for d in ctx.get("dropped_columns", []):
        if d.get("output_target") == "marked_excluded":
            continue
        b.add(
            "dq_dropped_column",
            "data_quality",
            "medium",
            f"Column '{d.get('name')}' was dropped ({d.get('reason')}).",
            {"column": d.get("name"), "reason": d.get("reason"), "output": d.get("output_target")},
            key=str(d.get("name")),
        )


def _distributions(b: _Builder, ctx: dict[str, Any], t: dict[str, float]) -> None:
    num = ctx["headline"].get("numeric", {}).get("columns", {})
    for col in sorted(num):
        s = num[col]
        if not s.get("count"):
            continue
        fig = s.get("detail_figure") or s.get("figure")
        skew, mean, median, mn = r2(s.get("skew")), r2(s.get("mean")), r2(s.get("median")), s.get("min")
        if skew is not None and skew > t["skew"]:
            transform = "a log transform" if (mn is not None and mn >= 0) else "a Yeo-Johnson transform"
            b.add(
                "dist_right_skew",
                "distributions",
                "medium",
                f"'{col}' is right-skewed (skew = {fmt(skew)}): its median ({fmt(median)}) is below its mean ({fmt(mean)}), so {transform} is advisable for plots and parametric models.",
                {"column": col, "skew": skew, "median": median, "mean": mean},
                fig,
                key=col,
            )
        elif skew is not None and skew < -t["skew"]:
            b.add(
                "dist_left_skew",
                "distributions",
                "medium",
                f"'{col}' is left-skewed (skew = {fmt(skew)}): its median ({fmt(median)}) is above its mean ({fmt(mean)}).",
                {"column": col, "skew": skew, "median": median, "mean": mean},
                fig,
                key=col,
            )
        peaks = s.get("n_peaks_heuristic")
        if isinstance(peaks, int) and peaks >= 2:
            b.add(
                "dist_multimodal",
                "distributions",
                "low",
                f"'{col}' may have {fmt(peaks)} peaks (simple histogram heuristic), which can mean mixed sub-groups; check the plot.",
                {"column": col, "n_peaks_heuristic": peaks},
                fig,
                key=col,
            )
        pz = r2(s.get("pct_zeros"))
        if pz is not None and pz > t["zero_inflation_pct"]:
            b.add(
                "dist_zero_inflated",
                "distributions",
                "medium",
                f"'{col}' is zero-inflated: {fmt(pz)}% of its values are exactly zero.",
                {"column": col, "pct_zeros": pz, "n_zeros": int(s.get("n_zeros", 0))},
                fig,
                key=col,
            )
        po = r2(s.get("pct_outliers_iqr"))
        if po is not None and po > t["outlier_pct"]:
            b.add(
                "dist_outliers",
                "distributions",
                "medium",
                f"'{col}' has many outliers: {fmt(po)}% of its values (n = {fmt(int(s.get('n_outliers_iqr', 0)))}) are beyond 1.5×IQR. They are flagged, not removed.",
                {"column": col, "pct_outliers_iqr": po, "n_outliers_iqr": int(s.get("n_outliers_iqr", 0)), "iqr_multiplier": 1.5},
                _fig(ctx["headline"], "numeric", "figures", "outlier_summary") or fig,
                key=col,
            )


def _class_balance(b: _Builder, ctx: dict[str, Any], t: dict[str, float]) -> None:
    tg = ctx["headline"].get("target") or {}
    if not tg or not tg.get("name"):
        return
    name, fig = tg["name"], _fig(tg, "figures", "target")
    if tg.get("kind") == "categorical" and tg.get("n_classes"):
        label = tg["balance_label"]
        sev = {"highly imbalanced": "high", "mildly imbalanced": "medium"}.get(label, "info")
        mp, ratio = r2(tg["minority_pct"]), r2(tg["imbalance_ratio"])
        b.add(
            "balance_target",
            "class_balance",
            sev,
            f"Target '{name}' is {label}: the smallest class '{tg['minority_class']}' is {fmt(mp)}% of rows and the largest '{tg['majority_class']}' is {fmt(r2(tg['majority_pct']))}% (the largest class is {fmt(ratio)} times the smallest).",
            {
                "target": name,
                "minority_class": tg["minority_class"],
                "minority_pct": mp,
                "majority_class": tg["majority_class"],
                "majority_pct": r2(tg["majority_pct"]),
                "imbalance_ratio": ratio,
                "n_classes": int(tg["n_classes"]),
            },
            fig,
            key=name,
        )
    elif tg.get("kind") == "numeric" and tg.get("count"):
        ev = {"target": name, "min": r2(tg["min"]), "max": r2(tg["max"]), "median": r2(tg["median"]), "mean": r2(tg["mean"])}
        stmt = f"Target '{name}' is numeric, from {fmt(ev['min'])} to {fmt(ev['max'])} (median {fmt(ev['median'])}, mean {fmt(ev['mean'])})."
        if tg.get("n_zeros"):
            ev["pct_zeros"] = r2(tg["pct_zeros"])
            ev["n_zeros"] = int(tg["n_zeros"])
            stmt += f" {fmt(ev['pct_zeros'])}% of values (n = {fmt(ev['n_zeros'])}) are exactly zero, which may be a separate group."
        b.add("balance_target_numeric", "class_balance", "info", stmt, ev, fig, key=name)


def _relationships(b: _Builder, ctx: dict[str, Any], t: dict[str, float]) -> None:
    hl = ctx["headline"]
    nn = hl.get("numeric_numeric", {})
    corr_fig = _fig(nn, "figures", "correlation_heatmap")
    for d in nn.get("top_pairs", [])[:3]:
        rho, r = r2(d.get("spearman")), r2(d.get("pearson"))
        if rho is None or abs(rho) < t["corr_report_min"]:
            continue
        direction = "rise together" if rho > 0 else "move in opposite directions"
        b.add(
            "rel_numeric_pair",
            "relationships",
            "low",
            f"'{d['a']}' and '{d['b']}' {direction} (Spearman rho = {signed(rho)}, Pearson r = {signed(r)}; descriptive).",
            {"a": d["a"], "b": d["b"], "spearman": rho, "pearson": r, "n": int(d.get("n", 0))},
            _fig(nn, "figures", "top_scatter_pairs") or corr_fig,
            key=f"{d['a']}_{d['b']}",
        )
    for d in nn.get("collinear_pairs", []):
        r = r2(d.get("pearson"))
        b.add(
            "rel_collinear",
            "relationships",
            "medium",
            f"'{d['a']}' and '{d['b']}' are nearly collinear (Pearson r = {signed(r)}); models should not use both as if they were separate information.",
            {"a": d["a"], "b": d["b"], "pearson": r},
            corr_fig,
            key=f"{d['a']}_{d['b']}",
        )

    tr = hl.get("target_relationships", {})
    feats = tr.get("features", [])
    target = tr.get("target")
    tr_fig = _fig(tr, "figures", "target_relationships")
    num_cols = set(hl.get("column_groups", {}).get("numeric", []))
    best_num = next((f for f in feats if f["feature"] in num_cols), None)
    best_cat = next((f for f in feats if f["feature"] not in num_cols), None)
    for kind, f in (("numeric", best_num), ("categorical", best_cat)):
        if not f or f.get("value") is None:
            continue
        v = r2(f["value"])
        shown = signed(v) if f["measure"] == "Spearman rho" else fmt(v)
        b.add(
            f"rel_target_{kind}",
            "relationships",
            "medium" if abs(v) >= 0.3 else "low",
            f"The {kind} feature most associated with target '{target}' is '{f['feature']}' ({f['measure']} = {shown}; descriptive).",
            {"target": target, "feature": f["feature"], "measure": f["measure"], "value": v},
            tr_fig,
            key=f["feature"],
        )

    cc = hl.get("categorical_categorical", {})
    for d in cc.get("top_pairs", [])[:2]:
        v = r2(d.get("cramers_v"))
        if v is None or v < t["cramers_report_min"] or target in (d["a"], d["b"]):
            continue
        b.add(
            "rel_categorical_pair",
            "relationships",
            "low",
            f"'{d['a']}' and '{d['b']}' are associated (bias-corrected Cramér's V = {fmt(v)}; descriptive).",
            {"a": d["a"], "b": d["b"], "cramers_v": v},
            _fig(cc, "figures", "cramers_v_heatmap"),
            key=f"{d['a']}_{d['b']}",
        )
    nc = hl.get("numeric_categorical", {})
    for d in nc.get("top_pairs", [])[:2]:
        e = r2(d.get("eta_squared"))
        if e is None or e < t["eta_report_min"] or target in (d["numeric"], d["categorical"]):
            continue
        b.add(
            "rel_numeric_by_group",
            "relationships",
            "low",
            f"Groups of '{d['categorical']}' differ in '{d['numeric']}': the groups explain {fmt(r2(e * 100))}% of its variance (eta² = {fmt(e)}; descriptive).",
            {"numeric": d["numeric"], "categorical": d["categorical"], "eta_squared": e, "pct_variance_explained": r2(e * 100)},
            _fig(nc, "figures", "numeric_by_category"),
            key=f"{d['numeric']}_{d['categorical']}",
        )


def _cardinality(b: _Builder, ctx: dict[str, Any], t: dict[str, float]) -> None:
    hl = ctx["headline"]
    n_rows = int(hl.get("overview", {}).get("n_rows", 0))
    if 0 < n_rows < t["small_n_dataset"]:
        b.add(
            "struct_small_n",
            "cardinality_structure",
            "high",
            f"The dataset is small ({fmt(n_rows)} rows, under {fmt(int(t['small_n_dataset']))}); later test results will be less stable.",
            {"n_rows": n_rows, "threshold": int(t["small_n_dataset"])},
        )
    cats = hl.get("categorical", {}).get("columns", {})
    card_fig = _fig(hl, "categorical", "figures", "cardinality_bar")
    for col in sorted(cats):
        c = cats[col]
        if not c.get("count"):
            continue
        fig = c.get("figure")
        if c["n_unique"] > t["high_cardinality"]:
            b.add(
                "struct_high_cardinality",
                "cardinality_structure",
                "medium",
                f"'{col}' has {fmt(int(c['n_unique']))} levels (high cardinality); group rare levels before cross-tabulating it.",
                {"column": col, "n_unique": int(c["n_unique"])},
                card_fig,
                key=col,
            )
        if c.get("n_rare_levels", 0) > 0:
            ex = c["rare_levels"][0]
            b.add(
                "struct_rare_levels",
                "cardinality_structure",
                "low",
                f"'{col}' has {fmt(int(c['n_rare_levels']))} level(s) under {fmt(t['rare_level_pct'])}% of rows (e.g. '{ex['level']}', n = {fmt(int(ex['count']))}); these will give sparse cells in later chi-square tests (Phase 3).",
                {"column": col, "n_rare_levels": int(c["n_rare_levels"]), "example_level": ex["level"], "example_count": int(ex["count"]), "threshold_pct": t["rare_level_pct"]},
                fig,
                key=col,
            )
        elif c.get("smallest_group_n", 10**9) < t["small_n_group"]:
            b.add(
                "struct_small_group",
                "cardinality_structure",
                "low",
                f"'{col}' has a level with only {fmt(int(c['smallest_group_n']))} rows ('{c['rarest_level']}'), under the {fmt(int(t['small_n_group']))}-row guide for group comparisons.",
                {"column": col, "smallest_group_n": int(c["smallest_group_n"]), "level": c["rarest_level"], "threshold": int(t["small_n_group"])},
                fig,
                key=col,
            )


def _scaling(b: _Builder, ctx: dict[str, Any], t: dict[str, float]) -> None:
    sc = ctx.get("scaling") or {}
    for rec in sc.get("columns", []):
        tr = rec.get("recommended_transform")
        if tr in (None, "none"):
            continue
        sk = r2(rec.get("skewness"))
        b.add(
            "scale_transform",
            "scaling",
            "info",
            f"Scaling note: {tr} is recommended for '{rec['column']}' (skew = {fmt(sk)}) for plots and parametric models only; the main cleaned file is not transformed.",
            {"column": rec["column"], "transform": tr, "skew": sk},
            key=rec["column"],
        )
    ratio = r2(sc.get("scale_disparity_ratio"))
    if ratio is not None and sc.get("recommend_zscore_for_scale_sensitive"):
        b.add(
            "scale_disparity",
            "scaling",
            "info",
            f"Numeric columns differ a lot in spread (largest std is {fmt(ratio)} times the smallest); z-scores are advised only for scale-sensitive methods such as regularized regression, distance-based methods or PCA.",
            {"scale_disparity_ratio": ratio},
        )


def _implications(b: _Builder, ctx: dict[str, Any], t: dict[str, float]) -> None:
    hl = ctx["headline"]
    num = hl.get("numeric", {}).get("columns", {})
    rank_cols = sorted(
        c
        for c, s in num.items()
        if s.get("count")
        and ((s.get("skew") is not None and abs(s["skew"]) > t["skew"]) or (s.get("pct_outliers_iqr") or 0) > t["outlier_pct"])
    )
    if rank_cols:
        b.add(
            "impl_rank_based",
            "modeling_testing_implications",
            "medium",
            f"Rank-based methods (Spearman, Mann-Whitney, Kruskal-Wallis) are recommended for {fmt(len(rank_cols))} skewed or outlier-heavy column(s): "
            + ", ".join(f"'{c}'" for c in rank_cols[:12])
            + (" and more." if len(rank_cols) > 12 else "."),
            {"columns": rank_cols, "n_columns": len(rank_cols)},
        )
    cats = hl.get("categorical", {}).get("columns", {})
    target = (hl.get("target") or {}).get("name")
    for col in sorted(cats):
        c = cats[col]
        if not c.get("count") or col == target:
            continue
        mp = r2(c.get("mode_pct"))
        if mp is not None and mp >= t["unbalanced_mode_pct"] and c["n_unique"] >= 2:
            b.add(
                "impl_unbalanced_groups",
                "modeling_testing_implications",
                "low",
                f"Group sizes are very unbalanced for '{col}': '{c['mode']}' covers {fmt(mp)}% of rows and '{c['rarest_level']}' only {fmt(int(c['rarest_count']))} rows, so comparisons across its levels will rest on few cases.",
                {"column": col, "mode": c["mode"], "mode_pct": mp, "rarest_level": c["rarest_level"], "rarest_count": int(c["rarest_count"])},
                c.get("figure"),
                key=col,
            )
    tg = hl.get("target") or {}
    if tg.get("kind") == "categorical" and tg.get("balance_label") in {"highly imbalanced", "mildly imbalanced"}:
        b.add(
            "impl_target_imbalance",
            "modeling_testing_implications",
            "medium",
            f"Because target '{tg['name']}' is {tg['balance_label']}, compare groups using rates (% per class) rather than raw counts, and use stratified splits for any later modeling.",
            {"target": tg["name"], "balance_label": tg["balance_label"]},
            _fig(tg, "figures", "target"),
            key=tg["name"],
        )


def build_insights(
    profile: dict[str, Any],
    log: list[dict[str, Any]],
    headline: dict[str, Any],
    scaling: dict[str, Any] | None = None,
    dropped_columns: list[dict[str, Any]] | None = None,
    name_map: dict[str, str] | None = None,
    thresholds: dict[str, float] | None = None,
) -> list[dict[str, Any]]:
    """Run every rule and return insight dicts sorted by category, then severity, then id."""
    t = {**DEFAULT_THRESHOLDS, **(thresholds or {})}
    ctx = {
        "profile": profile or {},
        "log": log or [],
        "headline": headline or {},
        "scaling": scaling or {},
        "dropped_columns": dropped_columns or [],
        "name_map": name_map or {},
    }
    b = _Builder()
    for rule in (_data_quality, _distributions, _class_balance, _relationships, _cardinality, _scaling, _implications):
        rule(b, ctx, t)
    b.items.sort(key=lambda d: (CATEGORY_ORDER.index(d["category"]), SEVERITY_ORDER[d["severity"]], d["id"]))
    return b.items


# ---------------------------------------------------------------------------------------
# markdown
# ---------------------------------------------------------------------------------------

MANUAL_START = "<!-- MANUAL:START -->"
MANUAL_END = "<!-- MANUAL:END -->"
DEFAULT_MANUAL_BLOCK = f"""{MANUAL_START}
- **What surprised you?** *(Analyst to fill in)*
- **Which relationships look real vs. likely spurious?** *(Analyst to fill in)*
- **Anything suspicious about data collection or missingness?** *(Analyst to fill in)*
- **Known domain relationships present or absent?** *(Analyst to fill in)*
- **Target findings for Phase 5 benchmark recovery:** *(Analyst to fill in)*
{MANUAL_END}"""


def extract_manual_block(existing_md: str | None) -> str:
    """Return the existing MANUAL block (markers included) or the default template."""
    if not existing_md:
        return DEFAULT_MANUAL_BLOCK
    s, e = existing_md.find(MANUAL_START), existing_md.find(MANUAL_END)
    if s != -1 and e != -1 and e > s:
        return existing_md[s : e + len(MANUAL_END)]
    return DEFAULT_MANUAL_BLOCK


def render_insights_markdown(dataset_name: str, insights: list[dict[str, Any]], manual_block: str) -> str:
    """Build insights.md: automated section grouped by category + preserved manual section."""
    lines = [
        f"# Dataset Insights — `{dataset_name}`",
        "",
        "_The automated insights below are generated by fixed rules from computed values (no LLM). "
        "Each number is stored with its evidence in `insights.json`. Relationship numbers are descriptive only; "
        "no hypothesis tests were run in Phase 1._",
        "",
        "## Automated insights",
        "",
    ]
    if not insights:
        lines += ["_No automated insights were triggered._", ""]
    for cat in CATEGORY_ORDER:
        items = [i for i in insights if i["category"] == cat]
        if not items:
            continue
        lines += [f"### {CATEGORY_TITLES[cat]}", ""]
        for i in items:
            link = f" ([figure]({i['figure_ref']}))" if i.get("figure_ref") else ""
            lines.append(f"- **{i['severity'].upper()}** — {i['statement']}{link}")
        lines.append("")
    lines += ["## Manual insights (written by the analyst)", "", manual_block, ""]
    return "\n".join(lines)
