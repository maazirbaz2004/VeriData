"""Outcome-independent hypothesis space enumeration and type mapping (Phase 2 Section 3)."""

from __future__ import annotations

from itertools import combinations
from typing import Literal

from veridata.config import PipelineConfig
from veridata.contracts.hypothesis import (
    Direction,
    FeasibilityReport,
    Hypothesis,
    RelationshipType,
)
from veridata.errors import HypothesisError
from veridata.hypotheses.dedupe import deduplicate_hypotheses, make_hypothesis_id
from veridata.schemas import ColumnRole, ColumnSchemaEntry, SemanticType

_DERIVED_SUFFIXES: tuple[str, ...] = ("__was_missing", "__log1p", "__yeojohnson", "__z")

_UNSUPPORTED_SEMANTIC_TYPES: set[SemanticType] = {
    SemanticType.CONSTANT,
    SemanticType.ID_LIKE,
    SemanticType.FREE_TEXT,
    SemanticType.UNKNOWN,
    SemanticType.DATETIME,
}


def strip_derived_suffix(col_name: str) -> str:
    """Strip Phase 1 derived column suffixes to identify provenance base names."""
    for suffix in _DERIVED_SUFFIXES:
        if col_name.endswith(suffix):
            return col_name[: -len(suffix)]
    return col_name


def is_derived_column(col_name: str) -> bool:
    """Return True if a column name carries a Phase 1 derived transform suffix."""
    return any(col_name.endswith(suffix) for suffix in _DERIVED_SUFFIXES)


def is_trivially_related_by_name(col_a: str, col_b: str) -> bool:
    """Return True when two columns share the same base name via derived suffixes."""
    if col_a == col_b:
        return True
    base_a = strip_derived_suffix(col_a)
    base_b = strip_derived_suffix(col_b)
    return base_a == base_b


def filter_eligible_columns(
    schema: dict[str, ColumnSchemaEntry],
    config: PipelineConfig,
) -> tuple[list[str], list[dict[str, str]], list[str]]:
    """Select eligible columns from column_schema.json (Section 3.1).

    Uses ONLY schema metadata (role, semantic_type, n_unique) — never bivariate data.
    Returns ``(eligible_cols, excluded_columns, notes)``.
    """
    eligible: list[str] = []
    excluded: list[dict[str, str]] = []
    notes: list[str] = []
    has_datetime = False

    max_levels = config.hypotheses.max_levels_categorical

    for col in sorted(schema.keys()):
        entry = schema[col]
        if is_derived_column(col):
            excluded.append({"name": col, "reason": "derived_column"})
            continue
        if entry.role == ColumnRole.ID:
            excluded.append({"name": col, "reason": "id"})
            continue
        if entry.role == ColumnRole.EXCLUDED:
            excluded.append({"name": col, "reason": entry.exclude_reason or "excluded"})
            continue
        if entry.semantic_type == SemanticType.DATETIME:
            has_datetime = True
            excluded.append({"name": col, "reason": "datetime_not_testable"})
            continue
        if entry.semantic_type in _UNSUPPORTED_SEMANTIC_TYPES:
            excluded.append({"name": col, "reason": entry.semantic_type.value})
            continue
        if (
            entry.semantic_type
            in {SemanticType.CATEGORICAL_NOMINAL, SemanticType.CATEGORICAL_ORDINAL}
            and entry.n_unique > max_levels
        ):
            excluded.append(
                {
                    "name": col,
                    "reason": f"high_cardinality (n_unique={entry.n_unique} > {max_levels})",
                }
            )
            continue
        eligible.append(col)

    if has_datetime:
        notes.append("datetime columns not testable in this version")

    return eligible, excluded, notes


def effective_column_kind(
    entry: ColumnSchemaEntry,
    config: PipelineConfig,
) -> Literal["numeric", "binary", "categorical", "unsupported"]:
    """Map a column's Phase 1 SemanticType to its Phase 2 pairing category (Section 3.2)."""
    st = entry.semantic_type
    if st == SemanticType.NUMERIC_CONTINUOUS:
        return "numeric"
    if st == SemanticType.NUMERIC_DISCRETE:
        if entry.n_unique <= config.hypotheses.small_discrete_max_unique:
            if config.hypotheses.treat_small_discrete_as_numeric:
                return "numeric"
            return "binary" if entry.n_unique == 2 else "categorical"
        return "numeric"
    if st == SemanticType.BINARY:
        return "binary"
    if st in {SemanticType.CATEGORICAL_NOMINAL, SemanticType.CATEGORICAL_ORDINAL}:
        return "binary" if entry.n_unique == 2 else "categorical"
    return "unsupported"


