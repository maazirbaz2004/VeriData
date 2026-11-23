"""High-level Session API bridging UI (Phase 7) and evaluation (Phase 8) to LangGraph agents."""

from __future__ import annotations

import logging
import uuid
from pathlib import Path
from typing import Any, Callable

import pandas as pd
from pydantic import BaseModel, Field

from veridata.agent.checkpoint import get_checkpointer
from veridata.agent.datastore import GLOBAL_DATASTORE, DataStore
from veridata.agent.graph_batch import build_batch_graph
from veridata.agent.graph_chat import build_chat_graph
from veridata.agent.llm import LLMClient, NullLLM
from veridata.agent.state import BatchState, ChatState, FocusState
from veridata.agent.tools import ToolRegistry, ToolResult
from veridata.config import PipelineConfig
from veridata.contracts.findings import Finding
from veridata.profiling import build_column_schema, profile_dataset
from veridata.schemas import ColumnSchemaEntry
from veridata.validation.ledger import SessionLedger

logger = logging.getLogger("veridata.agent.session")


class Answer(BaseModel):
    """Normalized response contract for user queries."""

    text: str
    charts: list[str] = Field(default_factory=list)
    facts_used: list[str] = Field(default_factory=list)
    verified: bool = True
    followups: list[dict[str, Any]] = Field(default_factory=list)
    source: str = "agent"


