"""Append-only session testing ledger with JSONL persistence and revalidation diffs (Section 7.5)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

import numpy as np

from veridata.config import PipelineConfig
from veridata.contracts.hypothesis import Hypothesis
from veridata.contracts.ledger import Ledger, LedgerEntry
from veridata.contracts.results import TestResult
from veridata.contracts.validation import ValidationDecision
from veridata.errors import ValidationError
from veridata.validation.validator import validate


class SessionLedger:
    """Append-only manager for every statistical test executed in a dataset session."""

    def __init__(self, dataset_sha256: str, alpha: float = 0.05) -> None:
        self._ledger = Ledger(dataset_sha256=dataset_sha256, alpha=alpha, entries=[])
        self._index: dict[str, LedgerEntry] = {}
        self._last_decisions: dict[str, ValidationDecision] = {}

    @property
    def dataset_sha256(self) -> str:
        return self._ledger.dataset_sha256

    @property
    def entries(self) -> list[LedgerEntry]:
        return list(self._ledger.entries)

    def add(
        self,
        test_result: TestResult,
        stage: Literal["batch", "chat"] = "batch",
    ) -> tuple[LedgerEntry, bool]:
        """Append a TestResult to the ledger; return cached entry if hypothesis_id already exists."""
        hid = test_result.hypothesis_id
        if hid in self._index:
            return self._index[hid], False

        entry = LedgerEntry(
            seq=len(self._ledger.entries) + 1,
            hypothesis_hash=hid,
            stage=stage,
            test=test_result,
            added_at_utc=datetime.now(timezone.utc).isoformat(),
        )
        self._ledger.entries.append(entry)
        self._index[hid] = entry
        return entry, True

    def get(self, hypothesis_id: str) -> LedgerEntry | None:
        return self._index.get(hypothesis_id)

    def family(self) -> list[LedgerEntry]:
        """Return all entries eligible for the BH correction family (status=='ok' & finite p)."""
        return [
            e
            for e in self._ledger.entries
            if e.test.status == "ok"
            and e.test.p_value is not None
            and np.isfinite(e.test.p_value)
        ]

    def revalidate(
        self,
        hypotheses: dict[str, Hypothesis],
        config: PipelineConfig,
        *,
        family_id: str = "session",
    ) -> tuple[list[ValidationDecision], list[dict[str, Any]]]:
        """Recompute multiple-testing validation over all ledger entries and report status diffs."""
        results = [e.test for e in self._ledger.entries]
        decisions = validate(results, hypotheses, config, family_id=family_id)

        diffs: list[dict[str, Any]] = []
        new_map = {d.hypothesis_id: d for d in decisions}
        for hid, prev in self._last_decisions.items():
            curr = new_map.get(hid)
            if curr is not None and prev.accepted != curr.accepted:
                diffs.append(
                    {
                        "hypothesis_id": hid,
                        "previous_accepted": prev.accepted,
                        "current_accepted": curr.accepted,
                        "previous_q": prev.q_value,
                        "current_q": curr.q_value,
                        "previous_m": prev.family_size,
                        "current_m": curr.family_size,
                    }
                )
        self._last_decisions = new_map
        return decisions, diffs

    def save_jsonl(self, path: Path | str) -> Path:
        """Persist ledger header + append-only entries to JSONL."""
        out_path = Path(path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        lines = [
            json.dumps(
                {
                    "type": "header",
                    "schema_version": self._ledger.schema_version,
                    "dataset_sha256": self._ledger.dataset_sha256,
                    "alpha": self._ledger.alpha,
                },
                sort_keys=True,
            )
        ]
        for entry in self._ledger.entries:
            lines.append(
                json.dumps(
                    {"type": "entry", "data": entry.model_dump(mode="json")},
                    sort_keys=True,
                )
            )
        out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return out_path

    @classmethod
    def load_jsonl(
        cls,
        path: Path | str,
        *,
        expected_dataset_sha256: str | None = None,
    ) -> SessionLedger:
        """Load a persisted JSONL ledger and verify dataset SHA-256 if provided."""
        in_path = Path(path)
        if not in_path.exists():
            raise ValidationError(f"Ledger file not found: {in_path}")

        raw_lines = [
            line.strip()
            for line in in_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        if not raw_lines:
            raise ValidationError(f"Ledger file is empty: {in_path}")

        header = json.loads(raw_lines[0])
        if header.get("type") != "header":
            raise ValidationError(f"Invalid ledger header in {in_path}")

        sha = str(header["dataset_sha256"])
        if expected_dataset_sha256 is not None and sha != expected_dataset_sha256:
            raise ValidationError(
                f"Ledger dataset SHA-256 mismatch: expected '{expected_dataset_sha256}', "
                f"found '{sha}'."
            )

        mgr = cls(dataset_sha256=sha, alpha=float(header.get("alpha", 0.05)))
        for line in raw_lines[1:]:
            rec = json.loads(line)
            if rec.get("type") == "entry":
                entry = LedgerEntry.model_validate(rec["data"])
                mgr._ledger.entries.append(entry)
                mgr._index[entry.hypothesis_hash] = entry
        return mgr

