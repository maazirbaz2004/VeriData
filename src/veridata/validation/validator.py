"""Pure, deterministic validation orchestrator (Phase 3 Section 7.4)."""

from __future__ import annotations

from typing import Sequence

import numpy as np

from veridata.config import PipelineConfig
from veridata.contracts.findings import Finding
from veridata.contracts.hypothesis import Hypothesis
from veridata.contracts.results import TestResult
from veridata.contracts.validation import ValidationDecision
from veridata.validation.correction import apply_correction
from veridata.validation.rules import evaluate_validation_rules


def validate(
    results: Sequence[TestResult],
    hypotheses: dict[str, Hypothesis],
    config: PipelineConfig,
    *,
    family_id: str = "batch",
) -> list[ValidationDecision]:
    """Validate a list of TestResults with multiple-testing correction and rejection rules.

    Pure, deterministic, and order-independent: internal BH correction sorts by
    ``hypothesis_id`` before ranking so output decisions never depend on input order.
    """
    _ = hypotheses
    sorted_results = sorted(results, key=lambda r: r.hypothesis_id)

    family_results = [
        r
        for r in sorted_results
        if r.status == "ok" and r.p_value is not None and np.isfinite(r.p_value)
    ]
    p_vals = np.array([float(r.p_value) for r in family_results], dtype=float)
    corr = apply_correction(
        p_vals,
        method=config.stats.correction,
        alpha=config.stats.alpha,
    )

    q_by_id: dict[str, float] = {}
    rank_by_id: dict[str, int] = {}
    for idx, res in enumerate(family_results):
        q_by_id[res.hypothesis_id] = float(corr.q_values[idx])
        rank_by_id[res.hypothesis_id] = int(corr.ranks[idx])

    decisions_by_id: dict[str, ValidationDecision] = {}
    for res in sorted_results:
        decisions_by_id[res.hypothesis_id] = evaluate_validation_rules(
            res,
            q_value=q_by_id.get(res.hypothesis_id),
            rank_in_family=rank_by_id.get(res.hypothesis_id),
            family_size=corr.m,
            family_id=family_id,
            config=config,
        )

    return [decisions_by_id[r.hypothesis_id] for r in results]


def build_findings(
    hypotheses: dict[str, Hypothesis],
    results: Sequence[TestResult],
    decisions: Sequence[ValidationDecision],
) -> list[Finding]:
    """Join Hypotheses, TestResults, and ValidationDecisions into Finding records."""
    res_by_id = {r.hypothesis_id: r for r in results}
    dec_by_id = {d.hypothesis_id: d for d in decisions}
    findings: list[Finding] = []
    for hid in sorted(dec_by_id.keys()):
        if hid in hypotheses and hid in res_by_id:
            findings.append(
                Finding(
                    hypothesis=hypotheses[hid],
                    test=res_by_id[hid],
                    decision=dec_by_id[hid],
                    facts=[],
                )
            )
    # Order: accepted first (by q_value asc, comparable effect desc), then rejected by id
    findings.sort(
        key=lambda f: (
            0 if f.decision.accepted else 1,
            f.decision.q_value if f.decision.q_value is not None else 2.0,
            -(f.test.effect.comparable_value or 0.0) if f.test.effect else 0.0,
            f.hypothesis.id,
        )
    )
    return findings

