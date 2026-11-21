"""VeriData system adapters for the benchmark (Phase 4, Section 5).

Every variant runs the real product path: Phase 1 load/profile/clean (conservative) -> Phase 2
exhaustive enumeration without an LLM -> Phase 3 tests -> Phase 3 validation with the variant's
settings. Variants that share the same test-selection mode share one Stage-A run; only the
validation step (correction method, effect floor) is repeated (docs/decisions.md P4-7).
"""

from __future__ import annotations

import io
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from veridata.benchmark.truth import ReportedFinding, SystemOutput
from veridata.config import PipelineConfig, load_config
from veridata.contracts.findings import Finding
from veridata.contracts.hypothesis import Direction, HypothesisSet, RelationshipType
from veridata.contracts.results import TestResult


@dataclass(frozen=True)
class Variant:
    name: str
    aware_selection: bool
    correction: str  # bh | by | holm | bonferroni | none
    effect_floor: bool
    description: str
    floor_multiplier: float = 1.0  # tuning only: scales every effect-floor threshold


VARIANTS: dict[str, Variant] = {
    v.name: v
    for v in [
        Variant("veridata_full", True, "bh", True, "Assumption-aware selection + BH + effect floor (the product)."),
        Variant("veridata_nocorrection", True, "none", False, "Assumption-aware selection; raw p < alpha; no floor."),
        Variant("assumption_only", True, "none", False, "Alias of veridata_nocorrection (only assumption-aware selection on)."),
        Variant("bh_only", False, "bh", False, "Naive tests + BH; no floor."),
        Variant("floor_only", False, "none", True, "Naive tests; raw p < alpha + effect floor."),
        Variant("naive_tests", False, "bh", True, "Full validation but naive tests (Welch t / ANOVA / Pearson / chi-square always)."),
        Variant("naive_raw", False, "none", False, "Everything off: naive tests, raw p < alpha (the 'naive analyst')."),
        Variant("bonferroni", True, "bonferroni", True, "Full pipeline with Bonferroni instead of BH."),
        Variant("holm", True, "holm", True, "Full pipeline with Holm instead of BH."),
        Variant("by", True, "by", True, "Full pipeline with Benjamini-Yekutieli instead of BH."),
    ]
}
TUNING_GRID = (0.5, 0.75, 1.0, 1.25, 1.5)  # pre-declared floor multipliers (Section 8)


def get_variant(name: str) -> Variant:
    """Named variant, or a tuning variant 'tune_floor_x<m>' (full pipeline with floors scaled by m)."""
    if name in VARIANTS:
        return VARIANTS[name]
    if name.startswith("tune_floor_x"):
        m = float(name.removeprefix("tune_floor_x"))
        return Variant(name, True, "bh", True, f"Full pipeline with every effect floor x{m}.", floor_multiplier=m)
    raise KeyError(f"unknown system {name!r}; known: {sorted(VARIANTS)} or tune_floor_x<m>")


def tuning_variant_names(grid: tuple[float, ...] = TUNING_GRID) -> list[str]:
    return [f"tune_floor_x{m:.2f}" for m in grid]


DEFAULT_VARIANTS = ["veridata_full", "veridata_nocorrection", "bh_only", "floor_only", "naive_tests", "naive_raw", "bonferroni", "holm", "by"]


def benchmark_config(base: PipelineConfig | None = None) -> PipelineConfig:
    """Product defaults with the benchmark speed switch (Stage A only, no bootstrap CIs)."""
    cfg = (base or load_config()).model_copy(deep=True)
    cfg.stats.benchmark_fast_mode = True
    cfg.hypotheses.mode = "exhaustive"
    cfg.hypotheses.llm_proposals = False
    return cfg


def variant_config(base: PipelineConfig, variant: Variant) -> PipelineConfig:
    cfg = base.model_copy(deep=True)
    cfg.stats.assumption_aware_selection = variant.aware_selection
    cfg.stats.correction = variant.correction  # type: ignore[assignment]
    cfg.effect_floor.enabled = variant.effect_floor
    if variant.floor_multiplier != 1.0:
        for field_name, value in cfg.effect_floor.model_dump().items():
            if isinstance(value, float):
                setattr(cfg.effect_floor, field_name, round(value * variant.floor_multiplier, 6))
    return cfg


def prepare_dataset(csv_path: Path | str, dataset_id: str, cfg: PipelineConfig) -> tuple[pd.DataFrame, HypothesisSet, dict[str, Any]]:
    """Phase 1 (in memory) + Phase 2 exhaustive enumeration, exactly like the product path."""
    from veridata.cleaning import clean_dataset
    from veridata.hypotheses import generate_hypotheses
    from veridata.ingestion import load_csv
    from veridata.profiling import build_column_schema, profile_dataset

    ing = load_csv(csv_path, config=cfg)
    raw_profile = profile_dataset(ing.df_raw_str, df_naive=ing.df_naive, ingestion_meta=ing.metadata, config=cfg, dataset_name=dataset_id)
    cres = clean_dataset(ing.df_raw_str, raw_profile, config=cfg, ingestion_name_changes=ing.metadata.column_name_changes)
    raw_sem = {cres.name_map.get(c.name, c.name): c.semantic_type for c in raw_profile.columns}
    cfg_clean = cfg.model_copy(deep=True)
    for col in cres.df_clean_conservative.columns:
        if col in raw_sem and col not in cfg_clean.forced_types:
            cfg_clean.forced_types[col] = raw_sem[col]
    cleaned_profile = profile_dataset(
        cres.df_clean_conservative.astype("string").fillna("").astype(str),
        df_naive=cres.df_clean_conservative,
        ingestion_meta=ing.metadata,
        config=cfg_clean,
        dataset_name=dataset_id,
    )
    schema = build_column_schema(cleaned_profile, config=cfg)
    # Same as the CLI: Phase 2/3 read the cleaned CSV back from disk.
    buf = io.StringIO()
    cres.df_clean_conservative.to_csv(buf, index=False, lineterminator="\n")
    buf.seek(0)
    df = pd.read_csv(buf)
    hset = generate_hypotheses(df, schema, cleaned_profile, cfg, llm=None, mode="exhaustive", dataset_name=dataset_id)
    meta = {
        "n_hypotheses": len(hset.hypotheses),
        "n_infeasible": hset.manifest.n_infeasible,
        "excluded_columns": hset.manifest.excluded_columns,
        "semantic_types": {c.name: c.semantic_type.value for c in cleaned_profile.columns},
    }
    return df, hset, meta


