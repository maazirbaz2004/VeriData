"""Planted-truth dataset generator (Phase 4, Section 4).

``make_dataset(scenario, seed)`` returns a dataframe, its ``GroundTruth`` and the generating
``Structure``. Every dataset is a pure function of ``(scenario, seed)``.

Design (recorded in docs/decisions.md, P4-1 .. P4-6):
- Two-layer structural model: roots (and latent block factors) -> children, one parent per child.
  Siblings (same parent) are therefore dependent; the truth file includes them as induced pairs.
- Numeric roots and noise terms are drawn from a family (normal, lognormal, t3, zero-inflated,
  bimodal) standardised with its *population* mean and sd, so planted effects are exact in the
  population: Pearson r = beta, Cohen's d = delta, eta^2 from the level means. Monotonic
  (Spearman) and categorical-categorical (Cramér's V) effects are calibrated per dataset.
- Neutral column names (v01, v02, ...) assigned in random order; levels are L0, L1, ...
"""

from __future__ import annotations

import hashlib
import json
import math
from itertools import combinations
from pathlib import Path
from typing import Any, Literal

import numpy as np
import pandas as pd
from pydantic import BaseModel, Field

from veridata.benchmark.dag import Edge, Structure, d_connected_unconditional, dependence
from veridata.benchmark.truth import GroundTruth, TruthPair, pair_key

GENERATOR_VERSION = "1.0"
FAMILIES = ["normal", "lognormal", "t3", "zero_inflated", "bimodal"]
FORMS = ["linear", "monotonic", "binary_shift", "categorical_shift", "cat_cat"]
STRENGTH_GRID: dict[str, dict[str, Any]] = {
    "linear": {"small": 0.1, "medium": 0.3, "large": 0.5, "mixed": [0.1, 0.2, 0.3, 0.5]},
    "monotonic": {"small": 0.1, "medium": 0.3, "large": 0.5, "mixed": [0.1, 0.2, 0.3, 0.5]},
    "binary_shift": {"small": 0.2, "medium": 0.5, "large": 0.8, "mixed": [0.2, 0.5, 0.8]},
    "categorical_shift": {"small": 0.02, "medium": 0.06, "large": 0.14, "mixed": [0.02, 0.06, 0.14]},
    "cat_cat": {"small": 0.1, "medium": 0.3, "large": 0.5, "mixed": [0.1, 0.2, 0.3, 0.5]},
}
BIN_CUTS = {  # value -> strength bin, for stratified metrics
    "pearson_r": (0.25, 0.45),
    "spearman_rho": (0.25, 0.45),
    "cohens_d": (0.35, 0.65),
    "eta_squared": (0.04, 0.10),
    "cramers_v": (0.25, 0.45),
    "dependence": (0.25, 0.45),
}
RELATIONSHIP = {
    ("numeric", "numeric"): "numeric_vs_numeric",
    ("binary", "numeric"): "numeric_vs_binary",
    ("categorical", "numeric"): "numeric_vs_categorical",
    ("binary", "binary"): "categorical_vs_categorical",
    ("binary", "categorical"): "categorical_vs_categorical",
    ("categorical", "categorical"): "categorical_vs_categorical",
}
DECOY_C = 0.7


class NullBlocks(BaseModel):
    n_blocks: int = 0
    block_size: int = 4
    within_corr: float = 0.6


class Scenario(BaseModel):
    """One cell of the benchmark design (Section 4.2)."""

    scenario_id: str
    n_rows: int = 300
    n_cols: int = 30
    n_effects: int = 5
    effect_mix: dict[str, float] = Field(
        default_factory=lambda: {"linear": 0.3, "monotonic": 0.1, "binary_shift": 0.2, "categorical_shift": 0.2, "cat_cat": 0.2}
    )
    effect_strength: Literal["small", "medium", "large", "mixed"] = "medium"
    dist: Literal["normal", "lognormal", "t3", "zero_inflated", "bimodal", "mixed"] = "mixed"
    null_blocks: NullBlocks = Field(default_factory=NullBlocks)
    missing_rate: float = 0.0
    imbalance: Literal["none", "moderate", "strong"] = "moderate"
    col_type_mix: dict[str, float] = Field(default_factory=lambda: {"numeric": 0.55, "binary": 0.15, "categorical": 0.30})
    n_nonlinear_decoys: int = 0
    n_interaction_decoys: int = 0
    confounder: Literal["none", "common_cause"] = "none"
    sibling_reuse_prob: float = 0.35
    messy: bool = False


