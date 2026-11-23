"""Streamlit session_state wrapper around veridata.agent.Session (Phase 7 Section 3)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

import pandas as pd

from veridata.agent.session import Session, create_session
from veridata.app.compat import st
from veridata.config import PipelineConfig


def get_current_session() -> Session | None:
    """Retrieve active VeriData Session from Streamlit session_state."""
    return st.session_state.get("session")


def initialize_session(
    df: pd.DataFrame,
    dataset_name: str = "dataset",
    alpha: float = 0.05,
    correction: str = "bh",
    effect_floor: bool = True,
    offline_mode: bool = True,
) -> Session:
    """Initialize a new VeriData session and persist in Streamlit session_state."""
    cfg = PipelineConfig(
        name=dataset_name,
        stats={
            "alpha": alpha,
            "correction": correction,
        },
    )

    out_dir = Path(f"outputs/ui_sessions/{dataset_name}")
    sess = create_session(df, cfg, out_dir=out_dir)

    st.session_state["session"] = sess
    st.session_state["dataset_name"] = dataset_name
    st.session_state["df"] = df
    st.session_state["analysis_done"] = False
    st.session_state["chat_history"] = []
    return sess


def reset_session() -> None:
    """Reset the current UI session and clear cached state."""
    st.session_state["session"] = None
    st.session_state["df"] = None
    st.session_state["analysis_done"] = False
    st.session_state["chat_history"] = []
