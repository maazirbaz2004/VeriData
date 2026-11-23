"""Evaluate router intent classification and argument extraction accuracy on the gold set (Phase 6 M8)."""

from __future__ import annotations

import argparse
import json
import logging
from collections import defaultdict
from pathlib import Path
from typing import Any

from veridata.agent.fake_llm import FakeLLM
from veridata.agent.llm import AnthropicLLMClient, NullLLM
from veridata.agent.router import extract_arguments, route_intent_rules

logger = logging.getLogger("eval_router")


def load_gold_set(path: Path | str = "tests/gold/chat_questions.jsonl") -> list[dict[str, Any]]:
    items = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                items.append(json.loads(line))
    return items


def eval_router(gold_path: Path | str = "tests/gold/chat_questions.jsonl") -> dict[str, Any]:
    dataset_cols = {
        "insurance": ["age", "sex", "bmi", "children", "smoker", "region", "charges"],
        "telco_churn": [
            "gender", "SeniorCitizen", "Partner", "Dependents", "tenure",
            "PhoneService", "MultipleLines", "InternetService", "OnlineSecurity",
            "OnlineBackup", "DeviceProtection", "TechSupport", "StreamingTV",
            "StreamingMovies", "Contract", "PaperlessBilling", "PaymentMethod",
            "MonthlyCharges", "TotalCharges", "Churn",
        ],
        "heart_disease": [
            "age", "sex", "cp", "trestbps", "chol", "fbs", "restecg",
            "thalach", "exang", "oldpeak", "slope", "ca", "thal", "target",
        ],
    }

    questions = load_gold_set(gold_path)
    total = len(questions)
    intent_correct = 0
    arg_correct = 0
    per_intent_total = defaultdict(int)
    per_intent_correct = defaultdict(int)

    for item in questions:
        ds = item.get("dataset", "insurance")
        cols = dataset_cols.get(ds, dataset_cols["insurance"])
        q = item["question"]
        exp_intent = item["expected_intent"]
        exp_args = item.get("expected_args", {})

        # Rule router evaluation
        dec = route_intent_rules(q, cols)
        pred_intent = dec.intent
        per_intent_total[exp_intent] += 1

        is_intent_ok = pred_intent == exp_intent
        if is_intent_ok:
            intent_correct += 1
            per_intent_correct[exp_intent] += 1

        # Extract arguments
        extracted = extract_arguments(q, pred_intent, cols)
        is_arg_ok = True
        for k, v in exp_args.items():
            if extracted.get(k) != v:
                is_arg_ok = False
                break
        if is_arg_ok:
            arg_correct += 1

    intent_acc = intent_correct / total if total > 0 else 0.0
    arg_acc = arg_correct / total if total > 0 else 0.0

    print(f"\n========================================================")
    print(f"  VeriData Router Evaluation Report (Rule-based Baseline) ")
    print(f"========================================================")
    print(f"Total gold questions:      {total}")
    print(f"Overall Intent Accuracy:   {intent_acc:.1%} ({intent_correct}/{total})")
    print(f"Overall Argument Accuracy: {arg_acc:.1%} ({arg_correct}/{total})")
    print(f"--------------------------------------------------------")
    print(f"{'Intent':<25} {'Accuracy':<12} {'Counts'}")
    print(f"--------------------------------------------------------")
    for intent, count in sorted(per_intent_total.items()):
        acc = per_intent_correct[intent] / count if count > 0 else 0.0
        print(f"{intent:<25} {acc:>8.1%}     ({per_intent_correct[intent]}/{count})")
    print(f"========================================================\n")

    return {
        "total": total,
        "intent_accuracy": intent_acc,
        "argument_accuracy": arg_acc,
        "per_intent": {k: per_intent_correct[k] / v for k, v in per_intent_total.items()},
    }


if __name__ == "__main__":
    eval_router()
