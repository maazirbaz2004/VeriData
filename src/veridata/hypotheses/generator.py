"""Phase 2 orchestrator: generate_hypotheses() and JSON/Markdown artifact writers."""

from __future__ import annotations

import json
import logging
from collections import Counter
from pathlib import Path
from typing import Literal

import pandas as pd

from veridata.agent.llm import LLMClient
from veridata.config import PipelineConfig
from veridata.contracts.hypothesis import (
    Hypothesis,
    HypothesisManifest,
    HypothesisSet,
)
from veridata.hypotheses.dedupe import deduplicate_hypotheses
from veridata.hypotheses.enumerate import enumerate_hypotheses, filter_eligible_columns
from veridata.hypotheses.feasibility import screen_hypotheses
from veridata.hypotheses.llm_proposer import propose_hypotheses_with_llm
from veridata.hypotheses.ranking import prune_hypotheses_outcome_independent, rank_hypotheses
from veridata.hypotheses.safe_profile import build_safe_profile
from veridata.schemas import ColumnSchemaEntry, DataProfile

logger = logging.getLogger("veridata.hypotheses.generator")


def generate_hypotheses(
    df: pd.DataFrame,
    schema: dict[str, ColumnSchemaEntry],
    profile: DataProfile | None,
    config: PipelineConfig,
    llm: LLMClient | None = None,
    target: str | None = None,
    *,
    mode: Literal["exhaustive", "target_focused", "llm_prioritized"] | None = None,
    dataset_name: str | None = None,
    dataset_description: str = "unknown",
    column_descriptions: dict[str, str] | None = None,
) -> HypothesisSet:
    """Generate a validated, deduplicated, feasibility-screened, ranked HypothesisSet.

    Enforces Principle P2 (no peeking): selection and ranking depend ONLY on schema
    metadata, univariate profile summaries, and sample-size feasibility counts.
    """
    active_target = (
        target if target is not None else (config.hypotheses.target or config.target)
    )
    requested_mode: Literal["exhaustive", "target_focused", "llm_prioritized"] = (
        mode or config.hypotheses.mode
    )
    effective_mode: Literal["exhaustive", "target_focused", "llm_prioritized"] = requested_mode
    ds_name = dataset_name or config.name

    # 1. Enumerate candidates (for llm_prioritized, enumerate exhaustively first for accounting/top-up)
    enum_mode: Literal["exhaustive", "target_focused", "llm_prioritized"] = (
        "exhaustive" if requested_mode == "llm_prioritized" else requested_mode
    )
    enumerated, excluded_cols, notes, n_eligible_cols = enumerate_hypotheses(
        schema=schema,
        config=config,
        target=active_target,
        mode=enum_mode,
    )
    n_total_eligible_before_selection = len(enumerated)

    # 2. Screen feasibility on enumerated candidates
    screened_enum = screen_hypotheses(enumerated, df, schema, config)

    # 3. Build safe univariate-only profile & hash proving no outcome data used
    eligible_cols, _, _ = filter_eligible_columns(schema, config)
    safe_profile, alias_to_col, _, selection_inputs_hash = build_safe_profile(
        schema=schema,
        profile=profile,
        config=config,
        eligible_columns=eligible_cols,
        target=active_target,
        dataset_description=dataset_description,
        column_descriptions=column_descriptions,
    )

    # 4. Optional LLM proposals / prioritization
    llm_res = propose_hypotheses_with_llm(
        safe_profile=safe_profile,
        alias_to_col=alias_to_col,
        schema=schema,
        config=config,
        llm=llm,
    )

    topped_up_count = 0
    if requested_mode == "llm_prioritized":
        if llm_res.llm_used and llm_res.proposals:
            screened_llm = screen_hypotheses(llm_res.proposals, df, schema, config)
            deduped_llm = deduplicate_hypotheses(screened_llm)
            feasible_llm = [h for h in deduped_llm if h.feasibility.feasible]
            selected_ids = {h.id for h in deduped_llm}

            min_needed = config.hypotheses.min_llm_hypotheses
            combined: list[Hypothesis] = list(deduped_llm)

            if len(feasible_llm) < min_needed:
                ranked_enum = rank_hypotheses(
                    screened_enum,
                    schema=schema,
                    config=config,
                    target=active_target,
                    llm_relevance_map=llm_res.relevance_by_id,
                )
                for h in ranked_enum:
                    if len(feasible_llm) >= min_needed:
                        break
                    if h.feasibility.feasible and h.id not in selected_ids:
                        combined.append(h)
                        selected_ids.add(h.id)
                        feasible_llm.append(h)
                        topped_up_count += 1
                if topped_up_count > 0:
                    notes.append(
                        f"LLM returned fewer than {min_needed} feasible proposals; "
                        f"topped up with {topped_up_count} outcome-independent enumerated pairs."
                    )
            working = deduplicate_hypotheses(combined)
            notes.append(
                f"tested {sum(1 for h in working if h.feasibility.feasible)} of "
                f"{n_total_eligible_before_selection} eligible pairs, chosen before looking at results"
            )
        else:
            notes.append(
                "llm_prioritized requested without available LLM; fell back to exhaustive enumeration."
            )
            effective_mode = "exhaustive"
            working = screened_enum
    else:
        # In exhaustive / target_focused: LLM only annotates relevance & rationale on enumerated pairs
        if llm_res.llm_used and llm_res.proposals:
            enum_ids = {h.id for h in screened_enum}
            annotated: list[Hypothesis] = []
            llm_by_id = {h.id: h for h in deduplicate_hypotheses(llm_res.proposals)}
            for h in screened_enum:
                if h.id in llm_by_id:
                    lh = llm_by_id[h.id]
                    # Keep source="enumerated" when already in enumerated set (Section 5.3)
                    annotated.append(
                        h.model_copy(
                            update={
                                "rationale": lh.rationale or h.rationale,
                                "expected_direction": (
                                    lh.expected_direction
                                    if lh.expected_direction.value != "any"
                                    else h.expected_direction
                                ),
                            }
                        )
                    )
                else:
                    annotated.append(h)
            working = annotated
            _ = enum_ids
        else:
            working = screened_enum

    # 5. Outcome-independent ranking (ordering only)
    ranked = rank_hypotheses(
        working,
        schema=schema,
        config=config,
        target=active_target,
        llm_relevance_map=llm_res.relevance_by_id,
    )

    n_candidate_before_pruning = len(ranked)

    # 6. Outcome-independent pruning if feasible count > max_tests
    final_hyps, pruning_steps, n_pruned, mode_override = prune_hypotheses_outcome_independent(
        ranked,
        schema=schema,
        config=config,
        target=active_target,
    )
    if mode_override is not None:
        effective_mode = mode_override  # type: ignore[assignment]
    if n_pruned > 0:
        notes.append(f"{n_pruned} eligible pairs were not tested due to the max_tests cap.")

    feasible_final = [h for h in final_hyps if h.feasibility.feasible]
    infeasible_final = [h for h in final_hyps if not h.feasibility.feasible]
    rel_counts = dict(sorted(Counter(h.relationship.value for h in feasible_final).items()))

    manifest = HypothesisManifest(
        dataset_name=ds_name,
        mode=requested_mode,
        effective_mode=effective_mode,
        target=active_target,
        n_columns_total=len(schema),
        n_columns_eligible=n_eligible_cols,
        excluded_columns=excluded_cols,
        n_candidate_hypotheses=n_candidate_before_pruning,
        n_infeasible=len(infeasible_final),
        n_pruned=n_pruned,
        pruning_steps=pruning_steps,
        n_in_family_planned=len(feasible_final),
        n_total_eligible_before_selection=n_total_eligible_before_selection,
        counts_by_relationship=rel_counts,
        treat_small_discrete_as_numeric=config.hypotheses.treat_small_discrete_as_numeric,
        lump_rare_levels=config.hypotheses.lump_rare_levels,
        llm_used=llm_res.llm_used,
        llm_model=llm_res.llm_model,
        llm_prompt_version=llm_res.prompt_version,
        llm_unknown_aliases_dropped=llm_res.unknown_aliases_dropped,
        llm_invalid_rationales_dropped=llm_res.invalid_rationales_dropped,
        llm_topped_up_count=topped_up_count,
        selection_inputs_hash=selection_inputs_hash,
        notes=notes,
    )

    return HypothesisSet(hypotheses=final_hyps, manifest=manifest)


