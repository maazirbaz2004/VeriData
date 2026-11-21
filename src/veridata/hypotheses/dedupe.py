"""Hypothesis identity hashing and deduplication (Phase 2 Section 8)."""

from __future__ import annotations

import hashlib
from typing import Sequence

from veridata.contracts.hypothesis import Direction, Hypothesis, RelationshipType

SOURCE_PRIORITY: dict[str, int] = {
    "user": 3,
    "followup": 2,
    "llm": 1,
    "enumerated": 0,
}


def make_hypothesis_id(
    relationship: RelationshipType,
    column_a: str,
    column_b: str,
    covariates: Sequence[str] = (),
) -> str:
    """Return a stable 16-char SHA-1 identifier for a hypothesis.

    Symmetric pairs (A, B) and (B, A) produce the exact same ID because column
    names and covariates are sorted before hashing.
    """
    sorted_cols = sorted([column_a, column_b])
    sorted_covs = sorted(covariates)
    payload = f"{relationship.value}|{'|'.join(sorted_cols)}|{'|'.join(sorted_covs)}"
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()[:16]


def merge_hypotheses(existing: Hypothesis, incoming: Hypothesis) -> Hypothesis:
    """Merge two hypotheses sharing the same ID according to source priority.

    Priority: ``user`` > ``followup`` > ``llm`` > ``enumerated``.
    Keeps LLM/user rationale and expected_direction when available.
    """
    existing_prio = SOURCE_PRIORITY.get(existing.source, 0)
    incoming_prio = SOURCE_PRIORITY.get(incoming.source, 0)

    if incoming_prio > existing_prio:
        primary, secondary = incoming, existing
    else:
        primary, secondary = existing, incoming

    rationale = primary.rationale or secondary.rationale
    if (
        primary.source == "user"
        and not primary.rationale
        and secondary.source == "llm"
        and secondary.rationale
    ):
        rationale = secondary.rationale

    expected_direction = (
        primary.expected_direction
        if primary.expected_direction != Direction.ANY
        else secondary.expected_direction
    )

    merged_components = dict(secondary.priority_components)
    merged_components.update(primary.priority_components)

    created_stage = (
        "chat" if (existing.created_stage == "chat" or incoming.created_stage == "chat") else "batch"
    )

    return primary.model_copy(
        update={
            "rationale": rationale,
            "expected_direction": expected_direction,
            "priority_components": merged_components,
            "created_stage": created_stage,
        }
    )


def deduplicate_hypotheses(hypotheses: Sequence[Hypothesis]) -> list[Hypothesis]:
    """Collapse duplicate hypotheses by ID while preserving first-seen order."""
    by_id: dict[str, Hypothesis] = {}
    order: list[str] = []
    for hyp in hypotheses:
        if hyp.id not in by_id:
            by_id[hyp.id] = hyp
            order.append(hyp.id)
        else:
            by_id[hyp.id] = merge_hypotheses(by_id[hyp.id], hyp)
    return [by_id[hid] for hid in order]

