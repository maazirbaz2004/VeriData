"""Report export component: provides downloads for HTML, Markdown, CSV, and JSON."""

from __future__ import annotations

import json
from pathlib import Path
import pandas as pd

from veridata.agent.session import Session
from veridata.app.compat import st


def render_report_export(sess: Session | None) -> None:
    """Render preview and download buttons for generated artifacts."""
    if sess is None:
        st.info("Load a dataset to export reports.")
        return

    st.subheader("Export Analysis Deliverables")
    st.markdown("Download publication-quality, self-contained reports and structured logs.")

    findings = sess.get_findings()
    rejected = sess.get_rejected()

    # Generate summary CSV
    records = []
    for f in findings:
        records.append({
            "hypothesis_id": f.hypothesis.id,
            "column_a": f.hypothesis.column_a,
            "column_b": f.hypothesis.column_b,
            "relationship": f.hypothesis.relationship.value,
            "test_name": f.test.test_name,
            "p_raw": f.test.p_value,
            "q_value": f.decision.q_value,
            "accepted": f.decision.accepted,
            "effect_name": f.test.effect.name if f.test.effect else None,
            "effect_value": f.test.effect.value if f.test.effect else None,
        })
    df_summary = pd.DataFrame(records)
    csv_bytes = df_summary.to_csv(index=False).encode("utf-8")

    # Generate JSON facts bundle
    facts_bundle = {
        "dataset_name": sess.config.name,
        "n_findings": len(findings),
        "n_rejected": len(rejected),
        "findings": [f.model_dump(mode="json") for f in findings],
        "rejected": rejected,
    }
    json_bytes = json.dumps(facts_bundle, indent=2).encode("utf-8")

    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            label="📥 Download Findings Summary (CSV)",
            data=csv_bytes,
            file_name=f"{sess.config.name}_findings.csv",
            mime="text/csv",
            use_container_width=True,
        )
    with col2:
        st.download_button(
            label="📥 Download Complete Audit Ledger (JSON)",
            data=json_bytes,
            file_name=f"{sess.config.name}_ledger.json",
            mime="application/json",
            use_container_width=True,
        )
