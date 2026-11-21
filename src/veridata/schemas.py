"""Core Pydantic v2 Data Contracts for Phase 1 and Phase 2 Handoff (Section 6)."""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Any, Literal

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field


class SemanticType(str, Enum):
    """Semantic column types inferred by type_inference.py (Section 6.1)."""

    NUMERIC_CONTINUOUS = "numeric_continuous"
    NUMERIC_DISCRETE = "numeric_discrete"
    BINARY = "binary"
    CATEGORICAL_NOMINAL = "categorical_nominal"
    CATEGORICAL_ORDINAL = "categorical_ordinal"
    DATETIME = "datetime"
    ID_LIKE = "id_like"
    FREE_TEXT = "free_text"
    CONSTANT = "constant"
    UNKNOWN = "unknown"


class ColumnRole(str, Enum):
    """Column role in the Phase 2 handoff schema (Section 6.6)."""

    FEATURE = "feature"
    TARGET_CANDIDATE = "target_candidate"
    ID = "id"
    EXCLUDED = "excluded"


class TopValueEntry(BaseModel):
    """Top frequent value entry for categorical/binary/discrete columns."""

    value: str
    count: int
    pct: float


class NearDuplicatePair(BaseModel):
    """Candidate near-duplicate categorical label pair (Section 8)."""

    label_a: str
    label_b: str
    count_a: int
    count_b: int
    similarity: float


class ColumnProfile(BaseModel):
    """Detailed per-column profile (Section 6.2)."""

    name: str
    raw_dtype: str
    semantic_type: SemanticType
    semantic_type_reason: str
    n_total: int
    n_missing: int
    pct_missing: float
    n_unique: int
    pct_unique: float
    mode: Any | None = None
    top_values: list[TopValueEntry] = Field(default_factory=list)

    # Numeric-only fields
    min: float | None = None
    max: float | None = None
    mean: float | None = None
    median: float | None = None
    std: float | None = None
    q1: float | None = None
    q3: float | None = None
    iqr: float | None = None
    skewness: float | None = None
    kurtosis: float | None = None
    n_zeros: int | None = None
    n_negative: int | None = None

    # Outlier summary (detection only, numeric only)
    n_outliers_iqr_1_5: int | None = None
    n_outliers_iqr_3_0: int | None = None
    n_outliers_modz: int | None = None

    # String-quality flags
    has_leading_trailing_ws: bool = False
    n_leading_trailing_ws: int = 0
    has_internal_multi_ws: bool = False
    n_internal_multi_ws: int = 0
    has_unicode_oddities: bool = False
    n_unicode_oddities: int = 0
    has_mixed_case_variants: bool = False
    case_variant_groups: dict[str, list[str]] = Field(default_factory=dict)
    near_duplicate_labels: list[NearDuplicatePair] = Field(default_factory=list)
    n_missing_token_cells: int = 0
    missing_tokens_found: dict[str, int] = Field(default_factory=dict)
    looks_numeric_but_object: bool = False
    mixed_types: bool = False

    # Datetime-only fields
    min_date: str | None = None
    max_date: str | None = None
    n_unparseable: int | None = None

    # Missing mechanism note for conservative output (Section 9.9)
    missing_mechanism_note: str = "MCAR/MAR/MNAR unknown; not tested"


class MissingMatrixSummary(BaseModel):
    """Dataset-level missingness summary (Section 6.3)."""

    total_cells: int
    total_missing_cells: int
    pct_missing_cells: float
    rows_with_any_missing: int
    pct_rows_with_any_missing: float
    rows_with_gt_half_missing: int
    pct_rows_with_gt_half_missing: float


class DataProfile(BaseModel):
    """Full dataset profile serialized to profile.json (Section 6.3)."""

    schema_version: str = "1.0"
    dataset_name: str
    source_file: str
    sha256: str
    n_rows: int
    n_cols: int
    memory_mb: float
    n_duplicate_rows_raw: int = 0
    n_duplicate_rows: int = 0
    pct_duplicate_rows: float = 0.0
    n_fully_empty_rows: int = 0
    n_fully_empty_cols: int = 0
    columns: list[ColumnProfile]
    missing_matrix_summary: MissingMatrixSummary
    correlation_candidates_note: str = "none; Phase 2"
    warnings: list[str] = Field(default_factory=list)
    generated_at: str = ""
    library_versions: dict[str, str] = Field(default_factory=dict)


class ColumnSchemaEntry(BaseModel):
    """Per-column entry in column_schema.json for Phase 2 handoff (Section 6.6)."""

    semantic_type: SemanticType
    role: ColumnRole
    n_unique: int
    pct_missing: float
    exclude_reason: str | None = None
    binary_labels: list[str] | None = None


class IngestionMetadata(BaseModel):
    """Metadata produced by load_csv in ingestion.py (Section 7.1)."""

    source_file: str
    sha256: str
    file_size_mb: float
    encoding: str
    encoding_fallback_used: bool
    delimiter: str
    n_bad_lines: int
    n_rows: int
    n_cols: int
    column_name_changes: dict[str, str] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)


