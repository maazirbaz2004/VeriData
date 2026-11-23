"""Naive vs. Validated comparison: highlight the core thesis of the project."""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from veridata.agent.session import Session
from veridata.app.compat import st
from veridata.reporting.charts import PALETTE, setup_style


def render_naive_vs_validated(sess: Session | None) -> None:
    """Compare uncorrected raw p-value results against FDR-validated discoveries."""
    if sess is None:
        st.info("Load a dataset to view the Naive vs. Validated comparison.")
        return

    findings = sess.get_findings()
    rejected = sess.get_rejected()

    # Calculate metrics
    m_total = len(findings) + len(rejected)
    n_raw_significant = sum(
        1 for f in findings if f.test.p_value is not None and f.test.p_value < 0.05
    ) + sum(
        1 for r in rejected if r.get("p_raw") is not None and r.get("p_raw") < 0.05
    )
    n_validated = sum(1 for f in findings if f.decision.accepted)
    n_false_discoveries_stopped = max(0, n_raw_significant - n_validated)

    st.subheader("The VeriData Guarantee: Naive Analysis vs. Validated Discoveries")

    # Headline contrast cards
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Tests Evaluated", m_total)
    c2.metric("Naive 'Discoveries' (raw p < 0.05)", n_raw_significant, delta="False Positive Hazard", delta_color="inverse")
    c3.metric("VeriData Validated (BH FDR)", n_validated, delta="True Discoveries")
    c4.metric("Spurious Patterns Blocked", n_false_discoveries_stopped, delta="Protected by VeriData")

    st.divider()

    # Visual BH Plot
    st.markdown("#### Multiple-Testing Correction Plot (Sorted p-values vs. Benjamini-Hochberg Boundary)")

    all_p_values = []
    for f in findings:
        if f.test.p_value is not None:
            all_p_values.append(f.test.p_value)
    for r in rejected:
        p = r.get("p_raw")
        if p is not None:
            all_p_values.append(p)

    if len(all_p_values) >= 2:
        setup_style()
        fig, ax = plt.subplots(figsize=(7.0, 3.8))
        sorted_p = np.sort(all_p_values)
        m = len(sorted_p)
        ranks = np.arange(1, m + 1)
        bh_line = (ranks / m) * 0.05

        ax.plot(ranks, sorted_p, "o-", color=PALETTE[0], label="Observed p-values (sorted)", markersize=4, alpha=0.7)
        ax.plot(ranks, bh_line, "--", color=PALETTE[1], label="BH Critical Threshold (α = 0.05)", linewidth=2)
        ax.axhline(0.05, linestyle=":", color="gray", label="Naive α = 0.05 (Uncorrected)")

        ax.set_xlabel("Hypothesis Rank in Family")
        ax.set_ylabel("p-value")
        ax.set_title("Benjamini-Hochberg Multiple-Testing Control")
        ax.legend(loc="upper left")
        fig.tight_layout()

        st.pyplot(fig)
        plt.close(fig)
    else:
        st.caption("Perform multiple tests to see the Benjamini-Hochberg curve.")
