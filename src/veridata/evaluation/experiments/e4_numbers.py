"""E4 — Number correctness verification (Phase 5 verify_text + independent recomputation)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from veridata.config import load_config
from veridata.contracts.findings import Finding
from veridata.evaluation.independent_recompute import (
    extract_and_check_llm_claim,
    verify_veridata_finding_independently,
)
from veridata.reporting.facts import FactRegistry, build_facts, build_method_facts, finding_id
from veridata.reporting.language_lint import lint_text
from veridata.reporting.narration import explain_finding
from veridata.reporting.number_verifier import verify_text


def run_e4(
    *,
    cleaned_dir: Path = Path("data/cleaned"),
    outputs_dir: Path = Path("outputs"),
    eval_root: Path = Path("outputs/eval"),
    datasets: tuple[str, ...] = ("insurance", "telco_churn", "heart_disease", "student_performance"),
    suite: str = "smoke",
    split: str = "dev",
) -> dict[str, Any]:
    """Verify VeriData numbers (both verifiers) and any cached S1a/S1b LLM claims."""
    cfg = load_config()
    recomp_rows: list[dict[str, Any]] = []
    verif_rows: list[dict[str, Any]] = []

    for ds in datasets:
        csv_p = cleaned_dir / f"{ds}_cleaned.csv"
        findings_p = outputs_dir / ds / "findings.json"
        if not csv_p.exists() or not findings_p.exists():
            continue
        df = pd.read_csv(csv_p)
        raw_findings = json.loads(findings_p.read_text(encoding="utf-8"))
        reg = FactRegistry()
        build_method_facts(reg, cfg)
        for item in raw_findings[:40]:  # bounded sample per real dataset
            f_obj = Finding.model_validate(item)
            fid = finding_id(f_obj)
            build_facts(f_obj, reg)
            expl = explain_finding(f_obj, reg, config=cfg)
            vt = verify_text(expl.text, reg, [fid])
            li = lint_text(expl.text, f_obj, kind="finding" if f_obj.decision.accepted else "rejected")
            verif_rows.append(
                {
                    "dataset": ds,
                    "hypothesis_id": f_obj.hypothesis.id,
                    "accepted": f_obj.decision.accepted,
                    "phase5_verified": bool(vt.ok and expl.verified),
                    "lint_ok": len(li) == 0,
                }
            )
            indep = verify_veridata_finding_independently(item, df)
            if indep.get("checked"):
                recomp_rows.append(
                    {
                        "dataset": ds,
                        "hypothesis_id": f_obj.hypothesis.id,
                        "test_name": f_obj.test.test_name,
                        "independent_ok": bool(indep["ok"]),
                        "mismatches": "; ".join(indep.get("mismatches", [])),
                    }
                )

    # Also evaluate cached LLM-only outputs from E1 if present
    llm_claim_rows: list[dict[str, Any]] = []
    sys_root = eval_root / suite / split / "systems"
    bench_root = Path("outputs/benchmark") / suite / split
    if sys_root.exists():
        for sys_dir in sorted(sys_root.iterdir()):
            if not (sys_dir.is_dir() and sys_dir.name.startswith("S1")):
                continue
            for res_p in sorted(sys_dir.glob("*.json")):
                ds_id = res_p.stem.split("__r")[0]
                csv_p = bench_root / ds_id / "data.csv"
                if not csv_p.exists():
                    continue
                df = pd.read_csv(csv_p)
                rec = json.loads(res_p.read_text(encoding="utf-8"))
                for f in rec.get("findings", []):
                    chk = extract_and_check_llm_claim(
                        col_a=f["col_a"],
                        col_b=f["col_b"],
                        claim_text=f.get("claim_text") or "",
                        claimed_p=f.get("p_value"),
                        claimed_effect=f.get("effect"),
                        df=df,
                    )
                    llm_claim_rows.append(
                        {
                            "system": sys_dir.name,
                            "dataset_id": ds_id,
                            "col_a": f["col_a"],
                            "col_b": f["col_b"],
                            "claim_text": f.get("claim_text") or "",
                            "checkable": chk["checkable"],
                            "verified": chk["verified"],
                            "hallucinated_column": chk["hallucinated_column"],
                            "details": "; ".join(chk.get("details", [])),
                            "human_audit_correct": "",
                            "human_audit_notes": "",
                        }
                    )

    out_dir = eval_root / "e4"
    out_dir.mkdir(parents=True, exist_ok=True)
    human_dir = eval_root / "human_sheets"
    human_dir.mkdir(parents=True, exist_ok=True)

    n_p5 = len(verif_rows)
    n_ind = len(recomp_rows)
    p5_rate = float(sum(1 for r in verif_rows if r["phase5_verified"]) / n_p5) if n_p5 else None
    ind_rate = float(sum(1 for r in recomp_rows if r["independent_ok"]) / n_ind) if n_ind else None

    llm_summary: dict[str, Any] = {}
    for sys_name in sorted({r["system"] for r in llm_claim_rows}):
        sub = [r for r in llm_claim_rows if r["system"] == sys_name]
        checkable = [r for r in sub if r["checkable"]]
        verified = [r for r in checkable if r["verified"] is True]
        halluc = [r for r in sub if r["hallucinated_column"]]
        llm_summary[sys_name] = {
            "total_claims": len(sub),
            "checkable_claims": len(checkable),
            "verified_rate": float(len(verified) / len(checkable)) if checkable else None,
            "fabricated_rate": float(1.0 - len(verified) / len(checkable)) if checkable else None,
            "unverifiable_share": float((len(sub) - len(checkable)) / len(sub)) if sub else None,
            "hallucinated_column_count": len(halluc),
        }

    payload = {
        "veridata_n_narrations_checked": n_p5,
        "veridata_phase5_verified_rate": p5_rate,
        "veridata_n_findings_recomputed": n_ind,
        "veridata_independent_verified_rate": ind_rate,
        "veridata_lint_pass_rate": float(sum(1 for r in verif_rows if r["lint_ok"]) / n_p5) if n_p5 else None,
        "llm_baselines": llm_summary,
    }
    (out_dir / "summary.json").write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")
    pd.DataFrame(verif_rows).to_csv(out_dir / "veridata_phase5_checks.csv", index=False)
    pd.DataFrame(recomp_rows).to_csv(out_dir / "veridata_recompute.csv", index=False)
    pd.DataFrame(llm_claim_rows).to_csv(out_dir / "llm_claims_checked.csv", index=False)
    pd.DataFrame(llm_claim_rows[:30]).to_csv(human_dir / "e4_llm_claims_audit.csv", index=False)
    return payload
