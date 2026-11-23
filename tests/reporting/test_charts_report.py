"""Phase 5: charts (all types + edge cases, deterministic), report builder, final gate, HTML, CLI."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from veridata.cli import main
from veridata.config import load_config
from veridata.contracts.findings import Finding
from veridata.errors import ReportingError
from veridata.reporting import report_builder as rb
from veridata.reporting.charts import plot_finding
from veridata.reporting.facts import FactRegistry, build_facts, build_method_facts
from veridata.reporting.report_builder import build_report

ROOT = Path(__file__).resolve().parents[2]
SAMPLE = json.loads((ROOT / "tests" / "fixtures" / "phase5_findings_sample.json").read_text(encoding="utf-8"))


def _df(ds: str) -> pd.DataFrame:
    return pd.read_csv(ROOT / "data" / "cleaned" / f"{ds}_cleaned.csv")


def _one(ds: str, test: str) -> Finding:
    """First finding of this test type in ``ds`` (validated ones first)."""
    items = sorted((x for x in SAMPLE[ds] if x["test"]["test_name"] == test), key=lambda x: not x["decision"]["accepted"])
    return Finding.model_validate(items[0])


def _any(test: str) -> tuple[str, Finding]:
    for ds in SAMPLE:
        if any(x["test"]["test_name"] == test for x in SAMPLE[ds]):
            return ds, _one(ds, test)
    raise LookupError(test)


def _reg(f: Finding) -> FactRegistry:
    reg = FactRegistry()
    build_method_facts(reg, load_config())
    build_facts(f, reg)
    return reg


@pytest.mark.parametrize("test", ["welch_t", "mann_whitney_u", "welch_anova", "kruskal_wallis", "spearman", "chi_square", "monte_carlo_chi_square"])
def test_chart_for_each_test_type(tmp_path: Path, test: str) -> None:
    ds, f = _any(test)
    res = plot_finding(f, _df(ds), _reg(f), tmp_path / "c.png")
    assert res.path.stat().st_size > 5000
    assert res.title
    res2 = plot_finding(f, _df(ds), _reg(f), tmp_path / "c2.png")
    assert hashlib.sha256(res.path.read_bytes()).digest() == hashlib.sha256(res2.path.read_bytes()).digest()


def test_chart_edge_cases(tmp_path: Path) -> None:
    rng = np.random.default_rng(1)
    base = _one("insurance", "welch_t")
    # tiny group (n = 8), integer values, NaNs, near-constant data
    df = pd.DataFrame({"charges": np.r_[rng.integers(0, 3, 8), rng.integers(0, 3, 200)].astype(float), "smoker": ["yes"] * 8 + ["no"] * 200})
    df.loc[::17, "charges"] = np.nan
    assert plot_finding(base, df, _reg(base), tmp_path / "a.png").path.exists()
    # many levels (15+) with a dominating level for a categorical chart
    cat = _one("telco_churn", "chi_square")
    a, b = cat.hypothesis.column_a, cat.hypothesis.column_b
    levels = [f"L{i}" for i in range(16)]
    dfc = pd.DataFrame({a: rng.choice(levels, 600, p=[0.6] + [0.4 / 15] * 15), b: rng.choice(["No", "Yes", "No internet service"], 600)})
    c2 = cat.model_copy(deep=True)
    c2.test.descriptives["row_labels"] = levels
    assert plot_finding(c2, dfc, _reg(c2), tmp_path / "b.png").path.exists()


@pytest.fixture(scope="module")
def built(tmp_path_factory: pytest.TempPathFactory):
    ds = "insurance"
    findings = [Finding.model_validate(x) for x in json.loads((ROOT / "outputs" / ds / "findings.json").read_text(encoding="utf-8"))]
    manifest = json.loads((ROOT / "outputs" / ds / "hypothesis_manifest.json").read_text(encoding="utf-8"))
    log = json.loads((ROOT / "outputs" / ds / "cleaning_log.json").read_text(encoding="utf-8"))
    prof = json.loads((ROOT / "outputs" / ds / "profile.json").read_text(encoding="utf-8"))
    out = tmp_path_factory.mktemp("rep")
    art = build_report(findings, manifest, log, prof, _df(ds), load_config(), None, out, report_date="2026-11-21")
    return art, findings, manifest, log, prof


def test_report_passes_gate_and_has_all_sections(built) -> None:
    art = built[0]
    assert art.ok
    md = art.markdown_path.read_text(encoding="utf-8")
    for h in ["## 1. Executive summary", "## 2. Validated findings", "## 3. Patterns that looked interesting but were rejected", "## 4. Likely derived", "## 5. Data quality summary", "## 6. Methods", "## 7. Limitations", "## 8. Appendix"]:
        assert h in md
    assert "assumed independent" in md and "not evidence of cause and effect" in md
    checks = json.loads(art.checks_path.read_text(encoding="utf-8"))
    assert checks["verifier"]["ok"] and checks["verifier"]["n_numbers_checked"] > 100
    assert checks["chart_text"]["ok"] and checks["lint"]["ok"] and checks["images"]["ok"]
    meta = json.loads(art.meta_path.read_text(encoding="utf-8"))
    assert set(meta["narration"].values()) == {"template"}
    rows = list(pd.read_csv(art.findings_csv).itertuples())
    assert len(rows) == len(built[1])


def test_html_is_self_contained_and_small(built) -> None:
    html = built[0].html_path.read_text(encoding="utf-8")
    assert 'src="figures/' not in html and "data:image/png;base64," in html
    assert "<details" in html and "http://" not in html and "https://" not in html
    assert built[0].html_path.stat().st_size < 15 * 1024 * 1024


def test_report_is_deterministic(tmp_path: Path, built) -> None:
    _, findings, manifest, log, prof = built
    a = build_report(findings, manifest, log, prof, _df("insurance"), load_config(), None, tmp_path / "a", report_date="2026-11-21")
    b = build_report(findings, manifest, log, prof, _df("insurance"), load_config(), None, tmp_path / "b", report_date="2026-11-21")
    assert a.markdown_path.read_bytes() == b.markdown_path.read_bytes()
    for p in sorted((tmp_path / "a" / "figures").glob("*.png")):
        assert p.read_bytes() == (tmp_path / "b" / "figures" / p.name).read_bytes(), p.name


def test_gate_fails_on_injected_number(tmp_path: Path, built, monkeypatch: pytest.MonkeyPatch) -> None:
    _, findings, manifest, log, prof = built
    monkeypatch.setattr(rb, "LIMITATIONS_STATIC", [*rb.LIMITATIONS_STATIC, "Roughly 37.5% of results may be wrong."])
    with pytest.raises(ReportingError):
        build_report(findings, manifest, log, prof, _df("insurance"), load_config(), None, tmp_path / "x", report_date="2026-11-21")
    monkeypatch.setattr(rb, "LIMITATIONS_STATIC", [*rb.LIMITATIONS_STATIC[:1], "Smoking causes higher charges."])
    with pytest.raises(ReportingError):
        build_report(findings, manifest, log, prof, _df("insurance"), load_config(), None, tmp_path / "y", report_date="2026-11-21")


def test_explain_finding_api() -> None:
    f = _one("insurance", "welch_t")
    reg = FactRegistry()
    ex = rb.explain_finding(f, reg, None, load_config())
    assert ex.verified and ex.source == "template" and ex.used_fact_keys


def test_cli_report_and_verify_text(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(ROOT)
    out = tmp_path / "cli_report"
    assert main(["report", "--dataset", "insurance", "--date", "2026-11-21", "--out", str(out)]) == 0
    assert (out / "report.html").exists()
    facts = tmp_path / "facts.json"
    facts.write_text(json.dumps([{"key": "A.r", "value": 0.42, "display": "0.42", "source": "x"}]), encoding="utf-8")
    assert main(["verify-text", "--facts", str(facts), "--text", "r = 0.42"]) == 0
    assert main(["verify-text", "--facts", str(facts), "--text", "r = 0.57"]) == 1
