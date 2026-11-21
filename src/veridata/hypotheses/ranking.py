"""Outcome-independent ranking and pruning of hypotheses (Phase 2 Section 6)."""

from __future__ import annotations

from typing import Any, Sequence

from veridata.config import PipelineConfig
from veridata.contracts.hypothesis import Hypothesis, RelationshipType
from veridata.schemas import ColumnSchemaEntry


def _interpretability_score(
    hypothesis: Hypothesis,
    schema: dict[str, ColumnSchemaEntry],
) -> float:
    """Heuristic interpretability score in [0, 1] based solely on relationship & cardinality."""
    rel = hypothesis.relationship
    if rel == RelationshipType.NUM_BINARY:
        return 1.0
    if rel == RelationshipType.NUM_NUM:
        return 0.8
    if rel == RelationshipType.NUM_NUM_NONLINEAR:
        return 0.7

    n_a = schema[hypothesis.column_a].n_unique if hypothesis.column_a in schema else 2
    n_b = schema[hypothesis.column_b].n_unique if hypothesis.column_b in schema else 2

    if rel == RelationshipType.CAT_CAT:
        if n_a <= 2 and n_b <= 2:
            return 1.0
        max_levels = max(n_a, n_b)
        return round(max(0.2, 0.75 - 0.03 * max(0, max_levels - 3)), 4)

    if rel == RelationshipType.NUM_CATEGORICAL:
        return round(max(0.2, 0.8 - 0.04 * max(0, n_b - 3)), 4)

    return 0.5


def _feasibility_strength(hypothesis: Hypothesis, min_group_n: int) -> float:
    """Sample-size strength score in [0, 1] using only counts (no outcome data)."""
    feas = hypothesis.feasibility
    if not feas.feasible or feas.n_pairwise_complete <= 0:
        return 0.0
    n_component = min(1.0, feas.n_pairwise_complete / 500.0)
    if feas.group_sizes:
        min_obs = min(feas.group_sizes.values())
        grp_component = min(1.0, min_obs / max(1.0, float(2 * min_group_n)))
        return round(0.5 * (n_component + grp_component), 4)
    return round(n_component, 4)


def score_hypothesis(
    hypothesis: Hypothesis,
    schema: dict[str, ColumnSchemaEntry],
    config: PipelineConfig,
    target: str | None = None,
    llm_relevance: float | None = None,
) -> tuple[float, dict[str, float]]:
    """Compute outcome-independent priority_score and its components in [0, 1]."""
    weights_cfg = config.hypotheses.ranking_weights

    pct_miss_a = schema[hypothesis.column_a].pct_missing if hypothesis.column_a in schema else 0.0
    pct_miss_b = schema[hypothesis.column_b].pct_missing if hypothesis.column_b in schema else 0.0

    components: dict[str, float] = {
        "feasibility_strength": _feasibility_strength(hypothesis, config.stats.min_group_n),
        "llm_relevance": round(
            float(llm_relevance) if llm_relevance is not None else 0.5, 4
        ),
        "interpretability": _interpretability_score(hypothesis, schema),
        "data_quality": round(max(0.0, min(1.0, 1.0 - 0.5 * (pct_miss_a + pct_miss_b))), 4),
    }

    active_weights: dict[str, float] = {
        "feasibility_strength": weights_cfg.feasibility_strength,
        "llm_relevance": weights_cfg.llm_relevance,
        "interpretability": weights_cfg.interpretability,
        "data_quality": weights_cfg.data_quality,
    }

    if target is not None:
        involves_target = 1.0 if target in (hypothesis.column_a, hypothesis.column_b) else 0.0
        components["target_involvement"] = involves_target
        active_weights["target_involvement"] = weights_cfg.target_involvement

    total_w = sum(active_weights.values())
    if total_w <= 0:
        return 0.0, components

    score = sum((w / total_w) * components[k] for k, w in active_weights.items())
    return round(score, 6), components


def rank_hypotheses(
    hypotheses: Sequence[Hypothesis],
    schema: dict[str, ColumnSchemaEntry],
    config: PipelineConfig,
    target: str | None = None,
    llm_relevance_map: dict[str, float] | None = None,
) -> list[Hypothesis]:
    """Order hypotheses by priority_score descending (tie-break: alphabetical id).

    Ranking ONLY orders hypotheses; it NEVER removes them.
    """
    rel_map = llm_relevance_map or {}
    scored: list[Hypothesis] = []
    for hyp in hypotheses:
        llm_rel = rel_map.get(hyp.id)
        if llm_rel is None and "llm_relevance" in hyp.priority_components:
            llm_rel = hyp.priority_components["llm_relevance"]
        score, comps = score_hypothesis(
            hyp,
            schema=schema,
            config=config,
            target=target,
            llm_relevance=llm_rel,
        )
        scored.append(
            hyp.model_copy(update={"priority_score": score, "priority_components": comps})
        )

    scored.sort(key=lambda h: (-h.priority_score, h.id))
    return scored


