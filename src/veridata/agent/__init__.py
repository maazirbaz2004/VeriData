"""VeriData Agent and LangGraph conversational interface (Phase 6)."""

from __future__ import annotations

from veridata.agent.checkpoint import get_checkpointer
from veridata.agent.datastore import GLOBAL_DATASTORE, DataStore
from veridata.agent.fake_llm import FakeLLM
from veridata.agent.followups import generate_followups
from veridata.agent.graph_batch import build_batch_graph
from veridata.agent.graph_chat import build_chat_graph
from veridata.agent.llm import AnthropicLLMClient, LLMClient, NullLLM
from veridata.agent.router import RouterDecision, route_intent
from veridata.agent.session import Answer, Session, create_session
from veridata.agent.state import BatchState, ChatState, FocusState
from veridata.agent.tools import ToolRegistry, ToolResult

__all__ = [
    "Session",
    "create_session",
    "Answer",
    "build_batch_graph",
    "build_chat_graph",
    "BatchState",
    "ChatState",
    "FocusState",
    "DataStore",
    "GLOBAL_DATASTORE",
    "ToolRegistry",
    "ToolResult",
    "route_intent",
    "RouterDecision",
    "generate_followups",
    "get_checkpointer",
    "LLMClient",
    "NullLLM",
    "AnthropicLLMClient",
    "FakeLLM",
]
