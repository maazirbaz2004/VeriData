"""In-memory DataStore keeping DataFrames and large artifacts decoupled from LangGraph state."""

from __future__ import annotations

import logging
import uuid
from typing import Any

import pandas as pd

logger = logging.getLogger("veridata.agent.datastore")


class DataStore:
    """Storage manager holding in-memory DataFrames and serialized artifacts by unique id."""

    def __init__(self) -> None:
        self._frames: dict[str, pd.DataFrame] = {}
        self._artifacts: dict[str, Any] = {}

    def put(self, df: pd.DataFrame, key: str | None = None) -> str:
        """Store a DataFrame; returns the access key."""
        k = key or f"df_{uuid.uuid4().hex[:12]}"
        self._frames[k] = df.copy()
        return k

    def get(self, key: str) -> pd.DataFrame:
        """Retrieve a copy of the stored DataFrame (tools never mutate the original)."""
        if key not in self._frames:
            raise KeyError(f"DataStore has no DataFrame with key '{key}'.")
        return self._frames[key].copy()

    def exists(self, key: str) -> bool:
        return key in self._frames

    def put_artifact(self, key: str, artifact: Any) -> None:
        self._artifacts[key] = artifact

    def get_artifact(self, key: str) -> Any:
        return self._artifacts.get(key)

    def clear(self) -> None:
        self._frames.clear()
        self._artifacts.clear()


# Global default store for process-local convenience
GLOBAL_DATASTORE = DataStore()
