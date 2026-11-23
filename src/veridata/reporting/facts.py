"""Fact registry: the only numbers allowed in user-facing text (Phase 5, Section 3).

Every number shown in an explanation, chart title, table or report section is a ``Fact`` with a
raw ``value`` and the exact ``display`` string. Templates fill ``{key}`` placeholders through
:meth:`FactRegistry.render`; the number verifier only accepts numbers that match a fact.
"""

from __future__ import annotations

import math
import re
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from veridata.contracts.facts import Fact
from veridata.contracts.findings import Finding
from veridata.contracts.hypothesis import RelationshipType

# ---------------------------------------------------------------------------------------
# formatting rules (Section 3.2)
# ---------------------------------------------------------------------------------------


def fmt_p(v: float) -> str:
    """p- and q-values: '<0.001' below 0.001, else 3 decimals."""
    return "<0.001" if v < 0.001 else f"{v:.3f}"


def fmt_effect(v: float) -> str:
    """Effect sizes, correlations and CI bounds: 2 decimals (never '-0.00')."""
    s = f"{v:.2f}"
    return "0.00" if s == "-0.00" else s


def fmt_mean(v: float) -> str:
    """Means / medians / SDs / slopes: 2 decimals with thousands separators; 2 significant digits below 1."""
    if v == 0 or not math.isfinite(v):
        return "0"
    a = abs(v)
    if a >= 1:
        s = f"{v:,.2f}"
    else:
        d = -int(math.floor(math.log10(a))) + 1  # noqa: RUF046
        s = f"{v:.{d}f}"
    return s.replace("-0.00", "0.00")


def fmt_count(v: float) -> str:
    return f"{int(round(v)):,}"  # noqa: RUF046 (v may be a numpy float)


def fmt_pct(v: float) -> str:
    """Percent value already on the 0-100 scale: 1 decimal with '%'."""
    s = f"{v:.1f}%"
    return "0.0%" if s == "-0.0%" else s


def fmt_stat(v: float) -> str:
    return f"{v:,.2f}"


def fmt_df(v: float) -> str:
    return fmt_count(v) if float(v).is_integer() else f"{v:,.1f}"


FORMATTERS = {
    "p": fmt_p,
    "effect": fmt_effect,
    "mean": fmt_mean,
    "count": fmt_count,
    "pct": fmt_pct,
    "stat": fmt_stat,
    "df": fmt_df,
}

# Backwards-compatible aliases
format_p_value = fmt_p
format_q_value = fmt_p
format_effect = fmt_effect
format_number = fmt_mean
format_percent = fmt_pct


@dataclass(frozen=True)
class AllowedNumber:
    key: str
    value: float
    display: str
    decimals: int
    is_percent: bool
    is_upper_bound: bool  # display like '<0.001'


def display_decimals(display: str) -> int:
    m = re.search(r"\.(\d+)", display)
    return len(m.group(1)) if m else 0


