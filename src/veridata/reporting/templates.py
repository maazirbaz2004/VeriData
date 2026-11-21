"""Deterministic explanation templates (Phase 5, Section 4) — always available, no LLM.

Every number reaches the text through ``FactRegistry.render`` placeholders such as ``{.mean_g1}``
(``.name`` = a fact of the current finding) or ``{method.alpha_pct}``. This module never formats
a number itself (enforced by a grep test).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from veridata.contracts.findings import Finding
from veridata.contracts.hypothesis import Direction, RelationshipType
from veridata.contracts.validation import RejectionReason
from veridata.reporting.facts import FactRegistry, finding_id

RANK_TESTS = {"mann_whitney_u", "kruskal_wallis", "spearman"}
FLOOR_FACT = {
    "hedges_g": "floor_cohens_d",
    "rank_biserial": "floor_rank_biserial",
    "pearson_r": "floor_correlation",
    "spearman_rho": "floor_correlation",
    "eta_squared": "floor_eta_squared",
    "epsilon_squared": "floor_epsilon_squared",
    "cramers_v_bc": "floor_cramers_v_df1",
}


@dataclass
class TemplateText:
    result: str
    magnitude: str = ""
    correction: str = ""
    caveats: list[str] = field(default_factory=list)
    required_caveats: list[str] = field(default_factory=list)

    @property
    def text(self) -> str:
        return " ".join(p for p in [self.result, self.magnitude, self.correction, *self.caveats] if p)


class _T:
    """Small helper: render with this finding's facts, choosing variants by fact availability."""

    def __init__(self, f: Finding, reg: FactRegistry):
        self.f, self.reg, self.fid = f, reg, finding_id(f)

    def has(self, *names: str) -> bool:
        return all(self.reg.has(f"{self.fid}.{n}") for n in names)

    def r(self, template: str) -> str:
        return self.reg.render(template, self.fid)

    def p_phrase(self, name: str) -> str:
        """'= 0.012' or '<0.001' (the display already carries the '<')."""
        disp = self.reg.get(f"{self.fid}.{name}").display
        return disp if disp.startswith("<") else "= " + disp


def _correction(t: _T) -> str:
    if not t.has("q_value", "family_size"):
        return ""
    return t.r("After correcting for {.family_size} tests ({method.correction_name} method, false discovery rate {method.alpha_pct}), the association is statistically supported (adjusted p ") + t.p_phrase("q_value") + ")."


def _ci(t: _T) -> str:
    return t.r(", 95% CI {.ci_low} to {.ci_high}") if t.has("ci_low", "ci_high") else ""


def _caveats(t: _T) -> list[str]:
    f = t.f
    out = []
    flags = set(f.decision.flags)
    if f.test.test_name in RANK_TESTS and f.test.fallback_used:
        out.append("The data were not close enough to the shape a parametric test needs, so a rank-based test was used instead.")
    if f.test.test_name == "monte_carlo_chi_square":
        out.append("Some table cells had few records, so the p-value comes from a simulation (permutation) test.")
    if "test_sensitive" in flags and t.has("alt_test_name"):
        out.append(t.r("A second test ({.alt_test_name}) did not fully agree, so treat this result with some caution."))
    if "fragile_to_outliers" in flags:
        out.append("The result changes noticeably when the most extreme values are left out, so it may rest on a few outliers.")
    if "small_n" in flags and t.has("n_used"):
        out.append(t.r("The sample is small ({.n_used} records), so the size of the effect is uncertain."))
    dropped = [k for k in ("dropped_level0", "dropped_level1", "dropped_level2") if t.has(k)]
    if dropped:
        names = ", ".join(t.r("{." + k + "}") for k in dropped)
        out.append(t.r("Rare levels with fewer than {method.min_group_n} records were left out of this test (") + names + ").")
    return out


