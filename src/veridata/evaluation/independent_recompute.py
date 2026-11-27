"""Independent statistical recomputation for E4/E7 numeric verification (Phase 8 Section 6).

CRITICAL INVARIANT (Phase 8 Section 6 & Master Plan Rule 2):
This module MUST NOT import ``veridata.stats``, ``veridata.validation``, ``veridata.reporting``,
or ``veridata.agent`` so number-correctness evaluation is completely non-circular.
"""

from __future__ import annotations

import math
import re
from typing import Any

import numpy as np
import pandas as pd
from scipy import stats as sp_stats


def _norm_label(val: Any) -> str:
    s = str(val).strip()
    try:
        f = float(s)
        if f.is_integer():
            return str(int(f))
    except ValueError:
        pass
    return s


def _clean_numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def _hedges_g_plain(x1: np.ndarray, x2: np.ndarray) -> float:
    n1, n2 = len(x1), len(x2)
    df = n1 + n2 - 2
    if df <= 0:
        return 0.0
    s1 = float(np.var(x1, ddof=1)) if n1 > 1 else 0.0
    s2 = float(np.var(x2, ddof=1)) if n2 > 1 else 0.0
    sp = math.sqrt(((n1 - 1) * s1 + (n2 - 1) * s2) / df)
    if sp <= 0.0:
        return 0.0
    d = (float(np.mean(x1)) - float(np.mean(x2))) / sp
    j = 1.0 - (3.0 / (4.0 * df - 1.0)) if df >= 2 else 1.0
    return float(d * j)


def _welch_anova_plain(groups: list[np.ndarray]) -> tuple[float, float, float, float]:
    """Welch (1951) heteroscedastic one-way ANOVA returning (F, df1, df2, p_value)."""
    k = len(groups)
    ns = np.array([len(g) for g in groups], dtype=float)
    means = np.array([float(np.mean(g)) for g in groups], dtype=float)
    vars_ = np.array([float(np.var(g, ddof=1)) for g in groups], dtype=float)
    if np.any(vars_ <= 0.0) or np.any(ns < 2):
        res = sp_stats.f_oneway(*groups)
        return float(res.statistic), float(k - 1), float(np.sum(ns) - k), float(res.pvalue)
    w = ns / vars_
    w_sum = float(np.sum(w))
    x_bar = float(np.sum(w * means) / w_sum)
    num = float(np.sum(w * (means - x_bar) ** 2) / (k - 1))
    lam = float(np.sum(((1.0 - w / w_sum) ** 2) / (ns - 1.0)))
    denom = 1.0 + (2.0 * (k - 2.0) / (k * k - 1.0)) * lam
    f_stat = num / denom
    df1 = float(k - 1)
    df2 = (k * k - 1.0) / (3.0 * lam) if lam > 0.0 else float(np.sum(ns) - k)
    p_val = float(1.0 - sp_stats.f.cdf(f_stat, df1, df2))
    return float(f_stat), df1, float(df2), p_val


def _cramers_v_bc_plain(tab: np.ndarray) -> float:
    r, c = tab.shape
    n = float(tab.sum())
    df_star = min(r - 1, c - 1)
    if n <= 1.0 or df_star <= 0:
        return 0.0
    chi2 = float(sp_stats.chi2_contingency(tab, correction=False)[0])
    phi2 = chi2 / n
    phi2_corr = max(0.0, phi2 - ((r - 1) * (c - 1)) / (n - 1.0))
    r_corr = r - ((r - 1) ** 2) / (n - 1.0)
    c_corr = c - ((c - 1) ** 2) / (n - 1.0)
    denom = min(r_corr - 1.0, c_corr - 1.0)
    if denom <= 0.0:
        return 0.0
    return float(math.sqrt(max(0.0, phi2_corr / denom)))


