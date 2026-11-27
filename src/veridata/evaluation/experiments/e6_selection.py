"""E6 — Test-selection accuracy (oracle acceptable-set accuracy + calibration consequence accuracy)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from veridata.benchmark.suites import suite_specs
from veridata.benchmark.systems import benchmark_config, prepare_dataset
from veridata.config import load_config
from veridata.contracts.hypothesis import RelationshipType
from veridata.stats.assumptions import check_expected_counts, check_normality, check_ties_rate
from veridata.stats.runner import prepare_inputs
from veridata.stats.selection import select_test


def oracle_acceptable_tests(
    rel: RelationshipType,
    *,
    n_total: int,
    group_sizes: list[int] | None = None,
    all_normal: bool = True,
    max_skew: float = 0.0,
    max_outliers: float = 0.0,
    max_ties: float = 0.0,
    is_2x2: bool = False,
    chi2_eligible: bool = True,
    clt_n: int = 50,
    extreme_skew: float = 2.0,
) -> set[str]:
    """Protocol-defined acceptable test set for one prepared hypothesis."""
    if rel == RelationshipType.NUM_BINARY:
        min_g = min(group_sizes) if group_sizes else 0
        clt_ok = min_g >= clt_n and max_skew <= extreme_skew
        if all_normal:
            return {"welch_t"} if min_g < clt_n else {"welch_t", "mann_whitney_u"}
        if clt_ok:
            return {"welch_t", "mann_whitney_u"}
        return {"mann_whitney_u"}

    if rel == RelationshipType.NUM_CATEGORICAL:
        min_g = min(group_sizes) if group_sizes else 0
        clt_ok = min_g >= clt_n and max_skew <= extreme_skew
        if all_normal:
            return {"welch_anova"} if min_g < clt_n else {"welch_anova", "kruskal_wallis"}
        if clt_ok:
            return {"welch_anova", "kruskal_wallis"}
        return {"kruskal_wallis"}

    if rel == RelationshipType.NUM_NUM:
        if max_ties > 0.50 or n_total < 30:
            return {"spearman"}
        if (all_normal and max_outliers < 0.02) or (
            n_total >= 200 and max_skew <= extreme_skew and max_outliers < 0.05
        ):
            return {"pearson", "spearman"}
        return {"spearman"}

    if rel == RelationshipType.CAT_CAT:
        if is_2x2:
            return {"chi_square"} if chi2_eligible else {"fisher_exact"}
        return {"chi_square"} if chi2_eligible else {"monte_carlo_chi_square"}

    return set()


def _always_nonparametric_test(rel: RelationshipType, collapsed_to_two: bool, is_2x2: bool) -> str:
    if rel == RelationshipType.NUM_BINARY or collapsed_to_two:
        return "mann_whitney_u"
    if rel == RelationshipType.NUM_CATEGORICAL:
        return "kruskal_wallis"
    if rel == RelationshipType.NUM_NUM:
        return "spearman"
    return "fisher_exact" if is_2x2 else "monte_carlo_chi_square"


def run_e6(
    *,
    suite: str = "core60",
    split: str = "dev",
    bench_root: Path = Path("outputs/benchmark"),
    cal_root: Path = Path("outputs/benchmark/calibration"),
    eval_root: Path = Path("outputs/eval"),
    confirm_final: bool = False,
    max_datasets: int = 12,
) -> dict[str, Any]:
    """Measure acceptable-set selection accuracy & calibration consequence accuracy."""
    specs = suite_specs(suite, split, confirm_final=confirm_final)[:max_datasets]
    base = bench_root / suite / split
    cfg_aware = benchmark_config(load_config())
    cfg_naive = cfg_aware.model_copy(deep=True)
    cfg_naive.stats.assumption_aware_selection = False

    rows: list[dict[str, Any]] = []
    for sp in specs:
        csv_p = base / sp.dataset_id / "data.csv"
        if not csv_p.exists():
            continue
        df, hset, _ = prepare_dataset(csv_p, sp.dataset_id, cfg_aware)
        for h in hset.hypotheses[:60]:
            prep = prepare_inputs(h, df, cfg_aware)
            if prep.status != "ok":
                continue
            eff_rel = (
                RelationshipType.NUM_BINARY
                if (prep.relationship == RelationshipType.NUM_CATEGORICAL and prep.collapsed_to_two_groups)
                else prep.relationship
            )

            # Inspect true sample characteristics for oracle lookup
            is_2x2 = False
            chi2_ok = True
            group_sizes: list[int] | None = None
            all_norm = True
            max_skew = 0.0
            max_out = 0.0
            max_ties = 0.0
            n_tot = prep.n_used

            if eff_rel in {RelationshipType.NUM_BINARY, RelationshipType.NUM_CATEGORICAL}:
                assert prep.groups is not None and prep.group_labels is not None
                group_sizes = [len(g) for g in prep.groups]
                for lbl, g in zip(prep.group_labels, prep.groups):
                    nc, meta = check_normality(g, lbl, cfg_aware)
                    all_norm = all_norm and nc.passed
                    max_skew = max(max_skew, abs(meta["skew"]))
                    max_out = max(max_out, meta["outlier_rate_3iqr"])
            elif eff_rel == RelationshipType.NUM_NUM:
                assert prep.x is not None and prep.y is not None
                max_ties = max(check_ties_rate(prep.x), check_ties_rate(prep.y))
                n_a, m_a = check_normality(prep.x, h.column_a, cfg_aware)
                n_b, m_b = check_normality(prep.y, h.column_b, cfg_aware)
                all_norm = n_a.passed and n_b.passed
                max_skew = max(abs(m_a["skew"]), abs(m_b["skew"]))
                max_out = max(m_a["outlier_rate_3iqr"], m_b["outlier_rate_3iqr"])
            elif eff_rel == RelationshipType.CAT_CAT:
                assert prep.contingency is not None
                _, exp_meta = check_expected_counts(prep.contingency, cfg_aware)
                is_2x2 = bool(exp_meta["is_2x2"])
                chi2_ok = bool(exp_meta["chi2_eligible"])

            acceptable = oracle_acceptable_tests(
                eff_rel,
                n_total=n_tot,
                group_sizes=group_sizes,
                all_normal=all_norm,
                max_skew=max_skew,
                max_outliers=max_out,
                max_ties=max_ties,
                is_2x2=is_2x2,
                chi2_eligible=chi2_ok,
                clt_n=cfg_aware.stats.large_n_clt,
                extreme_skew=cfg_aware.stats.extreme_skew,
            )

            spec_aware, *_ = select_test(prep, cfg_aware)
            spec_naive, *_ = select_test(prep, cfg_naive)
            nonparam_name = _always_nonparametric_test(eff_rel, prep.collapsed_to_two_groups, is_2x2)

            rows.append(
                {
                    "dataset_id": sp.dataset_id,
                    "relationship": eff_rel.value,
                    "aware_test": spec_aware.name,
                    "naive_test": spec_naive.name,
                    "nonparam_test": nonparam_name,
                    "aware_ok": spec_aware.name in acceptable,
                    "naive_ok": spec_naive.name in acceptable,
                    "nonparam_ok": nonparam_name in acceptable,
                }
            )

    df_res = pd.DataFrame(rows)
    by_rel = (
        df_res.groupby("relationship", as_index=False)
        .agg(
            n=("aware_ok", "count"),
            aware_acc=("aware_ok", "mean"),
            naive_acc=("naive_ok", "mean"),
            nonparam_acc=("nonparam_ok", "mean"),
        )
        .to_dict("records")
        if len(df_res)
        else []
    )

    # Consequence-based accuracy from Phase 4 calibration
    consequence: dict[str, Any] = {}
    t1_p = cal_root / "type1.csv"
    if t1_p.exists():
        t1 = pd.read_csv(t1_p)
        t1 = t1[t1["size"].notna()].copy()
        t1["size_ok"] = (t1["size"] >= 0.04 - 2 * t1["mc_se"]) & (t1["size"] <= 0.06 + 2 * t1["mc_se"])
        for sel in ("assumption_aware", "naive"):
            sub = t1[t1["selection"] == sel]
            consequence[sel] = {
                "n_cells": len(sub),
                "size_ok_rate": float(sub["size_ok"].mean()) if len(sub) else None,
                "max_type1_size": float(sub["size"].max()) if len(sub) else None,
            }

    out_dir = eval_root / suite / split / "e6"
    out_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "suite": suite,
        "split": split,
        "n_hypotheses_checked": len(df_res),
        "overall_aware_accuracy": float(df_res["aware_ok"].mean()) if len(df_res) else None,
        "overall_naive_accuracy": float(df_res["naive_ok"].mean()) if len(df_res) else None,
        "overall_nonparam_accuracy": float(df_res["nonparam_ok"].mean()) if len(df_res) else None,
        "by_relationship": by_rel,
        "consequence_accuracy": consequence,
    }
    (out_dir / "summary.json").write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")
    pd.DataFrame(by_rel).to_csv(out_dir / "selection_accuracy.csv", index=False)
    return payload
