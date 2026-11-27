"""Unit tests for GeminiLLMClient, .env loading, provider selection, caching, and retries."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from pydantic import BaseModel

from veridata.agent.llm import (
    AnthropicLLMClient,
    GeminiLLMClient,
    NullLLM,
    estimate_cost_usd,
    get_llm_client,
)
from veridata.config import LLMConfig
from veridata.errors import LLMError


class _SampleSchema(BaseModel):
    answer: str
    items: list[int]


class _FakeResponse:
    def __init__(self, status_code: int, json_data: dict[str, Any], text: str = "") -> None:
        self.status_code = status_code
        self._json = json_data
        self.text = text or str(json_data)

    def json(self) -> dict[str, Any]:
        return self._json


class _FakeHttpClient:
    def __init__(self, responses: list[_FakeResponse]) -> None:
        self.responses = list(responses)
        self.calls: list[dict[str, Any]] = []

    def post(self, url: str, *, headers: dict[str, str], json: dict[str, Any], timeout: float) -> _FakeResponse:
        self.calls.append({"url": url, "headers": headers, "json": json, "timeout": timeout})
        return self.responses.pop(0)


def test_gemini_text_and_caching(tmp_path: Path) -> None:
    http = _FakeHttpClient(
        [
            _FakeResponse(
                200,
                {
                    "candidates": [{"content": {"parts": [{"text": "Hello from Gemini"}]}}],
                    "usageMetadata": {"promptTokenCount": 120, "candidatesTokenCount": 30},
                },
            )
        ]
    )
    log_path = tmp_path / "calls.jsonl"
    client = GeminiLLMClient(
        api_key="test-key",
        model="gemini-2.5-flash",
        cache_dir=tmp_path / "cache",
        log_path=log_path,
        http_client=http,
    )

    out1 = client.text(system="sys", user="hi")
    out2 = client.text(system="sys", user="hi")
    assert out1 == "Hello from Gemini"
    assert out2 == "Hello from Gemini"
    assert len(http.calls) == 1
    assert http.calls[0]["headers"]["x-goog-api-key"] == "test-key"
    assert client.last_call_meta["cached"] is True
    assert estimate_cost_usd("gemini-2.5-flash", 1_000_000, 1_000_000) == pytest.approx(0.75)


def test_gemini_structured_strips_fences_and_retries_validation(tmp_path: Path) -> None:
    http = _FakeHttpClient(
        [
            _FakeResponse(
                200,
                {
                    "candidates": [{"content": {"parts": [{"text": '{"answer": "bad", "items": "not-a-list"}'}]}}],
                    "usageMetadata": {"promptTokenCount": 50, "candidatesTokenCount": 10},
                },
            ),
            _FakeResponse(
                200,
                {
                    "candidates": [
                        {"content": {"parts": [{"text": '```json\n{"answer": "ok", "items": [1, 2]}\n```'}]}}
                    ],
                    "usageMetadata": {"promptTokenCount": 80, "candidatesTokenCount": 15},
                },
            ),
        ]
    )
    client = GeminiLLMClient(
        api_key="test-key",
        cache_dir=tmp_path / "cache",
        retries=1,
        http_client=http,
    )
    res = client.structured(system="sys", user="give json", schema=_SampleSchema)
    assert res == _SampleSchema(answer="ok", items=[1, 2])
    assert len(http.calls) == 2


def test_gemini_retries_on_429_and_raises_on_400(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("time.sleep", lambda _s: None)
    http = _FakeHttpClient(
        [
            _FakeResponse(429, {"error": "rate limit"}, text="rate limit"),
            _FakeResponse(
                200,
                {
                    "candidates": [{"content": {"parts": [{"text": "Recovered"}]}}],
                    "usageMetadata": {"promptTokenCount": 10, "candidatesTokenCount": 5},
                },
            ),
        ]
    )
    client = GeminiLLMClient(api_key="k", use_cache=False, http_client=http)
    assert client.text(system="", user="u") == "Recovered"
    assert len(http.calls) == 2

    bad_http = _FakeHttpClient([_FakeResponse(400, {"error": "bad request"}, text="bad request")])
    bad_client = GeminiLLMClient(api_key="k", use_cache=False, http_client=bad_http)
    with pytest.raises(LLMError, match="HTTP 400"):
        bad_client.text(system="", user="u")


def test_get_llm_client_provider_selection(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    assert isinstance(get_llm_client(LLMConfig(provider="gemini")), NullLLM)

    monkeypatch.setenv("GEMINI_API_KEY", "g-key")
    c_gem = get_llm_client(LLMConfig(provider="gemini", model="claude-sonnet-4-5"))
    assert isinstance(c_gem, GeminiLLMClient)
    assert c_gem.model_name == "gemini-2.5-flash"

    # Even if provider says anthropic without an anthropic key, falls back to available Gemini key
    c_auto = get_llm_client(LLMConfig(provider="anthropic", model="claude-sonnet-4-5"))
    assert isinstance(c_auto, GeminiLLMClient)

    monkeypatch.setenv("ANTHROPIC_API_KEY", "a-key")
    c_ant = get_llm_client(LLMConfig(provider="anthropic", model="claude-sonnet-4-5"))
    assert isinstance(c_ant, AnthropicLLMClient)
