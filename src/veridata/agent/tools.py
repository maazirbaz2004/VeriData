"""Fixed, validated tool registry for conversational data science (Phase 6 Section 5)."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Literal

import pandas as pd
from pydantic import BaseModel, Field

from veridata.config import PipelineConfig
from veridata.contracts.facts import Fact
from veridata.contracts.findings import Finding
from veridata.contracts.hypothesis import (
    Direction,
    FeasibilityReport,
    Hypothesis,
    RelationshipType,
)
from veridata.contracts.results import TestResult
from veridata.contracts.validation import ValidationDecision
from veridata.hypotheses.dedupe import make_hypothesis_id
from veridata.reporting.charts import plot_distribution, plot_finding
from veridata.reporting.facts import FactRegistry, build_facts
from veridata.reporting.narration import explain_finding
from veridata.reporting.templates import render_rejection_template
from veridata.schemas import ColumnSchemaEntry
from veridata.stats.runner import run_hypothesis
from veridata.validation.ledger import SessionLedger

logger = logging.getLogger("veridata.agent.tools")


class ToolResult(BaseModel):
    """Normalized output contract returned by all chat tools."""

    tool: str
    ok: bool
    error: str | None = None
    finding: Finding | None = None
    facts: list[Fact] = Field(default_factory=list)
    charts: list[str] = Field(default_factory=list)
    table: list[dict[str, Any]] | None = None
    ledger_diff: list[dict[str, Any]] = Field(default_factory=list)
    meta: dict[str, Any] = Field(default_factory=dict)


class ToolRegistry:
    """Manages tool execution with argument schema validation against the dataset schema."""

    def __init__(
        self,
        df: pd.DataFrame,
        schema: dict[str, ColumnSchemaEntry | dict[str, Any]],
        config: PipelineConfig,
        ledger: SessionLedger,
        session_dir: Path | str = "outputs/chat_session",
    ) -> None:
        self.df = df
        self.schema = schema
        self.config = config
        self.ledger = ledger
        self.session_dir = Path(session_dir)
        self.session_dir.mkdir(parents=True, exist_ok=True)
        self.known_hypotheses: dict[str, Hypothesis] = {}
        self.last_findings: list[Finding] = []

    def _is_numeric(self, col: str) -> bool:
        if col not in self.df.columns:
            return False
        return bool(pd.api.types.is_numeric_dtype(self.df[col]))

    def _n_levels(self, col: str) -> int:
        if col not in self.df.columns:
            return 0
        return int(self.df[col].nunique(dropna=True))

    def describe_dataset(self) -> ToolResult:
        """Provide profile summary: rows, columns, types, and missingness."""
        n_rows, n_cols = self.df.shape
        missing = int(self.df.isna().sum().sum())
        missing_pct = float(missing / (n_rows * n_cols) * 100) if n_rows * n_cols > 0 else 0.0

        facts = [
            Fact(key="n_rows", value=n_rows, display=f"{n_rows:,}", source="df.shape[0]"),
            Fact(key="n_cols", value=n_cols, display=str(n_cols), source="df.shape[1]"),
            Fact(key="missing_pct", value=missing_pct, display=f"{missing_pct:.1f}%", source="missingness"),
        ]

        summary_table = []
        for col in sorted(self.df.columns):
            summary_table.append({
                "column": col,
                "dtype": str(self.df[col].dtype),
                "n_unique": int(self.df[col].nunique()),
                "missing": int(self.df[col].isna().sum()),
            })

        return ToolResult(
            tool="describe_dataset",
            ok=True,
            facts=facts,
            table=summary_table,
            meta={"summary": f"Dataset has {n_rows:,} rows, {n_cols} columns, and {missing_pct:.1f}% missing values."},
        )

    def describe_column(self, column: str) -> ToolResult:
        """Profile a specific column and generate distribution plot."""
        if column not in self.df.columns:
            return ToolResult(
                tool="describe_column",
                ok=False,
                error=f"Column '{column}' does not exist in dataset.",
            )

        col_s = self.df[column]
        n_missing = int(col_s.isna().sum())
        n_unique = int(col_s.nunique())
        facts = [
            Fact(key="column_name", value=column, display=column, source="column"),
            Fact(key="n_unique", value=n_unique, display=f"{n_unique:,}", source="nunique"),
            Fact(key="n_missing", value=n_missing, display=f"{n_missing:,}", source="missing"),
        ]

        if pd.api.types.is_numeric_dtype(col_s):
            col_clean = col_s.dropna()
            if len(col_clean) > 0:
                mean_val = float(col_clean.mean())
                med_val = float(col_clean.median())
                std_val = float(col_clean.std()) if len(col_clean) > 1 else 0.0
                facts.extend([
                    Fact(key="mean", value=mean_val, display=f"{mean_val:,.2f}", source="mean"),
                    Fact(key="median", value=med_val, display=f"{med_val:,.2f}", source="median"),
                    Fact(key="std", value=std_val, display=f"{std_val:,.2f}", source="std"),
                ])

        chart_path = self.session_dir / f"dist_{column}.png"
        try:
            plot_distribution(self.df, column, out_path=chart_path)
            charts = [str(chart_path)]
        except Exception as exc:
            logger.debug("Distribution plot failed: %s", exc)
            charts = []

        return ToolResult(
            tool="describe_column",
            ok=True,
            facts=facts,
            charts=charts,
            meta={"column": column},
        )

    def _execute_statistical_test(
        self,
        column_a: str,
        column_b: str,
        relationship: RelationshipType,
        tool_name: str,
    ) -> ToolResult:
        """Run hypothesis test, update session ledger, revalidate, and generate chart."""
        if column_a not in self.df.columns or column_b not in self.df.columns:
            return ToolResult(
                tool=tool_name,
                ok=False,
                error=f"Columns '{column_a}' or '{column_b}' not found in dataset.",
            )

        hid = make_hypothesis_id(relationship, column_a, column_b)
        hyp = Hypothesis(
            id=hid,
            column_a=column_a,
            column_b=column_b,
            relationship=relationship,
            expected_direction=Direction.ANY,
            source="user",
            created_stage="chat",
            status="queued",
            feasibility=FeasibilityReport(feasible=True, n_pairwise_complete=len(self.df)),
        )
        self.known_hypotheses[hid] = hyp

        # Check ledger cache (Principle P6/Deduplication)
        cached_entry = self.ledger.get(hid)
        if cached_entry is not None:
            test_res = cached_entry.test
            is_new = False
        else:
            test_res = run_hypothesis(hyp, self.df, self.config, stage="A")
            _, is_new = self.ledger.add(test_res, stage="chat")

        # Session-level revalidation
        decisions, diffs = self.ledger.revalidate(
            self.known_hypotheses, self.config, family_id="session"
        )
        dec_map = {d.hypothesis_id: d for d in decisions}
        current_dec = dec_map.get(
            hid,
            ValidationDecision(
                hypothesis_id=hid,
                accepted=False,
                family_id="session",
                family_size=len(self.ledger.entries),
            ),
        )

        finding = Finding(
            hypothesis=hyp,
            test=test_res,
            decision=current_dec,
        )
        finding_facts = build_facts(finding)
        finding.facts = finding_facts

        # Update last findings
        self.last_findings = [f for f in self.last_findings if f.hypothesis.id != hid]
        self.last_findings.insert(0, finding)

        # Generate chart
        chart_path = self.session_dir / f"{hid}.png"
        charts = []
        try:
            plot_finding(finding, self.df, out_path=chart_path)
            charts.append(str(chart_path))
        except Exception as exc:
            logger.debug("Finding plot failed: %s", exc)

        return ToolResult(
            tool=tool_name,
            ok=True,
            finding=finding,
            facts=finding_facts,
            charts=charts,
            ledger_diff=diffs,
            meta={
                "is_new": is_new,
                "family_size": current_dec.family_size,
                "q_value": current_dec.q_value,
                "accepted": current_dec.accepted,
            },
        )

    def compare_groups(self, numeric_column: str, group_column: str) -> ToolResult:
        """Compare a numeric variable across groups of a binary or categorical variable."""
        if not self._is_numeric(numeric_column):
            # Check if inverted
            if self._is_numeric(group_column):
                numeric_column, group_column = group_column, numeric_column
            else:
                return ToolResult(
                    tool="compare_groups",
                    ok=False,
                    error=f"'{numeric_column}' is not numeric. compare_groups requires a numeric column and a group column.",
                )

        n_levels = self._n_levels(group_column)
        if n_levels == 2:
            rel = RelationshipType.NUM_BINARY
        elif n_levels > 2:
            rel = RelationshipType.NUM_CATEGORICAL
        else:
            return ToolResult(
                tool="compare_groups",
                ok=False,
                error=f"Group column '{group_column}' has {n_levels} unique values (needs at least 2).",
            )

        return self._execute_statistical_test(numeric_column, group_column, rel, "compare_groups")

    def test_correlation(self, column_a: str, column_b: str) -> ToolResult:
        """Test linear or rank correlation between two numeric variables."""
        if not self._is_numeric(column_a) or not self._is_numeric(column_b):
            return ToolResult(
                tool="test_correlation",
                ok=False,
                error=f"Both columns must be numeric for correlation testing (got {column_a}, {column_b}).",
            )
        return self._execute_statistical_test(column_a, column_b, RelationshipType.NUM_NUM, "test_correlation")

    def test_association(self, column_a: str, column_b: str) -> ToolResult:
        """Test categorical association between two discrete/categorical variables."""
        return self._execute_statistical_test(column_a, column_b, RelationshipType.CAT_CAT, "test_association")

    def test_relationship(self, column_a: str, column_b: str) -> ToolResult:
        """Automatically dispatch to the appropriate test based on column types."""
        a_num = self._is_numeric(column_a)
        b_num = self._is_numeric(column_b)

        if a_num and b_num:
            return self.test_correlation(column_a, column_b)
        elif a_num and not b_num:
            return self.compare_groups(numeric_column=column_a, group_column=column_b)
        elif not a_num and b_num:
            return self.compare_groups(numeric_column=column_b, group_column=column_a)
        else:
            return self.test_association(column_a, column_b)

    def show_distribution(self, column: str, group_column: str | None = None) -> ToolResult:
        """Render distribution chart without running a hypothesis test."""
        return self.describe_column(column)

    def list_findings(self, top_k: int = 10, relationship: str | None = None) -> ToolResult:
        """List currently validated findings from the session ledger."""
        decisions, _ = self.ledger.revalidate(self.known_hypotheses, self.config, family_id="session")
        table: list[dict[str, Any]] = []

        for entry in self.ledger.entries:
            hid = entry.hypothesis_hash
            hyp = self.known_hypotheses.get(hid)
            if not hyp:
                continue
            if relationship and hyp.relationship.value != relationship:
                continue

            test = entry.test
            table.append({
                "hypothesis_id": hid,
                "column_a": hyp.column_a,
                "column_b": hyp.column_b,
                "relationship": hyp.relationship.value,
                "test_name": test.test_name,
                "p_raw": test.p_value,
                "effect_name": test.effect.name if test.effect else None,
                "effect_value": test.effect.value if test.effect else None,
                "magnitude": test.effect.magnitude if test.effect else None,
                "status": test.status,
            })

        table = table[:top_k]
        return ToolResult(
            tool="list_findings",
            ok=True,
            table=table,
            meta={"count": len(table), "total_in_ledger": len(self.ledger.entries)},
        )

    def explain_finding(self, finding_ref: str) -> ToolResult:
        """Provide detailed verified explanation for a finding."""
        target_finding: Finding | None = None
        if finding_ref in ("last", "latest") and self.last_findings:
            target_finding = self.last_findings[0]
        else:
            # Check by index or id
            if finding_ref.isdigit() and int(finding_ref) <= len(self.last_findings):
                idx = int(finding_ref) - 1
                if 0 <= idx < len(self.last_findings):
                    target_finding = self.last_findings[idx]
            if not target_finding:
                for f in self.last_findings:
                    if f.hypothesis.id == finding_ref or finding_ref in (f.hypothesis.column_a, f.hypothesis.column_b):
                        target_finding = f
                        break

        if not target_finding:
            return ToolResult(
                tool="explain_finding",
                ok=False,
                error=f"Finding reference '{finding_ref}' not found.",
            )

        reg = FactRegistry()
        reg.add_many(target_finding.facts, finding_id=target_finding.hypothesis.id)
        exp = explain_finding(target_finding, registry=reg)

        return ToolResult(
            tool="explain_finding",
            ok=True,
            finding=target_finding,
            facts=target_finding.facts,
            meta={"explanation": exp.text, "verified": exp.verified, "source": exp.source},
        )

    def explain_rejection(self, finding_ref: str) -> ToolResult:
        """Explain why a hypothesis pattern was rejected by validation."""
        target_finding: Finding | None = None
        for f in self.last_findings:
            if f.hypothesis.id == finding_ref or finding_ref in (f.hypothesis.column_a, f.hypothesis.column_b):
                target_finding = f
                break

        if not target_finding:
            return ToolResult(
                tool="explain_rejection",
                ok=False,
                error=f"Could not find test for reference '{finding_ref}'.",
            )

        reg = FactRegistry()
        reg.add_many(target_finding.facts, finding_id=target_finding.hypothesis.id)
        rej_text = render_rejection_template(target_finding, reg)

        return ToolResult(
            tool="explain_rejection",
            ok=True,
            finding=target_finding,
            facts=target_finding.facts,
            meta={"rejection_explanation": rej_text},
        )

    def get_ledger_status(self) -> ToolResult:
        """Report multiple-testing family size, alpha, and validation counts."""
        entries = self.ledger.entries
        family = self.ledger.family()
        accepted_count = sum(
            1 for e in entries if e.hypothesis_hash in self.ledger._last_decisions and self.ledger._last_decisions[e.hypothesis_hash].accepted
        )

        facts = [
            Fact(key="total_tests", value=len(entries), display=str(len(entries)), source="ledger.total"),
            Fact(key="family_size", value=len(family), display=str(len(family)), source="ledger.family"),
            Fact(key="accepted_count", value=accepted_count, display=str(accepted_count), source="ledger.accepted"),
            Fact(key="alpha", value=self.ledger._ledger.alpha, display=str(self.ledger._ledger.alpha), source="ledger.alpha"),
        ]

        return ToolResult(
            tool="get_ledger_status",
            ok=True,
            facts=facts,
            meta={
                "total_tests": len(entries),
                "family_size": len(family),
                "accepted_count": accepted_count,
            },
        )

    def suggest_next(self) -> ToolResult:
        """Generate follow-up recommendations."""
        from veridata.agent.followups import generate_followups

        last_f = self.last_findings[0] if self.last_findings else None
        followups = generate_followups(self.df, self.schema, self.ledger, last_finding=last_f)
        return ToolResult(
            tool="suggest_next",
            ok=True,
            table=followups,
            meta={"followups": followups},
        )