# ---------------------------------------------------------------------------------------
# distribution families (population-standardised)
# ---------------------------------------------------------------------------------------

_LN_SIGMA = 0.8


def family_moments(family: str) -> tuple[float, float]:
    """Population mean and sd of the raw (unstandardised) draw of a family."""
    if family == "normal":
        return 0.0, 1.0
    if family == "lognormal":
        m = math.exp(_LN_SIGMA**2 / 2)
        v = (math.exp(_LN_SIGMA**2) - 1) * math.exp(_LN_SIGMA**2)
        return m, math.sqrt(v)
    if family == "t3":
        return 0.0, math.sqrt(3.0)
    if family == "zero_inflated":
        m1 = math.exp(_LN_SIGMA**2 / 2)
        v1 = (math.exp(_LN_SIGMA**2) - 1) * math.exp(_LN_SIGMA**2)
        mean = 0.7 * m1
        second = 0.7 * (v1 + m1**2)
        return mean, math.sqrt(second - mean**2)
    if family == "bimodal":
        return 0.0, math.sqrt(0.25 + 2.25)
    raise ValueError(f"unknown family {family}")


def draw_raw(family: str, n: int, rng: np.random.Generator) -> np.ndarray:
    if family == "normal":
        return rng.standard_normal(n)
    if family == "lognormal":
        return np.exp(_LN_SIGMA * rng.standard_normal(n))
    if family == "t3":
        return rng.standard_t(3, n)
    if family == "zero_inflated":
        pos = np.exp(_LN_SIGMA * rng.standard_normal(n))
        return np.where(rng.random(n) < 0.3, 0.0, pos)
    if family == "bimodal":
        side = np.where(rng.random(n) < 0.5, -1.5, 1.5)
        return side + 0.5 * rng.standard_normal(n)
    raise ValueError(f"unknown family {family}")


def draw_standardized(family: str, n: int, rng: np.random.Generator) -> np.ndarray:
    m, s = family_moments(family)
    return (draw_raw(family, n, rng) - m) / s


# ---------------------------------------------------------------------------------------
# small helpers
# ---------------------------------------------------------------------------------------


def _sub_rng(seed: int, *tags: Any) -> np.random.Generator:
    h = hashlib.sha256(("|".join([str(seed), *map(str, tags)])).encode()).digest()
    return np.random.default_rng(int.from_bytes(h[:8], "little"))


def _level_probs(k: int, imbalance: str, rng: np.random.Generator) -> np.ndarray:
    if k == 2:
        lo = {"none": (0.40, 0.50), "moderate": (0.20, 0.35), "strong": (0.08, 0.15)}[imbalance]
        p_min = float(rng.uniform(*lo))
        p = np.array([p_min, 1 - p_min])
        return p[rng.permutation(2)]
    alpha = {"none": 30.0, "moderate": 3.0, "strong": 0.8}[imbalance]
    floor = {"none": 0.0, "moderate": 0.06, "strong": 0.04}[imbalance]
    p = rng.dirichlet([alpha] * k)
    for _ in range(5):
        p = np.maximum(p, floor)
        p = p / p.sum()
    return p


def _strength_value(form: str, strength: str, rng: np.random.Generator) -> float:
    g = STRENGTH_GRID[form][strength]
    return float(rng.choice(g)) if isinstance(g, list) else float(g)


def _bin(name: str, value: float | None) -> str:
    if value is None:
        return "n/a"
    lo, hi = BIN_CUTS.get(name, BIN_CUTS["dependence"])
    v = abs(value)
    return "small" if v < lo else ("medium" if v < hi else "large")


