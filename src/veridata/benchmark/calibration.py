"""Calibration experiments (Phase 4, Section 7). Deterministic, offline, no LLM.

7.1 Type-I error of the *selected* Phase 3 tests on null pairs, vs the naive (always-parametric) tests.
7.2 FDR / FWER of BH, BY, Bonferroni, Holm and no correction under dependence between tests.
7.3 Power sanity: empirical power of Welch's t and Pearson vs analytic power.

Replication counts are parameters; the defaults used for the committed results are recorded in
``docs/calibration_results.md``.
"""

from __future__ import annotations

import math
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from scipy import stats as sps

from veridata.benchmark.generator import FAMILIES, draw_standardized
from veridata.config import PipelineConfig, load_config
from veridata.contracts.hypothesis import FeasibilityReport, Hypothesis, RelationshipType
from veridata.validation.correction import apply_correction

ALPHA = 0.05


def _cfg(aware: bool) -> PipelineConfig:
    cfg = load_config().model_copy(deep=True)
    cfg.stats.benchmark_fast_mode = True
    cfg.stats.assumption_aware_selection = aware
    return cfg


def _hyp(rel: RelationshipType, n: int) -> Hypothesis:
    return Hypothesis(
        id="h_cal", column_a="a", column_b="b", relationship=rel, source="enumerated",
        feasibility=FeasibilityReport(feasible=True, n_pairwise_complete=n),
    )


def _labels(probs: list[float], n: int, rng: np.random.Generator) -> np.ndarray:
    return np.array([f"L{i}" for i in range(len(probs))], dtype=object)[rng.choice(len(probs), size=n, p=probs)]


GROUP_PROBS = {
    ("numeric_vs_binary", "balanced"): [0.5, 0.5],
    ("numeric_vs_binary", "90/10"): [0.9, 0.1],
    ("numeric_vs_categorical", "balanced"): [0.25, 0.25, 0.25, 0.25],
    ("numeric_vs_categorical", "90/10"): [0.7, 0.1, 0.1, 0.1],
}
CAT_CAT_SHAPES = {
    ("2x2", "balanced"): ([0.5, 0.5], [0.5, 0.5]),
    ("2x2", "90/10"): ([0.9, 0.1], [0.9, 0.1]),
    ("3x4", "balanced"): ([1 / 3] * 3, [0.25] * 4),
    ("3x4", "90/10"): ([0.8, 0.1, 0.1], [0.7, 0.1, 0.1, 0.1]),
}


def type1_cells(ns: tuple[int, ...] = (20, 50, 200, 1000)) -> list[dict[str, Any]]:
    cells = []
    for fam in FAMILIES:
        for n in ns:
            for imb in ("balanced", "90/10"):
                cells.append({"relationship": "numeric_vs_binary", "family": fam, "n": n, "imbalance": imb, "shape": "2 groups"})
                cells.append({"relationship": "numeric_vs_categorical", "family": fam, "n": n, "imbalance": imb, "shape": "4 groups"})
            cells.append({"relationship": "numeric_vs_numeric", "family": fam, "n": n, "imbalance": "n/a", "shape": "both columns same family"})
    for n in ns:
        for (shape, imb) in CAT_CAT_SHAPES:
            cells.append({"relationship": "categorical_vs_categorical", "family": "n/a", "n": n, "imbalance": imb, "shape": shape})
    return cells


def _null_frame(cell: dict[str, Any], rng: np.random.Generator) -> pd.DataFrame:
    n, rel = cell["n"], cell["relationship"]
    if rel == "numeric_vs_numeric":
        return pd.DataFrame({"a": 50 + 10 * draw_standardized(cell["family"], n, rng), "b": 5 + 2 * draw_standardized(cell["family"], n, rng)})
    if rel in {"numeric_vs_binary", "numeric_vs_categorical"}:
        return pd.DataFrame({"a": 50 + 10 * draw_standardized(cell["family"], n, rng), "b": _labels(GROUP_PROBS[(rel, cell["imbalance"])], n, rng)})
    pa, pb = CAT_CAT_SHAPES[(cell["shape"], cell["imbalance"])]
    return pd.DataFrame({"a": _labels(pa, n, rng), "b": _labels(pb, n, rng)})


