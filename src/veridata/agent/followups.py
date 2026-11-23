"""Deterministic follow-up candidate generation and outcome-independent ranking (Phase 6 Section 7)."""

from __future__ import annotations

import logging
from typing import Any

import pandas as pd
from pydantic import BaseModel, Field

from veridata.agent.llm import LLMClient
from veridata.contracts.findings import Finding
from veridata.contracts.hypothesis import RelationshipType
from veridata.hypotheses.dedupe import make_hypothesis_id
from veridata.schemas import ColumnSchemaEntry
from veridata.validation.ledger import SessionLedger

logger = logging.getLogger("veridata.agent.followups")


class FollowUpSuggestion(BaseModel):
    """An executable next-step suggestion presented as a one-click button."""

    id: str
    label: str
    tool: str
    arguments: dict[str, Any]
    warning: str = "This test will add one comparison to the multiple-testing family."


def generate_followups(
    df: pd.DataFrame,
    schema: dict[str, ColumnSchemaEntry | dict[str, Any]],
    ledger: SessionLedger,
    last_finding: Finding | None = None,
    max_followups: int = 3,
    llm: LLMClient | None = None,
) -> list[dict[str, Any]]:
    """Generate outcome-independent follow-up recommendations without peeking at effect sizes."""
    candidates: list[FollowUpSuggestion] = []
    tested_pairs: set[tuple[str, str]] = set()

    for entry in ledger.entries:
        h = entry.hypothesis_hash
        # Look up tested columns from test or cache
        if hasattr(entry.test, "hypothesis_id"):
            tested_pairs.add((entry.test.hypothesis_id, ""))

    if last_finding is not None:
        col_a = last_finding.hypothesis.column_a
        col_b = last_finding.hypothesis.column_b

        # 1. Other relationship involving col_a with untested columns
        numeric_cols = [
            c for c in df.columns
            if c != col_a and pd.api.types.is_numeric_dtype(df[c])
        ]
        cat_cols = [
            c for c in df.columns
            if c != col_a and (not pd.api.types.is_numeric_dtype(df[c]) or df[c].nunique() <= 10)
        ]

        # Suggest correlation with another numeric column
        for other_num in numeric_cols[:2]:
            if other_num != col_b:
                hid = make_hypothesis_id(RelationshipType.NUM_NUM, col_a, other_num)
                if ledger.get(hid) is None:
                    candidates.append(
                        FollowUpSuggestion(
                            id=f"corr_{col_a}_{other_num}",
                            label=f"Examine correlation between {col_a} and {other_num}",
                            tool="test_correlation",
                            arguments={"column_a": col_a, "column_b": other_num},
                        )
                    )

        # Suggest group comparison if col_a is numeric and there are categories
        if pd.api.types.is_numeric_dtype(df[col_a]):
            for other_cat in cat_cols[:2]:
                if other_cat != col_b and df[other_cat].nunique() >= 2:
                    candidates.append(
                        FollowUpSuggestion(
                            id=f"comp_{col_a}_{other_cat}",
                            label=f"Compare {col_a} across {other_cat} categories",
                            tool="compare_groups",
                            arguments={"numeric_column": col_a, "group_column": other_cat},
                        )
                    )

        # 2. Distribution / skew look for col_a
        candidates.append(
            FollowUpSuggestion(
                id=f"dist_{col_a}",
                label=f"Inspect the distribution of {col_a}",
                tool="show_distribution",
                arguments={"column": col_a},
                warning="Descriptive view (does not increase testing family).",
            )
        )

        # 3. Why was anything rejected?
        for hid, dec in ledger._last_decisions.items():
            if not dec.accepted:
                candidates.append(
                    FollowUpSuggestion(
                        id=f"rej_{hid}",
                        label="Review reasons for rejected hypothesis",
                        tool="explain_rejection",
                        arguments={"finding_ref": hid},
                        warning="Exploratory inspection of rejected patterns.",
                    )
                )
                break

    # If no candidates yet (or before any finding)
    if not candidates:
        all_cols = list(df.columns)
        if len(all_cols) >= 2:
            c1, c2 = all_cols[0], all_cols[1]
            candidates.append(
                FollowUpSuggestion(
                    id=f"rel_{c1}_{c2}",
                    label=f"Test relationship between {c1} and {c2}",
                    tool="test_relationship",
                    arguments={"column_a": c1, "column_b": c2},
                )
            )
        candidates.append(
            FollowUpSuggestion(
                id="status_ledger",
                label="Check multiple-testing family summary",
                tool="get_ledger_status",
                arguments={},
                warning="Informational summary.",
            )
        )

    # Return top candidates
    selected = candidates[:max_followups]
    return [c.model_dump() for c in selected]
