"""Pydantic v2 Finding contract joining Hypothesis, TestResult, ValidationDecision, and Facts."""

from __future__ import annotations

from pydantic import BaseModel, Field

from veridata.contracts.common import SCHEMA_VERSION
from veridata.contracts.facts import Fact
from veridata.contracts.hypothesis import Hypothesis
from veridata.contracts.results import TestResult
from veridata.contracts.validation import ValidationDecision


class Finding(BaseModel):
    """Joined view of a tested and validated hypothesis (Master Plan Section 5.5)."""

    schema_version: str = SCHEMA_VERSION
    hypothesis: Hypothesis
    test: TestResult
    decision: ValidationDecision
    facts: list[Fact] = Field(default_factory=list)