def _population_cramers_v(p: np.ndarray, q: np.ndarray, mapping: np.ndarray, w: float) -> float:
    """Population Cramér's V of the mixture: C2 = mapping[C1] with prob w, else C2 ~ q."""
    k1, k2 = len(p), len(q)
    joint = np.outer(p, (1 - w) * q)
    for i in range(k1):
        joint[i, mapping[i]] += p[i] * w
    r = joint.sum(axis=0)
    expected = np.outer(p, r)
    with np.errstate(divide="ignore", invalid="ignore"):
        chi2_over_n = float(np.nansum((joint - expected) ** 2 / np.where(expected > 0, expected, np.nan)))
    return math.sqrt(chi2_over_n / min(k1 - 1, k2 - 1))


def _calibrate_cat_cat(p: np.ndarray, q: np.ndarray, mapping: np.ndarray, target: float) -> tuple[float, float]:
    v_max = _population_cramers_v(p, q, mapping, 1.0)
    if v_max <= target:
        return 1.0, v_max
    lo, hi = 0.0, 1.0
    for _ in range(50):
        mid = (lo + hi) / 2
        if _population_cramers_v(p, q, mapping, mid) < target:
            lo = mid
        else:
            hi = mid
    w = (lo + hi) / 2
    return w, _population_cramers_v(p, q, mapping, w)


def _monotonic_child(xs: np.ndarray, b: float, noise: np.ndarray) -> np.ndarray:
    latent = b * xs + math.sqrt(max(0.0, 1 - b * b)) * noise
    return np.exp(latent)


def _calibrate_monotonic(family: str, target_abs: float, seed: int) -> tuple[float, float]:
    rng = _sub_rng(seed, "calib_monotonic", family)
    n = 40_000
    xs = draw_standardized(family, n, rng)
    noise = rng.standard_normal(n)
    from scipy import stats as sps

    def rho(b: float) -> float:
        return float(sps.spearmanr(xs, _monotonic_child(xs, b, noise)).statistic)

    lo, hi = 0.0, 0.999
    for _ in range(30):
        mid = (lo + hi) / 2
        if rho(mid) < target_abs:
            lo = mid
        else:
            hi = mid
    b = (lo + hi) / 2
    return b, rho(b)


# ---------------------------------------------------------------------------------------
# structure
# ---------------------------------------------------------------------------------------


