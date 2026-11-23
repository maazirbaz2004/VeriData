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

    repo_demo_dir = Path(__file__).resolve().parents[4] / "data" / "demo"
    demo_dir = repo_demo_dir if repo_demo_dir.exists() else Path("data/demo")
    loaded_df = None
    loaded_name = None

    demo_choices = [
        (col1, "Insurance", "btn_insurance", "insurance.csv", "insurance"),
        (col1, "Pure Noise", "btn_noise", "pure_noise.csv", "pure_noise"),
        (col2, "Messy Data", "btn_messy", "messy.csv", "messy_synthetic"),
        (col2, "Telco Churn", "btn_telco", "telco_churn.csv", "telco_churn"),
    ]
    for col, label, key, filename, ds_name in demo_choices:
        if col.button(label, key=key, use_container_width=True):
            p = demo_dir / filename
            if p.exists():
                try:
                    loaded_df = pd.read_csv(p)
                    loaded_name = ds_name
                except Exception as exc:
                    st.sidebar.error(f"Error loading demo dataset '{filename}': {exc}")
            else:
                st.sidebar.error(f"Demo dataset not found at: {p}")

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
        try:
            initialize_session(
                df=loaded_df,
                dataset_name=loaded_name,
                alpha=settings.get("alpha", 0.05),
                correction=settings.get("correction", "bh"),
                effect_floor=settings.get("effect_floor", True),
                offline_mode=settings.get("offline_demo", True),
            )
            st.sidebar.success(
                f"Loaded '{loaded_name}' ({len(loaded_df):,} rows x {len(loaded_df.columns)} cols)"
            )
        except Exception as exc:
            st.sidebar.error(f"Failed to initialize session: {exc}")

    return st.session_state.get("df")
