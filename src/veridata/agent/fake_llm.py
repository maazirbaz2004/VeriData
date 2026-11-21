"""Deterministic offline FakeLLM test double (Master Plan Section 9.4)."""

from __future__ import annotations

from typing import Any, Callable, TypeVar

from pydantic import BaseModel

from veridata.errors import LLMError

TModel = TypeVar("TModel", bound=BaseModel)


class FakeLLM:
    """Deterministic offline LLM client for unit and integration tests.

    ``responses`` can be:
    - a ``dict[str, Any]`` keyed by schema name (e.g. ``"LLMProposalBatch"``) or ``"text"``
    - a callable ``(schema_name, system, user) -> dict | BaseModel | str``
    """

    def __init__(
        self,
        responses: dict[str, Any] | Callable[[str, str, str], Any],
        *,
        model_name: str = "fake-llm-v1",
    ) -> None:
        self._responses = responses
        self.model_name = model_name
        self.calls: list[dict[str, Any]] = []

    def _resolve(self, key: str, system: str, user: str) -> Any:
        if callable(self._responses):
            return self._responses(key, system, user)
        if key not in self._responses:
            raise LLMError(f"FakeLLM has no scripted response for '{key}'.")
        resp = self._responses[key]
        if callable(resp):
            return resp(system, user)
        return resp

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
        self.calls.append(
            {
                "kind": "structured",
                "schema": schema.__name__,
                "system": system,
                "user": user,
                "temperature": temperature,
                "cache_key": cache_key,
            }
        )
        raw = self._resolve(schema.__name__, system, user)
        if isinstance(raw, schema):
            return raw
        if isinstance(raw, BaseModel):
            return schema.model_validate(raw.model_dump())
        try:
            return schema.model_validate(raw)
        except Exception as exc:  # noqa: BLE001
            raise LLMError(f"FakeLLM response failed validation for {schema.__name__}: {exc}") from exc

    def text(
        self,
        *,
        system: str,
        user: str,
        temperature: float = 0.0,
        max_tokens: int = 1500,
        cache_key: str | None = None,
    ) -> str:
        self.calls.append(
            {
                "kind": "text",
                "system": system,
                "user": user,
                "temperature": temperature,
                "cache_key": cache_key,
            }
        )
        raw = self._resolve("text", system, user)
        return str(raw)

