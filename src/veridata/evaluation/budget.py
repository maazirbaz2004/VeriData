"""Hard cost budget tracking and resumable spend log for Phase 8 LLM evaluations."""

from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from veridata.agent.llm import estimate_cost_usd
from veridata.errors import VeriDataError


class BudgetExceededError(VeriDataError):
    """Raised when evaluation LLM spend reaches eval.max_cost_usd."""


class CostTracker:
    """Thread-safe spend tracker backed by an append-only JSONL log."""

    def __init__(
        self,
        max_cost_usd: float = 15.0,
        log_path: Path | str | None = "outputs/eval/cost_log.jsonl",
    ) -> None:
        self.max_cost_usd = float(max_cost_usd)
        self.log_path = Path(log_path) if log_path else None
        self._lock = threading.Lock()
        self.total_cost_usd: float = 0.0
        self.total_input_tokens: int = 0
        self.total_output_tokens: int = 0
        self.calls: int = 0
        self.cached_calls: int = 0
        self._load_existing()

    def _load_existing(self) -> None:
        if self.log_path is None or not self.log_path.exists():
            return
        for line in self.log_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            self.total_cost_usd += float(rec.get("cost_usd", 0.0))
            self.total_input_tokens += int(rec.get("input_tokens", 0))
            self.total_output_tokens += int(rec.get("output_tokens", 0))
            self.calls += 1
            if rec.get("cached"):
                self.cached_calls += 1

    def check_can_spend(self, estimated_next_usd: float = 0.0) -> None:
        """Raise BudgetExceededError if cumulative spend would exceed max_cost_usd."""
        with self._lock:
            if self.total_cost_usd + estimated_next_usd > self.max_cost_usd + 1e-12:
                raise BudgetExceededError(
                    f"Evaluation LLM budget exceeded: spent ${self.total_cost_usd:.4f} "
                    f"(limit ${self.max_cost_usd:.2f}). Cached runs are preserved; raise eval.max_cost_usd to resume."
                )

    def record(
        self,
        *,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cached: bool = False,
        tag: str = "",
        cost_usd: float | None = None,
    ) -> float:
        """Record one LLM call and return its USD cost."""
        cost = 0.0 if cached else (
            float(cost_usd) if cost_usd is not None else estimate_cost_usd(model, input_tokens, output_tokens)
        )
        with self._lock:
            self.total_cost_usd += cost
            self.total_input_tokens += int(input_tokens)
            self.total_output_tokens += int(output_tokens)
            self.calls += 1
            if cached:
                self.cached_calls += 1

            if self.log_path is not None:
                self.log_path.parent.mkdir(parents=True, exist_ok=True)
                rec: dict[str, Any] = {
                    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                    "tag": tag,
                    "model": model,
                    "cached": cached,
                    "input_tokens": int(input_tokens),
                    "output_tokens": int(output_tokens),
                    "cost_usd": round(cost, 8),
                    "cumulative_cost_usd": round(self.total_cost_usd, 8),
                }
                with self.log_path.open("a", encoding="utf-8") as fh:
                    fh.write(json.dumps(rec, sort_keys=True) + "\n")
        return cost

    def summary(self) -> dict[str, Any]:
        with self._lock:
            return {
                "max_cost_usd": self.max_cost_usd,
                "total_cost_usd": round(self.total_cost_usd, 6),
                "remaining_usd": round(max(0.0, self.max_cost_usd - self.total_cost_usd), 6),
                "total_input_tokens": self.total_input_tokens,
                "total_output_tokens": self.total_output_tokens,
                "calls": self.calls,
                "cached_calls": self.cached_calls,
            }
