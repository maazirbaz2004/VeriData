"""Tests for the rule-based insight generator (Section 11) — pure rule functions."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest
from test_eda import make_frame  # same constructed frame as the EDA tests

from ads.eda.core import run_eda_core
from ads.eda.plots import EDASettings
from ads.insight_rules import (
    CATEGORY_ORDER,
    DEFAULT_MANUAL_BLOCK,
    SEVERITY_ORDER,
    build_insights,
    extract_manual_block,
    render_insights_markdown,
)

_NUM_RE = re.compile(r"(?<![\w.])-?\d[\d,]*\.?\d*(?![\w])")


def _evidence_numbers(ev: Any) -> list[float]:
    out: list[float] = []
    if isinstance(ev, dict):
        for v in ev.values():
            out += _evidence_numbers(v)
    elif isinstance(ev, list):
        for v in ev:
            out += _evidence_numbers(v)
    elif isinstance(ev, (int, float)) and not isinstance(ev, bool):
        out.append(float(ev))
    return out


def untraced_numbers(item: dict[str, Any]) -> list[float]:
    """Numbers printed in the statement that are not in its evidence (quoted names and 'Phase N' ignored)."""
    text = re.sub(r"'[^']*'", "", item["statement"])
    text = re.sub(r"Phase \d", "", text)
    text = text.replace("1.5×IQR", "").replace("eta²", "eta")
    ev = _evidence_numbers(item["evidence"])
    bad = []
    for tok in _NUM_RE.findall(text):
        n = float(tok.replace(",", ""))
        if not any(abs(n - e) < 1e-9 or abs(n - abs(e)) < 1e-9 for e in ev):
            bad.append(n)
    return bad


@pytest.fixture(scope="module")
def eda_headline(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Any]:
    df, sem, roles = make_frame()
    out = tmp_path_factory.mktemp("eda")
    return run_eda_core(df, sem, roles, "churn", EDASettings(), out)["headline"]


SAMPLE_LOG = [
    {"step": "handle_duplicates", "action": "dropped_duplicate_rows", "column": None, "n_cells_affected": 90, "n_rows_affected": 9, "rows_before": 309, "rows_after": 300},
    {"step": "convert_types", "action": "cast_dtype", "column": "income", "n_cells_affected": 14, "n_rows_affected": 14, "rows_before": 300, "rows_after": 300},
    {"step": "apply_validity_rules", "action": "invalid_to_NaN", "column": "age", "n_cells_affected": 3, "n_rows_affected": 3, "rows_before": 300, "rows_after": 300, "parameters": {"min": 0, "max": 120}},
    {"step": "standardize_categories", "action": "merged_case_variants", "column": "segment", "n_cells_affected": 7, "n_rows_affected": 7, "rows_before": 300, "rows_after": 300},
]
SAMPLE_PROFILE = {"columns": [{"name": "income", "missing_tokens_found": {"N/A": 6, "?": 4}}]}


def test_every_number_traces_to_evidence(eda_headline: dict[str, Any]) -> None:
    items = build_insights(SAMPLE_PROFILE, SAMPLE_LOG, eda_headline)
    assert len(items) >= 10
    for i in items:
        assert untraced_numbers(i) == [], i["statement"]


def test_records_are_valid_sorted_and_unique(eda_headline: dict[str, Any]) -> None:
    items = build_insights(SAMPLE_PROFILE, SAMPLE_LOG, eda_headline)
    ids = [i["id"] for i in items]
    assert len(ids) == len(set(ids))
    keys = [(CATEGORY_ORDER.index(i["category"]), SEVERITY_ORDER[i["severity"]], i["id"]) for i in items]
    assert keys == sorted(keys)
    for i in items:
        assert set(i) == {"id", "category", "severity", "statement", "evidence", "figure_ref"}
        assert i["figure_ref"] is None or i["figure_ref"].startswith("figures/")


def test_rules_fire_on_expected_inputs(eda_headline: dict[str, Any]) -> None:
    items = build_insights(SAMPLE_PROFILE, SAMPLE_LOG, eda_headline)
    by_rule = {i["id"].split("_")[0] + "_" + i["id"].split("_")[1] for i in items}
    text = " ".join(i["statement"] for i in items)
    assert "9 exact duplicate rows were removed" in text
    assert "'income' was stored as text" in text and "14 cells" in text
    assert "'N/A' (6)" in text and "10 cells" in text
    assert "outside its allowed range" in text
    assert "differed only by capitals or spaces" in text
    assert "Column 'income' has 3.33% missing values (n = 10 of 300 rows)." in text
    assert "'income' is right-skewed" in text  # log-normal column
    assert "Target 'churn'" in text
    assert "'cust_id' is ID-like" in text
    assert any(i["category"] == "relationships" for i in items)
    assert any(i["category"] == "modeling_testing_implications" for i in items)
    assert "dq_missing" in by_rule


def test_small_dataset_and_kept_duplicates() -> None:
    headline = {"overview": {"n_rows": 120}, "missingness": {"columns": {}}}
    log = [{"step": "handle_duplicates", "action": "kept_duplicates_warning", "column": None, "n_cells_affected": 0, "n_rows_affected": 5}]
    items = build_insights({}, log, headline)
    text = " ".join(i["statement"] for i in items)
    assert "small (120 rows" in text
    assert "5 exact duplicate rows were found but kept" in text


def test_scaling_notes_forwarded() -> None:
    scaling = {
        "columns": [
            {"column": "income", "skewness": 2.345, "recommended_transform": "log1p"},
            {"column": "age", "skewness": 0.1, "recommended_transform": "none"},
        ],
        "scale_disparity_ratio": 812.456,
        "recommend_zscore_for_scale_sensitive": True,
    }
    items = build_insights({}, [], {"overview": {"n_rows": 500}}, scaling)
    sc = [i for i in items if i["category"] == "scaling"]
    assert len(sc) == 2
    assert "log1p is recommended for 'income' (skew = 2.35)" in sc[1]["statement"] or "log1p is recommended for 'income' (skew = 2.35)" in sc[0]["statement"]
    for i in sc:
        assert untraced_numbers(i) == []


def test_no_inferential_wording(eda_headline: dict[str, Any]) -> None:
    md = render_insights_markdown("demo", build_insights(SAMPLE_PROFILE, SAMPLE_LOG, eda_headline), DEFAULT_MANUAL_BLOCK)
    low = md.lower()
    for word in ("p-value", "p value", "significant"):
        assert word not in low


def test_manual_block_is_preserved(tmp_path: Path, eda_headline: dict[str, Any]) -> None:
    items = build_insights({}, [], eda_headline)
    first = render_insights_markdown("demo", items, extract_manual_block(None))
    assert DEFAULT_MANUAL_BLOCK in first
    edited = first.replace("*(Analyst to fill in)*", "Smokers pay far more.", 1)
    again = render_insights_markdown("demo", items, extract_manual_block(edited))
    assert "Smokers pay far more." in again
    assert again.count("<!-- MANUAL:START -->") == 1 and again.count("<!-- MANUAL:END -->") == 1
    # broken markers fall back to the template instead of losing the file structure
    assert extract_manual_block("no markers here") == DEFAULT_MANUAL_BLOCK


def test_build_insights_is_deterministic(eda_headline: dict[str, Any]) -> None:
    assert build_insights(SAMPLE_PROFILE, SAMPLE_LOG, eda_headline) == build_insights(SAMPLE_PROFILE, SAMPLE_LOG, eda_headline)
