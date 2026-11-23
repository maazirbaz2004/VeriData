"""Phase 4 suites, dev/test guard, runner (cache, failure isolation), variants and calibration smoke tests."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import numpy as np
import pytest

from veridata.benchmark import calibration as cal
from veridata.benchmark.runner import evaluate_suite, generate_suite, run_suite
from veridata.benchmark.suites import SplitGuardError, check_split, suite_scenarios, suite_specs
from veridata.benchmark.systems import benchmark_config, get_variant, variant_config


def test_core60_design() -> None:
    sc = suite_scenarios("core60")
    assert len(sc) == 60
    assert sum(s.n_effects == 0 for s in sc) == 12
    assert {(s.n_rows, s.n_cols) for s in sc if s.n_effects == 0} == {(n, p) for n in (100, 300, 1000, 5000) for p in (10, 30, 60)}
    assert Counter(s.effect_strength for s in sc if s.n_effects) == {"small": 12, "medium": 12, "large": 12, "mixed": 12}
    assert {s.dist for s in sc if s.n_effects == 0} >= {"t3", "zero_inflated"}
    assert any(s.null_blocks.n_blocks for s in sc if s.n_effects == 0)
    assert len({s.scenario_id for s in sc}) == 60


def test_seed_split_and_guard(tmp_path: Path) -> None:
    dev = suite_specs("core60", "dev")
    assert all(0 <= s.seed < 1000 for s in dev)
    with pytest.raises(SplitGuardError):
        suite_specs("core60", "test")
    proto = tmp_path / "eval_protocol.md"
    proto.write_text("Status: DRAFT\n", encoding="utf-8")
    with pytest.raises(SplitGuardError):
        check_split("test", confirm_final=True, protocol_path=proto)
    proto.write_text("Status: FROZEN\n", encoding="utf-8")
    check_split("test", confirm_final=True, protocol_path=proto)


def test_variant_configs() -> None:
    base = benchmark_config()
    full = variant_config(base, get_variant("veridata_full"))
    assert full.stats.correction == "bh" and full.effect_floor.enabled and full.stats.assumption_aware_selection
    raw = variant_config(base, get_variant("naive_raw"))
    assert raw.stats.correction == "none" and not raw.effect_floor.enabled and not raw.stats.assumption_aware_selection
    tuned = variant_config(base, get_variant("tune_floor_x1.50"))
    assert tuned.effect_floor.cohens_d == pytest.approx(base.effect_floor.cohens_d * 1.5)


def test_runner_cache_failure_isolation_and_variant_ordering(tmp_path: Path) -> None:
    only = ["smoke_linear_n300_p12__seed10", "smoke_groups_n300_p14__seed20", "smoke_null_n200_p12__seed0"]
    generate_suite("smoke", "dev", out_root=tmp_path, only=only)
    systems = ["veridata_full", "veridata_nocorrection", "bonferroni"]
    r1 = run_suite("smoke", "dev", systems, out_root=tmp_path, only=only)
    assert r1["n_run"] == 3
    r2 = run_suite("smoke", "dev", systems, out_root=tmp_path, only=only)
    assert r2["n_run"] == 0  # cache hit
    base = tmp_path / "smoke" / "dev"
    for d in only[:2]:
        full = json.loads((base / "results" / "veridata_full" / f"{d}.json").read_text())
        noc = json.loads((base / "results" / "veridata_nocorrection" / f"{d}.json").read_text())
        bonf = json.loads((base / "results" / "bonferroni" / f"{d}.json").read_text())
        pairs = lambda o: {(f["col_a"], f["col_b"]) for f in o["findings"]}
        assert pairs(bonf) <= pairs(full)  # Bonferroni is stricter than BH
        assert len(noc["findings"]) >= len(full["findings"])
    # corrupt one dataset: it is recorded as an error, the others still evaluate
    bad = base / only[0] / "data.csv"
    bad.write_bytes(b"\x00\x01garbage")
    run_suite("smoke", "dev", ["veridata_full"], out_root=tmp_path, only=only)
    ev = evaluate_suite("smoke", "dev", ["veridata_full"], out_root=tmp_path, only=only, n_resamples=100)
    s = ev["summary"]["veridata_full"]
    assert s["n_errors"] == 1 and s["if_reported"]["n_datasets"] == 2
    assert (base / "results" / "summary.md").exists()


def test_tuning_variants_refuse_test_split() -> None:
    with pytest.raises(ValueError):
        run_suite("smoke", "test", ["tune_floor_x1.00"], confirm_final=True)


def test_type1_smoke() -> None:
    cells = [c for c in cal.type1_cells((200,)) if c["family"] in ("normal", "n/a") and c["imbalance"] in ("balanced", "n/a")]
    rows = [r for i, c in enumerate(cells) for r in cal._run_type1_cell(c, 40, i)]
    assert rows and all(r["n_valid"] > 0 for r in rows)
    sizes = [r["size"] for r in rows if r["selection"] == "assumption_aware"]
    assert np.mean(sizes) < 0.2


def test_fdr_dependence_smoke() -> None:
    df = cal.run_fdr_dependence(reps=30, ps=(20,), n_jobs=1)
    ind = df[(df["scenario"] == "independent")].set_index("method")
    assert ind.loc["bh", "fdr"] <= 0.2 and ind.loc["none", "fwer"] > 0.5
    assert ind.loc["bonferroni", "fwer"] <= ind.loc["none", "fwer"]
    blk = df[(df["scenario"] == "null_blocks")]
    assert set(blk["method"]) == {"bh", "by", "bonferroni", "holm", "none"}


def test_power_formulas() -> None:
    assert cal._fisher_power(0.0001, 100) == pytest.approx(0.05, abs=0.01)
    assert cal._fisher_power(0.4, 100) > 0.9