def recompute_pair_stats(
    df: pd.DataFrame,
    col_a: str,
    col_b: str,
    *,
    test_name: str | None = None,
    relationship: str | None = None,
) -> dict[str, Any]:
    """Independently recompute n_used, p_value, effect_size, and descriptives from df."""
    if col_a not in df.columns or col_b not in df.columns:
        return {"ok": False, "error": f"Unknown column(s): {col_a}, {col_b}"}

    sub = df[[col_a, col_b]].dropna().copy()
    n_used = len(sub)
    if n_used == 0:
        return {"ok": False, "error": "No pairwise complete rows."}

    # Infer relationship when omitted
    if relationship is None:
        a_num = pd.api.types.is_numeric_dtype(sub[col_a]) and sub[col_a].nunique() > 2
        b_num = pd.api.types.is_numeric_dtype(sub[col_b]) and sub[col_b].nunique() > 2
        if a_num and b_num:
            relationship = "numeric_vs_numeric"
        elif a_num and not b_num:
            relationship = "numeric_vs_binary" if sub[col_b].nunique() == 2 else "numeric_vs_categorical"
        elif b_num and not a_num:
            col_a, col_b = col_b, col_a
            sub = sub[[col_a, col_b]]
            relationship = "numeric_vs_binary" if sub[col_b].nunique() == 2 else "numeric_vs_categorical"
        else:
            relationship = "categorical_vs_categorical"

    if relationship in {"numeric_vs_numeric", "numeric_vs_numeric_nonlinear"}:
        x = _clean_numeric(sub[col_a]).to_numpy(dtype=float)
        y = _clean_numeric(sub[col_b]).to_numpy(dtype=float)
        mask = np.isfinite(x) & np.isfinite(y)
        x, y = x[mask], y[mask]
        n_used = len(x)
        if n_used < 3:
            return {"ok": False, "error": "Insufficient numeric pairs."}
        r_p, p_p = sp_stats.pearsonr(x, y)
        r_s, p_s = sp_stats.spearmanr(x, y)
        chosen = test_name or "spearman"
        is_pearson = chosen == "pearson"
        return {
            "ok": True,
            "n_used": n_used,
            "test_name": chosen,
            "p_value": float(p_p if is_pearson else p_s),
            "p_pearson": float(p_p),
            "p_spearman": float(p_s),
            "effect_value": float(r_p if is_pearson else r_s),
            "pearson_r": float(r_p),
            "spearman_rho": float(r_s),
            "mean_a": float(np.mean(x)),
            "mean_b": float(np.mean(y)),
            "median_a": float(np.median(x)),
            "median_b": float(np.median(y)),
        }

    if relationship in {"numeric_vs_binary", "numeric_vs_categorical"}:
        sub = sub.copy()
        sub[col_a] = _clean_numeric(sub[col_a])
        sub = sub.dropna(subset=[col_a, col_b])
        sub["_grp"] = sub[col_b].map(_norm_label)
        counts = sub["_grp"].value_counts()
        valid_lvls = sorted([str(k) for k, v in counts.items() if int(v) >= 2])
        if len(valid_lvls) < 2:
            return {"ok": False, "error": "Fewer than 2 groups."}
        groups = [sub.loc[sub["_grp"] == lvl, col_a].to_numpy(dtype=float) for lvl in valid_lvls]
        n_used = int(sum(len(g) for g in groups))
        group_means = {lvl: float(np.mean(g)) for lvl, g in zip(valid_lvls, groups)}
        group_medians = {lvl: float(np.median(g)) for lvl, g in zip(valid_lvls, groups)}

        if len(valid_lvls) == 2:
            g1, g2 = groups[0], groups[1]
            t_stat, p_welch = sp_stats.ttest_ind(g1, g2, equal_var=False)
            u_stat, p_mwu = sp_stats.mannwhitneyu(g1, g2, alternative="two-sided")
            g_val = _hedges_g_plain(g1, g2)
            r_rb = float(2.0 * (float(u_stat) / (len(g1) * len(g2))) - 1.0)
            chosen = test_name or "welch_t"
            is_mwu = chosen == "mann_whitney_u"
            return {
                "ok": True,
                "n_used": n_used,
                "test_name": chosen,
                "p_value": float(p_mwu if is_mwu else p_welch),
                "p_welch": float(p_welch),
                "p_mwu": float(p_mwu),
                "statistic": float(u_stat if is_mwu else t_stat),
                "effect_value": float(r_rb if is_mwu else g_val),
                "hedges_g": float(g_val),
                "rank_biserial": float(r_rb),
                "group_means": group_means,
                "group_medians": group_medians,
                "group_sizes": {lvl: len(g) for lvl, g in zip(valid_lvls, groups)},
            }

        f_stat, _, _, p_wanova = _welch_anova_plain(groups)
        h_stat, p_kw = sp_stats.kruskal(*groups)
        all_vals = np.concatenate(groups)
        grand = float(np.mean(all_vals))
        ss_tot = float(np.sum((all_vals - grand) ** 2))
        ss_bet = float(sum(len(g) * (float(np.mean(g)) - grand) ** 2 for g in groups))
        eta_sq = float(ss_bet / ss_tot) if ss_tot > 0 else 0.0
        eps_sq = float(h_stat / (n_used - 1.0)) if n_used > 1 else 0.0
        chosen = test_name or "kruskal_wallis"
        is_kw = chosen == "kruskal_wallis"
        return {
            "ok": True,
            "n_used": n_used,
            "test_name": chosen,
            "p_value": float(p_kw if is_kw else p_wanova),
            "p_welch_anova": float(p_wanova),
            "p_kruskal": float(p_kw),
            "statistic": float(h_stat if is_kw else f_stat),
            "effect_value": float(eps_sq if is_kw else eta_sq),
            "eta_squared": float(eta_sq),
            "epsilon_squared": float(eps_sq),
            "group_means": group_means,
            "group_medians": group_medians,
            "group_sizes": {lvl: len(g) for lvl, g in zip(valid_lvls, groups)},
        }

    # CAT_CAT
    sub_a = sub[col_a].map(_norm_label)
    sub_b = sub[col_b].map(_norm_label)
    ct = pd.crosstab(sub_a, sub_b)
    if ct.shape[0] < 2 or ct.shape[1] < 2:
        return {"ok": False, "error": "Degenerate contingency table."}
    tab = ct.to_numpy(dtype=float)
    chi2, p_chi2, _, _ = sp_stats.chi2_contingency(tab, correction=False)
    p_fisher = float(sp_stats.fisher_exact(tab)[1]) if tab.shape == (2, 2) else None
    v_bc = _cramers_v_bc_plain(tab)
    chosen = test_name or "chi_square"
    p_main = p_fisher if (chosen == "fisher_exact" and p_fisher is not None) else float(p_chi2)
    return {
        "ok": True,
        "n_used": int(tab.sum()),
        "test_name": chosen,
        "p_value": float(p_main),
        "p_chi2": float(p_chi2),
        "p_fisher": p_fisher,
        "statistic": float(chi2),
        "effect_value": float(v_bc),
        "cramers_v_bc": float(v_bc),
    }


