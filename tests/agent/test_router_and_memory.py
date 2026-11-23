"""Tests for context memory, pronoun resolution, and router intent classification."""

import pytest

from veridata.agent.memory import FocusState, resolve_coreference, summarize_history, update_focus
from veridata.agent.router import extract_arguments, route_intent_rules, validate_arguments


def test_coreference_pronoun_resolution():
    focus = FocusState(columns=["charges", "smoker"], hypothesis_id="h1")
    all_cols = ["charges", "smoker", "age", "region"]

    # "it" -> charges
    resolved, cols = resolve_coreference("Show the distribution of it.", focus, all_cols)
    assert "charges" in resolved
    assert "charges" in cols

    # "the other one" -> smoker
    resolved2, cols2 = resolve_coreference("Now tell me about the other one.", focus, all_cols)
    assert "smoker" in resolved2
    assert "smoker" in cols2

    # "now by region" -> region
    resolved3, cols3 = resolve_coreference("Now by region", focus, all_cols)
    assert "region" in cols3


def test_memory_summarization():
    messages = [{"role": "user", "content": f"msg {i}", "tool": "comp"} for i in range(15)]
    summarized = summarize_history(messages, max_turns_kept=5)
    assert len(summarized) == 6  # 1 summary + 5 kept
    assert summarized[0]["is_summary"] is True
    assert "Summary of previous 10 turns" in summarized[0]["content"]


def test_router_rule_baseline_accuracy():
    cols = ["charges", "smoker", "age", "bmi"]

    d1 = route_intent_rules("Can you give me an overview of the dataset?", cols)
    assert d1.intent == "describe_dataset"

    d2 = route_intent_rules("Compare charges by smoker", cols)
    assert d2.intent == "compare_groups"

    d3 = route_intent_rules("Is age correlated with charges?", cols)
    assert d3.intent == "test_correlation"

    d4 = route_intent_rules("What should we test next?", cols)
    assert d4.intent == "suggest_next"

    d5 = route_intent_rules("Why was the hypothesis rejected?", cols)
    assert d5.intent == "explain_rejection"


def test_validate_arguments_ambiguity():
    cols = ["charges", "smoker", "age"]

    # Valid args
    valid, args, pending = validate_arguments("describe_column", {"column": "charges"}, cols)
    assert valid
    assert pending is None

    # Missing column -> triggers clarification
    invalid, _, pending_clar = validate_arguments("describe_column", {}, cols)
    assert not invalid
    assert pending_clar is not None
    assert "Which column would you like to inspect?" in pending_clar["question"]
