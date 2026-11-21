"""Phase 3 data preparation, single-hypothesis execution, Stage B enrichment, and batch runner."""

from __future__ import annotations

import json
import logging
import time
from collections import Counter
from pathlib import Path
from typing import Any, Callable, Literal

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from pydantic import BaseModel, Field
from scipy import stats as sp_stats

from veridata.config import PipelineConfig
from veridata.contracts.findings import Finding
from veridata.contracts.hypothesis import Hypothesis, HypothesisSet, RelationshipType
from veridata.contracts.results import AssumptionCheck, TestResult
from veridata.contracts.validation import ValidationDecision
from veridata.errors import ValidationError
from veridata.stats.effect_sizes import (
    cramers_v_bias_corrected,
    epsilon_squared_kruskal,
    eta_and_omega_squared,
    rank_biserial_and_ps,
)
from veridata.stats.intervals import (
    bootstrap_ci_multi_group,
    bootstrap_ci_paired,
    bootstrap_ci_two_group,
    spearman_rho_ci_fisher,
)
from veridata.stats.registry import REGISTRY
from veridata.stats.selection import select_test
from veridata.stats.types import PreparedData, derive_seed
from veridata.validation.ledger import SessionLedger
from veridata.validation.validator import build_findings, validate

logger = logging.getLogger("veridata.stats.runner")


class RunOutput(BaseModel):
    """Complete output of Phase 3 batch testing and validation (Section 9)."""

    results: list[TestResult] = Field(default_factory=list)
    decisions: list[ValidationDecision] = Field(default_factory=list)
    findings: list[Finding] = Field(default_factory=list)
    ledger_path: str | None = None
    summary: dict[str, Any] = Field(default_factory=dict)


