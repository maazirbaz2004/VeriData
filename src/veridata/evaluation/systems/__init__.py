"""Evaluation system adapters (VeriData S2/S3/A1-A6 and LLM-only S1a/S1b)."""

from __future__ import annotations

from veridata.evaluation.systems.llm_only import (
    LLM_SYSTEM_IDS,
    LLMFindingItem,
    LLMFindingsPayload,
    canonicalize_llm_findings,
    run_llm_only_system,
)
from veridata.evaluation.systems.veridata_variants import (
    PHASE8_VARIANTS,
    VariantSpec,
    run_phase8_variants_on_csv,
    run_phase8_variants_on_df,
)

__all__ = [
    "LLM_SYSTEM_IDS",
    "PHASE8_VARIANTS",
    "LLMFindingItem",
    "LLMFindingsPayload",
    "VariantSpec",
    "canonicalize_llm_findings",
    "run_llm_only_system",
    "run_phase8_variants_on_csv",
    "run_phase8_variants_on_df",
]
