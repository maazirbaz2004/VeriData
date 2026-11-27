"""Statistical aggregation, bootstrap CIs, repeat collapsing, and paired comparisons (Phase 8)."""

from __future__ import annotations

import itertools
from collections import defaultdict
from collections.abc import Iterable, Sequence
from typing import Any

import numpy as np
from scipy import stats as sps


def bootstrap_metric_ci(
    values: Sequence[float | None],
    *,
    n_resamples: int = 2000,
    seed: int = 0,
    level: float = 0.95,
) -> dict[str, float | None]:
    """Compute mean and percentile bootstrap CI over a sequence of dataset-level values."""
    clean = [float(v) for v in values if v is not None and np.isfinite(float(v))]
    if not clean:
        return {"mean": None, "ci_low": None, "ci_high": None, "n": 0}
    arr = np.asarray(clean, dtype=float)
    mean_val = float(np.mean(arr))
    if len(arr) == 1:
        return {"mean": mean_val, "ci_low": mean_val, "ci_high": mean_val, "n": 1}

    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(arr), size=(n_resamples, len(arr)))
    boot_means = np.mean(arr[idx], axis=1)
    lo_q = (1.0 - level) / 2.0
    hi_q = 1.0 - lo_q
    return {
        "mean": mean_val,
        "ci_low": float(np.quantile(boot_means, lo_q)),
        "ci_high": float(np.quantile(boot_means, hi_q)),
        "n": len(arr),
    }


def collapse_repeats(
    per_run_rows: Sequence[dict[str, Any]],
    *,
    group_key: str = "dataset_id",
    metric_keys: Sequence[str] = (
        "fdp",
        "recall",
        "precision",
        "n_reported",
        "tp",
        "fp",
        "fn",
        "any_false_discovery",
    ),
) -> list[dict[str, Any]]:
    """Average per-dataset metrics over LLM repeats before dataset-level inference.

    Phase 8 rule: repeats on the same dataset are NOT independent datasets; collapse to
    one dataset-level row (carrying both repeat mean and within-dataset SD) first.
    """
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in per_run_rows:
        grouped[str(row[group_key])].append(row)

    collapsed: list[dict[str, Any]] = []
    for ds_id in sorted(grouped):
        runs = grouped[ds_id]
        base = dict(runs[0])
        base["n_repeats"] = len(runs)
        for k in metric_keys:
            vals = [float(r[k]) for r in runs if r.get(k) is not None and np.isfinite(float(r[k]))]
            if vals:
                base[k] = float(np.mean(vals))
                base[f"{k}_repeat_sd"] = float(np.std(vals, ddof=1)) if len(vals) > 1 else 0.0
            else:
                base[k] = None
                base[f"{k}_repeat_sd"] = None
        collapsed.append(base)
    return collapsed


def paired_wilcoxon(
    a_by_dataset: dict[str, float | None],
    b_by_dataset: dict[str, float | None],
    *,
    n_resamples: int = 2000,
    seed: int = 0,
) -> dict[str, Any]:
    """Paired Wilcoxon signed-rank test and bootstrap CI on (a - b) across shared datasets."""
    shared = sorted(
        k
        for k in (set(a_by_dataset) & set(b_by_dataset))
        if a_by_dataset[k] is not None
        and b_by_dataset[k] is not None
        and np.isfinite(float(a_by_dataset[k]))  # type: ignore[arg-type]
        and np.isfinite(float(b_by_dataset[k]))  # type: ignore[arg-type]
    )
    if not shared:
        return {
            "n_pairs": 0,
            "mean_diff": None,
            "median_diff": None,
            "ci_low": None,
            "ci_high": None,
            "statistic": None,
            "p_value": None,
        }

    diffs = np.array([float(a_by_dataset[k]) - float(b_by_dataset[k]) for k in shared], dtype=float)  # type: ignore[arg-type]
    ci = bootstrap_metric_ci(diffs.tolist(), n_resamples=n_resamples, seed=seed)
    nonzero = diffs[np.abs(diffs) > 1e-15]
    if len(nonzero) == 0:
        stat_val, p_val = 0.0, 1.0
    else:
        res = sps.wilcoxon(diffs, alternative="two-sided", zero_method="wilcox")
        stat_val = float(res.statistic)
        p_val = float(res.pvalue)

    return {
        "n_pairs": len(diffs),
        "mean_diff": float(np.mean(diffs)),
        "median_diff": float(np.median(diffs)),
        "ci_low": ci["ci_low"],
        "ci_high": ci["ci_high"],
        "statistic": stat_val,
        "p_value": p_val,
    }


def jaccard_similarity(set_a: Iterable[Any], set_b: Iterable[Any]) -> float:
    """Jaccard similarity |A & B| / |A | B|, returning 1.0 when both sets are empty."""
    a = set(set_a)
    b = set(set_b)
    if not a and not b:
        return 1.0
    union = a | b
    return float(len(a & b) / len(union))


def mean_pairwise_jaccard(sets: Sequence[Iterable[Any]]) -> float | None:
    """Mean pairwise Jaccard similarity across >= 2 sets."""
    if len(sets) < 2:
        return None
    frozen = [set(s) for s in sets]
    sims = [jaccard_similarity(a, b) for a, b in itertools.combinations(frozen, 2)]
    return float(np.mean(sims)) if sims else None