def prepare_inputs(
    hypothesis: Hypothesis,
    df: pd.DataFrame,
    config: PipelineConfig,
) -> PreparedData:
    """Prepare pairwise-complete, rare-level-filtered inputs without mutating df (Section 3)."""
    col_a = hypothesis.column_a
    col_b = hypothesis.column_b
    rel = hypothesis.relationship
    min_n = config.stats.min_n_pairwise
    min_grp = config.stats.min_group_n

    if col_a not in df.columns or col_b not in df.columns:
        return PreparedData(
            hypothesis=hypothesis,
            relationship=rel,
            n_used=0,
            status="error",
            status_reason=f"Missing column(s) in dataframe: {col_a}, {col_b}",
        )

    sub = df[[col_a, col_b]].dropna()
    if len(sub) < min_n:
        return PreparedData(
            hypothesis=hypothesis,
            relationship=rel,
            n_used=int(len(sub)),
            status="skipped_infeasible",
            status_reason=f"n_used={len(sub)} < min_n_pairwise ({min_n})",
        )

    warnings: list[str] = []

    if rel in {RelationshipType.NUM_NUM, RelationshipType.NUM_NUM_NONLINEAR}:
        x_ser = pd.to_numeric(sub[col_a], errors="coerce").to_numpy(dtype=float)
        y_ser = pd.to_numeric(sub[col_b], errors="coerce").to_numpy(dtype=float)
        mask = np.isfinite(x_ser) & np.isfinite(y_ser)
        x_arr, y_arr = x_ser[mask], y_ser[mask]
        n_used = int(len(x_arr))
        if n_used < min_n:
            return PreparedData(
                hypothesis=hypothesis,
                relationship=rel,
                n_used=n_used,
                status="skipped_infeasible",
                status_reason=f"finite n_used={n_used} < min_n_pairwise ({min_n})",
            )
        if float(np.std(x_arr)) == 0.0 or float(np.std(y_arr)) == 0.0:
            return PreparedData(
                hypothesis=hypothesis,
                relationship=rel,
                n_used=n_used,
                status="skipped_infeasible",
                status_reason="degenerate: zero variance in numeric variable after NA removal",
            )
        if len(np.unique(x_arr)) < 5 or len(np.unique(y_arr)) < 5:
            warnings.append("Numeric variable has < 5 distinct values (heavy ties).")
        return PreparedData(
            hypothesis=hypothesis,
            relationship=rel,
            n_used=n_used,
            x=x_arr,
            y=y_arr,
            warnings=warnings,
        )

    if rel in {RelationshipType.NUM_BINARY, RelationshipType.NUM_CATEGORICAL}:
        num_arr = pd.to_numeric(sub[col_a], errors="coerce").to_numpy(dtype=float)
        valid_mask = np.isfinite(num_arr)
        num_valid = num_arr[valid_mask]
        grp_valid = sub[col_b].iloc[np.where(valid_mask)[0]].astype(str).to_numpy()

        unique_labels = sorted(set(grp_valid.tolist()))
        dropped: list[str] = []
        kept_groups: list[np.ndarray] = []
        kept_labels: list[str] = []
        group_sizes: dict[str, int] = {}

        for lbl in unique_labels:
            vals = num_valid[grp_valid == lbl]
            if len(vals) < min_grp:
                dropped.append(lbl)
            else:
                kept_labels.append(lbl)
                kept_groups.append(vals)
                group_sizes[lbl] = int(len(vals))

        if dropped:
            warnings.append(f"dropped_levels (< min_group_n={min_grp}): {', '.join(dropped)}")

        if rel == RelationshipType.NUM_BINARY and (len(kept_groups) != 2 or len(dropped) > 0):
            return PreparedData(
                hypothesis=hypothesis,
                relationship=rel,
                n_used=int(sum(len(g) for g in kept_groups)),
                group_sizes=group_sizes,
                status="skipped_infeasible",
                status_reason=f"Binary grouping requires 2 groups with n >= {min_grp} (dropped={dropped}).",
                dropped_levels=dropped,
                warnings=warnings,
            )

        if len(kept_groups) < 2:
            return PreparedData(
                hypothesis=hypothesis,
                relationship=rel,
                n_used=int(sum(len(g) for g in kept_groups)),
                group_sizes=group_sizes,
                status="skipped_infeasible",
                status_reason=f"Fewer than 2 groups remain with n >= {min_grp}.",
                dropped_levels=dropped,
                warnings=warnings,
            )

        all_kept = np.concatenate(kept_groups)
        n_used = int(len(all_kept))
        if n_used < min_n:
            return PreparedData(
                hypothesis=hypothesis,
                relationship=rel,
                n_used=n_used,
                group_sizes=group_sizes,
                status="skipped_infeasible",
                status_reason=f"n_used={n_used} after rare-level filter < min_n_pairwise ({min_n})",
                dropped_levels=dropped,
                warnings=warnings,
            )
        if float(np.std(all_kept)) == 0.0:
            return PreparedData(
                hypothesis=hypothesis,
                relationship=rel,
                n_used=n_used,
                group_sizes=group_sizes,
                status="skipped_infeasible",
                status_reason="degenerate: numeric outcome is constant across all retained groups",
                dropped_levels=dropped,
                warnings=warnings,
            )

        collapsed = rel == RelationshipType.NUM_CATEGORICAL and len(kept_groups) == 2
        if len(np.unique(all_kept)) < 5:
            warnings.append("Numeric outcome has < 5 distinct values (heavy ties).")
        return PreparedData(
            hypothesis=hypothesis,
            relationship=rel,
            n_used=n_used,
            groups=kept_groups,
            group_labels=kept_labels,
            group_sizes=group_sizes,
            collapsed_to_two_groups=collapsed,
            dropped_levels=dropped,
            warnings=warnings,
        )

    if rel == RelationshipType.CAT_CAT:
        ser_a = sub[col_a].astype(str)
        ser_b = sub[col_b].astype(str)
        counts_a = ser_a.value_counts().to_dict()
        counts_b = ser_b.value_counts().to_dict()

        dropped_a = sorted([k for k, v in counts_a.items() if int(v) < min_grp])
        dropped_b = sorted([k for k, v in counts_b.items() if int(v) < min_grp])
        dropped = [f"{col_a}:{lvl}" for lvl in dropped_a] + [f"{col_b}:{lvl}" for lvl in dropped_b]

        kept_a = {k for k, v in counts_a.items() if int(v) >= min_grp}
        kept_b = {k for k, v in counts_b.items() if int(v) >= min_grp}
        mask = ser_a.isin(kept_a) & ser_b.isin(kept_b)
        ser_a_kept = ser_a.loc[mask]
        ser_b_kept = ser_b.loc[mask]
        n_used = int(mask.sum())

        if dropped:
            warnings.append(f"dropped_levels (< min_group_n={min_grp}): {', '.join(dropped)}")

        if n_used < min_n:
            return PreparedData(
                hypothesis=hypothesis,
                relationship=rel,
                n_used=n_used,
                status="skipped_infeasible",
                status_reason=f"n_used={n_used} < min_n_pairwise ({min_n})",
                dropped_levels=dropped,
                warnings=warnings,
            )

        ct = pd.crosstab(ser_a_kept, ser_b_kept)
        ct = ct.loc[ct.sum(axis=1) > 0, ct.sum(axis=0) > 0]
        if ct.shape[0] < 2 or ct.shape[1] < 2:
            return PreparedData(
                hypothesis=hypothesis,
                relationship=rel,
                n_used=n_used,
                status="skipped_infeasible",
                status_reason="degenerate: contingency table has < 2 rows or < 2 columns",
                dropped_levels=dropped,
                warnings=warnings,
            )

        return PreparedData(
            hypothesis=hypothesis,
            relationship=rel,
            n_used=n_used,
            contingency=ct.to_numpy(dtype=int),
            row_labels=[str(x) for x in ct.index.tolist()],
            col_labels=[str(x) for x in ct.columns.tolist()],
            cat_a_values=ser_a_kept.to_numpy(dtype=object),
            cat_b_values=ser_b_kept.to_numpy(dtype=object),
            dropped_levels=dropped,
            warnings=warnings,
        )

    return PreparedData(
        hypothesis=hypothesis,
        relationship=rel,
        n_used=0,
        status="error",
        status_reason=f"Unsupported relationship type: {rel.value}",
    )


