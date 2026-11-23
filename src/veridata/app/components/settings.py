"""Sidebar settings component: alpha, correction method, effect floor, and privacy notice."""

from __future__ import annotations

from typing import Any
from veridata.app.compat import st


def render_settings() -> dict[str, Any]:
    """Render sidebar controls and return resolved configuration dictionary."""
    st.sidebar.markdown("### VeriData Controls")

    with st.sidebar.expander("Validation Settings", expanded=False):
        alpha = st.slider("FDR Alpha Level", min_value=0.01, max_value=0.20, value=0.05, step=0.01)
        correction = st.selectbox("Multiple-Testing Correction", options=["bh", "by", "bonferroni", "holm"], index=0)
        effect_floor = st.checkbox("Standardized Effect Floor", value=True)
        offline_demo = st.checkbox("Offline Demo Mode", value=True)

    st.sidebar.divider()
    st.sidebar.markdown(
        "<small>**Privacy Notice**: In offline demo mode, all computation runs locally with zero external network calls. "
        "When LLM is enabled, only column names and profile summaries are transmitted; raw row values are never sent.</small>",
        unsafe_allow_html=True,
    )

    return {
        "alpha": alpha,
        "correction": correction,
        "effect_floor": effect_floor,
        "offline_demo": offline_demo,
    }
