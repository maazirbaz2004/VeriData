"""Automated conservative and imputed data cleaning package (Section 9)."""

from __future__ import annotations

import pandas as pd

from ads.cleaning.categories import step4_standardize_categories
from ads.cleaning.log import (
    CleaningLog,
    render_cleaning_log_markdown,
    save_cleaning_log_json,
    save_cleaning_log_markdown,
)
from ads.cleaning.missing import (
    step3_normalize_missing_tokens,
    step9_handle_missing_values,
)
from ads.cleaning.outliers import (
    detect_outliers_pre_imputation,
    step10_apply_outlier_action,
)
from ads.cleaning.steps import (
    CleaningInvariantError,
    step1_normalize_column_names,
    step2_clean_whitespace_and_unicode,
    step5_convert_types,
    step6_apply_validity_rules,
    step7_handle_duplicates,
    step8_structural_drops,
    step11_validate_invariants,
)
from ads.config import PipelineConfig, load_config
from ads.schemas import (
    CleaningResult,
    DataProfile,
    DroppedColumnRecord,
    OutlierColumnReport,
    SemanticType,
)


def clean_dataset(
    df_raw_str: pd.DataFrame,
    profile: DataProfile,
    config: PipelineConfig | None = None,
    ingestion_name_changes: dict[str, str] | None = None,
) -> CleaningResult:
    """Run all 11 deterministic cleaning steps in fixed order without mutating input (Section 9)."""
    cfg = config or load_config()
    steps_cfg = cfg.cleaning.steps_enabled
    log = CleaningLog()
    dropped_columns: list[DroppedColumnRecord] = []

    # Work on a copy; convert any existing Categorical columns back to object for processing
    df = df_raw_str.copy(deep=True)
    for col in df.columns:
        if isinstance(df[col].dtype, pd.CategoricalDtype):
            df[col] = df[col].astype("object")

    n_rows_initial = len(df)
    semantic_types: dict[str, SemanticType] = {
        c.name: c.semantic_type for c in profile.columns
    }
    name_map: dict[str, str] = {}

    # Step 1: Column-name normalization
    if steps_cfg.normalize_column_names:
        df, name_map = step1_normalize_column_names(
            df, log, cfg, ingestion_name_changes=ingestion_name_changes
        )
        if name_map:
            semantic_types = {
                name_map.get(col_k, col_k): sem_v
                for col_k, sem_v in semantic_types.items()
            }

    # Step 2: Whitespace and unicode cleanup
    if steps_cfg.clean_whitespace_unicode:
        df = step2_clean_whitespace_and_unicode(df, log)

    # Step 3: Missing-token normalization
    if steps_cfg.normalize_missing_tokens:
        df = step3_normalize_missing_tokens(df, log, cfg)

    # Step 4: Category label standardization
    if steps_cfg.standardize_categories:
        df = step4_standardize_categories(df, semantic_types, log, cfg)

    # Step 5: Type conversion
    if steps_cfg.convert_types:
        df = step5_convert_types(df, semantic_types, log, cfg)

    # Step 6: Validity rules + generic sanity checks
    if steps_cfg.apply_validity_rules:
        df = step6_apply_validity_rules(df, semantic_types, log, cfg)

    # Step 7: Duplicates
    if steps_cfg.handle_duplicates:
        df = step7_handle_duplicates(df, semantic_types, log, cfg)

    # Step 8: Structural drops
    high_missing_cols: list[str] = []
    if steps_cfg.structural_drops:
        df, high_missing_cols = step8_structural_drops(
            df, semantic_types, dropped_columns, log, cfg
        )

    # Step 10 (Part A - Detection): Detect outliers BEFORE imputation so imputed values do not skew fences (Section 9.10)
    outlier_reports: dict[str, OutlierColumnReport] = {}
    outlier_masks: dict[str, pd.Series] = {}
    if steps_cfg.handle_outliers:
        outlier_reports, outlier_masks = detect_outliers_pre_imputation(
            df, semantic_types, cfg
        )

    # Step 9: Missing value handling -> produces Output A (conservative) and Output B (imputed)
    if steps_cfg.handle_missing_values:
        df_cons, df_imp = step9_handle_missing_values(
            df, semantic_types, high_missing_cols, dropped_columns, log, cfg
        )
    else:
        df_cons, df_imp = df.copy(), df.copy()

    # Step 10 (Part B - Action): Log flagged outliers and apply cap/remove to imputed output if configured
    if steps_cfg.handle_outliers:
        df_cons, df_imp = step10_apply_outlier_action(
            df_cons, df_imp, outlier_reports, outlier_masks, log, cfg
        )

    # Step 11: Final validation of cleaned output
    if steps_cfg.validate_invariants:
        df_cons, df_imp = step11_validate_invariants(
            df_cons, df_imp, n_rows_initial, semantic_types, log, cfg
        )

    return CleaningResult(
        df_clean_conservative=df_cons,
        df_clean_imputed=df_imp,
        log=log.entries,
        dropped_columns=dropped_columns,
        dropped_row_count_conservative=n_rows_initial - len(df_cons),
        dropped_row_count_imputed=n_rows_initial - len(df_imp),
        outlier_report=outlier_reports,
        name_map=name_map,
        summary=log.summary_dict(),
    )


__all__ = [
    "CleaningInvariantError",
    "CleaningLog",
    "clean_dataset",
    "detect_outliers_pre_imputation",
    "render_cleaning_log_markdown",
    "save_cleaning_log_json",
    "save_cleaning_log_markdown",
    "step1_normalize_column_names",
    "step2_clean_whitespace_and_unicode",
    "step3_normalize_missing_tokens",
    "step4_standardize_categories",
    "step5_convert_types",
    "step6_apply_validity_rules",
    "step7_handle_duplicates",
    "step8_structural_drops",
    "step9_handle_missing_values",
    "step10_apply_outlier_action",
    "step11_validate_invariants",
]
