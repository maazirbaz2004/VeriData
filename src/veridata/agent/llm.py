"""Provider-agnostic LLM client interface, Gemini/Anthropic implementations, caching, and NullLLM."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, ClassVar, Protocol, TypeVar, runtime_checkable

from dotenv import load_dotenv
from pydantic import BaseModel
from pydantic import ValidationError as PydanticValidationError

from veridata.config import LLMConfig
from veridata.errors import LLMError, LLMUnavailable

logger = logging.getLogger("veridata.agent.llm")

TModel = TypeVar("TModel", bound=BaseModel)

# Approximate USD per 1M tokens (input, output) for budget tracking & logging.
MODEL_PRICING_PER_M: dict[str, tuple[float, float]] = {
    "gemini-2.5-flash": (0.15, 0.60),
    "gemini-2.5-flash-lite": (0.10, 0.40),
    "gemini-2.5-pro": (1.25, 10.00),
    "gemini-2.0-flash": (0.10, 0.40),
    "claude-sonnet-4-5": (3.00, 15.00),
    "claude-3-5-sonnet-latest": (3.00, 15.00),
    "claude-3-5-haiku-latest": (0.80, 4.00),
}


def estimate_cost_usd(model: str, input_tokens: int, output_tokens: int) -> float:
    """Estimate call cost in USD from token counts."""
    in_rate, out_rate = MODEL_PRICING_PER_M.get(model, (0.30, 1.20))
    return (input_tokens * in_rate + output_tokens * out_rate) / 1_000_000.0


def _strip_json_fences(raw: str) -> str:
    text = raw.strip()
    m = re.match(r"^```(?:json)?\s*\n?(.*?)\n?```\s*$", text, flags=re.DOTALL | re.IGNORECASE)
    if m:
        return m.group(1).strip()
    return text


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


class _BaseCachedLLMClient:
    """Shared disk cache and call-logging utilities for HTTP/SDK LLM clients."""

    def __init__(
        self,
        *,
        model: str,
        cache_dir: Path | str | None = ".cache/llm",
        use_cache: bool = True,
        retries: int = 2,
        log_path: Path | str | None = None,
    ) -> None:
        self.model_name = model
        self._cache_dir = Path(cache_dir) if cache_dir else None
        self._use_cache = use_cache and self._cache_dir is not None
        self._retries = max(0, int(retries))
        self._log_path = Path(log_path) if log_path else None
        self.last_call_meta: dict[str, Any] = {}

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
        cost = 0.0 if cached else estimate_cost_usd(self.model_name, input_tokens, output_tokens)
        record = {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "model": self.model_name,
            "kind": kind,
            "schema_name": schema_name,
            "cached": cached,
            "latency_ms": round(latency_ms, 2),
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "estimated_cost_usd": round(cost, 8),
        }
        self.last_call_meta = record
        if self._log_path is None:
            return
        self._log_path.parent.mkdir(parents=True, exist_ok=True)
        with self._log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, sort_keys=True) + "\n")


class GeminiLLMClient(_BaseCachedLLMClient):
    """Google Gemini REST API client via httpx with schema-validated JSON and disk cache."""

    _BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"
    _RETRYABLE_STATUS: ClassVar[set[int]] = {429, 500, 502, 503, 504}

    def __init__(
        self,
        *,
        api_key: str,
        model: str = "gemini-2.5-flash",
        cache_dir: Path | str | None = ".cache/llm",
        use_cache: bool = True,
        retries: int = 2,
        log_path: Path | str | None = None,
        timeout_s: float = 90.0,
        http_client: Any = None,
    ) -> None:
        super().__init__(
            model=model,
            cache_dir=cache_dir,
            use_cache=use_cache,
            retries=retries,
            log_path=log_path,
        )
        self._api_key = api_key
        self._timeout_s = timeout_s
        self._http_client = http_client

    def _post_generate(self, payload: dict[str, Any]) -> dict[str, Any]:
        import httpx

        url = f"{self._BASE_URL}/{self.model_name}:generateContent"
        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": self._api_key,
        }

        last_exc: Exception | None = None
        for attempt in range(3):
            try:
                if self._http_client is not None:
                    resp = self._http_client.post(url, headers=headers, json=payload, timeout=self._timeout_s)
                else:
                    resp = httpx.post(url, headers=headers, json=payload, timeout=self._timeout_s)
                if resp.status_code in self._RETRYABLE_STATUS and attempt < 2:
                    time.sleep(1.0 * (2**attempt))
                    continue
                if resp.status_code >= 400:
                    raise LLMError(f"Gemini API HTTP {resp.status_code}: {resp.text[:400]}")
                return dict(resp.json())
            except LLMError:
                raise
            except Exception as exc:
                last_exc = exc
                if attempt < 2:
                    time.sleep(1.0 * (2**attempt))
                    continue
                raise LLMError(f"Gemini API request failed: {exc}") from exc
        raise LLMError(f"Gemini API request failed: {last_exc}")

    @staticmethod
    def _extract_text_and_usage(data: dict[str, Any]) -> tuple[str, int, int]:
        candidates = data.get("candidates") or []
        if not candidates:
            prompt_fb = data.get("promptFeedback")
            raise LLMError(f"Gemini returned no candidates (promptFeedback={prompt_fb}).")
        parts = candidates[0].get("content", {}).get("parts", [])
        text = "".join(str(p.get("text", "")) for p in parts if isinstance(p, dict)).strip()
        usage = data.get("usageMetadata") or {}
        in_tok = int(usage.get("promptTokenCount") or 0)
        out_tok = int(usage.get("candidatesTokenCount") or 0)
        return text, in_tok, out_tok

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

        schema_json = json.dumps(schema.model_json_schema(), indent=2)
        schema_prompt = (
            f"{user}\n\n"
            f"Return ONLY a valid JSON object matching this exact JSON Schema ({schema.__name__}):\n"
            f"{schema_json}"
        )
        contents: list[dict[str, Any]] = [{"role": "user", "parts": [{"text": schema_prompt}]}]
        last_error: Exception | None = None
        total_in = 0
        total_out = 0

        for attempt in range(self._retries + 1):
            payload: dict[str, Any] = {
                "contents": contents,
                "generationConfig": {
                    "temperature": temperature,
                    "maxOutputTokens": max_tokens,
                    "responseMimeType": "application/json",
                },
            }
            if system.strip():
                payload["systemInstruction"] = {"parts": [{"text": system}]}

            data = self._post_generate(payload)
            raw_text, in_tok, out_tok = self._extract_text_and_usage(data)
            total_in += in_tok
            total_out += out_tok
            cleaned = _strip_json_fences(raw_text)

            try:
                parsed = schema.model_validate_json(cleaned)
                self._write_cache(digest, {"data": parsed.model_dump(mode="json")})
                self._log_call(
                    kind="structured",
                    schema_name=schema.__name__,
                    cached=False,
                    latency_ms=(time.perf_counter() - t0) * 1000.0,
                    input_tokens=total_in,
                    output_tokens=total_out,
                )
                return parsed
            except (PydanticValidationError, ValueError) as exc:
                last_error = exc
                logger.warning(
                    "Gemini structured validation failed (attempt %d/%d): %s",
                    attempt + 1,
                    self._retries + 1,
                    exc,
                )
                contents.append({"role": "model", "parts": [{"text": raw_text}]})
                contents.append(
                    {
                        "role": "user",
                        "parts": [
                            {
                                "text": (
                                    f"Your previous JSON failed schema validation with error:\n{exc}\n"
                                    "Return ONLY corrected JSON matching the schema."
                                )
                            }
                        ],
                    }
                )

        raise LLMError(
            f"Gemini structured output failed after {self._retries + 1} attempts: {last_error}"
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

        payload: dict[str, Any] = {
            "contents": [{"role": "user", "parts": [{"text": user}]}],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            },
        }
        if system.strip():
            payload["systemInstruction"] = {"parts": [{"text": system}]}

        data = self._post_generate(payload)
        out_text, in_tok, out_tok = self._extract_text_and_usage(data)
        self._write_cache(digest, {"text": out_text})
        self._log_call(
            kind="text",
            schema_name="str",
            cached=False,
            latency_ms=(time.perf_counter() - t0) * 1000.0,
            input_tokens=in_tok,
            output_tokens=out_tok,
        )
        return out_text


class AnthropicLLMClient(_BaseCachedLLMClient):
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
        super().__init__(
            model=model,
            cache_dir=cache_dir,
            use_cache=use_cache,
            retries=retries,
            log_path=log_path,
        )
        self._api_key = api_key
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
            except Exception as exc:
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
        except Exception as exc:
            raise LLMError(f"Anthropic text request failed: {exc}") from exc


def get_llm_client(
    config: LLMConfig | None = None,
    *,
    use_cache: bool = True,
    log_path: Path | str | None = None,
) -> LLMClient:
    """Load .env and return GeminiLLMClient or AnthropicLLMClient when configured, else NullLLM."""
    load_dotenv(override=False)
    cfg = config or LLMConfig()
    gemini_key = (os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY") or "").strip()
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()

    provider = cfg.provider.lower().strip()
    if provider == "gemini" and gemini_key:
        model = "gemini-2.5-flash" if cfg.model.startswith("claude") else cfg.model
        return GeminiLLMClient(
            api_key=gemini_key,
            model=model,
            cache_dir=cfg.cache_dir,
            use_cache=use_cache,
            retries=cfg.retries,
            log_path=log_path,
        )
    if provider == "anthropic" and anthropic_key:
        model = "claude-sonnet-4-5" if cfg.model.startswith("gemini") else cfg.model
        return AnthropicLLMClient(
            api_key=anthropic_key,
            model=model,
            cache_dir=cfg.cache_dir,
            use_cache=use_cache,
            retries=cfg.retries,
            log_path=log_path,
        )
    if gemini_key:
        model = "gemini-2.5-flash" if cfg.model.startswith("claude") else cfg.model
        return GeminiLLMClient(
            api_key=gemini_key,
            model=model,
            cache_dir=cfg.cache_dir,
            use_cache=use_cache,
            retries=cfg.retries,
            log_path=log_path,
        )
    if anthropic_key:
        model = "claude-sonnet-4-5" if cfg.model.startswith("gemini") else cfg.model
        return AnthropicLLMClient(
            api_key=anthropic_key,
            model=model,
            cache_dir=cfg.cache_dir,
            use_cache=use_cache,
            retries=cfg.retries,
            log_path=log_path,
        )
    return NullLLM()
