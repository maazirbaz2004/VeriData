"""Custom exception hierarchy for VeriData (Master Plan Section 9.3)."""

from __future__ import annotations


class VeriDataError(Exception):
    """Base exception for all VeriData library errors."""


class DataError(VeriDataError):
    """Raised on invalid, unreadable, or corrupt input datasets."""


class ConfigError(VeriDataError):
    """Raised on invalid or contradictory configuration."""


class HypothesisError(VeriDataError):
    """Raised during hypothesis enumeration, feasibility, or parsing."""


class StatsError(VeriDataError):
    """Raised by statistical test execution or assumption checks."""


class ValidationError(VeriDataError):
    """Raised by statistical validation or multiple-testing ledger invariants."""


class ReportingError(VeriDataError):
    """Raised during fact extraction, narration verification, or report rendering."""


class AgentError(VeriDataError):
    """Raised by LangGraph agent orchestration or routing."""


class LLMError(VeriDataError):
    """Raised when an LLM provider call fails or produces invalid structured output."""


class LLMUnavailable(LLMError):
    """Raised when no LLM provider/API key is configured; callers fall back offline (P4)."""

