"""Live stage progress tracker powered by LangGraph batch streaming."""

from __future__ import annotations

from typing import Callable
from veridata.agent.session import Session
from veridata.app.compat import st


def run_analysis_with_progress(sess: Session) -> bool:
    """Execute batch graph and render streaming status messages."""
    with st.status("Running VeriData Validation Pipeline...", expanded=True) as status_box:
        def on_progress(msg: str):
            st.write(f"- {msg}")

        try:
            res = sess.run_batch(progress_callback=on_progress)
            if res.get("status") == "done":
                status_box.update(label="Validation Pipeline Complete!", state="complete", expanded=False)
                st.session_state["analysis_done"] = True
                return True
            else:
                status_box.update(label="Analysis completed with warnings.", state="error")
                return False
        except Exception as exc:
            status_box.update(label=f"Pipeline error: {exc}", state="error")
            return False
