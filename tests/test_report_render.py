"""Tests for per-dataset report rendering (report.md + report.html) — pure template code."""

from __future__ import annotations

import re
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

from test_eda import make_frame

from ads.eda.core import run_eda_core
from ads.eda.plots import EDASettings
from ads.insight_rules import DEFAULT_MANUAL_BLOCK, build_insights
from ads.report_render import build_context, markdown_to_html, render_html, render_markdown


def test_markdown_to_html_constructs() -> None:
    md = "\n".join(
        [
            "# Title",
            "",
            "Some **bold**, `code` and a [link](x.md).",
            "",
            "| Name | Value |",
            "| :--- | ---: |",
            "| a \\| b | 1,234 |",
            "",
            "![A chart](figures/a.png)",
            "",
            "*Figure 1. A chart.* Caption text.",
            "",
            "- one",
            "- two <script>",
            "",
            "> quoted note",
            "<!-- MANUAL:START -->",
        ]
    )
    html = markdown_to_html(md)
    assert "<h1>Title</h1>" in html
    assert "<strong>bold</strong>" in html and "<code>code</code>" in html and '<a href="x.md">link</a>' in html
    assert '<td class="num">1,234</td>' in html and "<td>a | b</td>" in html
    assert '<img src="figures/a.png" alt="A chart"' in html
    assert '<p class="caption"><em>Figure 1. A chart.</em> Caption text.</p>' in html
    assert "<li>two &lt;script&gt;</li>" in html  # escaped
    assert "<blockquote>quoted note</blockquote>" in html
    assert "MANUAL" not in html


class _TagChecker(HTMLParser):
    VOID = {"img", "meta", "br", "hr", "link"}

    def __init__(self) -> None:
        super().__init__()
        self.stack: list[str] = []
        self.errors = 0

    def handle_starttag(self, tag: str, attrs: Any) -> None:
        if tag not in self.VOID:
            self.stack.append(tag)

    def handle_endtag(self, tag: str) -> None:
        if self.stack and self.stack[-1] == tag:
            self.stack.pop()
        else:
            self.errors += 1


def _context(tmp_path: Path) -> dict[str, Any]:
    df, sem, roles = make_frame()
    res = run_eda_core(df, sem, roles, "churn", EDASettings(), tmp_path)
    log = [
        {"step": "handle_duplicates", "action": "dropped_duplicate_rows", "column": None, "n_cells_affected": 90, "n_rows_affected": 9, "rows_before": 309, "rows_after": 300},
        {"step": "normalize_missing_tokens", "action": "converted_to_NaN", "column": "income", "n_cells_affected": 10, "n_rows_affected": 10, "rows_before": 300, "rows_after": 300},
    ]
    profile = {
        "source_file": "data/raw/demo.csv",
        "sha256": "abc123",
        "n_duplicate_rows": 9,
        "memory_mb": 0.1,
        "missing_matrix_summary": {"total_missing_cells": 15, "pct_missing_cells": 0.005},
        "warnings": ["Column 'income' has extreme skew."],
        "columns": [{"name": "income", "raw_dtype": "object", "semantic_type": "numeric_continuous", "pct_missing": 0.0333, "n_unique": 290, "semantic_type_reason": "numeric | parse rate 1.0"}],
    }
    return build_context(
        name="demo",
        profile=profile,
        log=log,
        cleaning_summary={"total_cells_affected": 100},
        dropped_columns=[],
        outlier_report={"income": {"n_flagged": 12, "pct_flagged": 0.04, "n_extreme": 3, "iqr_1_5_lower": -1000.0, "iqr_1_5_upper": 60000.5, "action_taken": "flag"}},
        shapes={"raw": (309, 9), "conservative": (300, 9), "imputed": (300, 10)},
        figures=res["figures"],
        tables=res["tables"],
        headline=res["headline"],
        scaling={"columns": [{"column": "income", "skewness": 2.1, "recommended_transform": "log1p", "reason": "skew > 1"}], "decision_paragraph": "Primary cleaned output is **not** scaled.", "scaled_csv_path": "data/cleaned/demo_scaled.csv"},
        insights=build_insights(profile, log, res["headline"]),
        manual_block=DEFAULT_MANUAL_BLOCK.replace("*(Analyst to fill in)*", "Income drives spend.", 1),
        output_files=["[report.md](report.md): this report"],
    )


def test_report_markdown_has_every_section_and_valid_links(tmp_path: Path) -> None:
    ctx = _context(tmp_path)
    md = render_markdown(ctx)
    for heading in [
        "## 1. Overview",
        "## 2. Column profile (raw file)",
        "## 3. Data cleaning",
        "### What the TA asked for",
        "## 4. Exploratory data analysis",
        "## 5. Insights",
        "### Manual insights (written by the analyst)",
        "## 6. Normalization / scaling",
        "## 7. Output files",
    ]:
        assert heading in md, heading
    for req in ["| Missing values |", "| Duplicates |", "| Outliers |", "| Inconsistent formats |"]:
        assert req in md
    assert "dropped duplicate rows: 9 rows" in md
    assert "Income drives spend." in md and "MANUAL:START" not in md
    images = re.findall(r"!\[[^\]]*\]\((figures/[^)]+)\)", md)
    assert len(images) == sum(len(s["figures"]) for s in ctx["eda_sections"])
    for rel in images:
        assert (tmp_path / rel).exists(), rel
    numbers = [int(n) for n in re.findall(r"\*Figure (\d+)\.", md)]
    assert numbers == list(range(1, len(numbers) + 1))
    assert "significant" not in md.lower() and "p-value" not in md.lower()


def test_report_html_is_well_formed_and_matches_markdown(tmp_path: Path) -> None:
    md = render_markdown(_context(tmp_path))
    page = render_html(md, "Phase 1 Report — demo")
    checker = _TagChecker()
    checker.feed(page)
    assert checker.errors == 0 and checker.stack == []
    assert page.count("<img ") == md.count("![")
    assert page.count("<table>") == len(re.findall(r"^\| :?-", md, flags=re.M))
    assert "<title>Phase 1 Report — demo</title>" in page


def test_report_rendering_is_deterministic(tmp_path: Path) -> None:
    a = render_markdown(_context(tmp_path / "a"))
    b = render_markdown(_context(tmp_path / "b"))
    assert a == b