class IngestionResult(BaseModel):
    """Full return value of load_csv (Section 7.1)."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    df_raw_str: pd.DataFrame
    df_naive: pd.DataFrame
    metadata: IngestionMetadata


class CleaningLogEntry(BaseModel):
    """Structured record for every cleaning operation (Section 6.4)."""

    step: str
    column: str | None = None
    action: str
    n_cells_affected: int = 0
    n_rows_affected: int = 0
    rows_before: int
    rows_after: int
    reason: str
    before_examples: list[str] = Field(default_factory=list)
    after_examples: list[str] = Field(default_factory=list)
    parameters: dict[str, Any] = Field(default_factory=dict)
    severity: Literal["info", "warning"] = "info"


class DroppedColumnRecord(BaseModel):
    """Record of a dropped or excluded column."""

    name: str
    reason: str
    output_target: Literal["both", "imputed_only", "marked_excluded"] = "both"


class OutlierColumnReport(BaseModel):
    """Per-column outlier detection report (Section 9.10)."""

    column: str
    method: str = "iqr_and_modz"
    n_flagged: int
    n_extreme: int
    pct_flagged: float
    iqr_1_5_lower: float | None = None
    iqr_1_5_upper: float | None = None
    iqr_3_0_lower: float | None = None
    iqr_3_0_upper: float | None = None
    min_flagged_value: float | None = None
    max_flagged_value: float | None = None
    indices_flagged_sample: list[int] = Field(default_factory=list)
    action_taken: Literal["flag", "cap", "remove"] = "flag"


class CleaningResult(BaseModel):
    """Return value of clean_dataset (Section 6.5)."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    df_clean_conservative: pd.DataFrame
    df_clean_imputed: pd.DataFrame
    log: list[CleaningLogEntry] = Field(default_factory=list)
    dropped_columns: list[DroppedColumnRecord] = Field(default_factory=list)
    dropped_row_count_conservative: int = 0
    dropped_row_count_imputed: int = 0
    outlier_report: dict[str, OutlierColumnReport] = Field(default_factory=dict)
    name_map: dict[str, str] = Field(default_factory=dict)
    summary: dict[str, Any] = Field(default_factory=dict)


class ColumnScalingRecommendation(BaseModel):
    """Per-column scaling recommendation (Section 11b)."""

    column: str
    skewness: float
    kurtosis: float
    min_val: float
    max_val: float
    std_val: float
    min_non_negative: bool
    recommended_transform: Literal["log1p", "yeo-johnson", "none"]
    reason: str


class ScalingReport(BaseModel):
    """Output of analyze_scaling in scaling.py (Section 11b)."""

    dataset_name: str
    columns: list[ColumnScalingRecommendation] = Field(default_factory=list)
    max_std: float | None = None
    min_std: float | None = None
    scale_disparity_ratio: float | None = None
    recommend_zscore_for_scale_sensitive: bool = False
    decision_paragraph: str = ""
    scaling_params: dict[str, dict[str, float]] = Field(default_factory=dict)
    scaled_csv_path: str | None = None


class FigureArtifact(BaseModel):
    """Metadata for a generated EDA figure (Section 10.9)."""

    filename: str
    path: str
    title: str
    caption: str
    section: str


class EDAResult(BaseModel):
    """Return value of run_eda in eda/ (Section 10.9)."""

    figures: list[FigureArtifact] = Field(default_factory=list)
    tables_markdown: dict[str, str] = Field(default_factory=dict)
    headline_numbers: dict[str, Any] = Field(default_factory=dict)


class InsightRecord(BaseModel):
    """Single rule-based insight record (Section 11)."""

    id: str
    category: Literal[
        "data_quality",
        "distributions",
        "class_balance",
        "relationships",
        "cardinality_structure",
        "scaling",
        "modeling_testing_implications",
    ]
    severity: Literal["high", "medium", "low", "info"] = "info"
    statement: str
    evidence: dict[str, Any] = Field(default_factory=dict)
    figure_ref: str | None = None


class InsightsReport(BaseModel):
    """Container for automated and manual insights (Section 11)."""

    dataset_name: str
    insights: list[InsightRecord] = Field(default_factory=list)
    markdown_path: str | None = None
    json_path: str | None = None


class ManifestEntry(BaseModel):
    """Ground-truth record for an injected defect in the messy synthetic dataset (Section 12.2)."""

    problem_id: str
    problem_type: str
    columns: list[str]
    n_cells: int
    n_rows: int
    row_indices_sample: list[int] = Field(default_factory=list)
    description: str
    expected_pipeline_behavior: Literal["auto_fixed", "flagged_only", "left_alone"]
    details: dict[str, Any] = Field(default_factory=dict)


class MessyManifest(BaseModel):
    """Full manifest for a synthetic messy dataset (Section 12.2)."""

    dataset_name: str
    seed: int
    n_rows_clean: int
    n_cols_clean: int
    n_rows_messy: int
    n_cols_messy: int
    entries: list[ManifestEntry] = Field(default_factory=list)


class Phase1Result(BaseModel):
    """Return object from run_phase1 in pipeline.py (Section 14.1)."""

    dataset_name: str
    out_dir: Path
    cleaned_conservative_csv: Path
    cleaned_imputed_csv: Path
    scaled_csv: Path | None = None
    profile_json: Path
    column_schema_json: Path
    cleaning_log_json: Path
    insights_json: Path | None = None
    report_md: Path | None = None

