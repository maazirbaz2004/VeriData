"""Structural model (DAG) bookkeeping and plain-numpy dependence measures (Phase 4, Section 4.4).

The benchmark DAG has two layers: root columns (and latent factors) and child columns, where
every child has exactly one parent. Dependence between two observed columns exists exactly when
one is the parent of the other or they share a parent (a common ancestor). A shared *child*
(collider) does not create marginal dependence.

The measures here are deliberately independent of ``veridata.stats`` so the truth file never
depends on the system being evaluated.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd
from scipy import stats as sps


@dataclass
class Edge:
    parent: str  # observed column name, or a latent node name starting with "__"
    child: str
    form: str
    params: dict[str, Any] = field(default_factory=dict)
    target: dict[str, Any] = field(default_factory=dict)  # population effect name/value
    detectable: bool = True


@dataclass
class Structure:
    """Everything needed to simulate a dataset of any size with fixed parameters."""

    columns: dict[str, str]  # observed name -> numeric | binary | categorical
    roots: dict[str, dict[str, Any]]  # observed or latent root -> generation spec
    edges: list[Edge]
    interactions: list[dict[str, Any]] = field(default_factory=list)  # {"child", "parents": [a, b], ...}
    numeric_scale: dict[str, tuple[float, float]] = field(default_factory=dict)  # obs = loc + scale * value

    def parents_of(self) -> dict[str, list[str]]:
        par: dict[str, list[str]] = {}
        for e in self.edges:
            par.setdefault(e.child, []).append(e.parent)
        for it in self.interactions:
            par.setdefault(it["child"], []).extend(it["parents"])
        return par

    def ancestors(self) -> dict[str, set[str]]:
        par = self.parents_of()
        memo: dict[str, set[str]] = {}

        def anc(node: str) -> set[str]:
            if node in memo:
                return memo[node]
            out: set[str] = set()
            for p in par.get(node, []):
                out.add(p)
                out |= anc(p)
            memo[node] = out
            return out

        for c in self.columns:
            anc(c)
        return memo


def d_connected_unconditional(a: str, b: str, ancestors: dict[str, set[str]]) -> bool:
    """True iff a and b are dependent through the DAG without conditioning (ancestor or common ancestor)."""
    aa, ab = ancestors.get(a, set()), ancestors.get(b, set())
    return a in ab or b in aa or bool(aa & ab)


# ---------------------------------------------------------------------------------------
# dependence measures (plain numpy / scipy; never veridata.stats)
# ---------------------------------------------------------------------------------------


def _complete(x: pd.Series, y: pd.Series) -> tuple[pd.Series, pd.Series]:
    mask = x.notna() & y.notna()
    return x[mask], y[mask]


def spearman_signed(x: pd.Series, y: pd.Series) -> float:
    x, y = _complete(x, y)
    if len(x) < 3 or x.nunique() < 2 or y.nunique() < 2:
        return 0.0
    return float(sps.spearmanr(x.to_numpy(dtype=float), y.to_numpy(dtype=float)).statistic)


def rank_eta(values: pd.Series, groups: pd.Series) -> tuple[float, str | None]:
    """Bias-corrected correlation ratio on ranks, and the level with the highest mean rank."""
    v, g = _complete(values, groups)
    n = len(v)
    if n < 3 or g.nunique() < 2:
        return 0.0, None
    r = pd.Series(sps.rankdata(v.to_numpy(dtype=float)), index=v.index)
    grand = r.mean()
    ss_tot = float(((r - grand) ** 2).sum())
    if ss_tot <= 0:
        return 0.0, None
    grp = r.groupby(g.astype(str))
    ss_b = float((grp.count() * (grp.mean() - grand) ** 2).sum())
    k = grp.ngroups
    eta2 = ss_b / ss_tot
    eta2_adj = max(0.0, eta2 - (k - 1) / (n - 1)) if n > 1 else 0.0
    return math.sqrt(eta2_adj), str(grp.mean().idxmax())


def cramers_v_bias_corrected(x: pd.Series, y: pd.Series) -> float:
    x, y = _complete(x, y)
    if len(x) < 3:
        return 0.0
    table = pd.crosstab(x.astype(str), y.astype(str)).to_numpy(dtype=float)
    r, k = table.shape
    if r < 2 or k < 2:
        return 0.0
    n = table.sum()
    expected = np.outer(table.sum(1), table.sum(0)) / n
    chi2 = float(((table - expected) ** 2 / expected).sum())
    phi2 = chi2 / n
    phi2c = max(0.0, phi2 - (k - 1) * (r - 1) / (n - 1))
    rc = r - (r - 1) ** 2 / (n - 1)
    kc = k - (k - 1) ** 2 / (n - 1)
    denom = min(rc - 1, kc - 1)
    return float(math.sqrt(phi2c / denom)) if denom > 0 else 0.0


def cramers_v_plain(x: pd.Series, y: pd.Series) -> float:
    x, y = _complete(x, y)
    table = pd.crosstab(x.astype(str), y.astype(str)).to_numpy(dtype=float)
    r, k = table.shape
    if r < 2 or k < 2:
        return 0.0
    n = table.sum()
    expected = np.outer(table.sum(1), table.sum(0)) / n
    chi2 = float(((table - expected) ** 2 / expected).sum())
    return float(math.sqrt(chi2 / n / min(r - 1, k - 1)))


def dependence(x: pd.Series, y: pd.Series, tx: str, ty: str) -> tuple[float, dict[str, Any] | None]:
    """Large-n dependence strength on a common 0..1 scale, plus the observed direction.

    numeric-numeric: |Spearman rho|; numeric-group: bias-corrected rank correlation ratio;
    group-group: bias-corrected Cramér's V.
    """
    num = {"numeric"}
    if tx in num and ty in num:
        rho = spearman_signed(x, y)
        return abs(rho), {"kind": "sign", "value": "+" if rho > 0 else "-"}
    if tx in num or ty in num:
        values, groups, gcol = (x, y, y.name) if tx in num else (y, x, x.name)
        eta, top = rank_eta(values, groups)
        return eta, ({"kind": "group_diff", "group_col": str(gcol), "higher_level": top, "n_levels": int(groups.dropna().nunique())} if top else None)
    return cramers_v_bias_corrected(x, y), None