class FactRegistry:
    """All facts of a report, namespaced per finding (``<finding_id>.<name>``)."""

    def __init__(self) -> None:
        self._facts: dict[str, Fact] = {}
        self._owner: dict[str, str] = {}

    # -- building -------------------------------------------------------------------
    def add(self, fact: Fact, owner: str = "report", *, finding_id: str | None = None) -> None:
        resolved_owner = finding_id if finding_id is not None else owner
        if fact.key in self._facts and self._facts[fact.key].display != fact.display:
            raise ValueError(f"fact {fact.key!r} registered twice with different displays")
        self._facts[fact.key] = fact
        self._owner[fact.key] = resolved_owner

    def add_many(
        self, facts: Iterable[Fact], owner: str = "report", *, finding_id: str | None = None
    ) -> None:
        resolved_owner = finding_id if finding_id is not None else owner
        for fact in facts:
            self.add(fact, resolved_owner)

    def num(
        self,
        owner: str,
        name: str,
        value: float,
        kind: str,
        source: str,
        unit: str | None = None,
    ) -> Fact:
        key = f"{owner}.{name}"
        disp = FORMATTERS[kind](value)
        f = Fact(
            key=key,
            value=float(value) if kind != "count" else int(round(value)),  # noqa: RUF046
            display=disp,
            unit=unit if unit else ("%" if kind == "pct" else None),
            source=source,
        )
        self.add(f, owner)
        return f

    def text(self, owner: str, name: str, value: str, source: str) -> Fact:
        key = f"{owner}.{name}"
        f = Fact(key=key, value=str(value), display=str(value), unit="text", source=source)
        self.add(f, owner)
        return f

    # -- reading --------------------------------------------------------------------
    def get(self, key: str) -> Fact:
        return self._facts[key]

    def has(self, key: str) -> bool:
        return key in self._facts

    def for_finding(self, finding_id: str) -> list[Fact]:
        return [f for k, f in self._facts.items() if self._owner[k] == finding_id]

    def all(self) -> list[Fact]:
        return list(self._facts.values())

    def owners(self) -> set[str]:
        return set(self._owner.values())

    def allowed_numbers(
        self, finding_ids: Iterable[str] | None = None, include_report: bool = True
    ) -> list[AllowedNumber]:
        ids = (
            None
            if finding_ids is None
            else set(finding_ids) | ({"report", "method", "summary"} if include_report else set())
        )
        out = []
        for k, f in self._facts.items():
            if ids is not None and self._owner[k] not in ids:
                continue
            if f.unit == "text" or not isinstance(f.value, (int, float)):
                continue
            out.append(
                AllowedNumber(
                    k,
                    float(f.value),
                    f.display,
                    display_decimals(f.display),
                    f.display.endswith("%"),
                    f.display.startswith("<"),
                )
            )
        return out

    def string_facts(self, finding_ids: Iterable[str] | None = None) -> list[str]:
        """Exact strings (column names, levels, names) that may contain digits without being numbers."""
        ids = None if finding_ids is None else set(finding_ids) | {"report", "method", "summary"}
        vals = {
            str(f.display)
            for k, f in self._facts.items()
            if f.unit == "text" and (ids is None or self._owner[k] in ids)
        }
        return sorted((v for v in vals if v), key=len, reverse=True)

    def string_tokens(self) -> set[str]:
        return {s.lower() for s in self.string_facts()}

    _PH = re.compile(r"\{([A-Za-z0-9_.:\-]+)\}")

    def render(self, template: str, finding_id: str | None = None) -> str:
        """Fill ``{key}`` (or ``{.name}`` = this finding's fact) placeholders; raises on a missing key."""

        def sub(m: re.Match[str]) -> str:
            k = m.group(1)
            if k.startswith(".") and finding_id:
                k = f"{finding_id}{k}"
            elif k not in self._facts and finding_id and f"{finding_id}.{k}" in self._facts:
                k = f"{finding_id}.{k}"
            if k not in self._facts:
                raise KeyError(f"template uses unknown fact {k!r}")
            return self._facts[k].display

        return self._PH.sub(sub, template)

    def facts_table_md(self, finding_id: str) -> str:
        rows = ["| Fact | Shown as | Comes from |", "| :--- | :--- | :--- |"]
        for f in sorted(self.for_finding(finding_id), key=lambda f: f.key):
            rows.append(f"| `{f.key.split('.', 1)[1]}` | {_cell(f.display)} | `{f.source}` |")
        return "\n".join(rows) + "\n"


def _cell(s: str) -> str:
    return s.replace("|", "\\|").replace("\n", " ")


# ---------------------------------------------------------------------------------------
# build_facts (Section 3.1)
# ---------------------------------------------------------------------------------------

EFFECT_LABELS = {
    "hedges_g": "Hedges' g",
    "rank_biserial": "rank-biserial correlation",
    "eta_squared": "eta squared",
    "epsilon_squared": "epsilon squared",
    "pearson_r": "Pearson r",
    "spearman_rho": "Spearman rho",
    "cramers_v_bc": "Cramér's V",
    "outlier_influence": "outlier influence",
}
TEST_LABELS = {
    "welch_t": "Welch's t-test",
    "mann_whitney_u": "Mann-Whitney U test",
    "welch_anova": "Welch's ANOVA",
    "kruskal_wallis": "Kruskal-Wallis test",
    "pearson": "Pearson correlation test",
    "spearman": "Spearman rank correlation test",
    "chi_square": "chi-square test of independence",
    "fisher_exact": "Fisher's exact test",
    "monte_carlo_chi_square": "Monte Carlo (permutation) chi-square test",
    "none": "no test (skipped)",
}