def build_structure(scenario: Scenario, seed: int) -> tuple[Structure, dict[str, Any]]:
    rng = _sub_rng(seed, "structure", scenario.scenario_id)
    p = scenario.n_cols
    nb = scenario.null_blocks
    reserved_num = nb.n_blocks * nb.block_size + 2 * scenario.n_nonlinear_decoys + 3 * scenario.n_interaction_decoys
    n_bin = int(round(p * scenario.col_type_mix.get("binary", 0)))  # noqa: RUF046
    n_cat = int(round(p * scenario.col_type_mix.get("categorical", 0)))  # noqa: RUF046
    n_num = p - n_bin - n_cat
    min_num = reserved_num + (2 if scenario.n_effects else 0)
    while n_num < min_num and (n_bin + n_cat) > 0:
        if n_cat >= n_bin and n_cat > 0:
            n_cat -= 1
        else:
            n_bin -= 1
        n_num += 1
    if n_num < reserved_num:
        raise ValueError(f"scenario {scenario.scenario_id}: not enough columns for blocks/decoys")

    width = max(2, len(str(p)))
    names = [f"v{i:0{width}d}" for i in range(1, p + 1)]
    types = ["numeric"] * n_num + ["binary"] * n_bin + ["categorical"] * n_cat
    perm = rng.permutation(p)
    columns = {names[perm[i]]: types[i] for i in range(p)}
    order = list(columns)  # dataframe column order (random w.r.t. roles)

    def pick_family() -> str:
        return str(rng.choice(FAMILIES)) if scenario.dist == "mixed" else scenario.dist

    free: dict[str, list[str]] = {t: [c for c in order if columns[c] == t] for t in ("numeric", "binary", "categorical")}
    for cols_of_type in free.values():
        rng.shuffle(cols_of_type)

    roots: dict[str, dict[str, Any]] = {}
    edges: list[Edge] = []
    interactions: list[dict[str, Any]] = []
    families: dict[str, str] = {}

    def take(t: str) -> str:
        return free[t].pop()

    # null blocks (latent factor -> block members)
    for bi in range(nb.n_blocks):
        latent = f"__F{bi + 1}"
        roots[latent] = {"type": "latent"}
        for _ in range(nb.block_size):
            c = take("numeric")
            fam = pick_family()
            families[c] = fam
            edges.append(Edge(latent, c, "latent_factor", {"rho": nb.within_corr, "noise": fam}, {"name": "pearson_r", "value": nb.within_corr}))

    # decoys (normal roots, never reused)
    for _ in range(scenario.n_nonlinear_decoys):
        x, y = take("numeric"), take("numeric")
        roots[x] = {"type": "numeric", "family": "normal"}
        families[x] = families[y] = "normal"
        edges.append(Edge(x, y, "quadratic", {"c": DECOY_C}, {"name": "dependence", "value": None}, detectable=False))
    for _ in range(scenario.n_interaction_decoys):
        x1, x2, y = take("numeric"), take("numeric"), take("numeric")
        roots[x1] = {"type": "numeric", "family": "normal"}
        roots[x2] = {"type": "numeric", "family": "normal"}
        families[x1] = families[x2] = families[y] = "normal"
        interactions.append({"child": y, "parents": [x1, x2], "c": DECOY_C})

    # planted effects
    parent_type = {"linear": ["numeric"], "monotonic": ["numeric"], "binary_shift": ["binary"], "categorical_shift": ["categorical"], "cat_cat": ["binary", "categorical"]}
    child_type = {"linear": ["numeric"], "monotonic": ["numeric"], "binary_shift": ["numeric"], "categorical_shift": ["numeric"], "cat_cat": ["binary", "categorical"]}
    mix = {f: float(scenario.effect_mix.get(f, 0.0)) for f in FORMS}
    tot = sum(mix.values()) or 1.0
    probs = np.array([mix[f] / tot for f in FORMS])
    parents_used: list[str] = []
    skipped: list[str] = []
    level_cache: dict[str, dict[str, Any]] = {}

    def group_spec(c: str) -> dict[str, Any]:
        if c not in level_cache:
            k = 2 if columns[c] == "binary" else int(rng.choice([3, 5, 8], p=[0.45, 0.40, 0.15]))
            level_cache[c] = {"levels": [f"L{i}" for i in range(k)], "p": _level_probs(k, scenario.imbalance, rng).tolist()}
        return level_cache[c]

    for i in range(scenario.n_effects):
        placed = False
        tries = [str(rng.choice(FORMS, p=probs))] + [f for f in rng.permutation(FORMS).tolist()]
        for form in tries:
            ctypes = [t for t in child_type[form] if free[t]]
            if not ctypes:
                continue
            ptypes = parent_type[form]
            reuse_pool = [c for c in parents_used if columns[c] in ptypes]
            force_reuse = scenario.confounder == "common_cause" and i == 1 and reuse_pool
            parent = None
            if reuse_pool and (force_reuse or rng.random() < scenario.sibling_reuse_prob):
                parent = str(rng.choice(reuse_pool))
            else:
                fresh = [t for t in ptypes if free[t]]
                # do not use the last free column of the child's type as a parent
                fresh = [t for t in fresh if len(free[t]) > (1 if t in ctypes else 0)]
                if fresh:
                    parent = take(str(rng.choice(fresh)))
            if parent is None:
                continue
            ctypes = [t for t in child_type[form] if free[t]]
            if not ctypes:
                continue
            child = take(str(rng.choice(ctypes)))
            if parent not in roots:
                if columns[parent] == "numeric":
                    families[parent] = pick_family()
                    roots[parent] = {"type": "numeric", "family": families[parent]}
                else:
                    roots[parent] = {"type": columns[parent], **group_spec(parent)}
                parents_used.append(parent)
            value = _strength_value(form, scenario.effect_strength, rng)
            sign = 1.0 if rng.random() < 0.5 else -1.0
            fam = pick_family()
            if columns[child] == "numeric":
                families[child] = fam
            if form == "linear":
                edges.append(Edge(parent, child, form, {"beta": sign * value, "noise": fam}, {"name": "pearson_r", "value": sign * value}))
            elif form == "monotonic":
                b, achieved = _calibrate_monotonic(families[parent], value, seed)
                edges.append(Edge(parent, child, form, {"b": sign * b, "noise": "normal"}, {"name": "spearman_rho", "value": sign * value, "achieved": sign * achieved}))
            elif form == "binary_shift":
                lv = roots[parent]["levels"]
                edges.append(Edge(parent, child, form, {"delta": value, "level": lv[1] if sign > 0 else lv[0], "noise": fam}, {"name": "cohens_d", "value": value, "higher_level": lv[1] if sign > 0 else lv[0]}))
            elif form == "categorical_shift":
                spec = roots[parent]
                pr = np.array(spec["p"])
                u = rng.permutation(np.linspace(-1, 1, len(pr)))
                var_u = float(np.sum(pr * u**2) - np.sum(pr * u) ** 2)
                a = math.sqrt(value / (1 - value) / var_u)
                means = {lvl: float(a * u[j]) for j, lvl in enumerate(spec["levels"])}
                top = max(means, key=lambda k: means[k])
                edges.append(Edge(parent, child, form, {"means": means, "noise": fam}, {"name": "eta_squared", "value": value, "higher_level": top}))
            else:  # cat_cat
                pspec = roots[parent]
                cspec = group_spec(child)
                k1, k2 = len(pspec["levels"]), len(cspec["levels"])
                mapping = rng.integers(0, k2, size=k1)
                if len(set(mapping.tolist())) < 2:
                    mapping[0], mapping[1 % k1] = 0, 1
                w, achieved = _calibrate_cat_cat(np.array(pspec["p"]), np.array(cspec["p"]), mapping, value)
                edges.append(
                    Edge(parent, child, form, {"w": w, "mapping": mapping.tolist(), "q": cspec["p"], "levels": cspec["levels"]}, {"name": "cramers_v", "value": achieved, "target": value})
                )
            placed = True
            break
        if not placed:
            skipped.append(f"effect_{i + 1}")

    # remaining columns are pure noise roots
    for t, cols in free.items():
        for c in cols:
            if t == "numeric":
                families[c] = pick_family()
                roots[c] = {"type": "numeric", "family": families[c]}
            else:
                roots[c] = {"type": t, **group_spec(c)}

    numeric_scale: dict[str, tuple[float, float]] = {}
    for c, t in columns.items():
        if t != "numeric":
            continue
        fam = families.get(c, "normal")
        positive = c in roots and fam in {"lognormal", "zero_inflated"}
        loc = 0.0 if positive else float(np.round(rng.uniform(-20, 100), 1))
        scale = float(np.round(10 ** rng.uniform(-0.3, 1.3), 3))
        numeric_scale[c] = (loc, scale)

    structure = Structure(columns={c: columns[c] for c in order}, roots=roots, edges=edges, interactions=interactions, numeric_scale=numeric_scale)
    info = {"families": families, "effects_requested": scenario.n_effects, "effects_placed": scenario.n_effects - len(skipped), "skipped": skipped, "n_numeric": n_num, "n_binary": n_bin, "n_categorical": n_cat}
    return structure, info


