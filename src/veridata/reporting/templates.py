"""Deterministic text templates for finding explanations and rejection reasons (Phase 5 Section 4)."""

from __future__ import annotations

from veridata.contracts.findings import Finding
from veridata.contracts.hypothesis import RelationshipType
from veridata.contracts.validation import RejectionReason
from veridata.reporting.facts import FactRegistry


def render_template(finding: Finding, registry: FactRegistry) -> str:
    """Generate a 100% compliant, deterministic, fact-rendered explanation."""
    hid = finding.hypothesis.id
    rel = finding.hypothesis.relationship
    dec = finding.decision
    test = finding.test
    eff = test.effect

    # If the finding was rejected by validation
    if not dec.accepted:
        return render_rejection_template(finding, registry)

    col_a = finding.hypothesis.column_a
    col_b = finding.hypothesis.column_b
    n_used = registry.render("{n_used}", hid)
    q_disp = registry.render("{q_display}", hid)
    m_tests = registry.render("{family_size}", hid)
    eff_name = eff.name if eff else "effect"
    eff_val = registry.render("{effect_value}", hid) if eff else "N/A"
    mag = eff.magnitude if eff else "unspecified"

    # Relationship-specific template
    if rel == RelationshipType.NUM_BINARY:
        # Welch or Mann-Whitney
        if "welch" in test.test_name.lower() or "t-test" in test.test_name.lower():
            text = (
                f"Among {n_used} records, the values of {col_a} were associated with {col_b}. "
                f"The difference is {mag} ({eff_name} = {eff_val}). "
                f"After correcting for {m_tests} tests (FDR 5%), the association is statistically supported (adjusted p {q_disp}). "
                f"This is an observed association and does not show that {col_b} causes differences in {col_a}."
            )
        else:
            text = (
                f"Values of {col_a} tended to differ across levels of {col_b} (n = {n_used}). "
                f"The association is {mag} ({eff_name} = {eff_val}). "
                f"After correcting for {m_tests} tests (FDR 5%), the association is statistically supported (adjusted p {q_disp}). "
                f"This reflects a rank-based association and does not establish a causal relationship."
            )
    elif rel == RelationshipType.NUM_CATEGORICAL:
        text = (
            f"Across levels of {col_b}, values of {col_a} showed variation (n = {n_used}). "
            f"The overall association is {mag} ({eff_name} = {eff_val}). "
            f"After correcting for {m_tests} tests (FDR 5%), the association is statistically supported (adjusted p {q_disp}). "
            f"This is an observed association and does not establish that {col_b} determines {col_a}."
        )
    elif rel == RelationshipType.NUM_NUM:
        direction = registry.render("{direction_observed}", hid)
        if direction not in ("positive", "negative"):
            direction = "positive"
        text = (
            f"{col_a} and {col_b} are {direction}ly associated (n = {n_used}). "
            f"The correlation is {mag} ({eff_name} = {eff_val}). "
            f"After correcting for {m_tests} tests (FDR 5%), the association is statistically supported (adjusted p {q_disp}). "
            f"This reflects an observed correlation, not a direct causal link."
        )
    elif rel == RelationshipType.CAT_CAT:
        text = (
            f"{col_a} and {col_b} showed an association across categories (n = {n_used}). "
            f"The degree of association is {mag} ({eff_name} = {eff_val}). "
            f"After correcting for {m_tests} tests (FDR 5%), the association is statistically supported (adjusted p {q_disp}). "
            f"This reflects category co-occurrence, not a causal dependency."
        )
    else:
        text = (
            f"An association between {col_a} and {col_b} was observed (n = {n_used}). "
            f"The estimated effect is {mag} ({eff_name} = {eff_val}). "
            f"After multiple-testing correction across {m_tests} tests, adjusted p is {q_disp}."
        )

    # Append assumption caveats if any
    caveats = []
    assumptions_list = getattr(test, "assumptions", []) or getattr(test, "assumption_checks", [])
    for check in assumptions_list:
        if not check.passed and check.severity in ("violation", "warning"):
            caveats.append(f"Note: {check.name} assumption check noted {check.detail}.")
    if caveats:
        text += " " + " ".join(caveats)

    return registry.render(text, hid)


def render_rejection_template(finding: Finding, registry: FactRegistry) -> str:
    """Render deterministic explanation for why a test was rejected."""
    hid = finding.hypothesis.id
    dec = finding.decision
    col_a = finding.hypothesis.column_a
    col_b = finding.hypothesis.column_b
    p_raw = registry.render("{p_raw}", hid)
    q_disp = registry.render("{q_display}", hid)
    m_tests = registry.render("{family_size}", hid)
    eff = finding.test.effect
    eff_val = registry.render("{effect_value}", hid) if eff else "N/A"
    eff_name = eff.name if eff else "effect"

    primary_reason = dec.reasons[0] if dec.reasons else RejectionReason.NOT_SIGNIFICANT_AFTER_CORRECTION

    if primary_reason == RejectionReason.NOT_SIGNIFICANT_AFTER_CORRECTION:
        return (
            f"For {col_a} and {col_b}, the raw p-value was {p_raw}, but after correcting for {m_tests} "
            f"tests the adjusted p is {q_disp}. With this family size, a pattern like this is expected by "
            f"chance, so it is not reported as a validated finding."
        )
    elif primary_reason == RejectionReason.EFFECT_BELOW_THRESHOLD:
        return (
            f"For {col_a} and {col_b}, the test was statistically detectable (adjusted p {q_disp}), "
            f"but the effect size is negligible ({eff_name} = {eff_val}), falling below the practical importance threshold."
        )
    elif primary_reason == RejectionReason.TRIVIAL_RELATIONSHIP:
        return (
            f"{col_a} and {col_b} appear to be derived from one another or measure the same underlying construct "
            f"({eff_name} = {eff_val}); this is a data-structure artifact, not an empirical discovery."
        )
    elif primary_reason == RejectionReason.INSUFFICIENT_DATA:
        return f"There was insufficient complete pairwise data between {col_a} and {col_b} to perform a reliable test."
    elif primary_reason == RejectionReason.ASSUMPTION_VIOLATED:
        return f"Statistical assumptions for testing {col_a} and {col_b} were violated with no valid nonparametric fallback."
    else:
        return (
            f"Testing {col_a} vs {col_b} did not meet validation criteria (adjusted p {q_disp}, raw p {p_raw})."
        )
