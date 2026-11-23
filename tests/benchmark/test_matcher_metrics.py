"""Phase 4 matcher and metrics tests, against hand-built truths (Section 10: Matcher, Metrics)."""

from __future__ import annotations

import pytest

from veridata.benchmark.matcher import match_findings
from veridata.benchmark.metrics import (
    aggregate,
    aggregate_point,
    bootstrap_ci,
    dataset_metrics,
    q_calibration,
    stratified_recall,
)
from veridata.benchmark.truth import GroundTruth, ReportedFinding, TruthPair

COLS = {"a": "numeric", "b": "numeric", "c": "binary", "d": "numeric", "e": "categorical", "f": "categorical", "g": "numeric"}


def _truth() -> GroundTruth:
    return GroundTruth(
        dataset_id="hand", scenario_id="hand", seed=0, n_rows=500, columns=COLS,
        true_pairs=[
            TruthPair(col_a="a", col_b="b", type="direct", form="linear", population_effect={"bin": "medium"}, direction={"kind": "sign", "value": "+"}),
            TruthPair(col_a="c", col_b="d", type="direct", form="binary_shift", population_effect={"bin": "large"}, direction={"kind": "group_diff", "group_col": "c", "higher_level": "L1", "n_levels": 2}),
            TruthPair(col_a="d", col_b="e", type="direct", form="categorical_shift", population_effect={"bin": "small"}, direction={"kind": "group_diff", "group_col": "e", "higher_level": "L2", "n_levels": 3}),
            TruthPair(col_a="e", col_b="f", type="direct", form="cat_cat", population_effect={"bin": "small"}),
            TruthPair(col_a="a", col_b="g", type="direct", form="quadratic", detectable_by_default_tests=False),
            TruthPair(col_a="b", col_b="g", type="induced", form="induced", testable=False, direction={"kind": "sign", "value": "-"}),
        ],
        gray_pairs=[TruthPair(col_a="b", col_b="d", type="weak_induced", form="induced")],
        n_pairs_total=21, null_pairs_count=14,
    )


def F(a: str, b: str, direction: dict | None = None, q: float | None = None) -> ReportedFinding:
    return ReportedFinding(col_a=a, col_b=b, direction=direction, q_value=q)


def test_every_classification_path() -> None:
    t = _truth()
    found = [
        F("b", "a", {"kind": "sign", "value": "+"}, 0.001),  # TP, unordered pair
        F("a", "b", {"kind": "sign", "value": "-"}),  # duplicate -> collapsed
        F("d", "c", {"kind": "group_diff", "group_col": "c", "higher_level": "L0", "n_levels": 2}, 0.01),  # wrong group -> FP
        F("e", "d", {"kind": "group_diff", "group_col": "e", "higher_level": "L0", "n_levels": 3}),  # 3 levels: not checked -> TP
        F("e", "f"),  # cat-cat, no direction -> TP
        F("b", "d"),  # gray -> ignored
        F("a", "c", None, 0.04),  # null -> FP
        F("a", "zz"),  # unknown column -> FP
        F("g", "a"),  # undetectable decoy reported -> still a true pair
    ]
    m = match_findings(found, t)
    labels = {(f.col_a, f.col_b): (f.label, f.reason) for f in m.findings}
    assert labels[("a", "b")] == ("true", "true_pair")
    assert labels[("c", "d")] == ("false", "wrong_direction")
    assert labels[("d", "e")] == ("true", "true_pair")
    assert labels[("e", "f")] == ("true", "true_pair")
    assert labels[("b", "d")] == ("ignored", "gray_pair")
    assert labels[("a", "c")] == ("false", "null_pair")
    assert labels[("a", "zz")] == ("false", "unknown_column")
    assert labels[("a", "g")] == ("true", "true_pair")
    assert m.n_duplicates == 1 and m.tp == 4 and m.fp == 3

    met = dataset_metrics(m, t)
    # testable truths: a-b, c-d, d-e, e-f (a-g undetectable, b-g not testable)
    assert met["n_testable_truths"] == 4
    assert met["fn"] == 1  # c-d not credited (wrong direction)
    assert met["recall"] == pytest.approx(3 / 4)
    assert met["recall_all_true"] == pytest.approx(4 / 6)
    assert met["precision"] == pytest.approx(4 / 7)
    assert met["fdp"] == pytest.approx(3 / 7)
    assert met["fp_null_pairs"] == 1 and met["fp_wrong_direction"] == 1 and met["fp_unknown_column"] == 1