def _run_type1_cell(cell: dict[str, Any], reps: int, seed: int) -> list[dict[str, Any]]:
    from veridata.stats.runner import run_hypothesis

    rel = RelationshipType(cell["relationship"])
    rows = []
    for aware in (True, False):
        cfg = _cfg(aware)
        rng = np.random.default_rng(seed)  # same null datasets for both selection modes
        h = _hyp(rel, cell["n"])
        pvals: list[float] = []
        tests: Counter[str] = Counter()
        skipped = 0
        for _ in range(reps):
            df = _null_frame(cell, rng)
            res = run_hypothesis(h, df, cfg, stage="A")
            if res.status != "ok" or res.p_value is None or not np.isfinite(res.p_value):
                skipped += 1
                continue
            pvals.append(float(res.p_value))
            tests[res.test_name] += 1
        k = len(pvals)
        size = float(np.mean(np.array(pvals) < ALPHA)) if k else None
        se = math.sqrt(size * (1 - size) / k) if k and size is not None else None
        ks = float(sps.kstest(pvals, "uniform").statistic) if k >= 20 else None
        rows.append({
            **cell, "selection": "assumption_aware" if aware else "naive", "reps": reps, "n_valid": k, "n_skipped": skipped,
            "size": size, "mc_se": se, "ks_vs_uniform": ks, "tests_used": ";".join(f"{t}:{c}" for t, c in tests.most_common()),
            "pvalues": pvals,
        })
    return rows


def run_type1(reps: int = 1000, *, ns: tuple[int, ...] = (20, 50, 200, 1000), n_jobs: int = 2, seed: int = 7) -> pd.DataFrame:
    cells = type1_cells(ns)
    nested = Parallel(n_jobs=n_jobs)(delayed(_run_type1_cell)(c, reps, seed + i) for i, c in enumerate(cells))
    return pd.DataFrame([r for rows in nested for r in rows])


def type1_verdict(df: pd.DataFrame) -> dict[str, Any]:
    """Plan 7.1 criterion, with Monte-Carlo slack (+-2 SE) because reps may be below 5,000."""
    aware = df[(df["selection"] == "assumption_aware") & df["size"].notna()]
    inside = ((aware["size"] >= 0.04 - 2 * aware["mc_se"]) & (aware["size"] <= 0.06 + 2 * aware["mc_se"]))
    above = aware[aware["size"] > 0.075]
    return {
        "n_cells": len(aware),
        "share_inside_band": float(inside.mean()) if len(aware) else None,
        "n_above_0_075": len(above),
        "cells_above_0_075": above[["relationship", "family", "n", "imbalance", "shape", "size"]].to_dict("records"),
        "pass": bool(len(aware) and inside.mean() >= 0.90 and len(above) == 0),
    }


# ---------------------------------------------------------------------------------------
# 7.2 FDR under dependence (vectorised Pearson p-values -> the product's correction code)
# ---------------------------------------------------------------------------------------


def _covariance(p: int, scenario: str, rho: float, rng: np.random.Generator) -> tuple[np.ndarray, np.ndarray]:
    sigma = np.eye(p)
    if scenario == "independent":
        return sigma, np.zeros((p, p), dtype=bool)
    cols = rng.permutation(p)
    n_block_cols = int(round(0.4 * p))  # noqa: RUF046 (numpy-safe)
    block_cols = cols[:n_block_cols]
    for start in range(0, n_block_cols - 1, 5):
        b = block_cols[start : start + 5]
        if len(b) < 2:
            continue
        for i in b:
            for j in b:
                if i != j:
                    sigma[i, j] = rho
    if scenario == "sparse_truth":
        rest = cols[n_block_cols:]
        for i, j in zip(rest[0::2], rest[1::2]):
            sigma[i, j] = sigma[j, i] = 0.25
    true = (sigma != 0) & ~np.eye(p, dtype=bool)
    return sigma, true