def _num_binary(t: _T) -> TemplateText:
    tn = t.f.test.test_name
    if tn == "mann_whitney_u" and t.has("higher_group", "other_group"):
        res = t.r("Values of {.col_a} tended to be higher for {.col_b} = {.higher_group} than for {.col_b} = {.other_group}")
        if t.has("median_high", "median_other"):
            res += t.r(" (median {.median_high} vs {.median_other})")
        res += "."
        if t.has("prob_sup_high"):
            res += t.r(" The chance that a random {.higher_group} record has a higher {.col_a} than a random {.other_group} record is {.prob_sup_high}.")
        mag = t.r("The difference is {.magnitude_label} (rank-biserial correlation = {.effect_value}" + _ci(t) + ").") if t.has("effect_value") else ""
        return TemplateText(res, mag, _correction(t), _caveats(t))
    # Welch's t (means)
    if t.has("mean_g1", "mean_g2", "g1", "g2"):
        res = t.r("Among {.n_used} records, the average {.col_a} was {.mean_g1} for {.col_b} = {.g1} and {.mean_g2} for {.col_b} = {.g2}")
        if t.has("mean_diff", "mean_diff_ci_low", "mean_diff_ci_high"):
            res += t.r(" (difference {.mean_diff}, 95% CI {.mean_diff_ci_low} to {.mean_diff_ci_high})")
        elif t.has("mean_diff"):
            res += t.r(" (difference {.mean_diff})")
        res += "."
        if t.has("higher_group"):
            res += t.r(" On average, {.col_a} is higher for {.col_b} = {.higher_group}.")
    else:
        res = t.r("{.col_a} is associated with the groups of {.col_b}.")
    mag = t.r("The difference is {.magnitude_label} (Hedges' g = {.effect_value}" + _ci(t) + ").") if t.has("effect_value") else ""
    return TemplateText(res, mag, _correction(t), _caveats(t))


def _num_categorical(t: _T) -> TemplateText:
    tn = t.f.test.test_name
    stat = "median" if tn == "kruskal_wallis" else "mean"
    if t.has("highest_group", "lowest_group", f"{stat}_high", f"{stat}_low"):
        lead = "Values of {.col_a} tend to differ" if stat == "median" else "The average {.col_a} differs"
        groups = " across the {.n_groups} groups of {.col_b}" if t.has("n_groups") else " across the groups of {.col_b}"
        res = t.r(lead + groups + ": highest for {.highest_group} (" + stat + " {." + stat + "_high}) and lowest for {.lowest_group} (" + stat + " {." + stat + "_low}).")
    else:
        res = t.r("{.col_a} tends to differ across the groups of {.col_b}, so these columns are associated.")
    mag = ""
    if t.has("eta_sq_pct", "effect_value"):
        scale = "the ranks of " if stat == "median" else ""
        mag = t.r("About {.eta_sq_pct} of the variation in " + scale + "{.col_a} is associated with {.col_b} ({.effect_name} = {.effect_value}" + _ci(t) + ", {.magnitude_label}).")
    return TemplateText(res, mag, _correction(t), _caveats(t))


def _num_num(t: _T) -> TemplateText:
    d = t.f.test.direction_observed
    word = "positively" if d == Direction.POSITIVE else ("negatively" if d == Direction.NEGATIVE else "")
    if t.f.test.test_name == "pearson":
        res = t.r("{.col_a} and {.col_b} are " + word + " associated (Pearson r = {.effect_value}" + _ci(t) + "; n = {.n_used}).")
        if t.has("ols_slope"):
            res += t.r(" Along the fitted straight line, each extra unit of {.col_a} corresponds to {.ols_slope} units of {.col_b} on average.")
    else:
        res = t.r("{.col_a} and {.col_b} are " + word + " associated (Spearman rank correlation rho = {.effect_value}" + _ci(t) + "; n = {.n_used}). The relationship is monotonic and may not be linear.")
    mag = t.r("The association is {.magnitude_label}.") if t.has("magnitude_label") else ""
    return TemplateText(res.replace("are  associated", "are associated"), mag, _correction(t), _caveats(t))


def _cat_cat(t: _T) -> TemplateText:
    res = t.r("{.col_a} and {.col_b} are associated (Cramér's V = {.effect_value}" + _ci(t) + ", {.magnitude_label}; n = {.n_used}).")
    if t.has("cell1_row", "cell1_col", "cell1_observed", "cell1_expected", "cell1_more_or_fewer"):
        res += t.r(" The largest departure from independence: {.cell1_more_or_fewer} records with {.col_a} = {.cell1_row} and {.col_b} = {.cell1_col} than expected if the columns were unrelated ({.cell1_observed} observed vs {.cell1_expected} expected).")
    if t.has("odds_ratio", "odds_ratio_ci_low", "odds_ratio_ci_high"):
        res += t.r(" The odds ratio is {.odds_ratio} (95% CI {.odds_ratio_ci_low} to {.odds_ratio_ci_high}).")
    return TemplateText(res, "", _correction(t), _caveats(t))


