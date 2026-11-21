"""Phase 5: fact formatting, templates, number verifier (adversarial + fuzz) and language linter."""

from __future__ import annotations

import json
import random
import re
from pathlib import Path

import pytest

from veridata.config import load_config
from veridata.contracts.facts import Fact
from veridata.contracts.findings import Finding
from veridata.reporting.facts import (
    FactRegistry,
    build_facts,
    build_method_facts,
    finding_id,
    fmt_count,
    fmt_effect,
    fmt_mean,
    fmt_p,
    fmt_pct,
)
from veridata.reporting.language_lint import lint_text
from veridata.reporting.number_verifier import verify_text
from veridata.reporting.templates import explain_accepted, explain_rejected

ROOT = Path(__file__).resolve().parents[2]
SAMPLE = json.loads((ROOT / "tests" / "fixtures" / "phase5_findings_sample.json").read_text(encoding="utf-8"))
ALL = [(ds, Finding.model_validate(x)) for ds, items in SAMPLE.items() for x in items]


def _registry(findings: list[Finding]) -> FactRegistry:
    reg = FactRegistry()
    build_method_facts(reg, load_config())
    for f in findings:
        build_facts(f, reg)
    return reg


# ---------------------------------------------------------------------------------------
# formatting + registry
# ---------------------------------------------------------------------------------------


def test_formatting_rules() -> None:
    assert fmt_p(0.0004) == "<0.001" and fmt_p(0.01234) == "0.012"
    assert fmt_effect(0.4251) == "0.43" and fmt_effect(-0.001) == "0.00"
    assert fmt_mean(13270.4231) == "13,270.42" and fmt_mean(0.004321) == "0.0043" and fmt_mean(0) == "0"
    assert fmt_count(1338) == "1,338"
    assert fmt_pct(12.345) == "12.3%"


def test_registry_render_and_missing_key() -> None:
    reg = FactRegistry()
    reg.num("f1", "r", 0.4237, "effect", "test")
    assert reg.render("r = {.r}", "f1") == "r = 0.42"
    with pytest.raises(KeyError):
        reg.render("{.missing}", "f1")
    with pytest.raises(ValueError):
        reg.add(Fact(key="f1.r", value=0.5, display="0.50", source="x"), "f1")


# ---------------------------------------------------------------------------------------
# templates: every real finding verifies and lints at 100%
# ---------------------------------------------------------------------------------------


@pytest.mark.parametrize("ds,f", ALL, ids=[f"{ds}-{f.test.test_name}-{i}" for i, (ds, f) in enumerate(ALL)])
def test_template_text_verifies_and_lints(ds: str, f: Finding) -> None:
    reg = _registry([g for d, g in ALL if d == ds])
    fid = finding_id(f)
    text = explain_accepted(f, reg).text if f.decision.accepted else explain_rejected(f, reg)
    v = verify_text(text, reg, [fid])
    assert v.ok, (v.message(), text)
    issues = lint_text(text, f, kind="finding" if f.decision.accepted else "rejected")
    assert not issues, ([i.code for i in issues], text)


def test_every_test_path_is_covered_by_the_fixture() -> None:
    names = {f.test.test_name for _, f in ALL}
    assert {"welch_t", "mann_whitney_u", "welch_anova", "kruskal_wallis", "spearman", "chi_square", "monte_carlo_chi_square"} <= names
    reasons = {r.value for _, f in ALL for r in f.decision.reasons}
    assert {"not_significant_after_correction", "effect_below_threshold", "insufficient_data"} <= reasons


def test_templates_never_format_numbers_themselves() -> None:
    """Pitfall 8: no numeric format specs or round() in templates.py; numbers only via registry.render."""
    src = (ROOT / "src" / "veridata" / "reporting" / "templates.py").read_text(encoding="utf-8")
    assert not re.search(r"\{[^{}]*:[^{}]*[.,][0-9]*[fdeg%]\}", src)
    assert "round(" not in src and "%.2f" not in src and "format(" not in src


# ---------------------------------------------------------------------------------------
# verifier: adversarial cases (Section 6.4)
# ---------------------------------------------------------------------------------------


@pytest.fixture()
def reg2() -> FactRegistry:
    reg = FactRegistry()
    reg.num("A", "r", 0.4237, "effect", "x")
    reg.num("A", "n", 1338, "count", "x")
    reg.num("A", "pct", 12.34, "pct", "x")
    reg.num("A", "p", 0.0002, "p", "x")
    reg.num("A", "q", 0.0312, "p", "x")
    reg.num("A", "ci_low", -0.31, "effect", "x")
    reg.num("A", "ci_high", 0.12, "effect", "x")
    reg.text("A", "col", "age_2", "x")
    reg.text("A", "level", "65+", "x")
    reg.text("A", "col2", "v07", "x")
    reg.num("B", "r", 0.91, "effect", "x")
    reg.num("method", "ci", 95, "pct", "x")
    return reg


