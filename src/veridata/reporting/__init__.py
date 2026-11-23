"""Reporting and number verification package."""

from __future__ import annotations

from veridata.reporting.charts import plot_distribution, plot_finding
from veridata.reporting.facts import AllowedNumber, FactRegistry, build_facts
from veridata.reporting.language_lint import LintResult, lint_text
from veridata.reporting.narration import Explanation, explain_finding
from veridata.reporting.number_verifier import VerificationResult, verify_text
from veridata.reporting.phase1_report import render_dataset_report
from veridata.reporting.templates import render_rejection_template, render_template

__all__ = [
    "AllowedNumber",
    "FactRegistry",
    "build_facts",
    "render_template",
    "render_rejection_template",
    "verify_text",
    "VerificationResult",
    "lint_text",
    "LintResult",
    "explain_finding",
    "Explanation",
    "plot_finding",
    "plot_distribution",
    "render_dataset_report",
]
