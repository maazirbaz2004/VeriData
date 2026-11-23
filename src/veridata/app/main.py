"""VeriData Streamlit application main entrypoint (Phase 7 Section 3)."""

from __future__ import annotations

from veridata.app.compat import st
from veridata.app.components.chat import render_chat
from veridata.app.components.facts_viewer import render_facts_viewer
from veridata.app.components.findings import render_findings
from veridata.app.components.naive_vs_validated import render_naive_vs_validated
from veridata.app.components.overview import render_overview
from veridata.app.components.progress import run_analysis_with_progress
from veridata.app.components.rejected import render_rejected
from veridata.app.components.report_export import render_report_export
from veridata.app.components.settings import render_settings
from veridata.app.components.upload import render_upload_and_samples
from veridata.app.session import get_current_session


def main():
    st.set_page_config(
        page_title="VeriData — Agentic Data Scientist",
        page_icon="🔬",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # Sidebar
    st.sidebar.title("🔬 VeriData")
    st.sidebar.caption("Deterministic Ingestion · Fixed Statistical Tools · FDR Control")

    settings = render_settings()
    render_upload_and_samples(settings)

    sess = get_current_session()

    # Main Area
    st.title("VeriData: Trustworthy Agentic Data Scientist")
    st.markdown(
        "Upload a dataset to automatically profile, test hypotheses with unit-tested statistical tools, "
        "and control False Discovery Rate (FDR) so you only see validated discoveries."
    )

    if sess is not None:
        # Trigger batch analysis button if not yet run
        is_done = st.session_state.get("analysis_done", False)
        if not is_done:
            c1, c2 = st.columns([1, 3])
            with c1:
                if st.button("🚀 Run Full Analysis Pipeline", type="primary", use_container_width=True):
                    run_analysis_with_progress(sess)
            with c2:
                st.caption(f"Ready to analyze `{sess.config.name}` ({len(sess.df):,} rows x {len(sess.df.columns)} columns).")

    # 7 Primary Main Area Tabs
    tab_names = [
        "📊 Overview",
        "✅ Validated Findings",
        "🛡️ Rejected Patterns",
        "⚖️ Naive vs. Validated",
        "💬 Chat",
        "🔍 Facts & Traceability",
        "📥 Report & Export",
    ]
    tabs = st.tabs(tab_names)

    with tabs[0]:
        render_overview(sess)

    with tabs[1]:
        render_findings(sess)

    with tabs[2]:
        render_rejected(sess)

    with tabs[3]:
        render_naive_vs_validated(sess)

    with tabs[4]:
        render_chat(sess)

    with tabs[5]:
        render_facts_viewer(sess)

    with tabs[6]:
        render_report_export(sess)


if __name__ == "__main__":
    main()