def map_pair_to_relationship(
    col_a: str,
    entry_a: ColumnSchemaEntry,
    col_b: str,
    entry_b: ColumnSchemaEntry,
    config: PipelineConfig,
) -> tuple[str, str, RelationshipType] | None:
    """Deterministically orient a column pair and assign its RelationshipType (Section 3.2).

    Orientation convention:
    - For ``NUM_BINARY`` and ``NUM_CATEGORICAL``: ``column_a`` is ALWAYS the numeric
      outcome column and ``column_b`` is ALWAYS the grouping column.
    - For symmetric types (``NUM_NUM``, ``CAT_CAT``): columns are ordered alphabetically.
    """
    if col_a == col_b or is_trivially_related_by_name(col_a, col_b):
        return None

    kind_a = effective_column_kind(entry_a, config)
    kind_b = effective_column_kind(entry_b, config)

    if kind_a == "unsupported" or kind_b == "unsupported":
        return None

    if kind_a == "numeric" and kind_b == "numeric":
        c1, c2 = sorted([col_a, col_b])
        return c1, c2, RelationshipType.NUM_NUM

    if kind_a == "numeric" and kind_b == "binary":
        return col_a, col_b, RelationshipType.NUM_BINARY
    if kind_b == "numeric" and kind_a == "binary":
        return col_b, col_a, RelationshipType.NUM_BINARY

    if kind_a == "numeric" and kind_b == "categorical":
        return col_a, col_b, RelationshipType.NUM_CATEGORICAL
    if kind_b == "numeric" and kind_a == "categorical":
        return col_b, col_a, RelationshipType.NUM_CATEGORICAL

    if kind_a in {"binary", "categorical"} and kind_b in {"binary", "categorical"}:
        c1, c2 = sorted([col_a, col_b])
        return c1, c2, RelationshipType.CAT_CAT

    return None


def enumerate_hypotheses(
    schema: dict[str, ColumnSchemaEntry],
    config: PipelineConfig,
    target: str | None = None,
    mode: Literal["exhaustive", "target_focused", "llm_prioritized"] | None = None,
) -> tuple[list[Hypothesis], list[dict[str, str]], list[str], int]:
    """Enumerate all valid candidate hypotheses from the column schema (Section 3).

    Returns ``(hypotheses, excluded_columns, notes, n_columns_eligible)``.
    Feasibility is initialized as a placeholder and populated by ``feasibility.py``.
    """
    active_mode = mode or config.hypotheses.mode
    eligible_cols, excluded_cols, notes = filter_eligible_columns(schema, config)

    if active_mode == "target_focused":
        if not target:
            raise HypothesisError(
                "Mode 'target_focused' requires a target column (set via --target or config)."
            )
        if target not in eligible_cols:
            raise HypothesisError(
                f"Configured target column '{target}' is not eligible for hypothesis testing."
            )
        notes.append(f"non-target pairs were not tested by design (target='{target}')")

    placeholder_feasibility = FeasibilityReport(
        feasible=True,
        reasons=[],
        n_pairwise_complete=0,
    )

    candidates: list[Hypothesis] = []
    for col_a, col_b in combinations(eligible_cols, 2):
        if active_mode == "target_focused" and target not in (col_a, col_b):
            continue

        mapped = map_pair_to_relationship(col_a, schema[col_a], col_b, schema[col_b], config)
        if mapped is None:
            continue

        oriented_a, oriented_b, rel = mapped
        hid = make_hypothesis_id(rel, oriented_a, oriented_b)
        candidates.append(
            Hypothesis(
                id=hid,
                column_a=oriented_a,
                column_b=oriented_b,
                relationship=rel,
                expected_direction=Direction.ANY,
                source="enumerated",
                rationale="",
                feasibility=placeholder_feasibility,
                created_stage="batch",
                status="proposed",
            )
        )

        if rel == RelationshipType.NUM_NUM and config.hypotheses.enable_nonlinear:
            nl_rel = RelationshipType.NUM_NUM_NONLINEAR
            nl_hid = make_hypothesis_id(nl_rel, oriented_a, oriented_b)
            candidates.append(
                Hypothesis(
                    id=nl_hid,
                    column_a=oriented_a,
                    column_b=oriented_b,
                    relationship=nl_rel,
                    expected_direction=Direction.ANY,
                    source="enumerated",
                    rationale="",
                    feasibility=placeholder_feasibility,
                    created_stage="batch",
                    status="proposed",
                )
            )

    deduped = deduplicate_hypotheses(candidates)
    return deduped, excluded_cols, notes, len(eligible_cols)