def finding_id(f: Finding) -> str:
    return f.hypothesis.id


def _groups(desc: dict[str, Any]) -> dict[str, dict[str, Any]]:
    g = desc.get("groups") or {}
    return g if isinstance(g, dict) else {}


def build_facts(
    f: Finding, reg: FactRegistry | None = None, *, alpha: float = 0.05
) -> list[Fact]:
    """Register every number/label of one finding that text, charts or tables may show."""
    if reg is None:
        reg = FactRegistry()
    fid = finding_id(f)
    h, t, d = f.hypothesis, f.test, f.decision
    src = "TestResult"
    reg.text(fid, "col_a", h.column_a, "Hypothesis.column_a")
    reg.text(fid, "col_b", h.column_b, "Hypothesis.column_b")
    reg.text(fid, "test_name", TEST_LABELS.get(t.test_name, t.test_name), f"{src}.test_name")
    if t.n_used:
        reg.num(fid, "n_used", t.n_used, "count", f"{src}.n_used")
    if t.statistic is not None and math.isfinite(t.statistic):
        reg.num(fid, "statistic", t.statistic, "stat", f"{src}.statistic")
    if isinstance(t.df, (int, float)) and math.isfinite(float(t.df)):
        reg.num(fid, "df", float(t.df), "df", f"{src}.df")
    elif isinstance(t.df, list) and len(t.df) == 2:
        reg.num(fid, "df1", float(t.df[0]), "df", f"{src}.df[0]")
        reg.num(fid, "df2", float(t.df[1]), "df", f"{src}.df[1]")
    if d.p_raw is not None and math.isfinite(d.p_raw):
        reg.num(fid, "p_raw", d.p_raw, "p", "ValidationDecision.p_raw")
    if d.q_value is not None and math.isfinite(d.q_value):
        reg.num(fid, "q_value", d.q_value, "p", "ValidationDecision.q_value")
    if d.family_size:
        reg.num(fid, "family_size", d.family_size, "count", "ValidationDecision.family_size")
    if t.group_sizes:
        reg.num(fid, "n_groups", len(t.group_sizes), "count", "len(TestResult.group_sizes)")
    e = t.effect
    if e is not None:
        reg.text(fid, "effect_name", EFFECT_LABELS.get(e.name, e.name), "TestResult.effect.name")
        reg.num(fid, "effect_value", e.value, "effect", "TestResult.effect.value")
        reg.num(fid, "effect_abs", abs(e.value), "effect", "abs(TestResult.effect.value)")
        reg.text(fid, "magnitude_label", e.magnitude, "TestResult.effect.magnitude")
        if e.ci_low is not None and e.ci_high is not None:
            reg.num(fid, "ci_low", e.ci_low, "effect", "TestResult.effect.ci_low")
            reg.num(fid, "ci_high", e.ci_high, "effect", "TestResult.effect.ci_high")
        if e.comparable_value is not None:
            reg.num(
                fid,
                "comparable_value",
                e.comparable_value,
                "effect",
                "TestResult.effect.comparable_value",
            )
        if e.name in {"eta_squared", "epsilon_squared"}:
            reg.num(
                fid,
                "eta_sq_pct",
                100 * e.value,
                "pct",
                f"100 * TestResult.effect.value ({e.name})",
            )
    desc = t.descriptives or {}
    rel = h.relationship
    groups = _groups(desc)
    order = [str(x) for x in desc.get("group_order", list(groups))]
    for i, lbl in enumerate(order, start=1):
        g = groups.get(lbl) or groups.get(str(lbl)) or {}
        reg.text(fid, f"g{i}", lbl, f"TestResult.descriptives.group_order[{i - 1}]")
        if "n" in g:
            reg.num(fid, f"n_g{i}", g["n"], "count", f"TestResult.descriptives.groups[{lbl}].n")
        for stat in ("mean", "median", "sd"):
            if stat in g and g[stat] is not None:
                reg.num(
                    fid,
                    f"{stat}_g{i}",
                    g[stat],
                    "mean",
                    f"TestResult.descriptives.groups[{lbl}].{stat}",
                )
    for key, nm in (
        ("higher_group", "higher_group"),
        ("highest_group", "highest_group"),
        ("lowest_group", "lowest_group"),
    ):
        if desc.get(key) is not None:
            reg.text(fid, nm, str(desc[key]), f"TestResult.descriptives.{key}")
    if rel in {RelationshipType.NUM_BINARY, RelationshipType.NUM_CATEGORICAL} and order:
        hg = str(desc.get("higher_group") or desc.get("highest_group") or "")
        if hg in order:
            i = order.index(hg) + 1
            reg.text(
                fid,
                "other_group",
                order[1] if i == 1 and len(order) > 1 else order[0],
                "the other group in TestResult.descriptives.group_order",
            )
            for stat in ("mean", "median"):
                if reg.has(f"{fid}.{stat}_g{i}"):
                    reg.add(_alias(reg, f"{fid}.{stat}_g{i}", f"{fid}.{stat}_high"), fid)
                    j = 2 if i == 1 else 1
                    if reg.has(f"{fid}.{stat}_g{j}") and len(order) == 2:
                        reg.add(_alias(reg, f"{fid}.{stat}_g{j}", f"{fid}.{stat}_other"), fid)
        lg = str(desc.get("lowest_group") or "")
        if lg in order:
            i = order.index(lg) + 1
            for stat in ("mean", "median"):
                if reg.has(f"{fid}.{stat}_g{i}"):
                    reg.add(_alias(reg, f"{fid}.{stat}_g{i}", f"{fid}.{stat}_low"), fid)
    for key, kind in (
        ("mean_diff", "mean"),
        ("mean_diff_ci_low", "mean"),
        ("mean_diff_ci_high", "mean"),
        ("probability_of_superiority", "effect"),
        ("hodges_lehmann_shift", "mean"),
        ("ols_slope", "mean"),
        ("omega_squared", "effect"),
    ):
        v = desc.get(key)
        if isinstance(v, (int, float)) and math.isfinite(float(v)):
            reg.num(fid, key, float(v), kind, f"TestResult.descriptives.{key}")
    if "mean_diff" in desc and isinstance(desc["mean_diff"], (int, float)):
        reg.num(
            fid,
            "mean_diff_abs",
            abs(float(desc["mean_diff"])),
            "mean",
            "abs(TestResult.descriptives.mean_diff)",
        )
    if "probability_of_superiority" in desc and isinstance(
        desc["probability_of_superiority"], (int, float)
    ):
        ps = float(desc["probability_of_superiority"])
        reg.num(
            fid,
            "prob_sup_high",
            max(ps, 1 - ps),
            "effect",
            "max(P(superiority), 1 - P(superiority))",
        )
    for key in ("fisher_odds_ratio", "odds_ratio", "odds_ratio_ci_low", "odds_ratio_ci_high"):
        v = desc.get(key)
        if isinstance(v, (int, float)) and math.isfinite(float(v)):
            reg.num(fid, key, float(v), "effect", f"TestResult.descriptives.{key}")
    cells = desc.get("top_residual_cells") or []
    for i, c in enumerate(cells[:2], start=1):
        if not isinstance(c, dict):
            continue
        reg.text(
            fid, f"cell{i}_row", str(c.get("row")), f"TestResult.descriptives.top_residual_cells[{i - 1}].row"
        )
        reg.text(
            fid, f"cell{i}_col", str(c.get("col")), f"TestResult.descriptives.top_residual_cells[{i - 1}].col"
        )
        obs, exp = c.get("observed"), c.get("expected")
        if isinstance(obs, (int, float)):
            reg.num(
                fid,
                f"cell{i}_observed",
                obs,
                "count",
                f"TestResult.descriptives.top_residual_cells[{i - 1}].observed",
            )
        if isinstance(exp, (int, float)):
            reg.num(
                fid,
                f"cell{i}_expected",
                exp,
                "mean",
                f"TestResult.descriptives.top_residual_cells[{i - 1}].expected",
            )
        if isinstance(obs, (int, float)) and isinstance(exp, (int, float)):
            reg.text(
                fid,
                f"cell{i}_more_or_fewer",
                "more" if obs > exp else "fewer",
                "observed vs expected count",
            )
    if isinstance(desc.get("row_labels"), list) and isinstance(desc.get("col_labels"), list):
        reg.num(
            fid,
            "n_rows_table",
            len(desc["row_labels"]),
            "count",
            "len(TestResult.descriptives.row_labels)",
        )
        reg.num(
            fid,
            "n_cols_table",
            len(desc["col_labels"]),
            "count",
            "len(TestResult.descriptives.col_labels)",
        )
        for i, lbl in enumerate(desc["row_labels"]):
            reg.text(fid, f"row_label{i}", str(lbl), f"TestResult.descriptives.row_labels[{i}]")
        for i, lbl in enumerate(desc["col_labels"]):
            reg.text(fid, f"col_label{i}", str(lbl), f"TestResult.descriptives.col_labels[{i}]")
    for i, lvl in enumerate(desc.get("dropped_levels") or []):
        reg.text(fid, f"dropped_level{i}", str(lvl), f"TestResult.descriptives.dropped_levels[{i}]")
    if t.group_sizes:
        for i, (lbl, n) in enumerate(t.group_sizes.items()):
            reg.text(fid, f"group_label{i}", str(lbl), f"TestResult.group_sizes key {i}")
            reg.num(fid, f"group_size{i}", n, "count", f"TestResult.group_sizes[{lbl}]")
    if "sensitivity_alt_test" in desc and isinstance(desc["sensitivity_alt_test"], dict):
        alt = desc["sensitivity_alt_test"]
        reg.text(
            fid,
            "alt_test_name",
            TEST_LABELS.get(str(alt.get("test_name")), str(alt.get("test_name"))),
            "TestResult.descriptives.sensitivity_alt_test.test_name",
        )
        if isinstance(alt.get("effect_value"), (int, float)):
            reg.num(
                fid,
                "alt_effect_value",
                float(alt["effect_value"]),
                "effect",
                "TestResult.descriptives.sensitivity_alt_test.effect_value",
            )
    reg.text(fid, "direction_word", _direction_word(f), "TestResult.direction_observed")
    return reg.for_finding(fid)


