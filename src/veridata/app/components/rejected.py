"""Rejected Patterns tab: showcases why chance patterns and small effects are filtered out."""

from __future__ import annotations

import pandas as pd
from veridata.agent.session import Session
from veridata.app.compat import st


def render_rejected(sess: Session | None) -> None:
    """Display table of rejected hypotheses with plain-language rejection reasons."""
    if sess is None:
        st.info("Load a dataset to view rejected patterns.")
        return

    rejected = sess.get_rejected()
    st.subheader(f"Filtered Patterns ({len(rejected)} Rejected)")

    st.markdown(
        "A standard unvalidated analyst or naive LLM reports every pattern with raw p < 0.05. "
        "VeriData applies Benjamini-Hochberg FDR correction and effect-size floors to reject false discoveries."
    )

    if not rejected:
        st.success("No patterns were rejected in this session.")
        return

    # Format table
    records = []
    for r in rejected:
        records.append({
            "Hypothesis ID": r.get("hypothesis_id"),
            "Raw p": f"{r.get('p_raw'):.3e}" if r.get("p_raw") is not None else "N/A",
            "FDR q": f"{r.get('q_value'):.3e}" if r.get("q_value") is not None else "N/A",
            "Primary Reason": r.get("reasons", ["unspecified"])[0],
            "Explanation": r.get("reason_text", "Failed statistical threshold."),
        })

    df_rej = pd.DataFrame(records)

    # Filter by reason
    all_reasons = ["All"] + sorted(list({rec["Primary Reason"] for rec in records}))
    sel_reason = st.selectbox("Filter by rejection reason:", options=all_reasons)

    if sel_reason != "All":
        df_rej = df_rej[df_rej["Primary Reason"] == sel_reason]

    st.dataframe(df_rej, use_container_width=True)
