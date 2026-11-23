"""Validated Findings tab: expandable cards with charts, plain language explanations, and stats."""

from __future__ import annotations

from pathlib import Path
from veridata.agent.session import Session
from veridata.app.compat import st
from veridata.contracts.findings import Finding
from veridata.reporting.facts import FactRegistry, build_facts
from veridata.reporting.narration import explain_finding


def render_findings(sess: Session | None) -> None:
    """Render list of validated discoveries with transparent traceability."""
    if sess is None:
        st.info("Load a dataset to view validated discoveries.")
        return

    findings = sess.get_findings()
    validated = [f for f in findings if f.decision.accepted]

    st.subheader(f"Validated Discoveries ({len(validated)})")

    if not validated:
        st.info("No discoveries passed the validation layer (FDR control & effect size floor). "
                "See the 'Rejected Patterns' tab to inspect why unvalidated patterns were filtered out.")
        return

    # Sort validated by comparable effect size descending
    sorted_findings = sorted(
        validated,
        key=lambda f: f.test.effect.value if f.test.effect else 0.0,
        reverse=True,
    )

    for idx, f in enumerate(sorted_findings, 1):
        col_a = f.hypothesis.column_a
        col_b = f.hypothesis.column_b
        eff = f.test.effect
        eff_str = f"{eff.name}: {eff.value:.2f} ({eff.magnitude})" if eff else "N/A"
        q_val = f.decision.q_value
        q_str = f"q = {q_val:.3e}" if q_val is not None else "N/A"

        header_label = f"#{idx} — {col_a} ↔ {col_b} | {eff_str} | {q_str}"

        with st.expander(header_label, expanded=(idx == 1)):
            c1, c2 = st.columns([3, 2])

            with c1:
                reg = FactRegistry()
                reg.add_many(f.facts or build_facts(f), finding_id=f.hypothesis.id)
                exp = explain_finding(f, registry=reg)

                st.markdown("**Plain-Language Explanation:**")
                st.markdown(f"> {exp.text}")

                st.markdown("**Statistical Details:**")
                st.markdown(
                    f"- **Test Executed:** `{f.test.test_name}`\n"
                    f"- **Raw p-value:** `{f.test.p_value:.3e}`\n"
                    f"- **FDR-adjusted q-value:** `{q_str}`\n"
                    f"- **Sample size (complete pairwise):** `{f.test.n_used:,}`\n"
                    f"- **Validation verdict:** `Validated Discovery (FDR alpha 0.05)`"
                )

            with c2:
                # Chart
                chart_path = sess.out_dir / f"{f.hypothesis.id}.png"
                if chart_path.exists():
                    st.image(str(chart_path), caption=f"{col_a} vs {col_b}", use_container_width=True)
                else:
                    st.caption("Distribution plot generated during test.")