def _compute_outlier_influence_check(
    prepared: PreparedData,
    result: TestResult,
) -> AssumptionCheck | None:
    """Leave-1%-out outlier influence check for numeric tests (Section 5)."""
    if result.effect is None or result.n_used < 30:
        return None
    base_val = result.effect.value
    if abs(base_val) < 1e-9:
        return None

    try:
        if prepared.relationship == RelationshipType.NUM_NUM and prepared.x is not None and prepared.y is not None:
            x, y = prepared.x, prepared.y
            lo_x, hi_x = np.percentile(x, [0.5, 99.5])
            lo_y, hi_y = np.percentile(y, [0.5, 99.5])
            mask = (x >= lo_x) & (x <= hi_x) & (y >= lo_y) & (y <= hi_y)
            if mask.sum() < 20:
                return None
            if result.test_name == "pearson":
                new_val = float(sp_stats.pearsonr(x[mask], y[mask]).statistic)
            else:
                new_val = float(sp_stats.spearmanr(x[mask], y[mask]).statistic)
        elif (
            prepared.groups is not None
            and len(prepared.groups) == 2
            and result.test_name in {"welch_t", "mann_whitney_u"}
        ):
            g1, g2 = prepared.groups[0], prepared.groups[1]
            lo1, hi1 = np.percentile(g1, [0.5, 99.5])
            lo2, hi2 = np.percentile(g2, [0.5, 99.5])
            t1 = g1[(g1 >= lo1) & (g1 <= hi1)]
            t2 = g2[(g2 >= lo2) & (g2 <= hi2)]
            if len(t1) < 8 or len(t2) < 8:
                return None
            if result.test_name == "welch_t":
                from veridata.stats.effect_sizes import hedges_g

                new_val, _, _ = hedges_g(t1, t2)
            else:
                u_s = float(sp_stats.mannwhitneyu(t1, t2, alternative="two-sided").statistic)
                new_val, _, _ = rank_biserial_and_ps(u_s, len(t1), len(t2))
        else:
            return None
    except Exception:  # noqa: BLE001
        return None

    sign_flip = (base_val * new_val) < 0.0
    rel_change = abs(abs(new_val) - abs(base_val)) / max(1e-9, abs(base_val))
    passed = (not sign_flip) and (rel_change <= 0.50)
    return AssumptionCheck(
        name="outlier_influence",
        method="trim_1pct_sensitivity",
        statistic=round(rel_change, 4),
        p_value=None,
        passed=passed,
        severity="info" if passed else "warning",
        detail=(
            f"Trimming top/bottom 0.5% changed effect from {base_val:.3f} to {new_val:.3f} "
            f"(rel_change={rel_change:.1%}, sign_flip={sign_flip})."
        ),
    )


