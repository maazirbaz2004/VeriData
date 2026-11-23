"""Dataset Overview tab: row/col metrics, column types table, missingness, and cleaning log."""

from __future__ import annotations

import pandas as pd
from veridata.agent.session import Session
from veridata.app.compat import st


def render_overview(sess: Session | None) -> None:
    """Display profile, dimensions, column types, and missingness."""
    if sess is None:
        st.info("Upload a CSV file or select a demo dataset in the sidebar to view overview.")
        return

    df = sess.df
    st.subheader(f"Dataset Overview — `{sess.config.name}`")

    # Metrics
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Rows", f"{len(df):,}")
    m2.metric("Columns", len(df.columns))
    n_numeric = sum(1 for c in df.columns if pd.api.types.is_numeric_dtype(df[c]))
    m3.metric("Numeric Columns", n_numeric)
    m4.metric("Categorical Columns", len(df.columns) - n_numeric)

    st.divider()

    # Column inspection table
    st.markdown("#### Column Inventory & Types")
    col_records = []
    for col in sorted(df.columns):
        col_records.append({
            "Column": col,
            "Type": str(df[col].dtype),
            "Unique Values": int(df[col].nunique()),
            "Missing Count": int(df[col].isna().sum()),
            "Missing %": f"{df[col].isna().mean() * 100:.1f}%",
        })
    st.dataframe(pd.DataFrame(col_records), use_container_width=True)

    # Missingness summary
    total_missing = df.isna().sum().sum()
    if total_missing > 0:
        st.markdown("#### Missingness Summary")
        missing_series = df.isna().sum()[lambda x: x > 0].sort_values(ascending=False)
        st.dataframe(missing_series.to_frame("Missing Count"), use_container_width=True)
