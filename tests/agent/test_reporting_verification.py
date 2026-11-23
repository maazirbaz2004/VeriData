"""Adversarial tests for number verification and language linting (Phase 5 & 6 requirements)."""

import pytest

from veridata.contracts.facts import Fact
from veridata.contracts.findings import Finding
from veridata.contracts.hypothesis import Direction, FeasibilityReport, Hypothesis, RelationshipType
from veridata.contracts.results import EffectSize, TestResult
from veridata.contracts.validation import ValidationDecision
from veridata.reporting.facts import FactRegistry, build_facts
from veridata.reporting.language_lint import lint_text
from veridata.reporting.narration import explain_finding
from veridata.reporting.number_verifier import verify_text
from veridata.reporting.templates import render_template


@pytest.fixture
def sample_finding():
    hyp = Hypothesis(
        id="hyp_test_01",
        column_a="charges",
        column_b="smoker",
        relationship=RelationshipType.NUM_BINARY,
        expected_direction=Direction.A_GREATER,
        source="user",
        feasibility=FeasibilityReport(feasible=True, n_pairwise_complete=1000),
    )
    test = TestResult(
        hypothesis_id="hyp_test_01",
        status="ok",
        test_name="welch_t",
        n_used=1000,
        statistic=12.45,
        p_value=0.00001,
        effect=EffectSize(name="hedges_g", value=1.42, ci_low=1.20, ci_high=1.64, magnitude="large"),
        descriptives={"mean_diff": 23000.0},
    )
    dec = ValidationDecision(
        hypothesis_id="hyp_test_01",
        p_raw=0.00001,
        q_value=0.00012,
        family_size=25,
        accepted=True,
    )
    finding = Finding(hypothesis=hyp, test=test, decision=dec)
    finding.facts = build_facts(finding)
    return finding


def test_template_text_verifies_100_percent(sample_finding):
    reg = FactRegistry()
    reg.add_many(sample_finding.facts, finding_id=sample_finding.hypothesis.id)

    text = render_template(sample_finding, reg)
    v_res = verify_text(text, reg, finding_ids=[sample_finding.hypothesis.id])
    assert v_res.ok, f"Verification violations: {[v.token for v in v_res.violations]}"

    l_res = lint_text(text, sample_finding)
    assert l_res.ok, f"Linter violations: {l_res.violations}"


def test_verifier_catches_fabricated_number(sample_finding):
    reg = FactRegistry()
    reg.add_many(sample_finding.facts, finding_id=sample_finding.hypothesis.id)

    valid_text = render_template(sample_finding, reg)
    # Inject fabricated statistic
    bad_text = valid_text + " The hazard ratio was 3.87."

    v_res = verify_text(bad_text, reg, finding_ids=[sample_finding.hypothesis.id])
    assert not v_res.ok
    assert any("3.87" in v.token for v in v_res.violations)


def test_linter_catches_causal_language(sample_finding):
    causal_text = "Smoking causes charges to increase by 50%."
    l_res = lint_text(causal_text, sample_finding)
    assert not l_res.ok
    assert any("Causal language" in v for v in l_res.violations)


def test_explain_finding_deterministic_fallback(sample_finding):
    # Without LLM, explain_finding must produce verified template
    exp = explain_finding(sample_finding, llm=None)
    assert exp.verified is True
    assert exp.source == "template"
    assert "charges" in exp.text
