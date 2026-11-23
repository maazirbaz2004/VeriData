"""Phase 4 generator and truth tests (Section 10: Generator, Truth)."""

from __future__ import annotations

import hashlib
import io
import math
import re
from itertools import combinations

import numpy as np
import pandas as pd
import pytest
from scipy import stats as sps

from veridata.benchmark.dag import cramers_v_plain, d_connected_unconditional
from veridata.benchmark.generator import (
    FAMILIES,
    NullBlocks,
    Scenario,
    _sub_rng,
    build_structure,
    draw_standardized,
    make_dataset,
    simulate,
    truth_selfcheck,
)
from veridata.benchmark.suites import suite_scenarios
from veridata.benchmark.truth import pair_key


def _csv_hash(df: pd.DataFrame) -> str:
    buf = io.StringIO()
    df.to_csv(buf, index=False, lineterminator="\n")
    return hashlib.sha256(buf.getvalue().encode()).hexdigest()


BASE = Scenario(
    scenario_id="t_base", n_rows=400, n_cols=30, n_effects=8, effect_strength="mixed", dist="mixed",
    null_blocks=NullBlocks(n_blocks=1, block_size=4, within_corr=0.6), missing_rate=0.05,
    n_nonlinear_decoys=1, n_interaction_decoys=1, confounder="common_cause",
)


def test_family_standardisation_is_exact_in_population() -> None:
    rng = np.random.default_rng(0)
    for fam in FAMILIES:
        x = draw_standardized(fam, 400_000, rng)
        assert abs(x.mean()) < 0.01, fam
        assert abs(x.std() - 1) < 0.02, fam


def test_determinism_and_seed_sensitivity() -> None:
    df1, t1, _ = make_dataset(BASE, 5)
    df2, t2, _ = make_dataset(BASE, 5)
    df3, _, _ = make_dataset(BASE, 6)
    assert _csv_hash(df1) == _csv_hash(df2)
    assert t1.model_dump() == t2.model_dump()
    assert _csv_hash(df1) != _csv_hash(df3)


def test_schema_names_types_and_missingness() -> None:
    df, truth, _ = make_dataset(BASE.model_copy(update={"missing_rate": 0.2, "n_rows": 2000}), 1)
    assert df.shape == (2000, 30)
    assert all(re.fullmatch(r"v\d{2}", c) for c in df.columns)  # neutral, non-leaking names
    assert list(df.columns) != sorted(df.columns)  # column order shuffled
    types = truth.columns
    assert set(types.values()) == {"numeric", "binary", "categorical"}
    for c, t in types.items():
        if t == "numeric":
            assert pd.api.types.is_float_dtype(df[c])
        else:
            levels = set(df[c].dropna())
            assert all(re.fullmatch(r"L\d", str(v)) for v in levels)
            assert len(levels) == (2 if t == "binary" else len(levels))
    miss = df.isna().mean()
    with_missing = miss[miss > 0]
    assert len(with_missing) == 15  # half of the columns
    assert abs(with_missing.mean() - 0.2) < 0.03


def test_pure_null_dataset_has_no_true_pairs() -> None:
    sc = Scenario(scenario_id="t_null", n_rows=300, n_cols=20, n_effects=0, dist="t3")
    _, truth, _ = make_dataset(sc, 2)
    assert truth.true_pairs == [] and truth.gray_pairs == []
    assert truth.is_pure_null
    assert truth.null_pairs_count == 190


def test_truth_classifies_every_pair_exactly_once() -> None:
    _, truth, _ = make_dataset(BASE, 3)
    t, g, n = truth.true_keys(), truth.gray_keys(), truth.null_keys()
    assert not (t & g) and not (t & n) and not (g & n)
    assert len(t) + len(g) + len(n) == math.comb(30, 2) == truth.n_pairs_total


