"""State checkpointing helpers for LangGraph workflows (MemorySaver & SQLite)."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from langgraph.checkpoint.memory import MemorySaver

logger = logging.getLogger("veridata.agent.checkpoint")


def get_checkpointer(session_dir: Path | str | None = None) -> Any:
    """Return a checkpointer instance. Defaults to MemorySaver."""
    # SQLiteSaver can be used if available and requested; MemorySaver is reliable and portable
    if session_dir is not None:
        try:
            from langgraph.checkpoint.sqlite import SqliteSaver
            db_path = Path(session_dir) / "checkpoint.db"
            db_path.parent.mkdir(parents=True, exist_ok=True)
            # SqliteSaver.from_conn_string works in langgraph
            return SqliteSaver.from_conn_string(str(db_path))
        except (ImportError, Exception) as exc:
            logger.debug("SqliteSaver unavailable (%s); using MemorySaver.", exc)
            return MemorySaver()
    return MemorySaver()