def enrich_stage_b(
    result: TestResult,
    prepared: PreparedData,
    config: PipelineConfig,
) -> TestResult:
    """Stage B enrichment on candidate findings: bootstrap CIs, sensitivity check, outlier influence."""
    if result.status != "ok" or result.effect is None:
        return result

    seed = result.seed if result.seed is not None else derive_seed(config.stats.seed, result.hypothesis_id)
    rng = np.random.default_rng(seed + 17)
    n_boot = (
        config.stats.bootstrap_resamples_benchmark
        if config.stats.benchmark_fast_mode
        else config.stats.bootstrap_resamples
    )

    effect = result.effect.model_copy(deep=True)
    warnings = list(result.warnings)
    assumptions = list(result.assumptions)
    descriptives = dict(result.descriptives)

    # 1. Bootstrap CIs where analytic CI was not already computed
    if effect.ci_low is None or effect.ci_high is None:
        if result.test_name == "mann_whitney_u" and prepared.groups is not None:
            g1, g2 = prepared.groups[0], prepared.groups[1]

            def _rb_stat(s1: np.ndarray, s2: np.ndarray) -> float:
                u = float(sp_stats.mannwhitneyu(s1, s2, alternative="two-sided", method="asymptotic").statistic)
                rb, _, _ = rank_biserial_and_ps(u, len(s1), len(s2))
                return rb

            lo, hi, method_used, warn = bootstrap_ci_two_group(
                g1, g2, _rb_stat, rng, n_resamples=n_boot
            )
            effect.ci_low, effect.ci_high, effect.ci_method = lo, hi, method_used
            if warn:
                warnings.append(warn)

        elif result.test_name == "welch_anova" and prepared.groups is not None:
            lo, hi, method_used, warn = bootstrap_ci_multi_group(
                prepared.groups,
                lambda gs: eta_and_omega_squared(gs)[0],
                rng,
                n_resamples=n_boot,
            )
            effect.ci_low, effect.ci_high, effect.ci_method = lo, hi, method_used
            if warn:
                warnings.append(warn)

        elif result.test_name == "kruskal_wallis" and prepared.groups is not None:
            def _eps_stat(gs: list[np.ndarray]) -> float:
                try:
                    h = float(sp_stats.kruskal(*gs).statistic)
                    return epsilon_squared_kruskal(h, sum(len(g) for g in gs))[0]
                except ValueError:
                    return float("nan")

            lo, hi, method_used, warn = bootstrap_ci_multi_group(
                prepared.groups, _eps_stat, rng, n_resamples=n_boot
            )
            effect.ci_low, effect.ci_high, effect.ci_method = lo, hi, method_used
            if warn:
                warnings.append(warn)

        elif result.test_name == "spearman" and prepared.x is not None and prepared.y is not None:
            if config.stats.benchmark_fast_mode:
                lo, hi, method_used = spearman_rho_ci_fisher(effect.value, len(prepared.x))
                effect.ci_low, effect.ci_high, effect.ci_method = lo, hi, method_used
            else:
                def _sp_stat(sx: np.ndarray, sy: np.ndarray) -> float:
                    if float(np.std(sx)) == 0.0 or float(np.std(sy)) == 0.0:
                        return float("nan")
                    return float(sp_stats.spearmanr(sx, sy).statistic)

                lo, hi, method_used, warn = bootstrap_ci_paired(
                    prepared.x, prepared.y, _sp_stat, rng, n_resamples=n_boot
                )
                effect.ci_low, effect.ci_high, effect.ci_method = lo, hi, method_used
                if warn:
                    warnings.append(warn)

        elif (
            result.test_name in {"chi_square", "fisher_exact", "monte_carlo_chi_square"}
            and prepared.cat_a_values is not None
            and prepared.cat_b_values is not None
        ):
            _, a_codes = np.unique(prepared.cat_a_values.astype(str), return_inverse=True)
            _, b_codes = np.unique(prepared.cat_b_values.astype(str), return_inverse=True)
            n_r = int(a_codes.max()) + 1
            n_c = int(b_codes.max()) + 1

            def _v_stat(sa: np.ndarray, sb: np.ndarray) -> float:
                ct = np.bincount(sa * n_c + sb, minlength=n_r * n_c).reshape(n_r, n_c)
                ct = ct[ct.sum(axis=1) > 0][:, ct.sum(axis=0) > 0]
                if ct.shape[0] < 2 or ct.shape[1] < 2:
                    return float("nan")
                return cramers_v_bias_corrected(ct)[0]

            lo, hi, method_used, warn = bootstrap_ci_paired(
                a_codes,
                b_codes,
                _v_stat,
                rng,
                n_resamples=min(n_boot, 500),
            )
            effect.ci_low, effect.ci_high, effect.ci_method = lo, hi, method_used
            if warn:
                warnings.append(warn)

    # 2. Sensitivity check (paired parametric vs non-parametric agreement)
    try:
        alt_name: str | None = None
        if result.test_name == "welch_t":
            alt_name = "mann_whitney_u"
        elif result.test_name == "mann_whitney_u" and prepared.groups is not None and all(
            float(np.std(g)) > 0.0 for g in prepared.groups
        ):
            alt_name = "welch_t"
        elif result.test_name == "pearson":
            alt_name = "spearman"
        elif result.test_name == "spearman":
            alt_name = "pearson"

        if alt_name is not None:
            alt_out = REGISTRY[alt_name].run(prepared, config, np.random.default_rng(seed + 31))
            primary_sig = (result.p_value or 1.0) < 0.05
            alt_sig = alt_out.p_value < 0.05
            same_sign = (effect.value * alt_out.effect.value) >= 0.0
            agree = (primary_sig == alt_sig) and same_sign
            descriptives["sensitivity_alt_test"] = {
                "test_name": alt_name,
                "p_value": alt_out.p_value,
                "effect_value": alt_out.effect.value,
                "agrees": agree,
            }
            if not agree:
                warnings.append(
                    f"test_sensitive: alternative test '{alt_name}' disagreed "
                    f"(alt p={alt_out.p_value:.4g}, alt effect={alt_out.effect.value:.3f})."
                )
    except Exception:  # noqa: BLE001
        pass

    # 3. Leave-1%-out outlier influence check
    out_check = _compute_outlier_influence_check(prepared, result)
    if out_check is not None:
        assumptions.append(out_check)

    return result.model_copy(
        update={
            "effect": effect,
            "warnings": warnings,
            "assumptions": assumptions,
            "descriptives": descriptives,
        }
    )


