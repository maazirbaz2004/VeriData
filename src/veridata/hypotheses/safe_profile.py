"""Safe univariate-only profile builder, prompt sanitization, and column aliasing (Section 5)."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from pydantic import BaseModel, Field

from veridata.config import PipelineConfig
from veridata.schemas import ColumnProfile, ColumnSchemaEntry, DataProfile, SemanticType

# Keys that must NEVER appear anywhere in a serialized SafeProfile (Principle P2)
FORBIDDEN_SAFE_PROFILE_KEYS: frozenset[str] = frozenset(
    {
        "correlation",
        "correlations",
        "pearson_r",
        "spearman_rho",
        "cramers_v",
        "eta_squared",
        "p_value",
        "q_value",
        "effect_size",
        "relationships",
        "bivariate",
        "group_means",
        "mean_diff",
        "contingency_table",
    }
)

_CONTROL_CHAR_RE = re.compile(r"[\x00-\x1f\x7f]+")
_FENCE_RE = re.compile(r"```+")
_XML_TAG_RE = re.compile(r"</?dataset_profile>", re.IGNORECASE)
_INJECTION_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions?", re.IGNORECASE),
    re.compile(r"disregard\s+(all\s+)?(previous|prior|above)", re.IGNORECASE),
    re.compile(r"system\s*prompt", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+", re.IGNORECASE),
)


def sanitize_text(text: str, *, max_len: int = 60) -> str:
    """Sanitize untrusted dataset-derived strings (column names, level labels) per P7.

    - Strips control characters
    - Neutralizes markdown fences, delimiter tags, and prompt-injection phrases
    - Collapses whitespace and truncates to ``max_len``
    """
    cleaned = _CONTROL_CHAR_RE.sub(" ", str(text))
    cleaned = _FENCE_RE.sub("", cleaned)
    cleaned = _XML_TAG_RE.sub("", cleaned)
    for pat in _INJECTION_PATTERNS:
        cleaned = pat.sub("[redacted]", cleaned)
    cleaned = " ".join(cleaned.split())
    if len(cleaned) > max_len:
        cleaned = cleaned[:max_len].rstrip()
    return cleaned


def _skew_bucket(col_profile: ColumnProfile | None) -> str | None:
    if col_profile is None:
        return None
    if col_profile.semantic_type not in {
        SemanticType.NUMERIC_CONTINUOUS,
        SemanticType.NUMERIC_DISCRETE,
    }:
        return None
    skew = col_profile.skewness
    kurt = col_profile.kurtosis
    if skew is None:
        return "symmetric"
    if kurt is not None and kurt > 5.0 and abs(skew) <= 1.0:
        return "heavy_tailed"
    if skew > 1.0:
        return "right_skewed"
    if skew < -1.0:
        return "left_skewed"
    return "symmetric"


class SafeTopLevel(BaseModel):
    label: str
    pct: float


class SafeColumnSummary(BaseModel):
    alias: str
    name: str
    semantic_type: str
    role: str
    n_unique: int
    pct_missing: float
    top_levels: list[SafeTopLevel] = Field(default_factory=list)
    skew_bucket: str | None = None
    user_description: str | None = None


class SafeProfile(BaseModel):
    """Univariate-only, sanitized dataset profile safe to pass to an LLM (Section 5.1)."""

    dataset_description: str = "unknown"
    n_rows: int
    target_alias: str | None = None
    columns: list[SafeColumnSummary] = Field(default_factory=list)


def build_safe_profile(
    schema: dict[str, ColumnSchemaEntry],
    profile: DataProfile | None,
    config: PipelineConfig,
    *,
    eligible_columns: list[str] | None = None,
    target: str | None = None,
    dataset_description: str = "unknown",
    column_descriptions: dict[str, str] | None = None,
) -> tuple[SafeProfile, dict[str, str], dict[str, str], str]:
    """Build a sanitized, aliased SafeProfile containing ONLY allowed univariate fields.

    Returns ``(safe_profile, alias_to_col, col_to_alias, selection_inputs_hash)``.
    """
    cols = sorted(eligible_columns) if eligible_columns is not None else sorted(schema.keys())
    prof_by_name: dict[str, ColumnProfile] = (
        {c.name: c for c in profile.columns} if profile is not None else {}
    )
    descs = dict(config.column_descriptions)
    if column_descriptions:
        descs.update(column_descriptions)

    alias_to_col: dict[str, str] = {}
    col_to_alias: dict[str, str] = {}
    summaries: list[SafeColumnSummary] = []

    for idx, col in enumerate(cols, start=1):
        alias = f"c{idx:02d}"
        alias_to_col[alias] = col
        col_to_alias[col] = alias

        entry = schema[col]
        cp = prof_by_name.get(col)

        top_levels: list[SafeTopLevel] = []
        if entry.semantic_type in {
            SemanticType.BINARY,
            SemanticType.CATEGORICAL_NOMINAL,
            SemanticType.CATEGORICAL_ORDINAL,
        }:
            if cp is not None and cp.top_values:
                for tv in cp.top_values[:8]:
                    top_levels.append(
                        SafeTopLevel(
                            label=sanitize_text(tv.value, max_len=60),
                            pct=round(float(tv.pct), 4),
                        )
                    )
            elif entry.binary_labels:
                for lbl in entry.binary_labels[:2]:
                    top_levels.append(
                        SafeTopLevel(label=sanitize_text(lbl, max_len=60), pct=0.5)
                    )

        user_desc = descs.get(col)
        summaries.append(
            SafeColumnSummary(
                alias=alias,
                name=sanitize_text(col, max_len=60),
                semantic_type=entry.semantic_type.value,
                role=entry.role.value,
                n_unique=entry.n_unique,
                pct_missing=round(float(entry.pct_missing), 4),
                top_levels=top_levels,
                skew_bucket=_skew_bucket(cp),
                user_description=sanitize_text(user_desc, max_len=120) if user_desc else None,
            )
        )

    n_rows = profile.n_rows if profile is not None else 0
    safe_prof = SafeProfile(
        dataset_description=sanitize_text(dataset_description, max_len=200),
        n_rows=n_rows,
        target_alias=col_to_alias.get(target) if target else None,
        columns=summaries,
    )

    canonical_json = json.dumps(safe_prof.model_dump(mode="json"), sort_keys=True)
    inputs_hash = hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()[:16]
    return safe_prof, alias_to_col, col_to_alias, inputs_hash


def format_safe_profile_block(safe_profile: SafeProfile) -> str:
    """Wrap the serialized SafeProfile inside explicit data delimiters (P7)."""
    payload = json.dumps(safe_profile.model_dump(mode="json"), indent=2, sort_keys=True)
    return f"<dataset_profile>\n{payload}\n</dataset_profile>"


def contains_forbidden_keys(data: Any) -> list[str]:
    """Recursively inspect a JSON-like structure for forbidden bivariate/outcome keys."""
    found: list[str] = []
    if isinstance(data, dict):
        for k, v in data.items():
            if str(k).lower() in FORBIDDEN_SAFE_PROFILE_KEYS:
                found.append(str(k))
            found.extend(contains_forbidden_keys(v))
    elif isinstance(data, list):
        for item in data:
            found.extend(contains_forbidden_keys(item))
    return found

