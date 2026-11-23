"""Facts viewer component: answers 'Where did this number come from?' (Section 3)."""

from __future__ import annotations

import pandas as pd
from veridata.agent.session import Session
from veridata.app.compat import st


def render_facts_viewer(sess: Session | None) -> None:
    """Examine underlying fact registry and traceable sources for every number."""
    if sess is None:
        st.info("Load a dataset to inspect verified facts.")
        return

    findings = sess.get_findings()
    st.subheader("Traceability: Where Did This Number Come From?")
    st.markdown(
        "VeriData enforces strict machine verification: every numeric value in reports and chat answers "
        "is traceable to a registered Fact computed deterministically by the statistical tools library."
    )

    if not findings:
        st.info("No findings evaluated in this session yet.")
        return

    options = {f"{f.hypothesis.column_a} vs {f.hypothesis.column_b} ({f.hypothesis.id})": f for f in findings}
    chosen_label = st.selectbox("Select finding to inspect facts:", list(options.keys()))

    if chosen_label:
        finding = options[chosen_label]
        records = []
        for fact in finding.facts:
            records.append({
                "Fact Key": fact.key,
                "Displayed String": fact.display,
                "Numeric Value": str(fact.value),
                "Source Origin": fact.source,
                "Unit": fact.unit or "—",
            })

        st.dataframe(pd.DataFrame(records), use_container_width=True)
