"""Multiple-testing correction procedures (Phase 3 Section 7.1)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np

from veridata.errors import ValidationError


@dataclass(frozen=True)
class CorrectionOutput:
    """Result of multiple-testing p-value adjustment over a family of size m."""

    p_values: np.ndarray
    q_values: np.ndarray
    reject_mask: np.ndarray
    ranks: np.ndarray
    m: int
    method: str
    alpha: float


def apply_correction(
    p_values: Sequence[float] | np.ndarray,
    method: str = "bh",
    alpha: float = 0.05,
) -> CorrectionOutput:
    """Apply multiple-testing correction (bh, by, holm, bonferroni, none).

    Benjamini-Hochberg is implemented from scratch and cross-checked against
    ``statsmodels.stats.multitest.multipletests(method='fdr_bh')`` in tests.
    """
    p = np.asarray(p_values, dtype=float)
    m = int(p.size)
    if m == 0:
        empty_f = np.array([], dtype=float)
        return CorrectionOutput(
            p_values=empty_f,
            q_values=empty_f,
            reject_mask=np.array([], dtype=bool),
            ranks=np.array([], dtype=int),
            m=0,
            method=method,
            alpha=alpha,
        )

    if not np.all(np.isfinite(p)):
        raise ValidationError("Non-finite p-values cannot enter multiple-testing correction.")

    p_clamped = np.clip(p, 0.0, 1.0)
    order = np.argsort(p_clamped, kind="mergesort")
    p_sorted = p_clamped[order]

    ranks = np.empty(m, dtype=int)
    ranks[order] = np.arange(1, m + 1, dtype=int)

    k = np.arange(1, m + 1, dtype=float)

    if method == "bh":
        raw_q = (m / k) * p_sorted
        q_sorted = np.minimum.accumulate(raw_q[::-1])[::-1]
        q_sorted = np.clip(q_sorted, 0.0, 1.0)
        q = np.empty(m, dtype=float)
        q[order] = q_sorted
    elif method == "by":
        c_m = float(np.sum(1.0 / k))
        raw_q = (m * c_m / k) * p_sorted
        q_sorted = np.minimum.accumulate(raw_q[::-1])[::-1]
        q_sorted = np.clip(q_sorted, 0.0, 1.0)
        q = np.empty(m, dtype=float)
        q[order] = q_sorted
    elif method == "holm":
        raw_q = (m - np.arange(m, dtype=float)) * p_sorted
        q_sorted = np.maximum.accumulate(raw_q)
        q_sorted = np.clip(q_sorted, 0.0, 1.0)
        q = np.empty(m, dtype=float)
        q[order] = q_sorted
    elif method == "bonferroni":
        q = np.clip(p_clamped * m, 0.0, 1.0)
    elif method == "none":
        q = p_clamped.copy()
    else:
        raise ValidationError(f"Unsupported multiple-testing correction method: '{method}'.")

    reject_mask = q <= alpha
    return CorrectionOutput(
        p_values=p_clamped,
        q_values=q,
        reject_mask=reject_mask,
        ranks=ranks,
        m=m,
        method=method,
        alpha=alpha,
    )