def run_hypothesis(
    hypothesis: Hypothesis,
    df: pd.DataFrame,
    config: PipelineConfig,
    *,
    stage: Literal["A", "B"] = "A",
) -> TestResult:
    """Execute a single statistical hypothesis test and return a TestResult."""
    t0 = time.perf_counter()
    seed = derive_seed(config.stats.seed, hypothesis.id)

    if not hypothesis.feasibility.feasible:
        return TestResult(
            hypothesis_id=hypothesis.id,
            status="skipped_infeasible",
            test_name="none",
            test_selection_reason="; ".join(hypothesis.feasibility.reasons) or "infeasible",
            n_used=hypothesis.feasibility.n_pairwise_complete,
            group_sizes=hypothesis.feasibility.group_sizes,
            runtime_ms=round((time.perf_counter() - t0) * 1000.0, 3),
            seed=seed,
            error="; ".join(hypothesis.feasibility.reasons) or "infeasible",
        )

    prepared = prepare_inputs(hypothesis, df, config)
    if prepared.status != "ok":
        status_out: Literal["skipped_infeasible", "error"] = (
            "skipped_infeasible" if prepared.status == "skipped_infeasible" else "error"
        )
        return TestResult(
            hypothesis_id=hypothesis.id,
            status=status_out,
            test_name="none",
            test_selection_reason=prepared.status_reason,
            n_used=prepared.n_used,
            group_sizes=prepared.group_sizes,
            warnings=prepared.warnings,
            runtime_ms=round((time.perf_counter() - t0) * 1000.0, 3),
            seed=seed,
            error=prepared.status_reason,
        )

    try:
        tool, assumptions, trace, fallback_used, reason_text = select_test(prepared, config)
        rng = np.random.default_rng(seed)
        raw = tool.run(prepared, config, rng)

        if not np.isfinite(raw.p_value) or not np.isfinite(raw.statistic):
            return TestResult(
                hypothesis_id=hypothesis.id,
                status="error",
                test_name=tool.name,
                test_selection_reason=reason_text,
                selection_trace=trace,
                fallback_used=fallback_used,
                n_used=prepared.n_used,
                group_sizes=prepared.group_sizes,
                assumptions=assumptions + raw.extra_assumptions,
                warnings=prepared.warnings + raw.warnings,
                runtime_ms=round((time.perf_counter() - t0) * 1000.0, 3),
                seed=seed,
                error="Non-finite test statistic or p-value.",
            )

        res = TestResult(
            hypothesis_id=hypothesis.id,
            status="ok",
            test_name=raw.test_name,
            test_selection_reason=reason_text,
            selection_trace=trace,
            fallback_used=fallback_used,
            n_used=prepared.n_used,
            group_sizes=prepared.group_sizes,
            statistic=raw.statistic,
            df=raw.df,
            p_value=float(np.clip(raw.p_value, 0.0, 1.0)),
            effect=raw.effect,
            descriptives=raw.descriptives,
            direction_observed=raw.direction_observed,
            assumptions=assumptions + raw.extra_assumptions,
            warnings=prepared.warnings + raw.warnings,
            runtime_ms=round((time.perf_counter() - t0) * 1000.0, 3),
            seed=seed,
            error=None,
        )
        if stage == "B":
            res = enrich_stage_b(res, prepared, config)
            res = res.model_copy(update={"runtime_ms": round((time.perf_counter() - t0) * 1000.0, 3)})
        return res
    except Exception as exc:  # noqa: BLE001
        return TestResult(
            hypothesis_id=hypothesis.id,
            status="error",
            test_name="none",
            n_used=prepared.n_used,
            group_sizes=prepared.group_sizes,
            warnings=prepared.warnings,
            runtime_ms=round((time.perf_counter() - t0) * 1000.0, 3),
            seed=seed,
            error=str(exc),
        )


