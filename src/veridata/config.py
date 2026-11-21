"""Configuration loading, merging, and validation (Section 5.4, Section 14.4)."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field

from veridata.schemas import SemanticType

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[2] / "configs" / "default.yaml"


class ValidityRule(BaseModel):
    """Domain validity rule per column (Section 5.4, Section 9.6)."""

    min: float | None = None
    max: float | None = None
    allowed_values: list[Any] | None = None


class IngestionConfig(BaseModel):
    max_file_size_mb: float = 200.0
    encodings_to_try: list[str] = Field(
        default_factory=lambda: ["utf-8", "utf-8-sig", "latin-1", "cp1252"]
    )
    delimiters_to_try: list[str] = Field(default_factory=lambda: [",", ";", "\t", "|"])


class TypeInferenceConfig(BaseModel):
    numeric_parse_threshold: float = 0.95
    discrete_max_unique: int = 20
    discrete_max_ratio: float = 0.05
    datetime_parse_threshold: float = 0.90
    month_first_default: bool = False
    id_unique_ratio: float = 0.98
    id_min_nonnull: int = 50
    text_mean_len: float = 40.0
    text_mean_words: float = 6.0
    text_unique_ratio: float = 0.50
    max_categorical_unique: int = 50
    categorical_max_ratio: float = 0.05


class ProfilingConfig(BaseModel):
    missing_tokens: list[str] = Field(
        default_factory=lambda: [
            "",
            " ",
            "NA",
            "N/A",
            "n/a",
            "NaN",
            "nan",
            "NULL",
            "null",
            "None",
            "none",
            "?",
            "-",
            "--",
            "missing",
            "#N/A",
        ]
    )
    candidate_missing_tokens: list[str] = Field(
        default_factory=lambda: ["unknown", "Unknown", "UNKNOWN"]
    )
    treat_unknown_as_missing: bool = False
    label_similarity_threshold: float = 0.90
    high_missing_warning_threshold: float = 0.40
    extreme_skew_warning_threshold: float = 2.0
    minority_imbalance_threshold: float = 0.10
    outlier_iqr_mild: float = 1.5
    outlier_iqr_extreme: float = 3.0
    outlier_modz_threshold: float = 3.5


class StepsEnabledConfig(BaseModel):
    normalize_column_names: bool = True
    clean_whitespace_unicode: bool = True
    normalize_missing_tokens: bool = True
    standardize_categories: bool = True
    convert_types: bool = True
    apply_validity_rules: bool = True
    handle_duplicates: bool = True
    structural_drops: bool = True
    handle_missing_values: bool = True
    handle_outliers: bool = True
    validate_invariants: bool = True


class CleaningConfig(BaseModel):
    snake_case_columns: bool = False
    auto_merge_fuzzy: bool = False
    missing_token_warning_ratio: float = 0.10
    drop_duplicates: Literal["always", "never", "auto"] = "auto"
    duplicate_auto_max_cols: int = 4
    duplicate_auto_max_rate: float = 0.20
    column_drop_threshold: float = 0.80
    row_drop_threshold: float = 0.50
    categorical_missing_as_level_threshold: float = 0.05
    missing_indicator_threshold: float = 0.05
    target_missing: Literal["drop", "keep"] = "drop"
    outlier_action: Literal["flag", "cap", "remove"] = "flag"
    outlier_remove_max_row_fraction: float = 0.05
    steps_enabled: StepsEnabledConfig = Field(default_factory=StepsEnabledConfig)


class EDAConfig(BaseModel):
    dpi: int = 150
    max_numeric_plots: int = 30
    max_categorical_plots: int = 30
    batch_panel_size: int = 6
    top_categories_shown: int = 15
    missing_heatmap_max_rows: int = 500
    scatter_max_points: int = 5000
    top_bivariate_pairs: int = 6
    max_group_levels_box: int = 8
    collinearity_threshold: float = 0.90


class ScalingConfig(BaseModel):
    skew_threshold: float = 1.0
    scale_disparity_ratio_threshold: float = 10.0
    generate_scaled_csv: bool = True


class InsightsConfig(BaseModel):
    zero_inflation_threshold: float = 0.30
    outlier_pct_threshold: float = 0.05
    rare_level_threshold: float = 0.01
    small_n_dataset_threshold: int = 200
    small_n_group_threshold: int = 20


class StatsConfig(BaseModel):
    alpha: float = 0.05
    correction: Literal["bh", "by", "holm", "bonferroni", "none"] = "bh"
    two_sided: bool = True
    min_n_pairwise: int = 20
    min_group_n: int = 8
    min_expected_count_chi2: int = 5
    normality_n_max: int = 5000
    large_n_clt: int = 50
    extreme_skew: float = 2.0
    bootstrap_resamples: int = 2000
    bootstrap_resamples_benchmark: int = 500
    permutation_resamples: int = 9999
    seed: int = 20260101


class EffectFloorConfig(BaseModel):
    cohens_d: float = 0.20
    rank_biserial: float = 0.10
    correlation: float = 0.10
    eta_squared: float = 0.01
    epsilon_squared: float = 0.01
    cramers_v_df1: float = 0.10
    enabled: bool = True


class RankingWeightsConfig(BaseModel):
    feasibility_strength: float = 0.25
    target_involvement: float = 0.30
    llm_relevance: float = 0.25
    interpretability: float = 0.10
    data_quality: float = 0.10


class HypothesesConfig(BaseModel):
    mode: Literal["exhaustive", "target_focused", "llm_prioritized"] = "exhaustive"
    target: str | None = None
    max_tests: int = 3000
    max_levels_categorical: int = 20
    small_discrete_max_unique: int = 10
    treat_small_discrete_as_numeric: bool = False
    lump_rare_levels: bool = False
    rare_level_min_fraction: float = 0.01
    enable_nonlinear: bool = False
    llm_proposals: bool = True
    max_llm_proposals: int = 40
    min_llm_hypotheses: int = 10
    ranking_weights: RankingWeightsConfig = Field(default_factory=RankingWeightsConfig)


class LLMConfig(BaseModel):
    provider: str = "anthropic"
    model: str = "claude-sonnet-4-5"
    temperature: float = 0.0
    max_tokens: int = 2000
    cache_dir: str = ".cache/llm"
    retries: int = 2


class ReportingConfig(BaseModel):
    narration: Literal["llm_slots", "template_only"] = "llm_slots"
    max_findings_in_report: int = 30
    charts_dpi: int = 150


class AgentConfig(BaseModel):
    checkpoint: Literal["memory", "sqlite"] = "sqlite"
    max_followups: int = 3
    max_tool_calls_per_turn: int = 4


class PipelineConfig(BaseModel):
    """Merged configuration for VeriData pipeline runs (default < dataset < CLI)."""

    # Dataset-specific fields (optional overrides from configs/datasets/<name>.yaml)
    name: str = "unnamed_dataset"
    file: str | None = None
    target: str | None = None
    id_columns: list[str] = Field(default_factory=list)
    forced_types: dict[str, SemanticType] = Field(default_factory=dict)
    ordinal_orders: dict[str, list[str]] = Field(default_factory=dict)
    missing_tokens_extra: list[str] = Field(default_factory=list)
    validity_rules: dict[str, ValidityRule] = Field(default_factory=dict)
    truth_types: dict[str, str] = Field(default_factory=dict)
    column_descriptions: dict[str, str] = Field(default_factory=dict)

    # Global module configurations
    ingestion: IngestionConfig = Field(default_factory=IngestionConfig)
    type_inference: TypeInferenceConfig = Field(default_factory=TypeInferenceConfig)
    profiling: ProfilingConfig = Field(default_factory=ProfilingConfig)
    cleaning: CleaningConfig = Field(default_factory=CleaningConfig)
    eda: EDAConfig = Field(default_factory=EDAConfig)
    scaling: ScalingConfig = Field(default_factory=ScalingConfig)
    insights: InsightsConfig = Field(default_factory=InsightsConfig)
    stats: StatsConfig = Field(default_factory=StatsConfig)
    effect_floor: EffectFloorConfig = Field(default_factory=EffectFloorConfig)
    hypotheses: HypothesesConfig = Field(default_factory=HypothesesConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    reporting: ReportingConfig = Field(default_factory=ReportingConfig)
    agent: AgentConfig = Field(default_factory=AgentConfig)

    def effective_missing_tokens(self) -> list[str]:
        """Return combined list of global missing tokens + dataset-specific tokens."""
        tokens = list(self.profiling.missing_tokens)
        if self.profiling.treat_unknown_as_missing:
            for tok in self.profiling.candidate_missing_tokens:
                if tok not in tokens:
                    tokens.append(tok)
        for tok in self.missing_tokens_extra:
            if tok not in tokens:
                tokens.append(tok)
        return tokens


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Recursively merge override dictionary into a copy of base dictionary."""
    result = deepcopy(base)
    for key, val in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(val, dict):
            result[key] = _deep_merge(result[key], val)
        else:
            result[key] = deepcopy(val)
    return result


def load_yaml_file(path: Path) -> dict[str, Any]:
    """Load a YAML file safely; return empty dict if file is empty."""
    if not path.exists():
        raise FileNotFoundError(f"Configuration file not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data if isinstance(data, dict) else {}


def load_config(
    dataset_config_path: Path | str | None = None,
    cli_overrides: dict[str, Any] | None = None,
    default_config_path: Path | str = DEFAULT_CONFIG_PATH,
) -> PipelineConfig:
    """Load and merge configurations following precedence: default.yaml < dataset.yaml < cli_overrides."""
    default_path = Path(default_config_path)
    merged: dict[str, Any] = load_yaml_file(default_path) if default_path.exists() else {}

    if dataset_config_path is not None:
        ds_path = Path(dataset_config_path)
        ds_data = load_yaml_file(ds_path)
        merged = _deep_merge(merged, ds_data)

    if cli_overrides:
        merged = _deep_merge(merged, cli_overrides)

    return PipelineConfig.model_validate(merged)


def dump_resolved_config(config: PipelineConfig, out_path: Path) -> None:
    """Save the fully resolved configuration to YAML for reproducibility (Section 14.4)."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    data = config.model_dump(mode="json")
    with out_path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True)

