"""Provider-agnostic LLM client interface, Anthropic implementation, caching, and NullLLM."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol, TypeVar, runtime_checkable

from pydantic import BaseModel, ValidationError as PydanticValidationError

from veridata.config import LLMConfig
from veridata.errors import LLMError, LLMUnavailable

logger = logging.getLogger("veridata.agent.llm")

TModel = TypeVar("TModel", bound=BaseModel)


@runtime_checkable
class LLMClient(Protocol):
    """Protocol implemented by all VeriData LLM backends (Master Plan Section 9.4)."""

    model_name: str

    def structured(
        self,
        *,
        system: str,
        user: str,
        schema: type[TModel],
        temperature: float = 0.0,
        max_tokens: int = 2000,
        cache_key: str | None = None,
    ) -> TModel: ...

    def text(
        self,
        *,
        system: str,
        user: str,
        temperature: float = 0.0,
        max_tokens: int = 1500,
        cache_key: str | None = None,
    ) -> str: ...


class NullLLM:
    """Offline fallback client that raises LLMUnavailable so callers degrade gracefully (P4)."""

    model_name: str = "none"

    def structured(
        self,
        *,
        system: str,
        user: str,
        schema: type[TModel],
        temperature: float = 0.0,
        max_tokens: int = 2000,
        cache_key: str | None = None,
    ) -> TModel:
        raise LLMUnavailable("No LLM client or API key configured; running offline.")

    def text(
        self,
        *,
        system: str,
        user: str,
        temperature: float = 0.0,
        max_tokens: int = 1500,
        cache_key: str | None = None,
    ) -> str:
        raise LLMUnavailable("No LLM client or API key configured; running offline.")


class AnthropicLLMClient:
    """Anthropic API client using forced tool calls for strict Pydantic structured outputs."""

    def __init__(
        self,
        *,
        api_key: str,
        model: str = "claude-sonnet-4-5",
        cache_dir: Path | str | None = ".cache/llm",
        use_cache: bool = True,
        retries: int = 2,
        log_path: Path | str | None = None,
    ) -> None:
        self.model_name = model
        self._api_key = api_key
        self._cache_dir = Path(cache_dir) if cache_dir else None
        self._use_cache = use_cache and self._cache_dir is not None
        self._retries = max(0, int(retries))
        self._log_path = Path(log_path) if log_path else None
        self._client: Any = None

    def _get_sdk_client(self) -> Any:
        if self._client is None:
            try:
                import anthropic  # type: ignore[import-not-found]
            except ImportError as exc:
                raise LLMUnavailable(
                    "The 'anthropic' package is not installed. Install with `pip install anthropic`."
                ) from exc
            self._client = anthropic.Anthropic(api_key=self._api_key)
        return self._client

    def _compute_cache_hash(
        self,
        *,
        kind: str,
        system: str,
        user: str,
        schema_name: str,
        temperature: float,
        cache_key: str | None,
    ) -> str:
        payload = json.dumps(
            {
                "kind": kind,
                "model": self.model_name,
                "system": system,
                "user": user,
                "schema_name": schema_name,
                "temperature": temperature,
                "cache_key": cache_key,
            },
            sort_keys=True,
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def _read_cache(self, digest: str) -> dict[str, Any] | None:
        if not self._use_cache or self._cache_dir is None:
            return None
        path = self._cache_dir / f"{digest}.json"
        if path.exists():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                return None
        return None

    def _write_cache(self, digest: str, payload: dict[str, Any]) -> None:
        if not self._use_cache or self._cache_dir is None:
            return
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        path = self._cache_dir / f"{digest}.json"
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def _log_call(
        self,
        *,
        kind: str,
        schema_name: str,
        cached: bool,
        latency_ms: float,
        input_tokens: int = 0,
        output_tokens: int = 0,
    ) -> None:
        if self._log_path is None:
            return
        self._log_path.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "model": self.model_name,
            "kind": kind,
            "schema_name": schema_name,
            "cached": cached,
            "latency_ms": round(latency_ms, 2),
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
        }
        with self._log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, sort_keys=True) + "\n")

    def structured(
        self,
        *,
        system: str,
        user: str,
        schema: type[TModel],
        temperature: float = 0.0,
        max_tokens: int = 2000,
        cache_key: str | None = None,
    ) -> TModel:
        t0 = time.perf_counter()
        digest = self._compute_cache_hash(
            kind="structured",
            system=system,
            user=user,
            schema_name=schema.__name__,
            temperature=temperature,
            cache_key=cache_key,
        )
        cached = self._read_cache(digest)
        if cached is not None and "data" in cached:
            result = schema.model_validate(cached["data"])
            self._log_call(
                kind="structured",
                schema_name=schema.__name__,
                cached=True,
                latency_ms=(time.perf_counter() - t0) * 1000.0,
            )
            return result

        client = self._get_sdk_client()
        tool_name = f"submit_{schema.__name__.lower()}"
        tool_def = {
            "name": tool_name,
            "description": f"Return a strictly valid {schema.__name__} JSON payload.",
            "input_schema": schema.model_json_schema(),
        }

        messages: list[dict[str, str]] = [{"role": "user", "content": user}]
        last_error: Exception | None = None

        for attempt in range(self._retries + 1):
            try:
                response = client.messages.create(
                    model=self.model_name,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    system=system,
                    tools=[tool_def],
                    tool_choice={"type": "tool", "name": tool_name},
                    messages=messages,
                )
                tool_input: dict[str, Any] | None = None
                for block in getattr(response, "content", []):
                    if getattr(block, "type", None) == "tool_use" and getattr(
                        block, "name", None
                    ) == tool_name:
                        tool_input = getattr(block, "input", None)
                        break

                if tool_input is None:
                    raise LLMError(f"Model did not invoke required tool '{tool_name}'.")

                parsed = schema.model_validate(tool_input)
                usage = getattr(response, "usage", None)
                in_tok = int(getattr(usage, "input_tokens", 0) or 0)
                out_tok = int(getattr(usage, "output_tokens", 0) or 0)
                self._write_cache(digest, {"data": parsed.model_dump(mode="json")})
                self._log_call(
                    kind="structured",
                    schema_name=schema.__name__,
                    cached=False,
                    latency_ms=(time.perf_counter() - t0) * 1000.0,
                    input_tokens=in_tok,
                    output_tokens=out_tok,
                )
                return parsed
            except (PydanticValidationError, LLMError) as exc:
                last_error = exc
                logger.warning(
                    "Structured output validation failed (attempt %d/%d): %s",
                    attempt + 1,
                    self._retries + 1,
                    exc,
                )
                messages.append(
                    {
                        "role": "user",
                        "content": (
                            f"Your previous tool call failed schema validation with error:\n{exc}\n"
                            "Please fix the output and invoke the tool again."
                        ),
                    }
                )
            except Exception as exc:  # noqa: BLE001
                raise LLMError(f"Anthropic API request failed: {exc}") from exc

        raise LLMError(
            f"Structured output failed after {self._retries + 1} attempts: {last_error}"
        )

    def text(
        self,
        *,
        system: str,
        user: str,
        temperature: float = 0.0,
        max_tokens: int = 1500,
        cache_key: str | None = None,
    ) -> str:
        t0 = time.perf_counter()
        digest = self._compute_cache_hash(
            kind="text",
            system=system,
            user=user,
            schema_name="str",
            temperature=temperature,
            cache_key=cache_key,
        )
        cached = self._read_cache(digest)
        if cached is not None and "text" in cached:
            self._log_call(
                kind="text",
                schema_name="str",
                cached=True,
                latency_ms=(time.perf_counter() - t0) * 1000.0,
            )
            return str(cached["text"])

        client = self._get_sdk_client()
        try:
            response = client.messages.create(
                model=self.model_name,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system,
                messages=[{"role": "user", "content": user}],
            )
            chunks = [
                getattr(block, "text", "")
                for block in getattr(response, "content", [])
                if getattr(block, "type", None) == "text"
            ]
            out_text = "".join(chunks).strip()
            usage = getattr(response, "usage", None)
            self._write_cache(digest, {"text": out_text})
            self._log_call(
                kind="text",
                schema_name="str",
                cached=False,
                latency_ms=(time.perf_counter() - t0) * 1000.0,
                input_tokens=int(getattr(usage, "input_tokens", 0) or 0),
                output_tokens=int(getattr(usage, "output_tokens", 0) or 0),
            )
            return out_text
        except Exception as exc:  # noqa: BLE001
            raise LLMError(f"Anthropic text request failed: {exc}") from exc


def get_llm_client(
    config: LLMConfig | None = None,
    *,
    use_cache: bool = True,
    log_path: Path | str | None = None,
) -> LLMClient:
    """Return an AnthropicLLMClient if ANTHROPIC_API_KEY is present, else NullLLM."""
    cfg = config or LLMConfig()
    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if cfg.provider == "anthropic" and api_key:
        return AnthropicLLMClient(
            api_key=api_key,
            model=cfg.model,
            cache_dir=cfg.cache_dir,
            use_cache=use_cache,
            retries=cfg.retries,
            log_path=log_path,
        )
    return NullLLM()

