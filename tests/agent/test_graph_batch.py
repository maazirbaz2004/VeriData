"""Tests for batch graph end-to-end execution and streaming progress."""

from pathlib import Path
import pandas as pd
import pytest

from veridata.agent.session import create_session
from veridata.config import PipelineConfig


def test_batch_graph_execution(tmp_path):
    csv_path = tmp_path / "test_data.csv"
    df = pd.DataFrame({
        "age": [25, 30, 45, 50, 22, 60, 35, 40],
        "charges": [1200.0, 1500.0, 4000.0, 4500.0, 1100.0, 5200.0, 2100.0, 3000.0],
        "smoker": ["no", "no", "yes", "yes", "no", "yes", "no", "no"],
        "region": ["north", "south", "north", "south", "east", "west", "east", "west"],
    })
    df.to_csv(csv_path, index=False)

    cfg = PipelineConfig(
        name="batch_test",
        file=str(csv_path),
    )

    sess = create_session(df, cfg, out_dir=tmp_path)
    progress_messages = []

    def on_progress(msg: str):
        progress_messages.append(msg)

    res = sess.run_batch(progress_callback=on_progress)

    assert res.get("status") == "done"
    assert len(progress_messages) >= 4
    assert (tmp_path / "report.md").exists() or Path("outputs/batch_test/report.md").exists()
