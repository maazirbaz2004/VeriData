"""Tests for Phase 3 multiple-testing correction, validation rules, and session ledger."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from statsmodels.stats.multitest import multipletests

from veridata.config import PipelineConfig
from veridata.contracts.hypothesis import FeasibilityReport, Hypothesis, RelationshipType
from veridata.contracts.results import AssumptionCheck, EffectSize, TestResult
from veridata.contracts.validation import RejectionReason
from veridata.errors import ValidationError
from veridata.validation.correction import apply_correction
from veridata.validation.ledger import SessionLedger
from veridata.validation.validator import validate


def test_bh_hand_computed_and_edge_cases() -> None:
    # Hand-computed: p = [0.01, 0.04, 0.03, 0.005], m = 4
    # Sorted: p_(1)=0.005, p_(2)=0.01, p_(3)=0.03, p_(4)=0.04
    # Raw (m/k)*p_(k): [0.02, 0.02, 0.04, 0.04] -> monotone: [0.02, 0.02, 0.04, 0.04]
    out = apply_correction([0.01, 0.04, 0.03, 0.005], method="bh", alpha=0.05)
    assert np.allclose(out.q_values, [0.02, 0.04, 0.04, 0.02], atol=1e-12)
    assert out.reject_mask.tolist() == [True, True, True, True]
    assert out.ranks.tolist() == [2, 4, 3, 1]

    # Edge cases: m=0, m=1, all 0, all 1
    assert apply_correction([], method="bh", alpha=0.05).m == 0
    assert apply_correction([0.03], method="bh", alpha=0.05).q_values[0] == pytest.approx(0.03)
    assert np.allclose(apply_correction([0.0, 0.0, 0.0], method="bh").q_values, [0.0, 0.0, 0.0])
    assert np.allclose(apply_correction([1.0, 1.0, 1.0], method="bh").q_values, [1.0, 1.0, 1.0])


def test_correction_matches_statsmodels_on_random_vectors() -> None:
    rng = np.random.default_rng(42)
    for _ in range(200):
        m = int(rng.integers(1, 60))
        p = rng.uniform(0.0, 1.0, size=m)
        if m >= 5:
            p[0] = p[1]  # inject ties
        for our_m, sm_m in [
            ("bh", "fdr_bh"),
            ("by", "fdr_by"),
            ("holm", "holm"),
            ("bonferroni", "bonferroni"),
        ]:
            ours = apply_correction(p, method=our_m, alpha=0.05)
            _, ref_q, _, _ = multipletests(p, alpha=0.05, method=sm_m)
            assert np.allclose(ours.q_values, ref_q, atol=1e-12)


def _mock_result(
    hid: str,
    p_val: float | None,
    eff_name: str = "pearson_r",
    eff_val: float = 0.4,
    status: str = "ok",
    n_used: int = 100,
    violation: bool = False,
) -> TestResult:
    effect = (
        EffectSize(
            name=eff_name,
            value=eff_val,
            magnitude="medium",
            comparable_value=abs(eff_val),
        )
        if status == "ok"
        else None
    )
    assumptions = (
        [
            AssumptionCheck(
                name="min_group_size",
                method="counts",
                passed=False,
                severity="violation",
                detail="violated",
            )
        ]
        if violation
        else []
    )
    return TestResult(
        hypothesis_id=hid,
        status=status,  # type: ignore[arg-type]
        test_name="pearson" if status == "ok" else "none",
        n_used=n_used,
        p_value=p_val,
        effect=effect,
        assumptions=assumptions,
    )


def test_validator_rules_and_order_invariance() -> None:
    cfg = PipelineConfig()
    results = [
        _mock_result("h_accept", p_val=0.0001, eff_val=0.45),
        _mock_result("h_trivial_small", p_val=0.0002, eff_val=0.03),  # sig but below 0.10 floor
        _mock_result("h_not_sig", p_val=0.25, eff_val=0.20),
        _mock_result("h_derived", p_val=0.00001, eff_val=0.9995),
        _mock_result("h_skipped", p_val=None, status="skipped_infeasible", n_used=5),
        _mock_result("h_viol", p_val=0.0005, eff_val=0.40, violation=True),
    ]
    hyps: dict[str, Hypothesis] = {}

    decs = validate(results, hyps, cfg, family_id="batch")
    by_id = {d.hypothesis_id: d for d in decs}

    # Family size m excludes h_skipped -> m = 5
    assert by_id["h_accept"].family_size == 5
    assert by_id["h_accept"].accepted is True
    assert by_id["h_accept"].reasons == []

    assert by_id["h_trivial_small"].accepted is False
    assert RejectionReason.EFFECT_BELOW_THRESHOLD in by_id["h_trivial_small"].reasons
    assert by_id["h_trivial_small"].would_pass_without_effect_floor is True

    assert by_id["h_not_sig"].accepted is False
    assert RejectionReason.NOT_SIGNIFICANT_AFTER_CORRECTION in by_id["h_not_sig"].reasons

    assert by_id["h_derived"].accepted is False
    assert RejectionReason.TRIVIAL_RELATIONSHIP in by_id["h_derived"].reasons
    assert "possible_derived_column" in by_id["h_derived"].flags

    assert by_id["h_skipped"].accepted is False
    assert RejectionReason.INSUFFICIENT_DATA in by_id["h_skipped"].reasons

    assert by_id["h_viol"].accepted is False
    assert RejectionReason.ASSUMPTION_VIOLATED in by_id["h_viol"].reasons

    # Order invariance
    decs_rev = validate(list(reversed(results)), hyps, cfg, family_id="batch")
    by_id_rev = {d.hypothesis_id: d for d in decs_rev}
    for hid in by_id:
        assert by_id[hid].model_dump() == by_id_rev[hid].model_dump()


def test_ledger_append_dedupe_revalidate_diff_and_persistence(tmp_path: Path) -> None:
    cfg = PipelineConfig()
    ledger = SessionLedger(dataset_sha256="abc123", alpha=0.05)

    # Initial batch: 1 test with p=0.03 -> accepted when m=1
    r1 = _mock_result("h1", p_val=0.03, eff_val=0.35)
    _, added1 = ledger.add(r1, stage="batch")
    _, added1_dup = ledger.add(r1, stage="chat")
    assert added1 is True
    assert added1_dup is False
    assert len(ledger.entries) == 1

    decs1, diffs1 = ledger.revalidate({}, cfg)
    assert decs1[0].accepted is True
    assert diffs1 == []

    # Add 3 chat tests with p=0.50 -> now m=4, q(h1) = 4 * 0.03 = 0.12 > 0.05 -> flips h1!
    for i in range(2, 5):
        ledger.add(_mock_result(f"h{i}", p_val=0.50, eff_val=0.30), stage="chat")

    decs2, diffs2 = ledger.revalidate({}, cfg)
    by_id2 = {d.hypothesis_id: d for d in decs2}
    assert by_id2["h1"].accepted is False
    assert len(diffs2) == 1
    assert diffs2[0]["hypothesis_id"] == "h1"
    assert diffs2[0]["previous_accepted"] is True
    assert diffs2[0]["current_accepted"] is False

    # JSONL round trip & SHA-256 mismatch guard
    p = ledger.save_jsonl(tmp_path / "ledger.jsonl")
    loaded = SessionLedger.load_jsonl(p, expected_dataset_sha256="abc123")
    assert len(loaded.entries) == 4
    with pytest.raises(ValidationError):
        SessionLedger.load_jsonl(p, expected_dataset_sha256="wrong_sha")

