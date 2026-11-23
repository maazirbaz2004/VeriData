"""Dataset upload and pre-loaded sample dataset selector."""

from __future__ import annotations

import io
from pathlib import Path
from typing import Any

import pandas as pd

from veridata.app.compat import st
from veridata.app.session import initialize_session


def render_upload_and_samples(settings: dict[str, Any]) -> pd.DataFrame | None:
    """Render upload options and demo buttons; return active DataFrame if loaded."""
    st.sidebar.markdown("### Dataset Source")

    # Sample dataset buttons
    st.sidebar.markdown("**Load Demo Dataset:**")
    col1, col2 = st.sidebar.columns(2)

    demo_dir = Path("data/demo")
    loaded_df = None
    loaded_name = None

    with col1:
        if st.button("Insurance", key="btn_insurance", use_container_width=True):
            p = demo_dir / "insurance.csv"
            if p.exists():
                loaded_df = pd.read_csv(p)
                loaded_name = "insurance"
        if st.button("Pure Noise", key="btn_noise", use_container_width=True):
            p = demo_dir / "pure_noise.csv"
            if p.exists():
                loaded_df = pd.read_csv(p)
                loaded_name = "pure_noise"

    with col2:
        if st.button("Messy Data", key="btn_messy", use_container_width=True):
            p = demo_dir / "messy.csv"
            if p.exists():
                loaded_df = pd.read_csv(p)
                loaded_name = "messy_synthetic"
        if st.button("Telco Churn", key="btn_telco", use_container_width=True):
            p = demo_dir / "telco_churn.csv"
            if p.exists():
                loaded_df = pd.read_csv(p)
                loaded_name = "telco_churn"

    st.sidebar.divider()
    uploaded_file = st.sidebar.file_uploader("Or Upload Custom CSV", type=["csv"])

    if uploaded_file is not None:
        try:
            # Enforce size limits: max 50 MB
            if uploaded_file.size > 50 * 1024 * 1024:
                st.sidebar.error("File exceeds 50 MB limit. Please upload a smaller sample.")
                return None
            loaded_df = pd.read_csv(uploaded_file)
            loaded_name = Path(uploaded_file.name).stem
        except Exception as exc:
            st.sidebar.error(f"Error reading CSV: {exc}")
            return None

    if loaded_df is not None and loaded_name is not None:
        initialize_session(
            df=loaded_df,
            dataset_name=loaded_name,
            alpha=settings.get("alpha", 0.05),
            correction=settings.get("correction", "bh"),
            effect_floor=settings.get("effect_floor", True),
            offline_mode=settings.get("offline_demo", True),
        )
        st.sidebar.success(f"Loaded '{loaded_name}' ({len(loaded_df):,} rows x {len(loaded_df.columns)} cols)")

    return st.session_state.get("df")