class Session:
    """Analytical session maintaining conversation state, testing ledger, and compiled graphs."""

    def __init__(
        self,
        df: pd.DataFrame,
        config: PipelineConfig,
        session_id: str | None = None,
        llm: LLMClient | None = None,
        out_dir: Path | str | None = None,
    ) -> None:
        self.session_id = session_id or f"sess_{uuid.uuid4().hex[:10]}"
        self.config = config
        self.llm = llm or NullLLM()
        self.out_dir = Path(out_dir) if out_dir else Path(f"outputs/sessions/{self.session_id}")
        self.out_dir.mkdir(parents=True, exist_ok=True)

        self.df = df.copy()
        self.dataset_id = GLOBAL_DATASTORE.put(self.df)
        self.profile = profile_dataset(self.df, dataset_name=config.name)
        self.schema = build_column_schema(self.profile, self.config)

        self.ledger = SessionLedger(
            dataset_sha256=self.profile.sha256,
            alpha=getattr(config.stats, "alpha", 0.05) if hasattr(config, "stats") else 0.05,
        )

        self.tools = ToolRegistry(
            df=self.df,
            schema=self.schema,
            config=self.config,
            ledger=self.ledger,
            session_dir=self.out_dir,
        )
        GLOBAL_DATASTORE.put_artifact(f"tools_{self.session_id}", self.tools)

        self.checkpointer = get_checkpointer(self.out_dir)
        self.chat_graph = build_chat_graph(checkpointer=self.checkpointer)
        self.batch_graph = build_batch_graph(checkpointer=self.checkpointer)

        # Chat state initialization
        self.state: ChatState = {
            "session_id": self.session_id,
            "dataset_id": self.dataset_id,
            "cleaned_dataset_id": self.dataset_id,
            "dataset_sha256": self.profile.sha256,
            "dataset_name": config.name,
            "schema": {k: v.model_dump(mode="json") for k, v in self.schema.items()},
            "profile_summary": {
                "n_rows": self.profile.n_rows,
                "n_cols": self.profile.n_cols,
                "columns": list(self.df.columns),
            },
            "messages": [],
            "user_input": "",
            "intent": None,
            "parsed_args": None,
            "pending_clarification": None,
            "focus": FocusState().model_dump(),
            "tool_calls_this_turn": 0,
            "last_tool_result": None,
            "ledger_path": str(self.out_dir / "ledger.jsonl"),
            "ledger_diff": [],
            "answer": None,
            "followups": [],
            "budget": {"tokens_left": 100_000, "tool_calls_left": 4},
            "errors": [],
        }

    def ask(self, user_message: str) -> Answer:
        """Send a message to the agent and receive a verified response."""
        self.state["user_input"] = user_message
        config_dict = {"configurable": {"thread_id": self.session_id}}

        # Run through chat graph
        final_state = self.chat_graph.invoke(self.state, config=config_dict)
        self.state.update(final_state)

        ans_dict = self.state.get("answer", {})
        followups = self.state.get("followups", [])

        return Answer(
            text=ans_dict.get("text", "I've processed your message."),
            charts=ans_dict.get("charts", []),
            facts_used=ans_dict.get("facts_used", []),
            verified=ans_dict.get("verified", True),
            followups=followups,
            source=ans_dict.get("source", "agent"),
        )

    def run_followup(self, tool_call: dict[str, Any]) -> Answer:
        """Execute a follow-up action directly, bypassing intent routing."""
        tool_name = tool_call.get("tool")
        arguments = tool_call.get("arguments", {})

        self.state["intent"] = tool_name
        self.state["parsed_args"] = arguments
        self.state["user_input"] = f"Run {tool_name}"

        return self.ask(f"Run {tool_name}")

    def run_batch(self, progress_callback: Callable[[str], None] | None = None) -> BatchState:
        """Execute the end-to-end batch analysis pipeline with streaming progress."""
        batch_state: BatchState = {
            "run_id": f"batch_{self.session_id}",
            "dataset_id": self.dataset_id,
            "dataset_name": self.config.name,
            "dataset_sha256": self.profile.sha256,
            "config": self.config.model_dump(mode="json"),
            "profile": self.profile.model_dump(mode="json"),
            "schema": {k: v.model_dump(mode="json") for k, v in self.schema.items()},
            "cleaning_log": [],
            "cleaned_dataset_id": self.dataset_id,
            "hypothesis_set": {},
            "results_path": "",
            "ledger_path": str(self.out_dir / "ledger.jsonl"),
            "decisions": [],
            "findings_path": "",
            "report_paths": {},
            "warnings": [],
            "errors": [],
            "stage_timings": {},
            "status": "pending",
            "progress_message": "Starting batch analysis...",
        }

        config_dict = {"configurable": {"thread_id": f"batch_{self.session_id}"}}
        for update in self.batch_graph.stream(batch_state, config=config_dict, stream_mode="updates"):
            for node_name, node_state in update.items():
                batch_state.update(node_state)
                msg = node_state.get("progress_message")
                if msg and progress_callback:
                    progress_callback(msg)

        batch_findings = GLOBAL_DATASTORE.get_artifact(f"findings_{batch_state.get('run_id')}")
        if batch_findings:
            self.tools.last_findings = batch_findings
            for f in batch_findings:
                self.tools.known_hypotheses[f.hypothesis.id] = f.hypothesis

        batch_ledger = GLOBAL_DATASTORE.get_artifact(f"ledger_{batch_state.get('run_id')}")
        if batch_ledger:
            self.ledger = batch_ledger
            self.tools.ledger = batch_ledger

        return batch_state

    def get_ledger_status(self) -> dict[str, Any]:
        """Return multiple-testing ledger summary statistics."""
        res = self.tools.get_ledger_status()
        return res.meta

    def get_findings(self) -> list[Finding]:
        """Return all findings tested and validated in this session."""
        return list(self.tools.last_findings)

    def get_rejected(self) -> list[dict[str, Any]]:
        """Return all tests rejected by validation."""
        rejected = []
        for hid, dec in self.ledger._last_decisions.items():
            if not dec.accepted:
                rejected.append({
                    "hypothesis_id": hid,
                    "p_raw": dec.p_raw,
                    "q_value": dec.q_value,
                    "reasons": [r.value if hasattr(r, "value") else str(r) for r in dec.reasons],
                    "reason_text": dec.reason_text,
                })
        return rejected

    def clear_conversation(self) -> None:
        """Clear conversation turns while keeping the multiple-testing family honest."""
        self.state["messages"] = []
        self.state["focus"] = FocusState().model_dump()
        self.state["pending_clarification"] = None


def create_session(
    df: pd.DataFrame,
    config: PipelineConfig,
    session_id: str | None = None,
    llm: LLMClient | None = None,
    out_dir: Path | str | None = None,
) -> Session:
    """Create and return a configured Session instance."""
    return Session(
        df=df,
        config=config,
        session_id=session_id,
        llm=llm,
        out_dir=out_dir,
    )
