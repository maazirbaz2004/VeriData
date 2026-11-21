"""Evaluate the Phase 2 NL hypothesis parser on tests/gold/nl_hypotheses.jsonl."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from veridata.config import load_config
from veridata.hypotheses.nl_parser import parse_nl_hypothesis
from veridata.schemas import ColumnSchemaEntry


def evaluate_gold_set(
    gold_path: Path = Path("tests/gold/nl_hypotheses.jsonl"),
    out_md_path: Path = Path("outputs/phase2/nl_parser_eval.md"),
) -> dict[str, float]:
    """Run offline NL parser evaluation across the gold set and write markdown report."""
    records = [
        json.loads(line)
        for line in gold_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    cache_df: dict[str, pd.DataFrame] = {}
    cache_schema: dict[str, dict[str, ColumnSchemaEntry]] = {}
    cache_cfg = {}

    total = len(records)
    status_correct = 0
    ok_total = 0
    cols_correct = 0
    rel_correct = 0
    dir_correct = 0
    rows_md: list[str] = []

    for rec in records:
        ds = rec["dataset"]
        if ds not in cache_df:
            cfg_path = Path("configs/datasets") / f"{ds}.yaml"
            cache_cfg[ds] = load_config(dataset_config_path=cfg_path if cfg_path.exists() else None)
            cache_df[ds] = pd.read_csv(Path("data/cleaned") / f"{ds}_cleaned.csv")
            raw_schema = json.loads(
                (Path("outputs") / ds / "column_schema.json").read_text(encoding="utf-8")
            )
            cache_schema[ds] = {
                k: ColumnSchemaEntry.model_validate(v) for k, v in raw_schema.items()
            }

        outcome = parse_nl_hypothesis(
            text=rec["text"],
            df=cache_df[ds],
            schema=cache_schema[ds],
            llm=None,
            config=cache_cfg[ds],
        )

        st_ok = outcome.status == rec["expected_status"]
        if st_ok:
            status_correct += 1

        c_ok_str = "-"
        r_ok_str = "-"
        d_ok_str = "-"
        if rec["expected_status"] == "ok":
            ok_total += 1
            if outcome.hypothesis is not None:
                got_cols = sorted([outcome.hypothesis.column_a, outcome.hypothesis.column_b])
                exp_cols = sorted(rec["expected_columns"])
                c_ok = got_cols == exp_cols
                r_ok = outcome.hypothesis.relationship.value == rec["expected_relationship"]
                d_ok = outcome.hypothesis.expected_direction.value == rec["expected_direction"]
            else:
                c_ok = r_ok = d_ok = False
            if c_ok:
                cols_correct += 1
            if r_ok:
                rel_correct += 1
            if d_ok:
                dir_correct += 1
            c_ok_str = "PASS" if c_ok else "FAIL"
            r_ok_str = "PASS" if r_ok else "FAIL"
            d_ok_str = "PASS" if d_ok else "FAIL"

        rows_md.append(
            f"| `{rec['id']}` | `{ds}` | {rec['text']} | `{rec['expected_status']}` "
            f"| `{outcome.status}` | {c_ok_str} | {r_ok_str} | {d_ok_str} |"
        )

    metrics = {
        "total": float(total),
        "status_accuracy": round(status_correct / max(1, total), 4),
        "column_accuracy": round(cols_correct / max(1, ok_total), 4),
        "relationship_accuracy": round(rel_correct / max(1, ok_total), 4),
        "direction_accuracy": round(dir_correct / max(1, ok_total), 4),
    }

    out_md_path.parent.mkdir(parents=True, exist_ok=True)
    md = "\n".join(
        [
            "# Phase 2 — Natural-Language Hypothesis Parser Evaluation",
            "",
            f"- **Gold set:** `{gold_path}` (`{total}` labeled sentences, `{ok_total}` positive `ok` pairs)",
            "- **Mode:** Offline deterministic fuzzy fallback (`llm=None`)",
            f"- **Status accuracy:** `{metrics['status_accuracy']:.1%}` ({status_correct}/{total})",
            f"- **Column identification accuracy (on `ok`):** `{metrics['column_accuracy']:.1%}` ({cols_correct}/{ok_total})",
            f"- **Relationship type accuracy (on `ok`):** `{metrics['relationship_accuracy']:.1%}` ({rel_correct}/{ok_total})",
            f"- **Direction accuracy (on `ok`):** `{metrics['direction_accuracy']:.1%}` ({dir_correct}/{ok_total})",
            "",
            "| ID | Dataset | Sentence | Expected | Got | Cols | Rel | Dir |",
            "| :--- | :--- | :--- | :--- | :--- | :---: | :---: | :---: |",
            *rows_md,
            "",
        ]
    )
    out_md_path.write_text(md, encoding="utf-8")
    return metrics


if __name__ == "__main__":
    m = evaluate_gold_set()
    print(json.dumps(m, indent=2))