def _alias(reg: FactRegistry, src_key: str, new_key: str) -> Fact:
    s = reg.get(src_key)
    return Fact(
        key=new_key,
        value=s.value,
        display=s.display,
        unit=s.unit,
        source=f"same as {src_key.split('.', 1)[1]}",
    )


def _direction_word(f: Finding) -> str:
    d = f.test.direction_observed
    if d is None:
        return "none"
    return {
        "positive": "positive",
        "negative": "negative",
        "a_greater": "a_greater",
        "b_greater": "b_greater",
    }.get(d.value, "any")


def build_method_facts(reg: FactRegistry, config: Any) -> None:
    """Thresholds and settings quoted in the Methods section."""
    s, fl = config.stats, config.effect_floor
    reg.num("method", "alpha", s.alpha, "effect", "config.stats.alpha")
    reg.num("method", "alpha_pct", 100 * s.alpha, "pct", "100 * config.stats.alpha")
    reg.num("method", "ci_level_pct", 95, "pct", "fixed 95% confidence level")
    reg.num("method", "min_n_pairwise", s.min_n_pairwise, "count", "config.stats.min_n_pairwise")
    reg.num("method", "min_group_n", s.min_group_n, "count", "config.stats.min_group_n")
    reg.num(
        "method",
        "min_expected",
        s.min_expected_count_chi2,
        "count",
        "config.stats.min_expected_count_chi2",
    )
    reg.num("method", "large_n_clt", s.large_n_clt, "count", "config.stats.large_n_clt")
    reg.num("method", "extreme_skew", s.extreme_skew, "effect", "config.stats.extreme_skew")
    reg.num(
        "method",
        "bootstrap_resamples",
        s.bootstrap_resamples,
        "count",
        "config.stats.bootstrap_resamples",
    )
    reg.num(
        "method",
        "permutation_resamples",
        s.permutation_resamples,
        "count",
        "config.stats.permutation_resamples",
    )
    for name in (
        "cohens_d",
        "rank_biserial",
        "correlation",
        "eta_squared",
        "epsilon_squared",
        "cramers_v_df1",
    ):
        reg.num(
            "method", f"floor_{name}", getattr(fl, name), "effect", f"config.effect_floor.{name}"
        )
    reg.text(
        "method",
        "correction_name",
        {
            "bh": "Benjamini-Hochberg",
            "by": "Benjamini-Yekutieli",
            "holm": "Holm",
            "bonferroni": "Bonferroni",
            "none": "no",
        }[s.correction],
        "config.stats.correction",
    )