def explain_accepted(f: Finding, reg: FactRegistry) -> TemplateText:
    t = _T(f, reg)
    rel = f.hypothesis.relationship
    tn = f.test.test_name
    # Route by the test that actually ran: a categorical column collapsed to 2 groups uses a 2-group test.
    if tn in {"welch_t", "mann_whitney_u"}:
        out = _num_binary(t)
    elif tn in {"welch_anova", "kruskal_wallis"}:
        out = _num_categorical(t)
    elif tn in {"pearson", "spearman"} or rel in {RelationshipType.NUM_NUM, RelationshipType.NUM_NUM_NONLINEAR}:
        out = _num_num(t)
    else:
        out = _cat_cat(t)
    out.caveats.append("This is an association, not evidence of cause and effect.")
    out.required_caveats = list(out.caveats)
    return out


def explain_rejected(f: Finding, reg: FactRegistry) -> str:
    t = _T(f, reg)
    parts: list[str] = []
    reasons = list(f.decision.reasons)
    if RejectionReason.TRIVIAL_RELATIONSHIP in reasons and t.has("effect_name", "effect_value"):
        return t.r("These columns appear to be derived from each other or to measure the same thing ({.effect_name} = {.effect_value}); this is a data-structure observation, not a discovery.")
    for r in reasons:
        if r == RejectionReason.NOT_SIGNIFICANT_AFTER_CORRECTION and t.has("p_raw", "q_value", "family_size"):
            parts.append("Raw p " + t.p_phrase("p_raw") + t.r(", but after correcting for {.family_size} tests the adjusted p is ") + t.reg.get(f"{t.fid}.q_value").display + ". With this many comparisons, a pattern like this is expected by chance, so it is not reported as a finding.")
        elif r == RejectionReason.EFFECT_BELOW_THRESHOLD and t.has("effect_name", "effect_value"):
            e = f.test.effect
            floor = FLOOR_FACT.get(e.name if e else "", "")
            floor_txt = t.r(", below the {method." + floor + "} threshold") if floor and t.reg.has(f"method.{floor}") else ""
            comp = t.r(" (comparable value {.comparable_value})") if e is not None and e.name == "cramers_v_bc" and t.has("comparable_value") else ""
            lead = "Statistically detectable" if RejectionReason.NOT_SIGNIFICANT_AFTER_CORRECTION not in reasons else "Also, the effect is tiny"
            if lead.startswith("Statistically") and t.has("q_value"):
                lead += " (adjusted p " + t.p_phrase("q_value") + ")"
            parts.append(lead + t.r(" but the effect is negligible ({.effect_name} = {.effect_value}") + comp + floor_txt + "), so it has little practical importance.")
        elif r == RejectionReason.ASSUMPTION_VIOLATED:
            parts.append("The assumptions of the available tests were not met and no safe alternative test exists, so no conclusion is drawn.")
        elif r == RejectionReason.INSUFFICIENT_DATA:
            parts.append("There were not enough usable records, or some groups were too small, to run a reliable test.")
        elif r == RejectionReason.DEGENERATE_DATA:
            parts.append("One of the columns had almost no variation in the records used, so no meaningful test was possible.")
        elif r == RejectionReason.TEST_ERROR:
            parts.append("The test could not be completed because of a computation problem.")
        elif r == RejectionReason.UNSTABLE_CI and t.has("ci_low", "ci_high"):
            parts.append(t.r("The 95% confidence interval for the effect ({.ci_low} to {.ci_high}) includes zero, so even the direction of the effect is not stable."))
    return " ".join(parts) or "Not reported as a finding."


SELECTION_PLAIN = {
    "welch_t": "Both groups looked close enough to normal (or were large enough), so the means were compared with Welch's t-test, which does not assume equal spreads.",
    "mann_whitney_u": "The groups were not close enough to normal, so a rank-based Mann-Whitney U test was used; it compares typical values without assuming a bell shape.",
    "welch_anova": "All groups looked close enough to normal (or were large enough), so the group means were compared with Welch's ANOVA, which does not assume equal spreads.",
    "kruskal_wallis": "Some groups were not close enough to normal, so the rank-based Kruskal-Wallis test was used.",
    "pearson": "Both columns looked close enough to normal without strong outliers, so the straight-line Pearson correlation was used.",
    "spearman": "The columns were skewed, had outliers or many ties, so the rank-based Spearman correlation was used.",
    "chi_square": "Every cell of the table had enough expected records, so the standard chi-square test of independence was used.",
    "fisher_exact": "The table had small expected counts, so Fisher's exact test was used.",
    "monte_carlo_chi_square": "Some table cells had too few expected records for the usual chi-square formula, so the p-value was computed by simulation (permutation).",
}


def how_tested(f: Finding) -> str:
    return SELECTION_PLAIN.get(f.test.test_name, "The test was chosen by the fixed selection rules described in the Methods section.")
