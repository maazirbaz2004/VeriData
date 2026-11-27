"""Unit tests for Phase 8 stats_utils (bootstrap CIs, repeat collapsing, Wilcoxon, Jaccard)."""

from __future__ import annotations

import numpy as np
import pytest
from scipy import stats as sp_stats

from veridata.evaluation.stats_utils import (
    bootstrap_metric_ci,
    collapse_repeats,
    jaccard_similarity,
    mean_pairwise_jaccard,
    paired_wilcoxon,
)


def test_collapse_repeats_hand_computed() -> None:
    rows = [
        {"dataset_id": "d1", "repeat": 0, "fdp": 0.10, "recall": 0.80},
        {"dataset_id": "d1", "repeat": 1, "fdp": 0.30, "recall": 0.60},
        {"dataset_id": "d2", "repeat": 0, "fdp": 0.00, "recall": 1.00},
    ]
    out = collapse_repeats(rows, metric_keys=("fdp", "recall"))
    assert len(out) == 2
    assert out[0]["dataset_id"] == "d1"
    assert out[0]["n_repeats"] == 2
    assert out[0]["fdp"] == pytest.approx(0.20)
    assert out[0]["fdp_repeat_sd"] == pytest.approx(np.std([0.10, 0.30], ddof=1))
    assert out[0]["recall"] == pytest.approx(0.70)
    assert out[1]["dataset_id"] == "d2"
    assert out[1]["fdp_repeat_sd"] == 0.0


def test_paired_wilcoxon_matches_scipy() -> None:
    a = {f"d{i}": float(i) * 0.01 for i in range(1, 13)}
    b = {f"d{i}": float(i) * 0.05 + 0.02 for i in range(1, 13)}
    res = paired_wilcoxon(a, b, n_resamples=500, seed=42)

    diffs = np.array([a[f"d{i}"] - b[f"d{i}"] for i in range(1, 13)])
    ref = sp_stats.wilcoxon(diffs, alternative="two-sided", zero_method="wilcox")
    assert res["n_pairs"] == 12
    assert res["mean_diff"] == pytest.approx(float(np.mean(diffs)))
    assert res["statistic"] == pytest.approx(float(ref.statistic))
    assert res["p_value"] == pytest.approx(float(ref.pvalue))
    assert res["ci_low"] <= res["mean_diff"] <= res["ci_high"]

    # Identical systems -> p = 1.0
    same = paired_wilcoxon(a, a, n_resamples=100, seed=0)
    assert same["p_value"] == 1.0
    assert same["mean_diff"] == 0.0


def test_bootstrap_and_jaccard_hand_computed() -> None:
    ci = bootstrap_metric_ci([0.0, 0.2, 0.4, 0.6], n_resamples=1000, seed=7)
    assert ci["mean"] == pytest.approx(0.3)
    assert 0.0 <= ci["ci_low"] <= 0.3 <= ci["ci_high"] <= 0.6

    assert jaccard_similarity([], []) == 1.0
    assert jaccard_similarity({"a", "b"}, {"b", "c"}) == pytest.approx(1.0 / 3.0)
    assert mean_pairwise_jaccard([{"a", "b"}, {"b", "c"}, {"a", "b"}]) == pytest.approx(
        (1.0 / 3.0 + 1.0 + 1.0 / 3.0) / 3.0
    )