def simulate(structure: Structure, n: int, rng: np.random.Generator) -> pd.DataFrame:
    """Draw ``n`` rows from the structure (no missingness)."""
    std: dict[str, np.ndarray] = {}  # standardised numeric values
    lab: dict[str, np.ndarray] = {}  # group labels
    for name, spec in structure.roots.items():
        if spec["type"] == "latent":
            std[name] = rng.standard_normal(n)
        elif spec["type"] == "numeric":
            std[name] = draw_standardized(spec["family"], n, rng)
        else:
            idx = rng.choice(len(spec["levels"]), size=n, p=spec["p"])
            lab[name] = np.array(spec["levels"], dtype=object)[idx]
    for e in structure.edges:
        pr = e.params
        if e.form == "linear":
            b = pr["beta"]
            std[e.child] = b * std[e.parent] + math.sqrt(1 - b * b) * draw_standardized(pr["noise"], n, rng)
        elif e.form == "latent_factor":
            r = pr["rho"]
            std[e.child] = math.sqrt(r) * std[e.parent] + math.sqrt(1 - r) * draw_standardized(pr["noise"], n, rng)
        elif e.form == "monotonic":
            std[e.child] = _monotonic_child(std[e.parent], pr["b"], rng.standard_normal(n))
        elif e.form == "quadratic":
            c = pr["c"]
            x = std[e.parent]
            std[e.child] = c * (x**2 - 1) / math.sqrt(2) + math.sqrt(1 - c * c) * rng.standard_normal(n)
        elif e.form == "binary_shift":
            std[e.child] = pr["delta"] * (lab[e.parent] == pr["level"]).astype(float) + draw_standardized(pr["noise"], n, rng)
        elif e.form == "categorical_shift":
            mu = np.array([pr["means"][lv] for lv in lab[e.parent]], dtype=float)
            std[e.child] = mu + draw_standardized(pr["noise"], n, rng)
        elif e.form == "cat_cat":
            levels_p = structure.roots[e.parent]["levels"]
            pos = {lv: i for i, lv in enumerate(levels_p)}
            mapped = np.array([pr["levels"][pr["mapping"][pos[v]]] for v in lab[e.parent]], dtype=object)
            indep = np.array(pr["levels"], dtype=object)[rng.choice(len(pr["levels"]), size=n, p=pr["q"])]
            lab[e.child] = np.where(rng.random(n) < pr["w"], mapped, indep)
    for it in structure.interactions:
        c = it["c"]
        a, b = it["parents"]
        std[it["child"]] = c * std[a] * std[b] + math.sqrt(1 - c * c) * rng.standard_normal(n)

    data: dict[str, Any] = {}
    for col, t in structure.columns.items():
        if t == "numeric":
            loc, scale = structure.numeric_scale[col]
            spec = structure.roots.get(col)
            v = std[col]
            if spec is not None and spec.get("family") in {"lognormal", "zero_inflated"}:
                m, s = family_moments(spec["family"])
                v = v * s + m  # back to the raw positive scale (keeps exact zeros)
            data[col] = np.round(loc + scale * v, 4)
        else:
            data[col] = lab[col]
    return pd.DataFrame(data, columns=list(structure.columns))