def run_stage_a(hset: HypothesisSet, df: pd.DataFrame, cfg: PipelineConfig) -> list[TestResult]:
    """Phase 3 Stage A for every hypothesis (sequential; the benchmark parallelises by dataset)."""
    from veridata.stats.runner import run_hypothesis

    return [run_hypothesis(h, df, cfg, stage="A") for h in sorted(hset.hypotheses, key=lambda h: h.id)]


def _finding_direction(f: Finding) -> dict[str, Any] | None:
    t = f.test
    h = f.hypothesis
    d = t.direction_observed
    rel = h.relationship
    if rel in {RelationshipType.NUM_NUM, RelationshipType.NUM_NUM_NONLINEAR}:
        if d == Direction.POSITIVE:
            return {"kind": "sign", "value": "+"}
        if d == Direction.NEGATIVE:
            return {"kind": "sign", "value": "-"}
        return None
    if rel in {RelationshipType.NUM_BINARY, RelationshipType.NUM_CATEGORICAL}:
        # Phase 2 contract: column_a is the numeric outcome, column_b the grouping column.
        top = t.descriptives.get("higher_group") or t.descriptives.get("highest_group")
        if top is None:
            return None
        n_levels = len(t.group_sizes) if t.group_sizes else None
        return {"kind": "group_diff", "group_col": h.column_b, "higher_level": str(top), "n_levels": n_levels}
    return None


def findings_to_reported(findings: list[Finding]) -> list[ReportedFinding]:
    out = []
    for f in findings:
        if not f.decision.accepted:
            continue
        eff = f.test.effect
        out.append(
            ReportedFinding(
                col_a=f.hypothesis.column_a,
                col_b=f.hypothesis.column_b,
                direction=_finding_direction(f),
                effect=None if eff is None else eff.comparable_value,
                p_value=f.decision.p_raw,
                q_value=f.decision.q_value,
                source_id=f.hypothesis.id,
            )
        )
    return out


def validate_variant(results: list[TestResult], hset: HypothesisSet, base_cfg: PipelineConfig, variant: Variant) -> list[Finding]:
    from veridata.validation.validator import build_findings, validate

    cfg = variant_config(base_cfg, variant)
    hyp_map = {h.id: h for h in hset.hypotheses}
    decisions = validate(results, hyp_map, cfg)
    return build_findings(hyp_map, results, decisions)


def run_veridata_variants(
    csv_path: Path | str,
    dataset_id: str,
    variants: list[str] | None = None,
    base_cfg: PipelineConfig | None = None,
) -> dict[str, SystemOutput]:
    """Run every requested variant on one dataset, sharing Stage A per selection mode."""
    names = variants or DEFAULT_VARIANTS
    cfg = benchmark_config(base_cfg)
    t0 = time.perf_counter()
    df, hset, meta = prepare_dataset(csv_path, dataset_id, cfg)
    t_prep = time.perf_counter() - t0
    stage: dict[bool, tuple[list[TestResult], float]] = {}
    outputs: dict[str, SystemOutput] = {}
    for name in names:
        v = get_variant(name)
        if v.aware_selection not in stage:
            t1 = time.perf_counter()
            sel_cfg = cfg.model_copy(deep=True)
            sel_cfg.stats.assumption_aware_selection = v.aware_selection
            stage[v.aware_selection] = (run_stage_a(hset, df, sel_cfg), time.perf_counter() - t1)
        results, t_stage = stage[v.aware_selection]
        t2 = time.perf_counter()
        findings = validate_variant(results, hset, cfg, v)
        reported = findings_to_reported(findings)
        n_ok = sum(1 for r in results if r.status == "ok")
        outputs[name] = SystemOutput(
            system_name=name,
            dataset_id=dataset_id,
            findings=reported,
            n_tests_attempted=n_ok,
            runtime_s=round(t_prep + t_stage + (time.perf_counter() - t2), 3),
            meta={
                **{k: meta[k] for k in ("n_hypotheses", "n_infeasible")},
                "n_raw_p_below_alpha": sum(1 for r in results if r.status == "ok" and r.p_value is not None and r.p_value < cfg.stats.alpha),
                "prep_s": round(t_prep, 3),
                "stage_a_s": round(t_stage, 3),
                "excluded_columns": meta["excluded_columns"],
            },
        )
    return outputs