def _fdr_cell(p: int, scenario: str, rho: float, reps: int, n: int, seed: int) -> list[dict[str, Any]]:
    rng = np.random.default_rng(seed)
    sigma, true = _covariance(p, scenario, rho, rng)
    iu = np.triu_indices(p, 1)
    true_v = true[iu]
    chol = np.linalg.cholesky(sigma)
    acc: dict[str, dict[str, list[float]]] = {m: {"fdp": [], "any_fd": [], "power": [], "n_rej": []} for m in ("bh", "by", "bonferroni", "holm", "none")}
    for _ in range(reps):
        x = rng.standard_normal((n, p)) @ chol.T
        r = np.corrcoef(x, rowvar=False)[iu]
        r = np.clip(r, -0.999999, 0.999999)
        t = r * np.sqrt((n - 2) / (1 - r**2))
        pv = 2 * sps.t.sf(np.abs(t), n - 2)
        for m in acc:
            rej = apply_correction(pv, method=m, alpha=ALPHA).reject_mask
            n_rej = int(rej.sum())
            n_false = int((rej & ~true_v).sum())
            acc[m]["fdp"].append(n_false / n_rej if n_rej else 0.0)
            acc[m]["any_fd"].append(1.0 if n_false else 0.0)
            acc[m]["n_rej"].append(float(n_rej))
            if true_v.any():
                acc[m]["power"].append(float((rej & true_v).sum() / true_v.sum()))
    rows = []
    for m, a in acc.items():
        fdr = float(np.mean(a["fdp"]))
        rows.append({
            "scenario": scenario, "block_corr": rho if scenario != "independent" else 0.0, "p": p, "n": n, "reps": reps,
            "n_pairs": len(true_v), "n_true_pairs": int(true_v.sum()), "method": m,
            "fdr": fdr, "fdr_mc_se": float(np.std(a["fdp"], ddof=1) / math.sqrt(reps)), "fwer": float(np.mean(a["any_fd"])),
            "power": float(np.mean(a["power"])) if a["power"] else None, "mean_rejections": float(np.mean(a["n_rej"])),
        })
    return rows


def run_fdr_dependence(reps: int = 300, *, ps: tuple[int, ...] = (20, 60, 120), n: int = 200, n_jobs: int = 2, seed: int = 11) -> pd.DataFrame:
    cells = [("independent", 0.0)] + [("null_blocks", r) for r in (0.3, 0.6, 0.9)] + [("sparse_truth", 0.6)]
    jobs = [(p, sc, rho) for p in ps for sc, rho in cells]
    nested = Parallel(n_jobs=n_jobs)(delayed(_fdr_cell)(p, sc, rho, reps, n, seed + i) for i, (p, sc, rho) in enumerate(jobs))
    return pd.DataFrame([r for rows in nested for r in rows])


# ---------------------------------------------------------------------------------------
# 7.3 power sanity
# ---------------------------------------------------------------------------------------


def _fisher_power(r: float, n: int, alpha: float = ALPHA) -> float:
    z = math.atanh(abs(r)) * math.sqrt(n - 3)
    zc = sps.norm.ppf(1 - alpha / 2)
    return float(sps.norm.cdf(z - zc) + sps.norm.cdf(-z - zc))


def run_power(reps: int = 400, *, seed: int = 13) -> pd.DataFrame:
    from statsmodels.stats.power import TTestIndPower

    from veridata.stats.runner import run_hypothesis

    cfg = _cfg(False)  # naive selection -> Welch's t and Pearson, whose power formulas are known
    rows = []
    rng = np.random.default_rng(seed)
    for n_group in (30, 100):
        for d in (0.2, 0.5, 0.8):
            h = _hyp(RelationshipType.NUM_BINARY, 2 * n_group)
            rej = []
            for _ in range(reps):
                df = pd.DataFrame({"a": np.concatenate([rng.standard_normal(n_group), d + rng.standard_normal(n_group)]), "b": ["L0"] * n_group + ["L1"] * n_group})
                res = run_hypothesis(h, df, cfg, stage="A")
                rej.append(1.0 if res.p_value is not None and res.p_value < ALPHA else 0.0)
            emp = float(np.mean(rej))
            ana = float(TTestIndPower().power(effect_size=d, nobs1=n_group, alpha=ALPHA, ratio=1.0))
            se = math.sqrt(max(ana * (1 - ana), 1e-6) / reps)
            rows.append({"test": "welch_t", "n": 2 * n_group, "effect": d, "reps": reps, "empirical_power": emp, "analytic_power": ana, "mc_se": se, "ok": abs(emp - ana) <= 3 * se + 0.02})
    for n in (30, 100):
        for r in (0.2, 0.4):
            h = _hyp(RelationshipType.NUM_NUM, n)
            rej = []
            for _ in range(reps):
                x = rng.standard_normal(n)
                y = r * x + math.sqrt(1 - r * r) * rng.standard_normal(n)
                res = run_hypothesis(h, pd.DataFrame({"a": x, "b": y}), cfg, stage="A")
                rej.append(1.0 if res.p_value is not None and res.p_value < ALPHA else 0.0)
            emp = float(np.mean(rej))
            ana = _fisher_power(r, n)
            se = math.sqrt(max(ana * (1 - ana), 1e-6) / reps)
            rows.append({"test": "pearson", "n": n, "effect": r, "reps": reps, "empirical_power": emp, "analytic_power": ana, "mc_se": se, "ok": abs(emp - ana) <= 3 * se + 0.02})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------------------
