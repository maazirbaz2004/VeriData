"""Tests for agent state schemas, DataStore copy isolation, and checkpointing."""

import pandas as pd
import pytest

from veridata.agent.checkpoint import get_checkpointer
from veridata.agent.datastore import DataStore, GLOBAL_DATASTORE
from veridata.agent.state import BatchState, ChatState, FocusState, append_list, merge_dicts


def test_datastore_copy_isolation():
    ds = DataStore()
    df = pd.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]})
    key = ds.put(df)

    retrieved = ds.get(key)
    retrieved["a"] = [10, 20, 30]

    # Original in datastore must be untouched
    original = ds.get(key)
    assert original["a"].tolist() == [1, 2, 3]


def test_datastore_artifacts():
    ds = DataStore()
    ds.put_artifact("art1", {"model": "test", "val": 42})
    assert ds.get_artifact("art1") == {"model": "test", "val": 42}
    assert ds.get_artifact("non_existent") is None


def test_state_reducers():
    d1 = {"a": 1}
    d2 = {"b": 2}
    merged = merge_dicts(d1, d2)
    assert merged == {"a": 1, "b": 2}

    l1 = [1, 2]
    l2 = [3, 4]
    appended = append_list(l1, l2)
    assert appended == [1, 2, 3, 4]


def test_focus_state_defaults():
    focus = FocusState()
    assert focus.columns == []
    assert focus.hypothesis_id is None
    assert focus.finding_id is None
    assert focus.last_chart_path is None


def test_checkpointer_creation(tmp_path):
    cp_mem = get_checkpointer(None)
    assert cp_mem is not None

    cp_file = get_checkpointer(tmp_path)
    assert cp_file is not None
