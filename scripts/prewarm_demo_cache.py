"""Pre-warm demo cache and generate precomputed analysis bundles for instant demo loading (Phase 7 Section 4)."""

from __future__ import annotations

import json
from pathlib import Path
import pandas as pd

from veridata.agent.session import create_session
from veridata.config import PipelineConfig


def prewarm_dataset(name: str, csv_path: Path | str, out_bundle_dir: Path) -> None:
    print(f"\n---> Pre-warming bundle for dataset: {name}")
    df = pd.read_csv(csv_path)
    bundle_dir = out_bundle_dir / name
    bundle_dir.mkdir(parents=True, exist_ok=True)

    cfg = PipelineConfig(name=name, file=str(csv_path))
    sess = create_session(df, cfg, out_dir=bundle_dir)

    # 1. Run batch analysis
    print(f"  Running batch analysis pipeline...")
    batch_res = sess.run_batch(progress_callback=lambda msg: print(f"    [Progress] {msg}"))

    # 2. Extract and save findings summary, ledger, decisions
    findings = sess.get_findings()
    rejected = sess.get_rejected()
    ledger_status = sess.get_ledger_status()

    # Save summary metadata
    bundle_meta = {
        "dataset_name": name,
        "n_rows": int(len(df)),
        "n_cols": int(len(df.columns)),
        "family_size": ledger_status.get("family_size", 0),
        "total_tests": ledger_status.get("total_tests", 0),
        "validated_count": len([f for f in findings if f.decision.accepted]),
        "rejected_count": len(rejected),
    }

    (bundle_dir / "bundle_meta.json").write_text(json.dumps(bundle_meta, indent=2), encoding="utf-8")
    (bundle_dir / "rejected.json").write_text(json.dumps(rejected, indent=2), encoding="utf-8")
    (bundle_dir / "findings_summary.json").write_text(
        json.dumps([f.model_dump(mode="json") for f in findings], indent=2),
        encoding="utf-8",
    )

    print(f"  Bundle saved at: {bundle_dir} (Validated: {bundle_meta['validated_count']}, Rejected: {bundle_meta['rejected_count']})")


def main():
    demo_dir = Path("data/demo")
    out_bundle_dir = Path("demo_bundles")
    out_bundle_dir.mkdir(parents=True, exist_ok=True)

    demo_datasets = [
        ("pure_noise", demo_dir / "pure_noise.csv"),
        ("insurance", demo_dir / "insurance.csv"),
        ("messy", demo_dir / "messy.csv"),
    ]

    for name, path in demo_datasets:
        if Path(path).exists():
            prewarm_dataset(name, path, out_bundle_dir)

    print("\nAll demo bundles successfully pre-warmed and saved to demo_bundles/.")


if __name__ == "__main__":
    main()