def test_induced_and_collider_rules() -> None:
    structure, _ = build_structure(BASE, 3)
    anc = structure.ancestors()
    parents: dict[str, list[str]] = {}
    for e in structure.edges:
        if not e.parent.startswith("__"):
            parents.setdefault(e.parent, []).append(e.child)
    _, truth, _ = make_dataset(BASE, 3)
    keys_true_or_gray = truth.true_keys() | truth.gray_keys()
    siblings = [(a, b) for kids in parents.values() for a, b in combinations(kids, 2)]
    assert siblings, "fixture should contain siblings (common_cause)"
    for a, b in siblings:
        assert pair_key(a, b) in keys_true_or_gray  # induced or gray, never null
    for it in structure.interactions:
        x1, x2 = it["parents"]
        assert not d_connected_unconditional(x1, x2, anc)  # collider does not connect its parents
        assert pair_key(x1, x2) in truth.null_keys()
        for x in (x1, x2):
            tp = next(p for p in truth.true_pairs if p.key == pair_key(x, it["child"]))
            assert tp.form == "interaction" and not tp.detectable_by_default_tests


def _large(sc: Scenario, seed: int) -> tuple[pd.DataFrame, object]:
    structure, _ = build_structure(sc, seed)
    return simulate(structure, 60_000, _sub_rng(seed, "large_check")), structure


@pytest.mark.parametrize("dist", ["normal", "lognormal", "t3", "zero_inflated", "bimodal"])
@pytest.mark.parametrize("form", ["linear", "monotonic", "binary_shift", "categorical_shift", "cat_cat"])
def test_planted_effect_sizes_match_targets(form: str, dist: str) -> None:
    """Large-n empirical effect within +-15% of the target (Section 10)."""
    sc = Scenario(
        scenario_id=f"t_{form}_{dist}", n_rows=200, n_cols=8, n_effects=1, effect_mix={form: 1.0}, effect_strength="medium",
        dist=dist, imbalance="moderate", col_type_mix={"numeric": 0.5, "binary": 0.25, "categorical": 0.25}, sibling_reuse_prob=0.0,
    )
    big, structure = _large(sc, 4)
    edges = [e for e in structure.edges if e.form == form]
    assert len(edges) == 1
    e = edges[0]
    x, y = big[e.parent], big[e.child]
    target = e.target
    if form == "linear":
        got = float(np.corrcoef(x, y)[0, 1])
        assert got == pytest.approx(target["value"], rel=0.15, abs=0.02)
    elif form == "monotonic":
        got = float(sps.spearmanr(x, y).statistic)
        assert got == pytest.approx(target["value"], rel=0.15, abs=0.02)
    elif form == "binary_shift":
        hi = target["higher_level"]
        g1, g0 = y[x == hi], y[x != hi]
        pooled = math.sqrt((g1.var() * (len(g1) - 1) + g0.var() * (len(g0) - 1)) / (len(y) - 2))
        assert (g1.mean() - g0.mean()) / pooled == pytest.approx(target["value"], rel=0.15)
    elif form == "categorical_shift":
        grand = y.mean()
        grp = y.groupby(x)
        eta2 = float((grp.count() * (grp.mean() - grand) ** 2).sum() / ((y - grand) ** 2).sum())
        assert eta2 == pytest.approx(target["value"], rel=0.15)
        assert grp.mean().idxmax() == target["higher_level"]
    else:
        assert cramers_v_plain(x, y) == pytest.approx(target["value"], rel=0.15, abs=0.01)


@pytest.mark.parametrize("sc", suite_scenarios("smoke"), ids=lambda s: s.scenario_id)
def test_truth_selfcheck_smoke_suite(sc: Scenario) -> None:
    rep = truth_selfcheck(sc, 0)
    assert rep["ok"], rep["failures"]


def test_truth_selfcheck_mixed_scenario() -> None:
    rep = truth_selfcheck(BASE, 9)
    assert rep["ok"], rep["failures"]