def _render_validation_summary_md(
    dataset_name: str,
    findings: list[Finding],
    summary: dict[str, Any],
) -> str:
    accepted = [f for f in findings if f.decision.accepted]
    rejected = [f for f in findings if not f.decision.accepted]

    lines = [
        f"# Phase 3 Statistical Validation Summary — `{dataset_name}`",
        "",
        "## Overview",
        f"- **Tests planned (manifest):** `{summary['n_planned']}`",
        f"- **Tests executed in family (`m`):** `{summary['m_tested']}` (`{summary['n_skipped']}` skipped, `{summary['n_errors']}` errors)",
        f"- **Correction method:** `{summary['correction']}` at $\\alpha = {summary['alpha']}$ (effect floor enabled: `{summary['effect_floor_enabled']}`)",
        f"- **Naive raw $p < \\alpha$:** `{summary['n_raw_sig']}`",
        f"- **Significant after correction ($q \\le \\alpha$):** `{summary['n_bh_sig']}`",
        f"- **Accepted findings (all gates):** `{summary['n_accepted']}`",
        f"- **Fallback rate:** `{summary['fallback_rate']:.1%}` · **Runtime:** `{summary['runtime_seconds']:.2f}s`",
        "",
        f"## Accepted Findings ({len(accepted)})",
        "",
    ]

    if accepted:
        lines.extend(
            [
                "| Column A | Column B | Test | n | Raw p | Adj q | Effect | 95% CI | Magnitude | Flags |",
                "| :--- | :--- | :--- | ---: | ---: | ---: | ---: | :--- | :--- | :--- |",
            ]
        )
        for f in accepted:
            eff = f.test.effect
            eff_str = f"{eff.name}={eff.value:.3f}" if eff else "n/a"
            ci_str = (
                f"[{eff.ci_low:.3f}, {eff.ci_high:.3f}]"
                if (eff and eff.ci_low is not None and eff.ci_high is not None)
                else "n/a"
            )
            mag = eff.magnitude if eff else "n/a"
            fl = ", ".join(f.decision.flags)
            lines.append(
                f"| `{f.hypothesis.column_a}` | `{f.hypothesis.column_b}` | `{f.test.test_name}` "
                f"| {f.test.n_used} | {f.decision.p_raw:.3g} | {f.decision.q_value:.3g} "
                f"| `{eff_str}` | `{ci_str}` | `{mag}` | {fl} |"
            )
    else:
        lines.append("*No findings passed all statistical validation gates.*")

    lines.extend(["", f"## Rejected / Skipped Hypotheses ({len(rejected)})", ""])
    if rejected:
        lines.extend(
            [
                "| Column A | Column B | Test | Raw p | Adj q | Reasons | Explanation |",
                "| :--- | :--- | :--- | ---: | ---: | :--- | :--- |",
            ]
        )
        for f in rejected:
            p_s = f"{f.decision.p_raw:.3g}" if f.decision.p_raw is not None else "n/a"
            q_s = f"{f.decision.q_value:.3g}" if f.decision.q_value is not None else "n/a"
            rs = ", ".join(r.value for r in f.decision.reasons)
            txt = f.decision.reason_text.replace("|", "/")
            lines.append(
                f"| `{f.hypothesis.column_a}` | `{f.hypothesis.column_b}` | `{f.test.test_name}` "
                f"| {p_s} | {q_s} | `{rs}` | {txt} |"
            )
    lines.append("")
    return "\n".join(lines)