# ---------------------------------------------------------------------------------------
# truth
# ---------------------------------------------------------------------------------------


def _testable(df: pd.DataFrame, a: str, b: str, ta: str, tb: str, min_n: int = 20, min_group: int = 8) -> bool:
    sub = df[[a, b]].dropna()
    if len(sub) < min_n:
        return False
    for col, t in ((a, ta), (b, tb)):
        if t in {"binary", "categorical"}:
            counts = sub[col].value_counts()
            if int((counts >= min_group).sum()) < 2:
                return False
    return True


def _relationship(ta: str, tb: str) -> str:
    key = tuple(sorted((ta, tb)))
    return RELATIONSHIP.get(key, "categorical_vs_categorical")  # type: ignore[arg-type]


def _direct_direction(e: Edge, columns: dict[str, str]) -> dict[str, Any] | None:
    if e.form in {"linear", "monotonic", "latent_factor"}:
        val = e.target["value"]
        return {"kind": "sign", "value": "+" if val > 0 else "-"}
    if e.form in {"binary_shift", "categorical_shift"}:
        n_levels = 2 if columns.get(e.parent) == "binary" else len(e.params["means"])
        return {"kind": "group_diff", "group_col": e.parent, "higher_level": e.target["higher_level"], "n_levels": n_levels}
    return None