def values_close_scalar(claimed: float, actual: float, *, rel_tol: float = 0.01, abs_tol: float = 0.005) -> bool:
    """E4 tolerance for means/correlations/effect sizes: +-1% relative or +-0.005 for small effects."""
    if not (math.isfinite(claimed) and math.isfinite(actual)):
        return False
    return abs(claimed - actual) <= max(rel_tol * abs(actual), abs_tol)


def pvalues_close(claimed_p: float, actual_p: float) -> bool:
    """E4 tolerance for p-values: both < 0.001 or |log10(p_claim) - log10(p_true)| <= 0.3."""
    if not (math.isfinite(claimed_p) and math.isfinite(actual_p)):
        return False
    if claimed_p < 0.0 or actual_p < 0.0:
        return False
    if claimed_p <= 0.001 and actual_p <= 0.001:
        return True
    p1 = max(claimed_p, 1e-300)
    p2 = max(actual_p, 1e-300)
    return abs(math.log10(p1) - math.log10(p2)) <= 0.3001


def verify_veridata_finding_independently(finding: dict[str, Any], df: pd.DataFrame) -> dict[str, Any]:
    """Independently verify n_used, p_raw, and effect.value of a VeriData Finding dict."""
    hyp = finding.get("hypothesis", {})
    test = finding.get("test", {})
    if test.get("status") != "ok":
        return {"checked": False, "ok": True, "reason": "non_ok_status"}

    col_a = str(hyp.get("column_a", ""))
    col_b = str(hyp.get("column_b", ""))
    rel = hyp.get("relationship")
    tname = test.get("test_name")

    recomp = recompute_pair_stats(df, col_a, col_b, test_name=tname, relationship=rel)
    if not recomp.get("ok"):
        return {"checked": True, "ok": False, "reason": recomp.get("error", "recompute_failed")}

    mismatches: list[str] = []
    # Note: VeriData may filter rare levels (< min_group_n) before n_used; check exact when all levels included
    claimed_n = test.get("n_used")
    if (
        isinstance(claimed_n, int)
        and tname in {"pearson", "spearman", "welch_t", "mann_whitney_u"}
        and claimed_n != recomp["n_used"]
    ):
        mismatches.append(f"n_used: claimed={claimed_n}, recomp={recomp['n_used']}")

    claimed_p = test.get("p_value")
    if (
        claimed_p is not None
        and tname != "monte_carlo_chi_square"
        and not pvalues_close(float(claimed_p), float(recomp["p_value"]))
    ):
        mismatches.append(f"p_value: claimed={claimed_p}, recomp={recomp['p_value']}")

    eff = test.get("effect") or {}
    if eff and eff.get("value") is not None:
        c_eff = float(eff["value"])
        r_eff = float(recomp["effect_value"])
        # For two-group effects, sign depends on group ordering (g1-g2 vs g2-g1)
        same_mag = values_close_scalar(abs(c_eff), abs(r_eff), rel_tol=0.02, abs_tol=0.01)
        if not same_mag:
            mismatches.append(f"effect: claimed={c_eff}, recomp={r_eff}")

    return {
        "checked": True,
        "ok": len(mismatches) == 0,
        "mismatches": mismatches,
        "recomputed": recomp,
    }