def _enrich_stage_b_task(
    res_item: TestResult,
    hyp: Hypothesis,
    df: pd.DataFrame,
    config: PipelineConfig,
) -> TestResult:
    prep = prepare_inputs(hyp, df, config)
    return enrich_stage_b(res_item, prep, config)


def run_all(
    hset: HypothesisSet,
    df: pd.DataFrame,
    config: PipelineConfig,
    *,
    n_jobs: int = -1,
    stage_b: bool = True,
    out_dir: Path | str | None = None,
    dataset_sha256: str = "",
    progress: Callable[[int, int], None] | None = None,
) -> RunOutput:
    """Execute Stage A + Validation + Stage B on a HypothesisSet (Section 9)."""
    t0 = time.perf_counter()
    hyps_sorted = sorted(hset.hypotheses, key=lambda h: h.id)
    hyp_map = {h.id: h for h in hyps_sorted}

    # Stage A: run all hypotheses (parallelize via joblib when worthwhile)
    use_parallel = n_jobs != 1 and len(hyps_sorted) >= 40
    if use_parallel:
        results_a: list[TestResult] = list(
            Parallel(n_jobs=n_jobs, backend="loky")(
                delayed(run_hypothesis)(h, df, config, stage="A") for h in hyps_sorted
            )
        )
    else:
        results_a = []
        for idx, h in enumerate(hyps_sorted, start=1):
            results_a.append(run_hypothesis(h, df, config, stage="A"))
            if progress is not None:
                progress(idx, len(hyps_sorted))

    results_a.sort(key=lambda r: r.hypothesis_id)

    # Initial validation to identify Stage B candidates
    decisions_a = validate(results_a, hyp_map, config, family_id="batch")
    dec_a_map = {d.hypothesis_id: d for d in decisions_a}

    # Stage B: compute CIs, sensitivity checks, and outlier influence ONLY on candidates
    final_results: list[TestResult] = []
    if stage_b:
        cand_ids = {
            r.hypothesis_id
            for r in results_a
            if r.status == "ok"
            and (
                (dec_a_map[r.hypothesis_id].q_value is not None and dec_a_map[r.hypothesis_id].q_value <= config.stats.alpha)
                or (r.p_value is not None and r.p_value < config.stats.ci_candidate_p)
            )
        }
        cands = [r for r in results_a if r.hypothesis_id in cand_ids]
        non_cands = [r for r in results_a if r.hypothesis_id not in cand_ids]

        if n_jobs != 1 and len(cands) >= 12:
            enriched_cands = list(
                Parallel(n_jobs=n_jobs, backend="loky")(
                    delayed(_enrich_stage_b_task)(r, hyp_map[r.hypothesis_id], df, config)
                    for r in cands
                )
            )
        else:
            enriched_cands = [
                _enrich_stage_b_task(r, hyp_map[r.hypothesis_id], df, config) for r in cands
            ]
        final_results = non_cands + enriched_cands
    else:
        final_results = results_a

    final_results.sort(key=lambda r: r.hypothesis_id)
    final_decisions = validate(final_results, hyp_map, config, family_id="batch")
    findings = build_findings(hyp_map, final_results, final_decisions)

    # Accounting invariant check against Phase 2 manifest
    m_tested = sum(1 for r in final_results if r.status == "ok")
    n_skipped_from_planned = sum(
        1
        for r in final_results
        if hyp_map[r.hypothesis_id].feasibility.feasible and r.status == "skipped_infeasible"
    )
    n_errors = sum(1 for r in final_results if r.status == "error")
    expected_m = hset.manifest.n_in_family_planned - n_skipped_from_planned - n_errors
    if m_tested != expected_m:
        raise ValidationError(
            f"Family size mismatch: tested m={m_tested}, expected {expected_m} "
            f"(planned={hset.manifest.n_in_family_planned}, runtime_skipped={n_skipped_from_planned}, errors={n_errors})."
        )

    # Populate ledger
    ledger = SessionLedger(dataset_sha256=dataset_sha256, alpha=config.stats.alpha)
    for r in final_results:
        ledger.add(r, stage="batch")

    runtime_sec = round(time.perf_counter() - t0, 3)
    n_raw_sig = sum(1 for d in final_decisions if d.would_pass_without_correction)
    n_bh_sig = sum(1 for d in final_decisions if d.would_pass_without_effect_floor)
    n_accepted = sum(1 for d in final_decisions if d.accepted)
    n_fallbacks = sum(1 for r in final_results if r.status == "ok" and r.fallback_used)

    reason_counts = Counter(
        reason.value for d in final_decisions for reason in d.reasons
    )
    test_counts = Counter(r.test_name for r in final_results if r.status == "ok")

    summary: dict[str, Any] = {
        "dataset_name": hset.manifest.dataset_name,
        "alpha": config.stats.alpha,
        "correction": config.stats.correction,
        "effect_floor_enabled": config.effect_floor.enabled,
        "n_planned": hset.manifest.n_in_family_planned,
        "m_tested": m_tested,
        "n_skipped": sum(1 for r in final_results if r.status == "skipped_infeasible"),
        "n_errors": n_errors,
        "n_raw_sig": n_raw_sig,
        "n_bh_sig": n_bh_sig,
        "n_accepted": n_accepted,
        "fallback_rate": round(n_fallbacks / max(1, m_tested), 4),
        "counts_by_rejection_reason": dict(sorted(reason_counts.items())),
        "counts_by_test": dict(sorted(test_counts.items())),
        "runtime_seconds": runtime_sec,
    }

    ledger_path_str: str | None = None
    if out_dir is not None:
        target_dir = Path(out_dir)
        target_dir.mkdir(parents=True, exist_ok=True)
        (target_dir / "results.json").write_text(
            json.dumps([r.model_dump(mode="json") for r in final_results], indent=2, sort_keys=True)
            + "\n",
            encoding="utf-8",
        )
        (target_dir / "decisions.json").write_text(
            json.dumps([d.model_dump(mode="json") for d in final_decisions], indent=2, sort_keys=True)
            + "\n",
            encoding="utf-8",
        )
        (target_dir / "findings.json").write_text(
            json.dumps([f.model_dump(mode="json") for f in findings], indent=2, sort_keys=True)
            + "\n",
            encoding="utf-8",
        )
        ledger_file = ledger.save_jsonl(target_dir / "ledger.jsonl")
        ledger_path_str = str(ledger_file)
        (target_dir / "validation_summary.json").write_text(
            json.dumps(summary, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        (target_dir / "validation_summary.md").write_text(
            _render_validation_summary_md(hset.manifest.dataset_name, findings, summary),
            encoding="utf-8",
        )

    return RunOutput(
        results=final_results,
        decisions=final_decisions,
        findings=findings,
        ledger_path=ledger_path_str,
        summary=summary,
    )
