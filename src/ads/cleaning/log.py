"""Structured cleaning log collector and JSON/Markdown serializers (Section 6.4, Section 9.12)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

from ads.schemas import CleaningLogEntry


class CleaningLog:
    """Collector for structured CleaningLogEntry items during clean_dataset()."""

    def __init__(self) -> None:
        self.entries: list[CleaningLogEntry] = []

    def add(
        self,
        step: str,
        action: str,
        rows_before: int,
        rows_after: int,
        reason: str,
        column: str | None = None,
        n_cells_affected: int = 0,
        n_rows_affected: int = 0,
        before_examples: list[ Any ] | None = None,
        after_examples: list[ Any ] | None = None,
        parameters: dict[str, Any] | None = None,
        severity: Literal["info", "warning"] = "info",
    ) -> CleaningLogEntry:
        """Create and append a CleaningLogEntry (capping examples at 5)."""
        b_ex = [str(x) for x in (before_examples or [])[:5]]
        a_ex = [str(x) for x in (after_examples or [])[:5]]
        entry = CleaningLogEntry(
            step=step,
            column=column,
            action=action,
            n_cells_affected=int(n_cells_affected),
            n_rows_affected=int(n_rows_affected),
            rows_before=int(rows_before),
            rows_after=int(rows_after),
            reason=reason,
            before_examples=b_ex,
            after_examples=a_ex,
            parameters=parameters or {},
            severity=severity,
        )
        self.entries.append(entry)
        return entry

    def total_rows_removed(self) -> int:
        """Sum of row removals across all row-dropping steps."""
        return sum(max(0, e.rows_before - e.rows_after) for e in self.entries)

    def has_meaningful_changes(self) -> bool:
        """Return True if any entry modified conservative cells or removed conservative rows/columns."""
        info_only_or_imputed_only_actions = {
            "none",
            "flagged_only",
            "flagged_outliers",
            "sanity_check_flag",
            "flagged_fuzzy_variants",
            "kept_duplicates_warning",
            "marked_excluded",
            "validation_passed",
            "imputed_median",
            "imputed_mode",
            "imputed_missing_level",
            "left_datetime_missing",
            "dropped_column_imputed_only",
            "dropped_missing_target_rows_imputed",
        }
        for e in self.entries:
            if e.action in info_only_or_imputed_only_actions:
                continue
            if e.n_cells_affected > 0 or (e.rows_before != e.rows_after):
                return True
        return False

    def summary_dict(self) -> dict[str, Any]:
        """Aggregate summary counts by step and action."""
        by_step: dict[str, int] = {}
        total_cells = 0
        warnings_count = 0
        for e in self.entries:
            by_step[e.step] = by_step.get(e.step, 0) + e.n_cells_affected
            total_cells += e.n_cells_affected
            if e.severity == "warning":
                warnings_count += 1
        return {
            "n_log_entries": len(self.entries),
            "total_cells_affected": total_cells,
            "total_rows_removed": self.total_rows_removed(),
            "n_warnings": warnings_count,
            "cells_affected_by_step": by_step,
        }


def save_cleaning_log_json(entries: list[CleaningLogEntry], path: Path | str) -> Path:
    """Serialize list of CleaningLogEntry items to cleaning_log.json."""
    out_path = Path(path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = [e.model_dump(mode="json") for e in entries]
    out_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return out_path


def render_cleaning_log_markdown(
    entries: list[CleaningLogEntry],
    dataset_name: str = "dataset",
) -> str:
    """Render a human-readable Markdown report of the cleaning log (Section 9.12)."""
    n_steps = len({e.step for e in entries})
    n_type_cols = sum(1 for e in entries if e.step == "convert_types" and e.n_cells_affected > 0)
    n_norm_cells = sum(
        e.n_cells_affected
        for e in entries
        if e.step in {"clean_whitespace_unicode", "normalize_missing_tokens", "standardize_categories"}
    )
    n_dup_removed = sum(
        max(0, e.rows_before - e.rows_after)
        for e in entries
        if e.step == "handle_duplicates"
    )
    n_struct_removed = sum(
        max(0, e.rows_before - e.rows_after)
        for e in entries
        if e.step == "structural_drops"
    )

    lines = [
        f"# Cleaning Log — `{dataset_name}`",
        "",
        "## Summary",
        (
            f"{n_steps} cleaning step group(s) recorded; {n_type_cols} column(s) type-converted; "
            f"{n_norm_cells} cell(s) normalized (whitespace/missing tokens/categories); "
            f"{n_dup_removed} duplicate row(s) removed; "
            f"{n_struct_removed} row(s) dropped for structural/missingness rules."
        ),
        "",
        "## Step-by-Step Log",
        "",
        "| Step | Column | Action | Severity | Cells Affected | Rows (Before -> After) | Reason | Examples (Before -> After) |",
        "| :--- | :--- | :--- | :--- | ---: | ---: | :--- | :--- |",
    ]

    for e in entries:
        col_str = f"`{e.column}`" if e.column else "*(table)*"
        row_str = f"{e.rows_before} -> {e.rows_after}"
        pairs = [
            f"`{b}` -> `{a}`"
            for b, a in zip(e.before_examples[:3], e.after_examples[:3])
        ]
        ex_str = "; ".join(pairs) if pairs else "-"
        reason_clean = e.reason.replace("|", "\\|")
        ex_clean = ex_str.replace("|", "\\|")
        lines.append(
            f"| `{e.step}` | {col_str} | `{e.action}` | {e.severity} | "
            f"{e.n_cells_affected} | {row_str} | {reason_clean} | {ex_clean} |"
        )

    return "\n".join(lines) + "\n"


def save_cleaning_log_markdown(
    entries: list[CleaningLogEntry],
    path: Path | str,
    dataset_name: str = "dataset",
) -> Path:
    """Write cleaning_log.md to disk."""
    out_path = Path(path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    md = render_cleaning_log_markdown(entries, dataset_name=dataset_name)
    out_path.write_text(md, encoding="utf-8")
    return out_path

