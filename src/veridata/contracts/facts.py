"""Pydantic v2 Fact contract for Phase 5 number verification (Master Plan Section 5.7)."""

from __future__ import annotations

from pydantic import BaseModel


class Fact(BaseModel):
    """Traceable numeric or formatted fact extracted from a TestResult/ValidationDecision."""

    key: str
    value: float | int | str
    display: str
    unit: str | None = None
    source: str

