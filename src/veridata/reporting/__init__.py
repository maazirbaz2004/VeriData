"""Reporting and number verification package.

- Phase 1 dataset report (profile / cleaning / EDA / insights): :func:`render_dataset_report`.
- Phase 5 findings report: facts, templates, narration, number verifier, language linter, charts,
  and the report builder (``veridata.reporting.facts``, ``templates``, ``narration``,
  ``number_verifier``, ``language_lint``, ``charts``, ``report_builder``).
"""

from __future__ import annotations

from veridata.reporting.charts import plot_distribution, plot_finding
from veridata.reporting.dataset_report import render_dataset_report
from veridata.reporting.facts import AllowedNumber, FactRegistry, build_facts, build_method_facts
from veridata.reporting.language_lint import LintIssue, LintResult, lint_text
from veridata.reporting.narration import Explanation, explain_finding
from veridata.reporting.number_verifier import VerificationResult, Violation, verify_text
from veridata.reporting.templates import (
    explain_accepted,
    explain_rejected,
    render_rejection_template,
    render_template,
)

__all__ = [
    "AllowedNumber",
    "FactRegistry",
    "build_facts",
    "build_method_facts",
    "explain_accepted",
    "explain_rejected",
    "render_template",
    "render_rejection_template",
    "verify_text",
    "VerificationResult",
    "Violation",
    "lint_text",
    "LintIssue",
    "LintResult",
    "explain_finding",
    "Explanation",
    "plot_finding",
    "plot_distribution",
    "render_dataset_report",
]
