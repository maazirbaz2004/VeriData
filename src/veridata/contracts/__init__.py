"""Shared Pydantic v2 data contracts across VeriData Phases 2–8."""

from __future__ import annotations

from veridata.contracts.common import SCHEMA_VERSION
from veridata.contracts.hypothesis import (
    Direction,
    FeasibilityReport,
    Hypothesis,
    HypothesisManifest,
    HypothesisSet,
    LLMHypothesisProposal,
    LLMProposalBatch,
    NLHypothesisParse,
    NLParseOutcome,
    RelationshipType,
)

__all__ = [
    "SCHEMA_VERSION",
    "Direction",
    "FeasibilityReport",
    "Hypothesis",
    "HypothesisManifest",
    "HypothesisSet",
    "LLMHypothesisProposal",
    "LLMProposalBatch",
    "NLHypothesisParse",
    "NLParseOutcome",
    "RelationshipType",
]

