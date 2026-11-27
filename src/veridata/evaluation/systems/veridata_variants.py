"""Phase 8 VeriData variant adapters (S2, S3, A1-A6) wrapping Phase 4 & Phase 3 pipelines."""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from veridata.benchmark.systems import (
    benchmark_config,
    findings_to_reported,
    prepare_dataset,
    run_stage_a,
)
from veridata.benchmark.truth import SystemOutput
from veridata.config import PipelineConfig
from veridata.contracts.findings import Finding
from veridata.contracts.hypothesis import HypothesisSet
from veridata.contracts.results import TestResult
from veridata.validation.validator import build_findings, validate


@dataclass(frozen=True)
class VariantSpec:
    """Configuration descriptor for one deterministic VeriData evaluation variant."""

    system_id: str
    alias: str
    aware_selection: bool
    correction: str
    effect_floor: bool
    gates_enabled: bool
    description: str


PHASE8_VARIANTS: dict[str, VariantSpec] = {
    v.system_id: v
    for v in [
        VariantSpec("S3_veridata_full", "veridata_full", True, "bh", True, True, "Full VeriData (assumption-aware + BH + effect floor + gates)."),
        VariantSpec("S2_veridata_nocorrection", "veridata_nocorrection", True, "none", False, True, "Assumption-aware selection, raw p < alpha, no floor."),
        VariantSpec("A1_bh_only", "bh_only", False, "bh", False, True, "Naive tests + BH; no floor."),
        VariantSpec("A2_floor_only", "floor_only", False, "none", True, True, "Naive tests + raw p < alpha + floor."),
        VariantSpec("A3_assumption_only", "assumption_only", True, "none", False, True, "Assumption-aware selection + raw p < alpha; no floor."),
        VariantSpec("A4_naive_tests", "naive_tests", False, "bh", True, True, "Always parametric/chi2 tests + BH + floor."),
        VariantSpec("A5_bonferroni", "bonferroni", True, "bonferroni", True, True, "Full pipeline with Bonferroni correction."),
        VariantSpec("A5_holm", "holm", True, "holm", True, True, "Full pipeline with Holm correction."),
        VariantSpec("A5_by", "by", True, "by", True, True, "Full pipeline with Benjamini-Yekutieli correction."),
        VariantSpec("A6_full_minus_floor", "full_minus_floor", True, "bh", False, True, "Full pipeline minus effect-size floor."),
        VariantSpec("A6_full_minus_gates", "full_minus_gates", True, "bh", True, False, "Full pipeline minus assumption & trivial gates."),
        VariantSpec("N0_naive_raw", "naive_raw", False, "none", False, True, "Everything off: naive tests, raw p < alpha, no floor."),
    ]
}

ALIAS_TO_SYSTEM_ID: dict[str, str] = {v.alias: v.system_id for v in PHASE8_VARIANTS.values()}
DEFAULT_PHASE8_VARIANT_IDS = list(PHASE8_VARIANTS.keys())


def resolve_variant_spec(name: str) -> VariantSpec:
    if name in PHASE8_VARIANTS:
        return PHASE8_VARIANTS[name]
    if name in ALIAS_TO_SYSTEM_ID:
        return PHASE8_VARIANTS[ALIAS_TO_SYSTEM_ID[name]]
    raise KeyError(f"Unknown Phase 8 variant: {name!r}")


def apply_variant_config(base: PipelineConfig, spec: VariantSpec) -> PipelineConfig:
    cfg = base.model_copy(deep=True)
    cfg.stats.assumption_aware_selection = spec.aware_selection
    cfg.stats.correction = spec.correction  # type: ignore[assignment]
    cfg.effect_floor.enabled = spec.effect_floor
    cfg.stats.enable_assumption_gate = spec.gates_enabled
    cfg.stats.enable_trivial_gate = spec.gates_enabled
    return cfg


