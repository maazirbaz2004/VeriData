"""Phase 3 Statistical Validation Layer (correction, rules, validator, ledger)."""

from __future__ import annotations

from veridata.validation.correction import CorrectionOutput, apply_correction
from veridata.validation.ledger import SessionLedger
from veridata.validation.rules import (
    effect_threshold_for,
    evaluate_validation_rules,
    is_trivial_or_derived,
)
from veridata.validation.validator import build_findings, validate

__all__ = [
    "CorrectionOutput",
    "SessionLedger",
    "apply_correction",
    "build_findings",
    "effect_threshold_for",
    "evaluate_validation_rules",
    "is_trivial_or_derived",
    "validate",
]

