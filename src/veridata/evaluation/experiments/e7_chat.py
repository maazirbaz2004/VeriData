"""E7 — Chat evaluation (single-turn gold, multi-turn sequences, ledger honesty, baseline)."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import pandas as pd

from veridata.agent.llm import LLMClient, NullLLM
from veridata.agent.session import create_session
from veridata.config import load_config
from veridata.evaluation.budget import BudgetExceededError, CostTracker
from veridata.evaluation.independent_recompute import (
    extract_and_check_llm_claim,
    verify_veridata_finding_independently,
)
from veridata.reporting.language_lint import lint_text


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _args_match(expected: dict[str, Any], actual: dict[str, Any] | None) -> bool:
    if not expected:
        return True
    act = actual or {}
    for k, v in expected.items():
        if str(act.get(k, "")).lower() != str(v).lower():
            return False
    return True


def run_e7(
    *,
    single_gold_path: Path = Path("tests/gold/chat_questions.jsonl"),
    multi_gold_path: Path = Path("configs/eval/chat_multiturn.jsonl"),
    cleaned_dir: Path = Path("data/cleaned"),
    configs_dir: Path = Path("configs/datasets"),
    eval_root: Path = Path("outputs/eval"),
    llm: LLMClient | None = None,
    cost_tracker: CostTracker | None = None,
) -> dict[str, Any]:
    """Evaluate VeriData chat over 85 single-turn questions and 12 multi-turn sessions."""
    single_items = _load_jsonl(single_gold_path)
    multi_items = _load_jsonl(multi_gold_path)

    # Load datasets once
    dfs: dict[str, pd.DataFrame] = {}
    cfgs: dict[str, Any] = {}
    for ds in ("insurance", "telco_churn", "heart_disease"):
        csv_p = cleaned_dir / f"{ds}_cleaned.csv"
        if csv_p.exists():
            dfs[ds] = pd.read_csv(csv_p)
            c_p = configs_dir / f"{ds}.yaml"
            cfgs[ds] = load_config(dataset_config_path=c_p if c_p.exists() else None)

    out_dir = eval_root / "e7"
    out_dir.mkdir(parents=True, exist_ok=True)
    human_dir = eval_root / "human_sheets"
    human_dir.mkdir(parents=True, exist_ok=True)

    # 1. Single-turn evaluation (grouped by dataset so each dataset shares one honest session or fresh turns)
    single_rows: list[dict[str, Any]] = []
    sessions_single: dict[str, Any] = {}
    for ds, df in dfs.items():
        sess = create_session(df, cfgs[ds], session_id=f"e7_single_{ds}", out_dir=out_dir / "sessions" / f"single_{ds}")
        sessions_single[ds] = sess

    followup_ok = 0
    followup_total = 0

    for item in single_items:
        ds = item.get("dataset", "insurance")
        if ds not in sessions_single:
            continue
        sess = sessions_single[ds]
        q = item["question"]
        exp_intent = item["expected_intent"]
        exp_args = item.get("expected_args", {})

        # Reset transient intent/args before each independent single-turn test while keeping ledger
        sess.state["intent"] = None
        sess.state["parsed_args"] = None
        sess.state["pending_clarification"] = None

        t0 = time.perf_counter()
        ans = sess.ask(q)
        lat_ms = (time.perf_counter() - t0) * 1000.0

        pred_intent = sess.state.get("intent") or ans.source
        pred_args = sess.state.get("parsed_args")
        intent_ok = pred_intent == exp_intent
        arg_ok = _args_match(exp_args, pred_args) if intent_ok else False

        # Independent recomputation for statistical test intents
        stat_ok: bool | None = None
        last_res = sess.state.get("last_tool_result") or {}
        if last_res.get("finding"):
            chk = verify_veridata_finding_independently(last_res["finding"], dfs[ds])
            if chk.get("checked"):
                stat_ok = bool(chk["ok"])

        li = lint_text(ans.text, kind="chat")
        causal_viols = sum(1 for issue in li if issue.code == "causal_language")

        # Follow-up executability probe (sample first 10 turns that produce follow-ups)
        if ans.followups and followup_total < 10:
            followup_total += 1
            try:
                f_ans = sess.run_followup(ans.followups[0]["tool_call"])
                if f_ans.verified and f_ans.text:
                    followup_ok += 1
            except Exception as exc:  # noqa: BLE001
                _ = str(exc)

        single_rows.append(
            {
                "id": item["id"],
                "dataset": ds,
                "question": q,
                "expected_intent": exp_intent,
                "pred_intent": pred_intent,
                "intent_ok": intent_ok,
                "arg_ok": arg_ok,
                "verified_numbers": bool(ans.verified),
                "stat_answer_ok": stat_ok,
                "causal_violations": causal_viols,
                "latency_ms": round(lat_ms, 2),
                "answer_text": ans.text,
            }
        )

    # 2. Multi-turn conversations (context carryover, clarification, duplicate suppression)
    multi_rows: list[dict[str, Any]] = []
    dup_checks = 0
    dup_suppressed = 0
    clar_checks = 0
    clar_ok = 0

    for conv in multi_items:
        ds = conv["dataset"]
        if ds not in dfs:
            continue
        sess = create_session(
            dfs[ds],
            cfgs[ds],
            session_id=f"e7_{conv['id']}",
            out_dir=out_dir / "sessions" / conv["id"],
        )
        for t_idx, turn in enumerate(conv["turns"]):
            sess.state["intent"] = None
            sess.state["parsed_args"] = None
            n_entries_before = len(sess.ledger.entries)
            t0 = time.perf_counter()
            ans = sess.ask(turn["question"])
            lat_ms = (time.perf_counter() - t0) * 1000.0
            n_entries_after = len(sess.ledger.entries)

            cat = turn.get("category", "")
            pred_intent = "clarification" if ans.source == "clarification" else (sess.state.get("intent") or ans.source)
            intent_ok = pred_intent == turn["expected_intent"]
            arg_ok = _args_match(turn.get("expected_args", {}), sess.state.get("parsed_args")) if intent_ok else False

            if cat == "duplicate_suppression":
                dup_checks += 1
                if n_entries_after == n_entries_before:
                    dup_suppressed += 1
            if cat == "ambiguous_clarification":
                clar_checks += 1
                if ans.source == "clarification":
                    clar_ok += 1

            li = lint_text(ans.text, kind="chat")
            multi_rows.append(
                {
                    "conv_id": conv["id"],
                    "turn": t_idx + 1,
                    "dataset": ds,
                    "category": cat,
                    "question": turn["question"],
                    "expected_intent": turn["expected_intent"],
                    "pred_intent": pred_intent,
                    "intent_ok": intent_ok,
                    "arg_ok": arg_ok,
                    "verified_numbers": bool(ans.verified),
                    "causal_violations": sum(1 for issue in li if issue.code == "causal_language"),
                    "latency_ms": round(lat_ms, 2),
                    "answer_text": ans.text,
                }
            )

    # 3. Optional Plain LLM Chat Baseline when API key is present
    llm_chat_summary: dict[str, Any] = {"status": "skipped_no_api_key"}
    if llm is not None and not isinstance(llm, NullLLM):
        prompt = Path("configs/prompts/eval_llm_chat_v1.txt").read_text(encoding="utf-8")
        stat_qs = [
            it
            for it in single_items
            if it["expected_intent"] in {"compare_groups", "test_correlation", "test_association"} and it["dataset"] in dfs
        ][:15]
        checked = 0
        ok_cnt = 0
        for it in stat_qs:
            if cost_tracker is not None:
                try:
                    cost_tracker.check_can_spend(0.01)
                except BudgetExceededError:
                    break
            ds = it["dataset"]
            df = dfs[ds]
            ctx = f"Columns: {list(df.columns)}\nDescribe:\n{df.describe(include='all').round(3).to_string()}"
            reply = llm.text(
                system=prompt,
                user=f"{ctx}\n\nQuestion: {it['question']}",
                temperature=0.0,
                max_tokens=500,
                cache_key=f"e7_chat_base:{it['id']}",
            )
            args = it.get("expected_args", {})
            ca = args.get("numeric_column") or args.get("column_a")
            cb = args.get("group_column") or args.get("column_b")
            if ca and cb:
                chk = extract_and_check_llm_claim(
                    col_a=ca, col_b=cb, claim_text=reply, claimed_p=None, claimed_effect=None, df=df
                )
                if chk["checkable"]:
                    checked += 1
                    if chk["verified"]:
                        ok_cnt += 1
        llm_chat_summary = {
            "status": "completed",
            "n_questions": len(stat_qs),
            "checkable": checked,
            "verified_rate": float(ok_cnt / checked) if checked else None,
        }

    # Export 20 sampled turns for human helpfulness/clarity rating
    rating_rows = [
        {
            "id": r["id"],
            "dataset": r["dataset"],
            "question": r["question"],
            "answer_text": r["answer_text"],
            "helpfulness_1_to_5": "",
            "clarity_1_to_5": "",
        }
        for r in single_rows[::4][:20]
    ]
    pd.DataFrame(rating_rows).to_csv(human_dir / "e7_chat_ratings.csv", index=False)

    stat_checks = [r["stat_answer_ok"] for r in single_rows if r["stat_answer_ok"] is not None]
    oos_rows = [r for r in single_rows if r["expected_intent"] == "out_of_scope"]
    all_rows = single_rows + multi_rows

    payload = {
        "n_single_turn": len(single_rows),
        "n_multi_turn": len(multi_rows),
        "single_intent_accuracy": float(sum(r["intent_ok"] for r in single_rows) / len(single_rows)) if single_rows else None,
        "single_arg_accuracy": float(sum(r["arg_ok"] for r in single_rows) / len(single_rows)) if single_rows else None,
        "multi_intent_accuracy": float(sum(r["intent_ok"] for r in multi_rows) / len(multi_rows)) if multi_rows else None,
        "answer_numeric_correctness": float(sum(stat_checks) / len(stat_checks)) if stat_checks else None,
        "verified_number_rate": float(sum(r["verified_numbers"] for r in all_rows) / len(all_rows)) if all_rows else None,
        "causal_language_violations": int(sum(r["causal_violations"] for r in all_rows)),
        "out_of_scope_refusal_rate": float(sum(r["intent_ok"] for r in oos_rows) / len(oos_rows)) if oos_rows else None,
        "clarification_rate": float(clar_ok / clar_checks) if clar_checks else None,
        "duplicate_suppression_rate": float(dup_suppressed / dup_checks) if dup_checks else None,
        "followup_executability_rate": float(followup_ok / followup_total) if followup_total else None,
        "mean_latency_ms": float(sum(r["latency_ms"] for r in all_rows) / len(all_rows)) if all_rows else None,
        "plain_llm_baseline": llm_chat_summary,
    }
    (out_dir / "summary.json").write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")
    pd.DataFrame(single_rows).to_csv(out_dir / "single_turn_results.csv", index=False)
    pd.DataFrame(multi_rows).to_csv(out_dir / "multi_turn_results.csv", index=False)
    return payload