def _validate_spec(
    results: list[TestResult],
    hset: HypothesisSet,
    base_cfg: PipelineConfig,
    spec: VariantSpec,
) -> list[Finding]:
    cfg = apply_variant_config(base_cfg, spec)
    hyp_map = {h.id: h for h in hset.hypotheses}
    decisions = validate(results, hyp_map, cfg)
    return build_findings(hyp_map, results, decisions)


def run_phase8_variants_on_csv(
    csv_path: Path | str,
    dataset_id: str,
    variants: list[str] | None = None,
    base_cfg: PipelineConfig | None = None,
) -> dict[str, SystemOutput]:
    """Run requested Phase 8 deterministic variants on a CSV, sharing Stage A per selection mode."""
    names = variants or DEFAULT_PHASE8_VARIANT_IDS
    cfg = benchmark_config(base_cfg)
    t0 = time.perf_counter()
    df, hset, meta = prepare_dataset(csv_path, dataset_id, cfg)
    t_prep = time.perf_counter() - t0
    return _run_variants_prepared(df, hset, meta, dataset_id, names, cfg, t_prep)


def run_phase8_variants_on_df(
    df: pd.DataFrame,
    dataset_id: str,
    variants: list[str] | None = None,
    base_cfg: PipelineConfig | None = None,
) -> dict[str, SystemOutput]:
    """Run requested Phase 8 deterministic variants on an already-cleaned DataFrame."""
    from veridata.hypotheses import generate_hypotheses
    from veridata.profiling import build_column_schema, profile_dataset

    names = variants or DEFAULT_PHASE8_VARIANT_IDS
    cfg = benchmark_config(base_cfg)
    t0 = time.perf_counter()
    profile = profile_dataset(
        df.astype("string").fillna("").astype(str),
        df_naive=df,
        config=cfg,
        dataset_name=dataset_id,
    )
    schema = build_column_schema(profile, config=cfg)
    hset = generate_hypotheses(df, schema, profile, cfg, llm=None, mode="exhaustive", dataset_name=dataset_id)
    meta = {
        "n_hypotheses": len(hset.hypotheses),
        "n_infeasible": hset.manifest.n_infeasible,
        "excluded_columns": hset.manifest.excluded_columns,
    }
    t_prep = time.perf_counter() - t0
    return _run_variants_prepared(df, hset, meta, dataset_id, names, cfg, t_prep)


def _run_variants_prepared(
    df: pd.DataFrame,
    hset: HypothesisSet,
    meta: dict[str, Any],
    dataset_id: str,
    names: list[str],
    cfg: PipelineConfig,
    t_prep: float,
) -> dict[str, SystemOutput]:
    stage: dict[bool, tuple[list[TestResult], float]] = {}
    outputs: dict[str, SystemOutput] = {}
    for name in names:
        spec = resolve_variant_spec(name)
        if spec.aware_selection not in stage:
            t1 = time.perf_counter()
            sel_cfg = cfg.model_copy(deep=True)
            sel_cfg.stats.assumption_aware_selection = spec.aware_selection
            stage[spec.aware_selection] = (run_stage_a(hset, df, sel_cfg), time.perf_counter() - t1)
        results, t_stage = stage[spec.aware_selection]
        t2 = time.perf_counter()
        findings = _validate_spec(results, hset, cfg, spec)
        reported = findings_to_reported(findings)
        n_ok = sum(1 for r in results if r.status == "ok")
        outputs[name] = SystemOutput(
            system_name=name,
            dataset_id=dataset_id,
            findings=reported,
            n_tests_attempted=n_ok,
            runtime_s=round(t_prep + t_stage + (time.perf_counter() - t2), 3),
            meta={
                "n_hypotheses": meta["n_hypotheses"],
                "n_infeasible": meta["n_infeasible"],
                "n_raw_p_below_alpha": sum(
                    1
                    for r in results
                    if r.status == "ok" and r.p_value is not None and r.p_value < cfg.stats.alpha
                ),
                "prep_s": round(t_prep, 3),
                "stage_a_s": round(t_stage, 3),
                "excluded_columns": meta["excluded_columns"],
            },
        )
    return outputs