def _pair_max_cardinality(hypothesis: Hypothesis, schema: dict[str, ColumnSchemaEntry]) -> int:
    n_a = schema[hypothesis.column_a].n_unique if hypothesis.column_a in schema else 0
    n_b = schema[hypothesis.column_b].n_unique if hypothesis.column_b in schema else 0
    if hypothesis.relationship == RelationshipType.NUM_CATEGORICAL:
        return n_b
    return max(n_a, n_b)


def prune_hypotheses_outcome_independent(
    hypotheses: Sequence[Hypothesis],
    schema: dict[str, ColumnSchemaEntry],
    config: PipelineConfig,
    target: str | None = None,
) -> tuple[list[Hypothesis], list[dict[str, Any]], int, str | None]:
    """Apply outcome-independent pruning when feasible count exceeds max_tests (Section 6).

    Order of operations, stopping as soon as feasible count <= max_tests:
    1. If ``target`` exists -> switch to ``target_focused`` (drop non-target pairs).
    2. Else drop ``NUM_CATEGORICAL`` / ``CAT_CAT`` pairs with highest cardinality first.
    3. Else keep pairs with highest ``priority_score`` (tie-break alphabetical id).

    Returns ``(kept_hypotheses, pruning_steps, total_pruned, effective_mode_override)``.
    """
    max_tests = config.hypotheses.max_tests
    feasible = [h for h in hypotheses if h.feasibility.feasible]
    infeasible = [h for h in hypotheses if not h.feasibility.feasible]

    if len(feasible) <= max_tests:
        return list(hypotheses), [], 0, None

    pruning_steps: list[dict[str, Any]] = []
    total_pruned = 0
    effective_mode_override: str | None = None

    # Step 1: switch to target_focused if target is configured
    if target is not None:
        kept_target = [h for h in feasible if target in (h.column_a, h.column_b)]
        pruned_cnt = len(feasible) - len(kept_target)
        if pruned_cnt > 0:
            feasible = kept_target
            total_pruned += pruned_cnt
            effective_mode_override = "target_focused"
            pruning_steps.append(
                {
                    "rule": "switch_to_target_focused",
                    "target": target,
                    "pruned_count": pruned_cnt,
                    "remaining_feasible": len(feasible),
                }
            )

    # Step 2: drop NUM_CATEGORICAL / CAT_CAT pairs with highest cardinality first
    if len(feasible) > max_tests:
        cat_rels = {RelationshipType.NUM_CATEGORICAL, RelationshipType.CAT_CAT}
        cat_hyps = [h for h in feasible if h.relationship in cat_rels]
        other_hyps = [h for h in feasible if h.relationship not in cat_rels]

        # Sort categorical pairs so highest cardinality (and lowest priority) are dropped first
        cat_hyps.sort(
            key=lambda h: (-_pair_max_cardinality(h, schema), h.priority_score, h.id),
        )
        excess = len(feasible) - max_tests
        n_drop_cat = min(excess, len(cat_hyps))
        if n_drop_cat > 0:
            kept_cat = cat_hyps[n_drop_cat:]
            feasible = other_hyps + kept_cat
            total_pruned += n_drop_cat
            pruning_steps.append(
                {
                    "rule": "drop_high_cardinality_categorical_pairs",
                    "pruned_count": n_drop_cat,
                    "remaining_feasible": len(feasible),
                }
            )

    # Step 3: keep top max_tests by outcome-independent priority_score
    if len(feasible) > max_tests:
        feasible.sort(key=lambda h: (-h.priority_score, h.id))
        pruned_cnt = len(feasible) - max_tests
        feasible = feasible[:max_tests]
        total_pruned += pruned_cnt
        pruning_steps.append(
            {
                "rule": "keep_top_priority_score",
                "pruned_count": pruned_cnt,
                "remaining_feasible": len(feasible),
            }
        )

    kept_all = feasible + infeasible
    kept_all.sort(key=lambda h: (-h.priority_score, h.id))
    return kept_all, pruning_steps, total_pruned, effective_mode_override

