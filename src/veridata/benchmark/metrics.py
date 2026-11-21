"""Per-dataset and aggregate benchmark metrics with bootstrap CIs (Phase 4, Section 6).

Conventions (frozen in docs/eval_protocol.md):
- FDP of a dataset = FP / (TP + FP); 0 when nothing is reported. FDR = mean FDP over datasets.
- Precision is undefined for empty reports (excluded from the precision mean; counted in n_empty).
- Recall (primary) = found testable truths / testable truths (detectable by default tests and
  feasible in the realised data); averaged over datasets with >= 1 testable truth. Micro recall
  pools all testable truths.
- FWER_null = fraction of zero-planted-effect datasets with >= 1 false discovery.
"""

from __future__ import annotations

import itertools
from collections import defaultdict
from collections.abc import Callable
from typing import Any

import numpy as np

from veridata.benchmark.matcher import MatchResult
from veridata.benchmark.truth import GroundTruth


def dataset_metrics(match: MatchResult, truth: GroundTruth, scenario: dict[str, Any] | None = None) -> dict[str, Any]:
    tp = match.tp
    fp = match.fp
    testable = [t for t in match.truths if t.detectable and t.testable]
    found_testable = sum(1 for t in testable if t.found)
    found_all = sum(1 for t in match.truths if t.found)
    n_rep = tp + fp
    sc = scenario or {}
    return {
        "dataset_id": truth.dataset_id,
        "scenario_id": truth.scenario_id,
        "n_rows": truth.n_rows,
        "n_cols": len(truth.columns),
        "n_effects": sc.get("n_effects"),
        "strength": sc.get("effect_strength"),
        "dist": sc.get("dist"),
        "has_null_blocks": bool((sc.get("null_blocks") or {}).get("n_blocks", 0)),
        "is_pure_null": truth.is_pure_null,
        "zero_planted": sc.get("n_effects") == 0,
        "n_true_pairs": len(truth.true_pairs),
        "n_testable_truths": len(testable),
        "n_reported": n_rep,
        "n_ignored_gray": sum(1 for f in match.findings if f.label == "ignored"),
        "tp": tp,
        "fp": fp,
        "fn": len(testable) - found_testable,
        "fp_null_pairs": sum(1 for f in match.findings if f.reason == "null_pair"),
        "fp_wrong_direction": sum(1 for f in match.findings if f.reason == "wrong_direction"),
        "fp_unknown_column": sum(1 for f in match.findings if f.reason == "unknown_column"),
        "recall": (found_testable / len(testable)) if testable else None,
        "recall_all_true": (found_all / len(match.truths)) if match.truths else None,
        "precision": (tp / n_rep) if n_rep else None,
        "fdp": (fp / n_rep) if n_rep else 0.0,
        "any_false_discovery": fp > 0,
    }


def _mean(vals: list[float]) -> float | None:
    return float(np.mean(vals)) if vals else None


def aggregate_point(rows: list[dict[str, Any]]) -> dict[str, Any]:
    with_truth = [r for r in rows if r["n_testable_truths"]]
    nonempty = [r for r in rows if r["n_reported"]]
    zero = [r for r in rows if r.get("zero_planted")]
    pure = [r for r in rows if r["is_pure_null"]]
    tot_test = sum(r["n_testable_truths"] for r in rows)
    tot_found = sum(r["n_testable_truths"] - r["fn"] for r in rows)
    return {
        "n_datasets": len(rows),
        "n_empty": len(rows) - len(nonempty),
        "fdr": _mean([r["fdp"] for r in rows]),
        "mean_fdp_nonempty": _mean([r["fdp"] for r in nonempty]),
        "recall": _mean([r["recall"] for r in with_truth]),
        "recall_micro": (tot_found / tot_test) if tot_test else None,
        "precision": _mean([r["precision"] for r in nonempty]),
        "fwer_null": _mean([1.0 if r["any_false_discovery"] else 0.0 for r in zero]),
        "pure_null_any_report": _mean([1.0 if r["n_reported"] else 0.0 for r in pure]),
        "mean_fp_null_datasets": _mean([float(r["fp"]) for r in zero]),
        "mean_reported": _mean([float(r["n_reported"]) for r in rows]),
        "mean_fp": _mean([float(r["fp"]) for r in rows]),
    }


def bootstrap_ci(rows: list[dict[str, Any]], stat: Callable[[list[dict[str, Any]]], dict[str, Any]], *, n_resamples: int = 2000, seed: int = 0, level: float = 0.95) -> dict[str, tuple[float | None, float | None]]:
    """Percentile CIs by resampling datasets with replacement."""
    if not rows:
        return {}
    rng = np.random.default_rng(seed)
    keys = [k for k, v in stat(rows).items() if isinstance(v, float) or v is None]
    draws: dict[str, list[float]] = defaultdict(list)
    n = len(rows)
    for _ in range(n_resamples):
        sample = [rows[i] for i in rng.integers(0, n, n)]
        s = stat(sample)
        for k in keys:
            if s[k] is not None:
                draws[k].append(float(s[k]))
    lo_q, hi_q = (1 - level) / 2, 1 - (1 - level) / 2
    return {k: ((float(np.quantile(draws[k], lo_q)), float(np.quantile(draws[k], hi_q))) if draws[k] else (None, None)) for k in keys}


def aggregate(rows: list[dict[str, Any]], *, n_resamples: int = 2000, seed: int = 0) -> dict[str, Any]:
    point = aggregate_point(rows)
    ci = bootstrap_ci(rows, aggregate_point, n_resamples=n_resamples, seed=seed)
    out = dict(point)
    for k, (lo, hi) in ci.items():
        out[f"{k}_ci_low"] = lo
        out[f"{k}_ci_high"] = hi
    return out


def stratified_recall(pair_rows: list[dict[str, Any]], by: list[str]) -> list[dict[str, Any]]:
    """Micro recall of testable truths grouped by the given keys (e.g. form, bin, n_rows)."""
    groups: dict[tuple, list[bool]] = defaultdict(list)
    for r in pair_rows:
        if r["detectable"] and r["testable"]:
            groups[tuple(r[k] for k in by)].append(bool(r["found"]))
    out = []
    for key in sorted(groups, key=lambda t: tuple(str(x) for x in t)):
        vals = groups[key]
        out.append({**dict(zip(by, key)), "n_truths": len(vals), "recall": float(np.mean(vals))})
    return out


def q_calibration(finding_rows: list[dict[str, Any]], edges: tuple[float, ...] = (0.0, 0.001, 0.01, 0.02, 0.03, 0.04, 0.05)) -> list[dict[str, Any]]:
    """Among reported findings with q in a bin: empirical false fraction (should be <= bin's upper q)."""
    out = []
    for lo, hi in itertools.pairwise(edges):
        sel = [r for r in finding_rows if r["label"] != "ignored" and r["q_value"] is not None and lo < r["q_value"] <= hi]
        if lo == 0.0:
            sel = [r for r in finding_rows if r["label"] != "ignored" and r["q_value"] is not None and r["q_value"] <= hi]
        out.append({"q_low": lo, "q_high": hi, "n": len(sel), "false_fraction": (sum(1 for r in sel if r["label"] == "false") / len(sel)) if sel else None})
    return out