_P_NUM_RE = re.compile(r"\bp\s*(?:=|<=|<)\s*(0?\.\d+(?:[eE][-+]?\d+)?|\d+(?:\.\d+)?[eE][-+]?\d+)")
_R_NUM_RE = re.compile(r"\b(?:r|rho|g|d|v|eta\^?2)\s*=\s*([-+]?\d+(?:\.\d+)?)", re.IGNORECASE)
_N_NUM_RE = re.compile(r"\bn\s*=\s*(\d{1,7})\b", re.IGNORECASE)


def extract_and_check_llm_claim(
    *,
    col_a: str,
    col_b: str,
    claim_text: str,
    claimed_p: float | None,
    claimed_effect: float | None,
    df: pd.DataFrame,
) -> dict[str, Any]:
    """Verify explicit numeric claims in an LLM finding against independent recomputation."""
    if col_a not in df.columns or col_b not in df.columns:
        return {"checkable": False, "verified": False, "hallucinated_column": True, "details": ["unknown_column"]}

    recomp = recompute_pair_stats(df, col_a, col_b)
    if not recomp.get("ok"):
        return {"checkable": False, "verified": False, "hallucinated_column": False, "details": ["recompute_failed"]}

    checks: list[tuple[str, bool, str]] = []

    p_to_check = claimed_p
    if p_to_check is None and claim_text:
        pm = _P_NUM_RE.search(claim_text)
        if pm:
            try:
                p_to_check = float(pm.group(1))
            except ValueError:
                p_to_check = None

    if p_to_check is not None:
        cand_ps = [
            float(recomp[k])
            for k in ("p_value", "p_pearson", "p_spearman", "p_welch", "p_mwu", "p_welch_anova", "p_kruskal", "p_chi2", "p_fisher")
            if recomp.get(k) is not None
        ]
        ok_p = any(pvalues_close(float(p_to_check), cp) for cp in cand_ps)
        checks.append(("p_value", ok_p, f"claimed={p_to_check}, candidates={cand_ps[:3]}"))

    eff_to_check = claimed_effect
    if eff_to_check is None and claim_text:
        rm = _R_NUM_RE.search(claim_text)
        if rm:
            try:
                eff_to_check = float(rm.group(1))
            except ValueError:
                eff_to_check = None

    if eff_to_check is not None:
        cand_es = [
            float(recomp[k])
            for k in ("effect_value", "pearson_r", "spearman_rho", "hedges_g", "rank_biserial", "eta_squared", "epsilon_squared", "cramers_v_bc")
            if recomp.get(k) is not None
        ]
        ok_e = any(values_close_scalar(abs(float(eff_to_check)), abs(ce), rel_tol=0.05, abs_tol=0.02) for ce in cand_es)
        checks.append(("effect", ok_e, f"claimed={eff_to_check}, candidates={cand_es[:3]}"))

    if claim_text:
        nm = _N_NUM_RE.search(claim_text)
        if nm:
            c_n = int(nm.group(1))
            ok_n = c_n == recomp["n_used"] or c_n == len(df)
            checks.append(("n", ok_n, f"claimed={c_n}, n_used={recomp['n_used']}"))

    if not checks:
        return {"checkable": False, "verified": None, "hallucinated_column": False, "details": ["no_explicit_numbers"]}

    all_ok = all(c[1] for c in checks)
    return {
        "checkable": True,
        "verified": all_ok,
        "hallucinated_column": False,
        "n_checks": len(checks),
        "n_passed": sum(1 for c in checks if c[1]),
        "details": [f"{name}:{'OK' if ok else 'FAIL'}({info})" for name, ok, info in checks],
    }
