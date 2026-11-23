"""Fact extraction, formatting rules, and FactRegistry for machine-verified reporting."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from veridata.contracts.facts import Fact
from veridata.contracts.findings import Finding
from veridata.contracts.results import TestResult
from veridata.contracts.validation import ValidationDecision


@dataclass(frozen=True)
class AllowedNumber:
    """A verified number allowed to appear in generated text."""

    value: float | int
    display: str
    tolerance: float
    key: str
    finding_id: str | None = None


def format_p_value(p: float | None) -> str:
    """Format p-value: '<0.001' or 3 decimals."""
    if p is None or math.isnan(p):
        return "N/A"
    if p < 0.001:
        return "<0.001"
    return f"{p:.3f}"


def format_q_value(q: float | None) -> str:
    """Format FDR q-value: '<0.001' or 3 decimals."""
    if q is None or math.isnan(q):
        return "N/A"
    if q < 0.001:
        return "<0.001"
    return f"{q:.3f}"


def format_effect(val: float | None, decimals: int = 2) -> str:
    """Format effect size or correlation to specified decimals."""
    if val is None or math.isnan(val):
        return "N/A"
    return f"{val:.{decimals}f}"


def format_number(val: float | int | None) -> str:
    """Format counts with commas, floats with adaptive precision."""
    if val is None or (isinstance(val, float) and math.isnan(val)):
        return "N/A"
    if isinstance(val, int):
        return f"{val:,}"
    if isinstance(val, float) and val.is_integer():
        return f"{int(val):,}"
    # Adaptive float
    if abs(val) >= 100:
        return f"{val:,.1f}"
    if abs(val) >= 1:
        return f"{val:.2f}"
    return f"{val:.3f}"


def format_percent(val: float | None) -> str:
    """Format proportion as percentage with 1 decimal."""
    if val is None or math.isnan(val):
        return "N/A"
    pct = val * 100 if val <= 1.0 else val
    return f"{pct:.1f}%"


class FactRegistry:
    """Thread-safe registry of all facts and allowed numbers extracted for an analysis."""

    def __init__(self) -> None:
        self._facts_by_key: dict[str, Fact] = {}
        self._facts_by_finding: dict[str, list[Fact]] = {}
        self._allowed_numbers: list[AllowedNumber] = []
        self._string_tokens: set[str] = set()

    def add(self, fact: Fact, finding_id: str | None = None) -> None:
        self._facts_by_key[fact.key] = fact
        if finding_id:
            self._facts_by_finding.setdefault(finding_id, []).append(fact)

        # Register numeric representation if applicable
        if isinstance(fact.value, (int, float)) and not math.isnan(fact.value):
            # Compute tolerance based on precision
            val = float(fact.value)
            # Default tolerance: half of least significant displayed unit or 1e-3
            display_str = str(fact.display).replace(",", "").rstrip("%")
            if "." in display_str:
                num_decimals = len(display_str.split(".")[1])
                tolerance = 0.55 * (10 ** (-num_decimals))
            else:
                tolerance = 0.55
            self._allowed_numbers.append(
                AllowedNumber(
                    value=val,
                    display=fact.display,
                    tolerance=tolerance,
                    key=fact.key,
                    finding_id=finding_id,
                )
            )
        elif isinstance(fact.value, str):
            self._string_tokens.add(fact.value.lower())

    def add_many(self, facts: list[Fact], finding_id: str | None = None) -> None:
        for f in facts:
            self.add(f, finding_id=finding_id)

    def get(self, key: str) -> Fact | None:
        return self._facts_by_key.get(key)

    def for_finding(self, finding_id: str) -> list[Fact]:
        return self._facts_by_finding.get(finding_id, [])

    def allowed_numbers(self, finding_ids: list[str] | None = None) -> list[AllowedNumber]:
        if finding_ids is None:
            return list(self._allowed_numbers)
        fset = set(finding_ids)
        return [
            an for an in self._allowed_numbers if an.finding_id is None or an.finding_id in fset
        ]

    def string_tokens(self) -> set[str]:
        return set(self._string_tokens)

    def render(self, template: str, finding_id: str | None = None) -> str:
        """Substitute {fact_key} placeholders with exact display strings."""
        result = template
        # Find placeholders
        import re

        placeholders = re.findall(r"\{([a-zA-Z0-9_\.]+)\}", template)
        for ph in placeholders:
            lookup_key = ph
            if finding_id and not ph.startswith(f"{finding_id}."):
                scoped_key = f"{finding_id}.{ph}"
                fact = self._facts_by_key.get(scoped_key) or self._facts_by_key.get(ph)
            else:
                fact = self._facts_by_key.get(ph)
            if fact is not None:
                result = result.replace(f"{{{ph}}}", str(fact.display))
        return result


def build_facts(finding: Finding) -> list[Fact]:
    """Convert a Finding into an exhaustive list of traceable Fact items."""
    hid = finding.hypothesis.id
    res: TestResult = finding.test
    dec: ValidationDecision = finding.decision
    facts: list[Fact] = []

    def _f(key: str, val: Any, disp: str, source: str, unit: str | None = None) -> None:
        facts.append(
            Fact(
                key=f"{hid}.{key}",
                value=val,
                display=disp,
                unit=unit,
                source=source,
            )
        )

    # Identifiers & column names
    _f("col_a", finding.hypothesis.column_a, finding.hypothesis.column_a, "hypothesis.column_a")
    _f("col_b", finding.hypothesis.column_b, finding.hypothesis.column_b, "hypothesis.column_b")
    _f("numeric_col", finding.hypothesis.column_a, finding.hypothesis.column_a, "hypothesis.column_a")
    _f("group_col", finding.hypothesis.column_b, finding.hypothesis.column_b, "hypothesis.column_b")
    _f("relationship", finding.hypothesis.relationship.value, finding.hypothesis.relationship.value, "hypothesis.relationship")

    # Sample sizes
    _f("n_used", res.n_used, format_number(res.n_used), "test.n_used")
    if res.group_sizes:
        for grp, sz in res.group_sizes.items():
            _f(f"n_{grp}", sz, format_number(sz), f"test.group_sizes[{grp}]")

    # Test statistics
    _f("test_name", res.test_name, res.test_name, "test.test_name")
    if res.statistic is not None:
        _f("statistic", res.statistic, format_number(res.statistic), "test.statistic")
    if res.df is not None:
        _f("df", res.df, format_number(res.df), "test.df")
    if res.p_value is not None:
        _f("p_raw", res.p_value, format_p_value(res.p_value), "test.p_value")
        _f("p_value", res.p_value, format_p_value(res.p_value), "test.p_value")

    # Validation
    if dec.q_value is not None:
        _f("q_value", dec.q_value, format_q_value(dec.q_value), "decision.q_value")
        _f("q_display", dec.q_value, format_q_value(dec.q_value), "decision.q_value")
    _f("family_size", dec.family_size, format_number(dec.family_size), "decision.family_size")
    _f("alpha", 0.05, "0.05", "config.alpha")
    _f("alpha_pct", 5, "5%", "config.alpha")
    _f("accepted", str(dec.accepted), str(dec.accepted), "decision.accepted")

    # Effect size
    if res.effect is not None:
        eff = res.effect
        _f("effect_name", eff.name, eff.name, "effect.name")
        _f("effect_value", eff.value, format_effect(eff.value), "effect.value")
        _f("magnitude_label", eff.magnitude, eff.magnitude, "effect.magnitude")
        if eff.ci_low is not None:
            _f("ci_low", eff.ci_low, format_effect(eff.ci_low), "effect.ci_low")
        if eff.ci_high is not None:
            _f("ci_high", eff.ci_high, format_effect(eff.ci_high), "effect.ci_high")
        if eff.ci_low is not None and eff.ci_high is not None:
            _f("diff_ci_low", eff.ci_low, format_effect(eff.ci_low), "effect.ci_low")
            _f("diff_ci_high", eff.ci_high, format_effect(eff.ci_high), "effect.ci_high")

    # Descriptives
    desc = res.descriptives or {}
    for k, v in desc.items():
        if isinstance(v, (int, float)):
            disp = format_effect(v) if isinstance(v, float) else format_number(v)
            _f(f"desc_{k}", v, disp, f"test.descriptives.{k}")
            _f(k, v, disp, f"test.descriptives.{k}")
        elif isinstance(v, str):
            _f(f"desc_{k}", v, v, f"test.descriptives.{k}")
            _f(k, v, v, f"test.descriptives.{k}")

    # Helper differences and direction
    if "mean_diff" in desc:
        md = float(desc["mean_diff"])
        _f("mean_diff", md, format_number(md), "test.descriptives.mean_diff")
    if "r" in desc:
        r_val = float(desc["r"])
        _f("r", r_val, format_effect(r_val), "test.descriptives.r")
        _f("direction_observed", "positive" if r_val >= 0 else "negative", "positive" if r_val >= 0 else "negative", "derived")
    if "rho" in desc:
        rho_val = float(desc["rho"])
        _f("rho", rho_val, format_effect(rho_val), "test.descriptives.rho")
        _f("direction_observed", "positive" if rho_val >= 0 else "negative", "positive" if rho_val >= 0 else "negative", "derived")
    if "odds_ratio" in desc:
        _f("odds_ratio", desc["odds_ratio"], format_effect(float(desc["odds_ratio"])), "test.descriptives.odds_ratio")
    if "cramers_v" in desc:
        _f("cramers_v", desc["cramers_v"], format_effect(float(desc["cramers_v"])), "test.descriptives.cramers_v")

    return facts