def compute_truth(
    structure: Structure,
    df: pd.DataFrame,
    scenario: Scenario,
    seed: int,
    *,
    n_truth: int = 20_000,
    induced_threshold: float = 0.05,
) -> GroundTruth:
    cols = structure.columns
    anc = structure.ancestors()
    direct: dict[tuple[str, str], TruthPair] = {}
    for e in structure.edges:
        if e.parent.startswith("__"):
            continue
        k = pair_key(e.parent, e.child)
        pe = dict(e.target)
        pe["bin"] = _bin(pe.get("name", ""), pe.get("value"))
        direct[k] = TruthPair(
            col_a=k[0], col_b=k[1], type="direct", form=e.form, population_effect=pe,
            direction=_direct_direction(e, cols), detectable_by_default_tests=e.detectable,
            relationship=_relationship(cols[e.parent], cols[e.child]),
        )
    for it in structure.interactions:
        for par in it["parents"]:
            k = pair_key(par, it["child"])
            direct[k] = TruthPair(
                col_a=k[0], col_b=k[1], type="direct", form="interaction",
                population_effect={"name": "dependence", "value": None, "c": it["c"], "bin": "n/a"},
                direction=None, detectable_by_default_tests=False, relationship="numeric_vs_numeric",
            )
    # latent blocks: members of the same block are direct (form latent_factor)
    blocks: dict[str, list[Edge]] = {}
    for e in structure.edges:
        if e.parent.startswith("__"):
            blocks.setdefault(e.parent, []).append(e)
    for members in blocks.values():
        for e1, e2 in combinations(members, 2):
            k = pair_key(e1.child, e2.child)
            rho = e1.params["rho"]
            direct[k] = TruthPair(
                col_a=k[0], col_b=k[1], type="direct", form="latent_factor",
                population_effect={"name": "pearson_r", "value": rho, "bin": _bin("pearson_r", rho)},
                direction={"kind": "sign", "value": "+"}, relationship="numeric_vs_numeric", via=[e1.parent],
            )

    big = simulate(structure, n_truth, _sub_rng(seed, "truth_draw"))
    true_pairs: list[TruthPair] = []
    gray: list[TruthPair] = []
    names = list(cols)
    for a, b in combinations(names, 2):
        k = pair_key(a, b)
        testable = _testable(df, a, b, cols[a], cols[b])
        if k in direct:
            tp = direct[k].model_copy()
            tp.testable = testable
            m, _ = dependence(big[k[0]], big[k[1]], cols[k[0]], cols[k[1]])
            tp.dependence_measure = round(m, 4)
            true_pairs.append(tp)
            continue
        if not d_connected_unconditional(a, b, anc):
            continue
        shared = sorted((anc.get(a, set()) | {a}) & (anc.get(b, set()) | {b}))
        m, dirn = dependence(big[k[0]], big[k[1]], cols[k[0]], cols[k[1]])
        tp = TruthPair(
            col_a=k[0], col_b=k[1], type="induced" if m >= induced_threshold else "weak_induced", form="induced",
            population_effect={"name": "dependence", "approx": round(m, 4), "bin": _bin("dependence", m)},
            direction=dirn, detectable_by_default_tests=True, testable=testable,
            relationship=_relationship(cols[a], cols[b]), via=shared, dependence_measure=round(m, 4),
        )
        (true_pairs if m >= induced_threshold else gray).append(tp)

    n_pairs = len(names) * (len(names) - 1) // 2
    return GroundTruth(
        dataset_id=f"{scenario.scenario_id}__seed{seed}",
        scenario_id=scenario.scenario_id,
        seed=seed,
        n_rows=len(df),
        columns=dict(cols),
        true_pairs=sorted(true_pairs, key=lambda p: p.key),
        gray_pairs=sorted(gray, key=lambda p: p.key),
        n_pairs_total=n_pairs,
        null_pairs_count=n_pairs - len(true_pairs) - len(gray),
        is_pure_null=len(true_pairs) == 0,
        notes={"n_truth": n_truth, "induced_threshold": induced_threshold, "generator_version": GENERATOR_VERSION},
    )


