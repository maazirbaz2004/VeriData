"""Tests for sandbox safety, S1a/S1b adapters with FakeLLM, pair canonicalization, and budget."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from veridata.agent.fake_llm import FakeLLM
from veridata.evaluation.budget import BudgetExceededError, CostTracker
from veridata.evaluation.sandbox import run_sandboxed_code, validate_and_inspect_code
from veridata.evaluation.systems.llm_only import (
    LLMFindingItem,
    canonicalize_llm_findings,
    run_llm_only_system,
)


def test_sandbox_blocks_unsafe_code_and_runs_safe_scipy(tmp_path: Path) -> None:
    for bad in ("import os\nos.listdir('.')", "open('secret.txt').read()", "eval('1+1')"):
        ok, err, _ = validate_and_inspect_code(bad)
        assert not ok
        assert err is not None

    csv_path = tmp_path / "tiny.csv"
    pd.DataFrame({"x": [1, 2, 3, 4, 5], "y": [2, 4, 6, 8, 10]}).to_csv(csv_path, index=False)
    res = run_sandboxed_code(
        "r, p = stats.pearsonr(df['x'], df['y'])\nprint(round(r, 4), round(p, 6))",
        csv_path,
        timeout_s=10.0,
    )
    assert res["ok"] is True
    assert "pearsonr" in res["tests_detected"]
    assert "1.0" in res["stdout"]


def test_canonicalize_llm_findings_handles_duplicates_and_unknown_cols() -> None:
    items = [
        LLMFindingItem(col_a="B", col_b="A", direction_sign="positive", p_value=0.001),
        LLMFindingItem(col_a="a", col_b="b", direction_sign="positive", p_value=0.002),  # duplicate
        LLMFindingItem(col_a="A", col_b="ghost_col", claim="hallucinated"),
    ]
    findings, meta = canonicalize_llm_findings(items, ["A", "B", "C"])
    assert len(findings) == 2
    assert meta["n_duplicates"] == 1
    assert meta["n_hallucinated_columns"] == 1
    assert findings[0].col_a == "B" and findings[0].col_b == "A"
    assert findings[0].direction == {"kind": "sign", "value": "+"}


def test_s1a_and_s1b_with_fakellm_and_budget_guard(tmp_path: Path) -> None:
    rng = np.random.default_rng(7)
    x = rng.normal(size=40)
    csv_path = tmp_path / "ds.csv"
    pd.DataFrame({"x": x, "y": 2.0 * x + rng.normal(scale=0.1, size=40)}).to_csv(csv_path, index=False)

    fake_s1a = FakeLLM({"LLMFindingsPayload": {"findings": [{"col_a": "x", "col_b": "y", "direction_sign": "positive", "p_value": 1e-10}]}})
    out_a = run_llm_only_system("S1a_summary_standard", csv_path, "ds_test", llm=fake_s1a, temperature=0.0)
    assert out_a.system_name == "S1a_summary_standard"
    assert len(out_a.findings) == 1

    calls = {"n": 0}

    def code_responder(_schema: str, _sys: str, _usr: str) -> dict:
        calls["n"] += 1
        if calls["n"] == 1:
            return {
                "action": "run_code",
                "python_code": "r, p = stats.pearsonr(df['x'], df['y'])\nprint(f'r={r:.3f}, p={p:.2e}')",
                "findings": [],
            }
        return {
            "action": "final",
            "python_code": "",
            "findings": [{"col_a": "x", "col_b": "y", "direction_sign": "positive", "effect_size": 0.99}],
        }

    fake_s1b = FakeLLM(code_responder)
    out_b = run_llm_only_system("S1b_code_careful", csv_path, "ds_test", llm=fake_s1b, temperature=0.0)
    assert out_b.meta["n_turns"] == 2
    assert "pearsonr" in out_b.meta["tests_detected"]
    assert len(out_b.findings) == 1

    # CostTracker stop & resume
    log_p = tmp_path / "cost.jsonl"
    ct = CostTracker(max_cost_usd=0.05, log_path=log_p)
    ct.record(model="gemini-2.5-flash", input_tokens=100_000, output_tokens=50_000, tag="t1")
    with pytest.raises(BudgetExceededError):
        ct.check_can_spend(0.02)
    ct_resumed = CostTracker(max_cost_usd=0.10, log_path=log_p)
    assert ct_resumed.total_cost_usd > 0.04
    ct_resumed.check_can_spend(0.01)
