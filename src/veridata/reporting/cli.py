"""`veridata report --dataset NAME` and `veridata verify-text` (Phase 5, Section 10)."""

from __future__ import annotations

import argparse
import datetime as _dt
import json
from pathlib import Path

import pandas as pd

from veridata.config import load_config
from veridata.contracts.facts import Fact
from veridata.contracts.findings import Finding
from veridata.errors import ReportingError
from veridata.reporting.facts import FactRegistry
from veridata.reporting.number_verifier import verify_text


def run_findings_report(args: argparse.Namespace) -> int:
    from veridata.reporting.report_builder import build_report

    ds = args.dataset
    base = Path("outputs") / ds
    needed = {"findings": base / "findings.json", "manifest": base / "hypothesis_manifest.json", "cleaned": Path("data/cleaned") / f"{ds}_cleaned.csv"}
    missing = [str(p) for p in needed.values() if not p.exists()]
    if missing:
        print(f"Missing inputs for '{ds}': {', '.join(missing)}. Run `veridata run`, `veridata hypotheses` and `veridata test` first.")
        return 1
    cfg_path = Path("configs/datasets") / f"{ds}.yaml"
    cfg = load_config(dataset_config_path=cfg_path if cfg_path.exists() else None)
    if args.max_findings:
        cfg.reporting.max_findings_in_report = args.max_findings
    if args.narration == "llm_slots":
        print("Note: LLM slot narration is not implemented yet (cut list); using template narration.")
    findings = [Finding.model_validate(x) for x in json.loads(needed["findings"].read_text(encoding="utf-8"))]
    manifest = json.loads(needed["manifest"].read_text(encoding="utf-8"))
    log_path, prof_path = base / "cleaning_log.json", base / "profile.json"
    log = json.loads(log_path.read_text(encoding="utf-8")) if log_path.exists() else []
    prof = json.loads(prof_path.read_text(encoding="utf-8")) if prof_path.exists() else {"dataset_name": ds}
    df = pd.read_csv(needed["cleaned"])
    out = Path(args.out) if args.out else base / "report"
    try:
        art = build_report(
            findings, manifest, log, prof, df, cfg, None, out, dataset_name=ds,
            report_date=args.date or _dt.date.today().isoformat(), formats=tuple(x.strip() for x in args.format.split(",") if x.strip()),
            allow_violations=args.allow_violations,
        )
    except ReportingError as exc:
        print(f"Report gate failed: {exc}")
        return 2
    print(f"Report written to {art.markdown_path}" + (f" and {art.html_path}" if art.html_path else "") + f" (gate {'passed' if art.ok else 'FAILED'})")
    return 0 if art.ok else 2


def run_verify_text(args: argparse.Namespace) -> int:
    reg = FactRegistry()
    for item in json.loads(Path(args.facts).read_text(encoding="utf-8")):
        f = Fact.model_validate(item)
        reg.add(f, f.key.split(".", 1)[0] if "." in f.key else "report")
    res = verify_text(args.text, reg)
    print(json.dumps({"ok": res.ok, "extracted": res.extracted, "violations": [v.as_dict() for v in res.violations]}, indent=2))
    return 0 if res.ok else 1