@pytest.mark.parametrize(
    "text",
    [
        "r = 0.42 and n = 1,338.",
        "r = .42 with n = 1338 records.",
        "12.3% of rows; adjusted p 0.031; raw p <0.001.",
        "95% CI -0.31 to 0.12.",
        "95% CI −0.31–0.12.",  # unicode minus and en-dash range
        "Column age_2 at level 65+ and v07.",  # digits inside identifiers / labels
        "1. first item\n2. second item\n## 3. Heading",  # list and heading numbers
        "![chart](figures/f01_x_2.png)",  # link target ignored
    ],
)
def test_verifier_accepts_registered_numbers(reg2: FactRegistry, text: str) -> None:
    v = verify_text(text, reg2, ["A"])
    assert v.ok, v.message()


@pytest.mark.parametrize(
    "text,reason",
    [
        ("r = 0.57", "not_in_registry"),  # fabricated
        ("r = 0.43", "precision_mismatch"),  # rounded differently
        ("about three times higher", "number_word"),  # number word
        ("twice as large", "number_word"),
        ("a 1.5 times bigger effect", "derived_number"),
        ("12.3 percent of 1338", None),  # allowed (percent word)
        ("p = 3e-5", "not_in_registry"),  # scientific notation
        ("p = 3.2×10^-4", "not_in_registry"),
        ("from 0.10 to 0.30", "not_in_registry"),  # range of unregistered numbers
        ("r = 0.91", "not_in_registry"),  # another finding's fact (cross-finding leakage)
        ("n = ١٣٣٨", "non_ascii_digit"),  # Arabic-Indic digits
        ("a 13% share", "any"),  # 12.3% registered: a rounded-off value is still a violation
        ("a share of 0.123", "any"),  # no fraction <-> percent conversion (decision P5-04)
        ("r = 0.95", "not_in_registry"),  # must not borrow the 95% confidence level
        ("r = 0.424", None),  # correct rounding of the real value 0.4237 at finer precision
        ("r = 0.421", "precision_mismatch"),  # finer precision but wrong rounding
        ("r = 42%", "not_in_registry"),  # an effect size written as a percent
        ("in 2024", "not_in_registry"),  # years are not allowed by default
    ],
)
def test_verifier_rejects_bad_numbers(reg2: FactRegistry, text: str, reason: str | None) -> None:
    v = verify_text(text, reg2, ["A"])
    if reason is None:
        assert v.ok, v.message()
    else:
        assert not v.ok, text
        assert reason == "any" or reason in {x.reason for x in v.violations}, (text, v.message())


def test_verifier_fuzz_detects_inserted_numbers(reg2: FactRegistry) -> None:
    base = "The average was higher for the group (r = 0.42, n = 1,338, adjusted p 0.031)."
    rng = random.Random(0)
    allowed = {"0.42", "1338", "0.031"}
    caught = total = 0
    for _ in range(500):
        num = rng.choice([f"{rng.uniform(-50, 50):.2f}", f"{rng.randint(2, 99999):,}", f"{rng.uniform(0, 1):.3f}", f"{rng.uniform(0, 100):.1f}%"])
        if num.replace(",", "") in allowed:
            continue
        words = base.split(" ")
        pos = rng.randint(0, len(words))
        text = " ".join(words[:pos] + [num] + words[pos:])
        total += 1
        caught += 0 if verify_text(text, reg2, ["A"]).ok else 1
    assert caught / total >= 0.99


# ---------------------------------------------------------------------------------------
# language linter
# ---------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text,code",
    [
        ("Smoking causes higher charges.", "causal_language"),
        ("Age leads to higher charges.", "causal_language"),
        ("Charges are driven by smoking.", "causal_language"),
        ("This proves that smokers pay more.", "overclaim"),
        ("The difference is significant.", "bare_significant"),
        ("Smoking significantly increases charges.", "bare_significant"),
    ],
)
def test_lint_flags_bad_wording(text: str, code: str) -> None:
    assert code in {i.code for i in lint_text(text)}


@pytest.mark.parametrize(
    "text",
    [
        "This is an association, not evidence of cause and effect.",
        "It does not show that smoking causes the difference.",
        "Smokers have higher charges on average; the association is statistically supported.",
        "The result is statistically significant after correction.",
    ],
)
def test_lint_allows_safe_wording(text: str) -> None:
    assert lint_text(text) == []


def test_lint_direction_and_mwu_rules() -> None:
    ff = {f.test.test_name: f for _, f in ALL if f.decision.accepted}
    sp = ff["spearman"]
    bad = sp.model_copy(deep=True)
    word = "negatively" if sp.test.direction_observed.value == "positive" else "positively"
    assert "direction_mismatch" in {i.code for i in lint_text(f"x and y are {word} associated after correcting for tests.", bad)}
    wt = ff["welch_t"]
    order = wt.test.descriptives["group_order"]
    wrong = next(g for g in order if g != wt.test.descriptives["higher_group"])
    txt = f"On average, {wt.hypothesis.column_a} is higher for {wt.hypothesis.column_b} = {wrong}. After correcting for tests it is associated."
    assert "direction_mismatch" in {i.code for i in lint_text(txt, wt)}
    mw = next(f for _, f in ALL if f.test.test_name == "mann_whitney_u")
    assert "mwu_means" in {i.code for i in lint_text("The means differ; associated after correcting.", mw)}
    assert "missing_qualifier" in {i.code for i in lint_text("x differs by y. After correcting for tests.", wt)}
