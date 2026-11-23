"""Chat panel component with conversational interaction, follow-up buttons, and verification badges."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from veridata.agent.session import Session
from veridata.app.compat import st


def render_chat(sess: Session | None) -> None:
    """Render interactive conversational panel with verified numbers and follow-ups."""
    if sess is None:
        st.info("Load a dataset to begin chatting with your data.")
        return

    st.subheader("Chat with Your Data")
    ledger_status = sess.get_ledger_status()
    st.caption(
        f"Multiple-Testing Family: `{ledger_status.get('total_tests', 0)}` tests evaluated · "
        f"`{ledger_status.get('accepted_count', 0)}` validated discoveries · "
        f"FDR `α = 0.05`"
    )

    history = st.session_state.get("chat_history", [])

    # Display past messages
    for msg in history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg.get("charts"):
                for cp in msg["charts"]:
                    if Path(cp).exists():
                        st.image(cp, use_container_width=True)
            if msg.get("verified") and msg["role"] == "assistant":
                st.markdown("<small style='color:green;'>✓ Numbers verified against FactRegistry</small>", unsafe_allow_html=True)

    # Chat input
    user_input = st.chat_input("Ask a question (e.g. 'Compare charges by smoker', 'What are the findings?')")

    if user_input:
        history.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        with st.chat_message("assistant"):
            answer = sess.ask(user_input)
            st.markdown(answer.text)
            if answer.charts:
                for cp in answer.charts:
                    if Path(cp).exists():
                        st.image(cp, use_container_width=True)
            if answer.verified:
                st.markdown("<small style='color:green;'>✓ Numbers verified against FactRegistry</small>", unsafe_allow_html=True)

            # Record in history
            history.append({
                "role": "assistant",
                "content": answer.text,
                "charts": answer.charts,
                "verified": answer.verified,
                "followups": answer.followups,
            })
            st.session_state["chat_history"] = history

            # Render suggested follow-ups
            if answer.followups:
                st.markdown("**Suggested Follow-ups:**")
                for f_idx, follow in enumerate(answer.followups):
                    if st.button(f"👉 {follow.get('label')}", key=f"fup_{len(history)}_{f_idx}"):
                        f_ans = sess.run_followup(follow)
                        history.append({"role": "user", "content": f"Follow-up: {follow.get('label')}"})
                        history.append({
                            "role": "assistant",
                            "content": f_ans.text,
                            "charts": f_ans.charts,
                            "verified": f_ans.verified,
                            "followups": f_ans.followups,
                        })
                        st.session_state["chat_history"] = history
