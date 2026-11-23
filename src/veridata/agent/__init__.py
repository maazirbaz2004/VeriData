"""VeriData Agent and LangGraph conversational interface (Phase 6)."""

from __future__ import annotations

from typing import Any

from veridata.agent.fake_llm import FakeLLM
from veridata.agent.llm import AnthropicLLMClient, LLMClient, NullLLM

_LAZY_EXPORTS: dict[str, tuple[str, str]] = {
    "get_checkpointer": ("veridata.agent.checkpoint", "get_checkpointer"),
    "GLOBAL_DATASTORE": ("veridata.agent.datastore", "GLOBAL_DATASTORE"),
    "DataStore": ("veridata.agent.datastore", "DataStore"),
    "generate_followups": ("veridata.agent.followups", "generate_followups"),
    "build_batch_graph": ("veridata.agent.graph_batch", "build_batch_graph"),
    "build_chat_graph": ("veridata.agent.graph_chat", "build_chat_graph"),
    "RouterDecision": ("veridata.agent.router", "RouterDecision"),
    "route_intent": ("veridata.agent.router", "route_intent"),
    "Answer": ("veridata.agent.session", "Answer"),
    "Session": ("veridata.agent.session", "Session"),
    "create_session": ("veridata.agent.session", "create_session"),
    "BatchState": ("veridata.agent.state", "BatchState"),
    "ChatState": ("veridata.agent.state", "ChatState"),
    "FocusState": ("veridata.agent.state", "FocusState"),
    "ToolRegistry": ("veridata.agent.tools", "ToolRegistry"),
    "ToolResult": ("veridata.agent.tools", "ToolResult"),
}


def __getattr__(name: str) -> Any:
    if name in _LAZY_EXPORTS:
        import importlib

        mod_name, attr_name = _LAZY_EXPORTS[name]
        mod = importlib.import_module(mod_name)
        val = getattr(mod, attr_name)
        globals()[name] = val
        return val
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


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
