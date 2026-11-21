"""Pydantic v2 Ledger contracts for honest multiple-testing accounting (Master Plan Section 5.6)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from veridata.contracts.common import SCHEMA_VERSION
from veridata.contracts.results import TestResult


class LedgerEntry(BaseModel):
    """Single immutable entry in the session testing ledger."""

    seq: int
    hypothesis_hash: str
    stage: Literal["batch", "chat"]
    test: TestResult
    added_at_utc: str


class Ledger(BaseModel):
    """Append-only record of every test attempted in a dataset session."""

    schema_version: str = SCHEMA_VERSION
    dataset_sha256: str
    alpha: float = 0.05
    entries: list[LedgerEntry] = Field(default_factory=list)