def _apply_missing(df: pd.DataFrame, rate: float, seed: int) -> pd.DataFrame:
    if rate <= 0:
        return df
    rng = _sub_rng(seed, "missing")
    out = df.copy()
    cols = list(out.columns)
    chosen = rng.choice(cols, size=max(1, len(cols) // 2), replace=False)
    for c in sorted(chosen):
        mask = rng.random(len(out)) < rate
        out[c] = out[c].astype(object).where(~mask, None) if out[c].dtype == object else out[c].mask(mask)
    return out


def make_dataset(scenario: Scenario, seed: int, *, n_truth: int = 20_000) -> tuple[pd.DataFrame, GroundTruth, Structure]:
    """Generate one dataset and its ground truth (deterministic in ``(scenario, seed)``)."""
    structure, info = build_structure(scenario, seed)
    df = simulate(structure, scenario.n_rows, _sub_rng(seed, "data_draw"))
    df = df.sample(frac=1.0, random_state=int(_sub_rng(seed, "row_shuffle").integers(0, 2**31 - 1))).reset_index(drop=True)
    df = _apply_missing(df, scenario.missing_rate, seed)
    truth = compute_truth(structure, df, scenario, seed, n_truth=n_truth)
    truth.notes.update(info)
    return df, truth, structure


def structure_summary(structure: Structure) -> dict[str, Any]:
    return {
        "edges": [{"parent": e.parent, "child": e.child, "form": e.form, "params": e.params, "target": e.target} for e in structure.edges],
        "interactions": structure.interactions,
        "roots": structure.roots,
    }


def save_dataset(out_dir: Path | str, df: pd.DataFrame, truth: GroundTruth, scenario: Scenario, structure: Structure) -> Path:
    """Write data.csv, truth.json and scenario.json; returns the dataset folder."""
    d = Path(out_dir)
    d.mkdir(parents=True, exist_ok=True)
    df.to_csv(d / "data.csv", index=False, lineterminator="\n")
    truth.save(d / "truth.json")
    meta = {"scenario": scenario.model_dump(mode="json"), "seed": truth.seed, "generator_version": GENERATOR_VERSION, "structure": structure_summary(structure)}
    (d / "scenario.json").write_text(json.dumps(meta, indent=2, sort_keys=True, default=float) + "\n", encoding="utf-8")
    return d


def truth_selfcheck(scenario: Scenario, seed: int, *, n_check: int = 20_000, true_min: float = 0.03, null_max: float = 0.04) -> dict[str, Any]:
    """Independent large draw: truth pairs must show dependence, null pairs must not (Section 4.4)."""
    structure, _ = build_structure(scenario, seed)
    df_small = simulate(structure, scenario.n_rows, _sub_rng(seed, "data_draw"))
    truth = compute_truth(structure, df_small, scenario, seed)
    big = simulate(structure, n_check, _sub_rng(seed, "selfcheck_draw"))
    cols = structure.columns
    failures: list[dict[str, Any]] = []
    for tp in truth.true_pairs:
        if not tp.detectable_by_default_tests:
            continue
        m, _ = dependence(big[tp.col_a], big[tp.col_b], cols[tp.col_a], cols[tp.col_b])
        if m < true_min:
            failures.append({"pair": [tp.col_a, tp.col_b], "kind": "true_pair_weak", "measure": m, "form": tp.form})
    max_null = 0.0
    for a, b in sorted(truth.null_keys()):
        m, _ = dependence(big[a], big[b], cols[a], cols[b])
        max_null = max(max_null, m)
        if m > null_max:
            failures.append({"pair": [a, b], "kind": "null_pair_dependent", "measure": m})
    return {"dataset_id": truth.dataset_id, "n_true": len(truth.true_pairs), "n_null": truth.null_pairs_count, "max_null_measure": round(max_null, 4), "failures": failures, "ok": not failures}
