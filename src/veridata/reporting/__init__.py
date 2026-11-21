"""Reporting.

- Phase 1 dataset report (profile / cleaning / EDA / insights): :func:`render_dataset_report`.
- Phase 5 findings report: facts, templates, number verifier, language linter, charts and the
  report builder (``veridata.reporting.facts``, ``templates``, ``number_verifier``,
  ``language_lint``, ``charts``, ``report_builder``).
"""

from veridata.reporting.dataset_report import render_dataset_report

__all__ = ["render_dataset_report"]
