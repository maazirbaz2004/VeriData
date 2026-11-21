"""Shared Pydantic v2 data contracts across VeriData Phases 2–8."""

from __future__ import annotations

from veridata.contracts.common import SCHEMA_VERSION
from veridata.contracts.facts import Fact
from veridata.contracts.findings import Finding
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
from veridata.contracts.ledger import Ledger, LedgerEntry
from veridata.contracts.results import AssumptionCheck, EffectSize, TestResult
from veridata.contracts.validation import RejectionReason, ValidationDecision

__all__ = [
    "SCHEMA_VERSION",
    "AssumptionCheck",
    "Direction",
    "EffectSize",
    "Fact",
    "FeasibilityReport",
    "Finding",
    "Hypothesis",
    "HypothesisManifest",
    "HypothesisSet",
    "LLMHypothesisProposal",
    "LLMProposalBatch",
    "Ledger",
    "LedgerEntry",
    "NLHypothesisParse",
    "NLParseOutcome",
    "RejectionReason",
    "RelationshipType",
    "TestResult",
    "ValidationDecision",
]
