"""LLM-only baseline adapters (S1a summary mode and S1b sandboxed code mode) for Phase 8."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Literal

import pandas as pd
from pydantic import BaseModel, Field

from veridata.agent.llm import LLMClient, NullLLM
from veridata.benchmark.truth import ReportedFinding, SystemOutput, pair_key
from veridata.errors import LLMError, LLMUnavailable
from veridata.evaluation.budget import CostTracker
from veridata.evaluation.sandbox import run_sandboxed_code

PROMPTS_DIR = Path(__file__).resolve().parents[4] / "configs" / "prompts"

LLM_SYSTEM_IDS = (
    "S1a_summary_standard",
    "S1a_summary_careful",
    "S1b_code_standard",
    "S1b_code_careful",
)


class LLMFindingItem(BaseModel):
    """Closed output schema for one finding returned by an LLM-only baseline."""

    col_a: str
    col_b: str
    direction_sign: Literal["positive", "negative", "any"] = "any"
    higher_group: str | None = None
    group_col: str | None = None
    p_value: float | None = None
    effect_size: float | None = None
    claim: str = ""


class LLMFindingsPayload(BaseModel):
    """Top-level structured findings payload for S1a and final S1b turn."""

    findings: list[LLMFindingItem] = Field(default_factory=list)


class LLMCodeStepPayload(BaseModel):
    """Structured turn action for S1b multi-turn sandboxed code mode."""

    action: Literal["run_code", "final"]
    python_code: str = ""
    findings: list[LLMFindingItem] = Field(default_factory=list)


def _load_prompt(filename: str) -> tuple[str, str]:
    path = PROMPTS_DIR / filename
    text = path.read_text(encoding="utf-8")
    first_line = text.splitlines()[0].strip() if text else ""
    version = first_line.removeprefix("# version:").strip() if first_line.startswith("# version:") else filename
    return text, version


def build_summary_context(df: pd.DataFrame, *, sample_seed: int = 42) -> str:
    """Build Phase 1 Mode-A style summary (schema + describe + head + seeded random sample)."""
    schema_rows = [
        {
            "column": str(col),
            "dtype": str(df[col].dtype),
            "n_unique": int(df[col].nunique(dropna=True)),
            "n_missing": int(df[col].isna().sum()),
            "sample_values": [str(v) for v in df[col].dropna().unique()[:5].tolist()],
        }
        for col in df.columns
    ]
    desc = df.describe(include="all").round(4).to_string()
    head_txt = df.head(5).to_string(index=False)
    sample_n = min(20, len(df))
    sample_txt = df.sample(n=sample_n, random_state=sample_seed).to_string(index=False)
    return (
        f"Dataset shape: {len(df)} rows x {len(df.columns)} columns\n\n"
        f"Column schema:\n{json.dumps(schema_rows, indent=2)}\n\n"
        f"Summary statistics (df.describe(include='all')):\n{desc}\n\n"
        f"First 5 rows:\n{head_txt}\n\n"
        f"Random sample ({sample_n} rows, seed={sample_seed}):\n{sample_txt}\n"
    )


def canonicalize_llm_findings(
    items: list[LLMFindingItem],
    df_columns: list[str],
) -> tuple[list[ReportedFinding], dict[str, Any]]:
    """Map LLM findings to canonical unordered pairs, flagging hallucinated columns and duplicates."""
    col_lookup = {c.lower(): c for c in df_columns}
    col_set = set(df_columns)
    seen: set[tuple[str, str]] = set()
    findings: list[ReportedFinding] = []
    hallucinated: list[dict[str, str]] = []
    n_duplicates = 0

    for item in items:
        raw_a = item.col_a.strip()
        raw_b = item.col_b.strip()
        ca = raw_a if raw_a in col_set else col_lookup.get(raw_a.lower(), raw_a)
        cb = raw_b if raw_b in col_set else col_lookup.get(raw_b.lower(), raw_b)
        if ca == cb:
            continue

        k = pair_key(ca, cb)
        if k in seen:
            n_duplicates += 1
            continue
        seen.add(k)

        if ca not in col_set or cb not in col_set:
            hallucinated.append({"col_a": raw_a, "col_b": raw_b})

        direction: dict[str, Any] | None = None
        if item.higher_group is not None:
            gcol = item.group_col or cb
            if gcol not in col_set:
                gcol = col_lookup.get(gcol.lower(), gcol)
            direction = {
                "kind": "group_diff",
                "group_col": gcol,
                "higher_level": str(item.higher_group),
            }
        elif item.direction_sign in {"positive", "negative"}:
            direction = {
                "kind": "sign",
                "value": "+" if item.direction_sign == "positive" else "-",
            }

        findings.append(
            ReportedFinding(
                col_a=ca,
                col_b=cb,
                direction=direction,
                effect=item.effect_size,
                p_value=item.p_value,
                q_value=None,
                claim_text=item.claim,
                source_id="llm_only",
            )
        )

    return findings, {
        "n_raw_items": len(items),
        "n_duplicates": n_duplicates,
        "n_hallucinated_columns": len(hallucinated),
        "hallucinated_pairs": hallucinated,
    }


def _record_usage(llm: LLMClient, cost_tracker: CostTracker | None, tag: str) -> float:
    meta = getattr(llm, "last_call_meta", None) or {}
    if cost_tracker is None or not meta:
        return 0.0
    return cost_tracker.record(
        model=str(meta.get("model", getattr(llm, "model_name", "unknown"))),
        input_tokens=int(meta.get("input_tokens", 0)),
        output_tokens=int(meta.get("output_tokens", 0)),
        cached=bool(meta.get("cached", False)),
        tag=tag,
    )


def run_llm_only_system(
    system_id: str,
    csv_path: Path | str,
    dataset_id: str,
    *,
    llm: LLMClient,
    temperature: float = 0.7,
    repeat_idx: int = 0,
    max_turns: int = 6,
    sandbox_timeout_s: float = 15.0,
    cost_tracker: CostTracker | None = None,
) -> SystemOutput:
    """Run S1a (summary) or S1b (sandboxed code) once for one dataset and repeat index."""
    if isinstance(llm, NullLLM):
        raise LLMUnavailable(f"Cannot run {system_id}: no LLM API key configured.")
    if system_id not in LLM_SYSTEM_IDS:
        raise ValueError(f"Unknown LLM baseline system: {system_id!r}")

    df = pd.read_csv(csv_path)
    cols = [str(c) for c in df.columns]
    is_code = system_id.startswith("S1b_")
    prompt_file = {
        "S1a_summary_standard": "eval_llm_summary_standard_v1.txt",
        "S1a_summary_careful": "eval_llm_summary_careful_v1.txt",
        "S1b_code_standard": "eval_llm_code_standard_v1.txt",
        "S1b_code_careful": "eval_llm_code_careful_v1.txt",
    }[system_id]
    sys_prompt, prompt_ver = _load_prompt(prompt_file)
    summary_ctx = build_summary_context(df, sample_seed=42 + repeat_idx)

    t0 = time.perf_counter()
    total_cost = 0.0
    tests_detected: list[str] = []
    n_turns = 0

    if not is_code:
        if cost_tracker is not None:
            cost_tracker.check_can_spend(0.01)
        user_msg = (
            f"Analyze this dataset and report ONLY statistically supported bivariate findings.\n\n"
            f"{summary_ctx}"
        )
        cache_key = f"{system_id}:{dataset_id}:r{repeat_idx}:T{temperature:.2f}:{prompt_ver}"
        payload = llm.structured(
            system=sys_prompt,
            user=user_msg,
            schema=LLMFindingsPayload,
            temperature=temperature,
            max_tokens=2000,
            cache_key=cache_key,
        )
        total_cost += _record_usage(llm, cost_tracker, f"{system_id}:{dataset_id}:r{repeat_idx}")
        items = payload.findings
        n_turns = 1
    else:
        history: list[str] = [
            f"Dataset context (DataFrame `df` is preloaded from CSV):\n{summary_ctx}"
        ]
        items = []
        for turn in range(max_turns):
            n_turns = turn + 1
            if cost_tracker is not None:
                cost_tracker.check_can_spend(0.01)
            force_final = turn == max_turns - 1
            turn_note = (
                "FINAL TURN: You MUST set action='final' and return your findings JSON now."
                if force_final
                else f"Turn {turn + 1}/{max_turns}: set action='run_code' with python_code, or action='final' with findings."
            )
            user_msg = "\n\n---\n\n".join(history) + f"\n\n{turn_note}"
            cache_key = f"{system_id}:{dataset_id}:r{repeat_idx}:t{turn}:T{temperature:.2f}:{prompt_ver}"
            step = llm.structured(
                system=sys_prompt,
                user=user_msg,
                schema=LLMCodeStepPayload,
                temperature=temperature,
                max_tokens=2200,
                cache_key=cache_key,
            )
            total_cost += _record_usage(llm, cost_tracker, f"{system_id}:{dataset_id}:r{repeat_idx}:t{turn}")
            if step.action == "final" or force_final:
                items = step.findings
                break
            sb_res = run_sandboxed_code(step.python_code, csv_path, timeout_s=sandbox_timeout_s)
            tests_detected.extend(sb_res.get("tests_detected", []))
            if sb_res["ok"]:
                obs = f"Turn {turn + 1} code stdout:\n{sb_res['stdout'] or '(no stdout)'}"
            else:
                obs = f"Turn {turn + 1} code error:\n{sb_res['error']}"
            history.append(f"Turn {turn + 1} code:\n```python\n{step.python_code}\n```\n\n{obs}")

    findings, parse_meta = canonicalize_llm_findings(items, cols)
    elapsed = round(time.perf_counter() - t0, 3)
    return SystemOutput(
        system_name=system_id,
        dataset_id=dataset_id,
        findings=findings,
        n_tests_attempted=None,
        runtime_s=elapsed,
        cost_usd=round(total_cost, 6),
        meta={
            **parse_meta,
            "repeat_idx": repeat_idx,
            "temperature": temperature,
            "prompt_version": prompt_ver,
            "model": getattr(llm, "model_name", "unknown"),
            "n_turns": n_turns,
            "tests_detected": sorted(set(tests_detected)),
        },
    )


def summarize_llm_error(system_id: str, dataset_id: str, exc: Exception) -> SystemOutput:
    """Create a structured error SystemOutput when an LLM call fails."""
    if isinstance(exc, LLMError):
        msg = str(exc)
    else:
        msg = f"{type(exc).__name__}: {exc}"
    return SystemOutput(
        system_name=system_id,
        dataset_id=dataset_id,
        findings=[],
        error=msg,
    )