def test_ignore_direction_mode_credits_wrong_direction() -> None:
    t = _truth()
    m = match_findings([F("c", "d", {"kind": "group_diff", "group_col": "c", "higher_level": "L0", "n_levels": 2})], t, "ignore")
    assert m.tp == 1 and m.fp == 0
    m2 = match_findings([F("a", "b", {"kind": "sign", "value": "-"})], t)
    assert m2.fp == 1
    # numeric-like level labels compare after normalisation ("1.0" == "1")
    t3 = _truth()
    t3.true_pairs[1].direction = {"kind": "group_diff", "group_col": "c", "higher_level": "1", "n_levels": 2}
    m3 = match_findings([F("c", "d", {"kind": "group_diff", "group_col": "c", "higher_level": "1.0"})], t3)
    assert m3.tp == 1


def test_empty_report_conventions() -> None:
    t = _truth()
    met = dataset_metrics(match_findings([], t), t)
    assert met["n_reported"] == 0 and met["fdp"] == 0.0 and met["precision"] is None
    assert met["recall"] == 0.0 and not met["any_false_discovery"]


def test_aggregate_hand_computed() -> None:
    rows = [
        {"n_testable_truths": 4, "n_reported": 5, "fn": 1, "fdp": 0.4, "recall": 0.75, "precision": 0.6, "zero_planted": False, "is_pure_null": False, "any_false_discovery": True, "fp": 2},
        {"n_testable_truths": 0, "n_reported": 0, "fn": 0, "fdp": 0.0, "recall": None, "precision": None, "zero_planted": True, "is_pure_null": True, "any_false_discovery": False, "fp": 0},
        {"n_testable_truths": 0, "n_reported": 1, "fn": 0, "fdp": 1.0, "recall": None, "precision": 0.0, "zero_planted": True, "is_pure_null": True, "any_false_discovery": True, "fp": 1},
        {"n_testable_truths": 2, "n_reported": 2, "fn": 0, "fdp": 0.0, "recall": 1.0, "precision": 1.0, "zero_planted": False, "is_pure_null": False, "any_false_discovery": False, "fp": 0},
    ]
    a = aggregate_point(rows)
    assert a["fdr"] == pytest.approx((0.4 + 0 + 1 + 0) / 4)
    assert a["mean_fdp_nonempty"] == pytest.approx((0.4 + 1 + 0) / 3)
    assert a["recall"] == pytest.approx((0.75 + 1.0) / 2)
    assert a["recall_micro"] == pytest.approx(5 / 6)
    assert a["precision"] == pytest.approx((0.6 + 0 + 1) / 3)
    assert a["fwer_null"] == pytest.approx(0.5)
    assert a["pure_null_any_report"] == pytest.approx(0.5)
    assert a["mean_fp_null_datasets"] == pytest.approx(0.5)
    assert a["n_empty"] == 1


def test_bootstrap_is_reproducible_and_brackets_point() -> None:
    rows = [{"n_testable_truths": 1, "n_reported": 1, "fn": 0 if i % 3 else 1, "fdp": (i % 5) / 10, "recall": 1.0 if i % 3 else 0.0,
             "precision": 1.0, "zero_planted": False, "is_pure_null": False, "any_false_discovery": bool(i % 5), "fp": i % 5} for i in range(30)]
    c1 = bootstrap_ci(rows, aggregate_point, n_resamples=300, seed=1)
    c2 = bootstrap_ci(rows, aggregate_point, n_resamples=300, seed=1)
    assert c1 == c2
    agg = aggregate(rows, n_resamples=300, seed=1)
    assert agg["fdr_ci_low"] <= agg["fdr"] <= agg["fdr_ci_high"]


def test_stratified_recall_and_q_calibration() -> None:
    pairs = [
        {"form": "linear", "bin": "small", "detectable": True, "testable": True, "found": True},
        {"form": "linear", "bin": "small", "detectable": True, "testable": True, "found": False},
        {"form": "linear", "bin": "large", "detectable": True, "testable": True, "found": True},
        {"form": "quadratic", "bin": "n/a", "detectable": False, "testable": True, "found": False},
    ]
    s = stratified_recall(pairs, ["form", "bin"])
    assert s == [{"form": "linear", "bin": "large", "n_truths": 1, "recall": 1.0}, {"form": "linear", "bin": "small", "n_truths": 2, "recall": 0.5}]
    qc = q_calibration([{"label": "true", "q_value": 0.0005}, {"label": "false", "q_value": 0.0008}, {"label": "true", "q_value": 0.03}, {"label": "ignored", "q_value": 0.03}])
    assert qc[0]["n"] == 2 and qc[0]["false_fraction"] == 0.5
    assert next(r for r in qc if r["q_low"] == 0.02)["n"] == 1
