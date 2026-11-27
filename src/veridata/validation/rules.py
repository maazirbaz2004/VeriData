"""Deterministic statistical validation rules and rejection reason templates (Section 7.3)."""

from __future__ import annotations

from veridata.config import PipelineConfig
from veridata.contracts.results import TestResult
from veridata.contracts.validation import RejectionReason, ValidationDecision


def effect_threshold_for(effect_name: str, config: PipelineConfig) -> float:
    """Return the configured 'small' standardized effect-size floor for an effect type."""
    ef = config.effect_floor
    mapping = {
        "hedges_g": ef.cohens_d,
        "cohens_d": ef.cohens_d,
        "rank_biserial": ef.rank_biserial,
        "pearson_r": ef.correlation,
        "spearman_rho": ef.correlation,
        "eta_squared": ef.eta_squared,
        "epsilon_squared": ef.epsilon_squared,
        "cramers_v_bc": ef.cramers_v_df1,
    }
    return float(mapping.get(effect_name, 0.10))


def is_trivial_or_derived(result: TestResult) -> bool:
    """Detect deterministic/derived relationships (|r|>=0.999, V>=0.99, perfect separation)."""
    if result.effect is None:
        return False
    name = result.effect.name
    val = result.effect.value
    if name in {"pearson_r", "spearman_rho"} and abs(val) >= 0.999:
        return True
    if name == "cramers_v_bc" and val >= 0.99:
        return True
    if name == "rank_biserial" and abs(val) >= 1.0 - 1e-12 and result.n_used >= 20:
        return True
    return bool(name in {"eta_squared", "epsilon_squared"} and val >= 0.999)


def _format_p(val: float | None) -> str:
    if val is None:
        return "N/A"
    if val < 1e-300:
        return "<1e-300"
    if val < 0.001:
        return f"{val:.2e}"
    return f"{val:.4f}"


def evaluate_validation_rules(
    result: TestResult,
    *,
    q_value: float | None,
    rank_in_family: int | None,
    family_size: int,
    family_id: str,
    config: PipelineConfig,
) -> ValidationDecision:
    """Apply validation gates in exact Section 7.3 order and build a ValidationDecision."""
    alpha = config.stats.alpha
    reasons: list[RejectionReason] = []
    reason_parts: list[str] = []
    flags: list[str] = []

    # Collect non-blocking diagnostic flags
    if any(a.severity == "warning" for a in result.assumptions):
        flags.append("assumption_warning")
    if any(a.name == "outlier_influence" and not a.passed for a in result.assumptions):
        flags.append("fragile_to_outliers")
    if any("test_sensitive" in w for w in result.warnings):
        flags.append("test_sensitive")
    if 0 < result.n_used < 50:
        flags.append("small_n")

    # 1. Status gates
    if result.status == "skipped_infeasible":
        is_degen = "degenerate" in (result.error or "").lower() or "degenerate" in (
            result.test_selection_reason or ""
        ).lower()
        code = RejectionReason.DEGENERATE_DATA if is_degen else RejectionReason.INSUFFICIENT_DATA
        reasons.append(code)
        detail = result.error or result.test_selection_reason or "insufficient sample size"
        return ValidationDecision(
            hypothesis_id=result.hypothesis_id,
            p_raw=None,
            q_value=None,
            family_id=family_id,
            family_size=family_size,
            rank_in_family=None,
            accepted=False,
            reasons=reasons,
            reason_text=f"Skipped before testing: {detail}.",
            flags=flags,
            would_pass_without_correction=False,
            would_pass_without_effect_floor=False,
        )

    if result.status == "error" or result.p_value is None:
        reasons.append(RejectionReason.TEST_ERROR)
        return ValidationDecision(
            hypothesis_id=result.hypothesis_id,
            p_raw=result.p_value,
            q_value=None,
            family_id=family_id,
            family_size=family_size,
            rank_in_family=None,
            accepted=False,
            reasons=reasons,
            reason_text=f"Test failed with error: {result.error or 'unknown error'}.",
            flags=flags,
            would_pass_without_correction=False,
            would_pass_without_effect_floor=False,
        )

    p_raw = float(result.p_value)
    would_pass_no_corr = bool(p_raw < alpha)
    would_pass_no_floor = bool(q_value is not None and q_value <= alpha)

    # 2. Multiple-testing gate
    if q_value is None or q_value > alpha:
        reasons.append(RejectionReason.NOT_SIGNIFICANT_AFTER_CORRECTION)
        reason_parts.append(
            f"Adjusted q={_format_p(q_value)} exceeds alpha={alpha} "
            f"(raw p={_format_p(p_raw)}, family m={family_size})."
        )

    # 3. Effect-size floor (if enabled)
    if config.effect_floor.enabled and result.effect is not None:
        thresh = effect_threshold_for(result.effect.name, config)
        comp = (
            result.effect.comparable_value
            if result.effect.comparable_value is not None
            else abs(result.effect.value)
        )
        if comp < thresh:
            reasons.append(RejectionReason.EFFECT_BELOW_THRESHOLD)
            reason_parts.append(
                f"Standardized effect |{result.effect.name}|={comp:.4f} is below "
                f"the practical floor ({thresh:.2f})."
            )

    # 4. Assumption gate
    if config.stats.enable_assumption_gate and any(
        a.severity == "violation" for a in result.assumptions
    ):
        reasons.append(RejectionReason.ASSUMPTION_VIOLATED)
        viol_names = [a.name for a in result.assumptions if a.severity == "violation"]
        reason_parts.append(
            f"Unresolved assumption violation(s): {', '.join(viol_names)}."
        )

    # 5. Trivial / derived relationship gate
    if config.stats.enable_trivial_gate and is_trivial_or_derived(result):
        reasons.append(RejectionReason.TRIVIAL_RELATIONSHIP)
        flags.append("possible_derived_column")
        eff_val = result.effect.value if result.effect else 0.0
        reason_parts.append(
            f"Near-deterministic relationship (effect={eff_val:.4f}) suggests a derived or duplicate column."
        )

    # 6. Strict CI mode (off by default)
    if (
        config.stats.strict_ci
        and result.effect is not None
        and result.effect.ci_low is not None
        and result.effect.ci_high is not None
        and result.effect.ci_low <= 0.0 <= result.effect.ci_high
    ):
        reasons.append(RejectionReason.UNSTABLE_CI)
        reason_parts.append(
            f"95% CI [{result.effect.ci_low:.4f}, {result.effect.ci_high:.4f}] includes zero."
        )

    accepted = len(reasons) == 0
    if accepted:
        eff_str = (
            f"{result.effect.name}={result.effect.value:.4f}"
            if result.effect is not None
            else "n/a"
        )
        reason_text = (
            f"Accepted: q={_format_p(q_value)} <= {alpha} (m={family_size}), {eff_str}."
        )
    else:
        reason_text = " ".join(reason_parts)

    return ValidationDecision(
        hypothesis_id=result.hypothesis_id,
        p_raw=p_raw,
        q_value=q_value,
        family_id=family_id,
        family_size=family_size,
        rank_in_family=rank_in_family,
        accepted=accepted,
        reasons=reasons,
        reason_text=reason_text,
        flags=sorted(set(flags)),
        would_pass_without_correction=would_pass_no_corr,
        would_pass_without_effect_floor=would_pass_no_floor,
    )