# plots + writing
# ---------------------------------------------------------------------------------------


def plot_type1(df: pd.DataFrame, out_dir: Path) -> list[Path]:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    out_dir.mkdir(parents=True, exist_ok=True)
    rels = ["numeric_vs_binary", "numeric_vs_categorical", "numeric_vs_numeric", "categorical_vs_categorical"]
    fig, axes = plt.subplots(2, 4, figsize=(15, 6.4), sharey="row", layout="constrained")
    for j, rel in enumerate(rels):
        for i, sel in enumerate(("assumption_aware", "naive")):
            ax = axes[i, j]
            sub = df[(df["relationship"] == rel) & (df["selection"] == sel)]
            pv = np.concatenate([np.asarray(p) for p in sub["pvalues"]]) if len(sub) else np.array([])
            ax.hist(pv, bins=20, range=(0, 1), color="#0072B2" if i == 0 else "#D55E00", edgecolor="white")
            if len(pv):
                ax.axhline(len(pv) / 20, color="#333333", ls="--", lw=1)
            ax.set_title(f"{rel.replace('_', ' ')}\n{sel.replace('_', '-')} tests", fontsize=9.5)
            ax.set_xlabel("p-value under the null")
    axes[0, 0].set_ylabel("count (dashed = uniform)")
    axes[1, 0].set_ylabel("count (dashed = uniform)")
    fig.suptitle("Null p-values should be flat (uniform): assumption-aware vs naive test selection")
    p1 = out_dir / "type1_pvalue_hist.png"
    fig.savefig(p1, dpi=130, metadata={"Software": None})
    plt.close(fig)

    fig, axes = plt.subplots(1, 4, figsize=(15, 4.2), sharey=True, layout="constrained")
    for j, rel in enumerate(rels):
        ax = axes[j]
        for sel, color, off in (("assumption_aware", "#0072B2", -0.12), ("naive", "#D55E00", 0.12)):
            sub = df[(df["relationship"] == rel) & (df["selection"] == sel) & df["size"].notna()].reset_index(drop=True)
            ax.errorbar(np.arange(len(sub)) + off, sub["size"], yerr=2 * sub["mc_se"], fmt="o", ms=3, color=color, label=sel.replace("_", "-"), alpha=0.85)
        ax.axhspan(0.04, 0.06, color="#999999", alpha=0.2)
        ax.axhline(0.05, color="#333333", lw=1)
        ax.set_title(rel.replace("_", " "), fontsize=9.5)
        ax.set_xlabel("cell (family x n x imbalance)")
    axes[0].set_ylabel("rejection rate at alpha = 0.05")
    axes[0].legend(fontsize=8)
    fig.suptitle("Empirical Type I error per cell (grey band = 0.04-0.06; bars = ±2 Monte-Carlo SE)")
    p2 = out_dir / "type1_size.png"
    fig.savefig(p2, dpi=130, metadata={"Software": None})
    plt.close(fig)
    return [p1, p2]


def write_outputs(type1: pd.DataFrame | None, fdr: pd.DataFrame | None, power: pd.DataFrame | None, out_dir: Path | str = Path("outputs/benchmark/calibration")) -> dict[str, Any]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    res: dict[str, Any] = {}
    if type1 is not None:
        type1.drop(columns=["pvalues"]).to_csv(out / "type1.csv", index=False)
        plot_type1(type1, out)
        res["type1"] = type1_verdict(type1)
    if fdr is not None:
        fdr.to_csv(out / "fdr_dependence.csv", index=False)
    if power is not None:
        power.to_csv(out / "power.csv", index=False)
        res["power_all_ok"] = bool(power["ok"].all())
    return res
