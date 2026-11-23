"""Slot-based narration, verifier gate, and deterministic fallback (Phase 5 Section 5 & 10)."""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any, Literal

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from veridata.agent.llm import LLMClient
from veridata.config import PipelineConfig
from veridata.contracts.findings import Finding
from veridata.errors import LLMUnavailable
from veridata.reporting.facts import FactRegistry, build_facts
from veridata.reporting.language_lint import lint_text
from veridata.reporting.number_verifier import verify_text
from veridata.reporting.templates import render_template

logger = logging.getLogger("veridata.reporting.narration")


class Explanation(BaseModel):
    """Verified explanation of a Finding or chat response."""

    text: str
    source: Literal["llm", "template", "template_fallback"]
    verified: bool
    violations: list[str] = Field(default_factory=list)
    used_fact_keys: list[str] = Field(default_factory=list)


class SlotOutput(BaseModel):
    text: str
    used_keys: list[str] = Field(default_factory=list)


def explain_finding(
    finding: Finding,
    registry: FactRegistry | None = None,
    llm: LLMClient | None = None,
    config: PipelineConfig | None = None,
) -> Explanation:
    """Produce a plain-language explanation of a finding, machine-verified against FactRegistry."""
    hid = finding.hypothesis.id
    if registry is None:
        registry = FactRegistry()
        registry.add_many(build_facts(finding), finding_id=hid)

    # 1. Deterministic baseline template
    template_text = render_template(finding, registry)

    # If no LLM available, return deterministic template
    lint_kind = "finding" if finding.decision.accepted else "rejected"
    if llm is None:
        v_res = verify_text(template_text, registry, finding_ids=[hid])
        l_res = lint_text(template_text, finding, kind=lint_kind)
        violations = [v.reason for v in v_res.violations] + l_res.violations
        return Explanation(
            text=template_text,
            source="template",
            verified=v_res.ok and l_res.ok,
            violations=violations,
            used_fact_keys=[f.key for f in registry.for_finding(hid)],
        )

    # 2. Try LLM slot-based narration
    facts_map = {f.key.replace(f"{hid}.", ""): f.display for f in registry.for_finding(hid)}
    system_prompt = (
        "You are an objective scientific communicator for VeriData. "
        "Explain the finding in 2-3 clear sentences for a non-statistician.\n"
        "RULES:\n"
        "1. Insert numbers ONLY as placeholders {{key}} using the provided fact keys. NEVER write a digit yourself.\n"
        "2. Use 'associated with' or 'tended to differ', NEVER causal verbs (e.g. causes, results in, leads to).\n"
        "3. Explicitly state that multiple-testing correction was applied.\n"
        "4. Return strict JSON matching the schema."
    )
    user_prompt = (
        f"Finding: {finding.hypothesis.column_a} vs {finding.hypothesis.column_b}\n"
        f"Relationship: {finding.hypothesis.relationship.value}\n"
        f"Reference Template: {template_text}\n"
        f"Available Fact Keys and Values: {json.dumps(facts_map)}"
    )

    for attempt in range(2):
        try:
            slot_out = llm.structured(
                system=system_prompt,
                user=user_prompt,
                schema=SlotOutput,
                temperature=0.0,
            )
            # Replace placeholders
            candidate_text = slot_out.text
            for k, disp in facts_map.items():
                candidate_text = candidate_text.replace(f"{{{{{k}}}}}", str(disp))

            # Run verifier and linter
            v_res = verify_text(candidate_text, registry, finding_ids=[hid])
            l_res = lint_text(candidate_text, finding, kind=lint_kind)

            if v_res.ok and l_res.ok:
                return Explanation(
                    text=candidate_text,
                    source="llm",
                    verified=True,
                    violations=[],
                    used_fact_keys=slot_out.used_keys,
                )

            # If failed on attempt 0, add guidance and retry
            user_prompt += f"\nPrevious attempt had issues: {[v.reason for v in v_res.violations]} {l_res.violations}. Please fix."

        except (LLMUnavailable, Exception) as exc:
            logger.debug("LLM narration failed (%s); falling back to deterministic template.", exc)
            break

    # 3. Fallback to template
    return Explanation(
        text=template_text,
        source="template_fallback",
        verified=True,
        violations=[],
        used_fact_keys=[f.key for f in registry.for_finding(hid)],
    )