def render_hypotheses_markdown(hypothesis_set: HypothesisSet) -> str:
    """Render a human-readable Markdown summary of the generated HypothesisSet."""
    m = hypothesis_set.manifest
    lines: list[str] = [
        f"# Phase 2 Hypothesis Set — `{m.dataset_name}`",
        "",
        "## Family Manifest Summary",
        f"- **Mode:** `{m.mode}` (effective: `{m.effective_mode}`)",
        f"- **Target:** `{m.target}`" if m.target else "- **Target:** *(none)*",
        f"- **Columns:** `{m.n_columns_eligible}` eligible / `{m.n_columns_total}` total",
        f"- **Candidate Hypotheses:** `{m.n_candidate_hypotheses}`",
        f"- **Planned Family Size (`m`):** `{m.n_in_family_planned}` feasible (`{m.n_infeasible}` infeasible, `{m.n_pruned}` pruned)",
        f"- **LLM Used:** `{m.llm_used}`"
        + (f" (`{m.llm_model}`, prompt `{m.llm_prompt_version}`)" if m.llm_used else ""),
        f"- **Selection Inputs Hash:** `{m.selection_inputs_hash}`",
        "",
    ]

    if m.counts_by_relationship:
        lines.append("### Planned Tests by Relationship Type")
        for rel, cnt in m.counts_by_relationship.items():
            lines.append(f"- `{rel}`: `{cnt}`")
        lines.append("")

    if m.excluded_columns:
        lines.append("### Excluded Columns")
        for exc in m.excluded_columns:
            lines.append(f"- `{exc['name']}`: {exc['reason']}")
        lines.append("")

    if m.notes:
        lines.append("### Manifest Notes")
        for note in m.notes:
            lines.append(f"- {note}")
        lines.append("")

    lines.extend(
        [
            "## Hypotheses (Ordered by Outcome-Independent Priority)",
            "",
            "| ID | Column A | Column B | Relationship | Feasible | n_complete | Priority | Source | Rationale |",
            "| :--- | :--- | :--- | :--- | :---: | ---: | ---: | :--- | :--- |",
        ]
    )
    for h in hypothesis_set.hypotheses:
        feas_str = "yes" if h.feasibility.feasible else "no"
        rat = h.rationale.replace("|", "/") if h.rationale else (
            "; ".join(h.feasibility.reasons).replace("|", "/") if not h.feasibility.feasible else ""
        )
        lines.append(
            f"| `{h.id}` | `{h.column_a}` | `{h.column_b}` | `{h.relationship.value}` "
            f"| {feas_str} | {h.feasibility.n_pairwise_complete} | {h.priority_score:.3f} "
            f"| `{h.source}` | {rat} |"
        )
    lines.append("")
    return "\n".join(lines)


def save_hypothesis_outputs(
    hypothesis_set: HypothesisSet,
    out_dir: Path | str,
) -> dict[str, Path]:
    """Write hypotheses.json, hypothesis_manifest.json, and hypotheses.md deterministically."""
    target_dir = Path(out_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    hyps_json_path = target_dir / "hypotheses.json"
    manifest_json_path = target_dir / "hypothesis_manifest.json"
    hyps_md_path = target_dir / "hypotheses.md"

    hyps_payload = [h.model_dump(mode="json") for h in hypothesis_set.hypotheses]
    hyps_json_path.write_text(
        json.dumps(hyps_payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    manifest_json_path.write_text(
        json.dumps(hypothesis_set.manifest.model_dump(mode="json"), indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    hyps_md_path.write_text(
        render_hypotheses_markdown(hypothesis_set),
        encoding="utf-8",
    )

    return {
        "hypotheses_json": hyps_json_path,
        "manifest_json": manifest_json_path,
        "hypotheses_md": hyps_md_path,
    }

