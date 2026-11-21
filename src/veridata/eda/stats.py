"""Descriptive statistics used by EDA and insights (Section 10).

Pure functions on pandas/numpy objects. Nothing here computes a p-value or runs a
hypothesis test: Cramér's V and eta-squared are effect-size style descriptive numbers,
computed directly from sums of squares / contingency counts.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd


def as_float(s: pd.Series) -> pd.Series:
    """Return ``s`` as a plain float64 series (nullable ints and pd.NA become NaN)."""
    if isinstance(s.dtype, pd.CategoricalDtype):
        s = s.astype("object")
    num = pd.to_numeric(s, errors="coerce")
    try:
        arr = num.astype("Float64").to_numpy(dtype="float64", na_value=np.nan)
    except (TypeError, ValueError):
        arr = np.asarray(num, dtype="float64")
    return pd.Series(arr, index=s.index, name=s.name)


def _fmt_label(v: Any) -> str:
    if isinstance(v, (float, np.floating)) and float(v).is_integer():
        return str(int(v))
    if isinstance(v, (bool, np.bool_)):
        return str(bool(v))
    return str(v)


def as_labels(s: pd.Series) -> pd.Series:
    """Return ``s`` as string labels (object dtype); missing values stay as None."""
    out = s.astype("object")
    mask = out.notna()
    labels = pd.Series([None] * len(out), index=out.index, dtype="object", name=s.name)
    if mask.any():
        labels.loc[mask] = out.loc[mask].map(_fmt_label)
    return labels


def value_counts_sorted(labels: pd.Series) -> pd.Series:
    """Value counts sorted by count (desc) then label (asc) so ties are deterministic."""
    vc = labels.dropna().value_counts()
    if vc.empty:
        return vc
    frame = pd.DataFrame({"label": vc.index.astype(str), "count": vc.to_numpy()})
    frame = frame.sort_values(["count", "label"], ascending=[False, True], kind="mergesort")
    return pd.Series(frame["count"].to_numpy(), index=frame["label"].to_numpy(), name="count")


def normalized_entropy(counts: pd.Series | np.ndarray) -> float:
    """Shannon entropy divided by log(k): 0 = one level dominates, 1 = perfectly even."""
    arr = np.asarray(counts, dtype="float64")
    arr = arr[arr > 0]
    k = len(arr)
    if k < 2:
        return 0.0
    p = arr / arr.sum()
    h = float(-(p * np.log(p)).sum())
    return h / math.log(k)


def cramers_v(x: pd.Series, y: pd.Series) -> float | None:
    """Bias-corrected Cramér's V (Bergsma 2013) between two categorical series.

    Built from the contingency table's chi-square *statistic* only; no p-value is computed.
    Returns None when either side has fewer than 2 observed levels.
    """
    frame = pd.DataFrame({"x": as_labels(x), "y": as_labels(y)}).dropna()
    if len(frame) < 2:
        return None
    table = pd.crosstab(frame["x"], frame["y"]).to_numpy(dtype="float64")
    r, k = table.shape
    if r < 2 or k < 2:
        return None
    n = table.sum()
    expected = np.outer(table.sum(axis=1), table.sum(axis=0)) / n
    with np.errstate(divide="ignore", invalid="ignore"):
        chi2 = float(np.nansum((table - expected) ** 2 / expected))
    phi2 = chi2 / n
    if n <= 1:
        return None
    phi2_corr = max(0.0, phi2 - ((k - 1) * (r - 1)) / (n - 1))
    r_corr = r - ((r - 1) ** 2) / (n - 1)
    k_corr = k - ((k - 1) ** 2) / (n - 1)
    denom = min(k_corr - 1, r_corr - 1)
    if denom <= 0:
        return 0.0
    return float(min(1.0, math.sqrt(phi2_corr / denom)))


def eta_squared(values: pd.Series, groups: pd.Series) -> float | None:
    """Share of the variance of ``values`` explained by ``groups`` (SS_between / SS_total).

    Plain sums of squares; no F statistic or p-value. Returns None if there are fewer than
    2 groups or no variation at all.
    """
    frame = pd.DataFrame({"y": as_float(values), "g": as_labels(groups)}).dropna()
    if len(frame) < 2 or frame["g"].nunique() < 2:
        return None
    grand = frame["y"].mean()
    ss_total = float(((frame["y"] - grand) ** 2).sum())
    if ss_total <= 0:
        return None
    grouped = frame.groupby("g", sort=True)["y"]
    ss_between = float((grouped.count() * (grouped.mean() - grand) ** 2).sum())
    return float(min(1.0, max(0.0, ss_between / ss_total)))


def iqr_outlier_mask(x: pd.Series, k: float = 1.5) -> pd.Series:
    """Boolean mask of values outside [Q1 - k*IQR, Q3 + k*IQR] (missing values are False)."""
    xf = as_float(x)
    valid = xf.dropna()
    if len(valid) < 4:
        return pd.Series(False, index=x.index)
    q1, q3 = valid.quantile(0.25), valid.quantile(0.75)
    iqr = q3 - q1
    lo, hi = q1 - k * iqr, q3 + k * iqr
    return ((xf < lo) | (xf > hi)).fillna(False)


def count_histogram_peaks(x: pd.Series, bins: int = 20, min_rel_height: float = 0.10) -> int | None:
    """Heuristic count of modes from a smoothed histogram (labelled as a heuristic in reports).

    Returns None when there are too few values or too few distinct values to say anything.
    A peak must reach ``min_rel_height`` of the tallest bar, and two neighbouring peaks only
    count separately if the valley between them dips below 80% of the smaller peak.
    """
    xf = as_float(x).dropna()
    xf = xf[np.isfinite(xf)]
    if len(xf) < 30 or xf.nunique() < 10:
        return None
    counts, _ = np.histogram(xf.to_numpy(), bins=bins)
    padded = np.concatenate([[counts[0]], counts, [counts[-1]]]).astype("float64")
    smooth = np.convolve(padded, np.ones(3) / 3.0, mode="valid")
    if smooth.max() <= 0:
        return None
    thresh = min_rel_height * smooth.max()
    candidates: list[int] = []
    for i in range(len(smooth)):
        left = smooth[i - 1] if i > 0 else -np.inf
        right = smooth[i + 1] if i < len(smooth) - 1 else -np.inf
        if smooth[i] >= thresh and smooth[i] > left and smooth[i] >= right:
            candidates.append(i)
    if not candidates:
        return 1
    peaks = [candidates[0]]
    for c in candidates[1:]:
        prev = peaks[-1]
        valley = smooth[prev : c + 1].min()
        if valley < 0.8 * min(smooth[prev], smooth[c]):
            peaks.append(c)
        elif smooth[c] > smooth[prev]:
            peaks[-1] = c
    return len(peaks)


def imbalance_label(minority_frac: float, ratio: float, highly_threshold: float = 0.10) -> str:
    """Plain label for class balance.

    highly imbalanced: smallest class < ``highly_threshold`` of rows;
    mildly imbalanced: largest/smallest class ratio >= 1.5; otherwise balanced.
    """
    if minority_frac < highly_threshold:
        return "highly imbalanced"
    if ratio >= 1.5:
        return "mildly imbalanced"
    return "balanced"


def upper_pairs(corr: pd.DataFrame) -> list[tuple[str, str, float]]:
    """All (a, b, value) pairs from the upper triangle of a square matrix, skipping NaN."""
    cols = list(corr.columns)
    out: list[tuple[str, str, float]] = []
    for i in range(len(cols)):
        for j in range(i + 1, len(cols)):
            v = corr.iat[i, j]
            if v is None or (isinstance(v, float) and math.isnan(v)):
                continue
            out.append((cols[i], cols[j], float(v)))
    return out


def safe_round(value: Any, digits: int = 3) -> float | None:
    """Round floats; turn NaN/inf/None into None."""
    if value is None:
        return None
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(v):
        return None
    return round(v, digits)


def pct(part: float, whole: float, digits: int = 2) -> float:
    """Percentage (0-100) rounded to ``digits``; 0 when the whole is 0."""
    if not whole:
        return 0.0
    return round(100.0 * float(part) / float(whole), digits)


def jsonable(obj: Any) -> Any:
    """Convert numpy/pandas scalars and containers to plain JSON-safe Python objects."""
    if isinstance(obj, dict):
        return {str(k): jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [jsonable(v) for v in obj]
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating, float)):
        f = float(obj)
        return f if math.isfinite(f) else None
    if isinstance(obj, (np.bool_,)):
        return bool(obj)
    if obj is pd.NA or obj is pd.NaT:
        return None
    if isinstance(obj, pd.Timestamp):
        return obj.isoformat()
    return obj
