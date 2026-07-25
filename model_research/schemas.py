from __future__ import annotations


PREDICTION_COLUMNS = (
    "outer_split_id",
    "datetime",
    "instrument",
    "method",
    "prediction",
    "prediction_artifact_id",
    "allowlist_sha256",
    "feature_order_sha256",
    "model_freeze_id",
    "experiment_class",
)

FORBIDDEN_PREDICTION_TOKENS = (
    "label",
    "future_return",
    "ic",
    "rank_ic",
    "nav",
    "sharpe",
    "test_selection_rank",
)

PRE_TEST_FREEZE_REQUIRED_FIELDS = (
    "outer_split_id",
    "method",
    "experiment_class",
    "allowlist_sha256",
    "feature_order_sha256",
    "training_target_transform_sha256",
    "preprocessing_config_sha256",
    "fitted_preprocessing_artifact_id",
    "selected_hyperparameters",
    "model_config_sha256",
    "model_binary_sha256",
    "training_data_sha256",
    "train_validation_date_sha256",
    "validation_search_sha256",
    "metric_registry_sha256",
    "random_seed",
    "code_commit_sha",
    "freeze_timestamp",
    "python_version",
    "numpy_version",
    "pandas_version",
    "scipy_version",
    "scikit_learn_version",
    "lightgbm_version",
    "qlib_commit_sha",
    "environment_lock_sha256",
    "num_threads",
    "omp_num_threads",
    "mkl_num_threads",
    "openblas_num_threads",
    "numexpr_num_threads",
    "blas_backend",
    "historical_test_already_observed",
    "authoritative_execution",
    "unbiased_final_estimate",
)


def prediction_schema_violations(columns: tuple[str, ...] | list[str]) -> list[str]:
    normalized = tuple(str(column).strip().lower() for column in columns)
    violations = [
        f"prediction_schema_mismatch:{normalized}!={PREDICTION_COLUMNS}"
    ] if normalized != PREDICTION_COLUMNS else []
    for column in normalized:
        for token in FORBIDDEN_PREDICTION_TOKENS:
            if column == token or column.startswith(f"{token}_"):
                violations.append(f"forbidden_prediction_column:{column}")
    return violations


def freeze_schema_missing(payload: dict[str, object]) -> list[str]:
    return sorted(set(PRE_TEST_FREEZE_REQUIRED_FIELDS) - set(payload))
