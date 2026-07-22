from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from research_validation.feature_matrix import canonical_hash, file_sha256


NOT_APPLICABLE_MODEL_BINARY = "not_applicable_transparent_baseline"
NOT_APPLICABLE_PREPROCESSOR = "not_applicable_stateless_daily_cross_section"
NOT_APPLICABLE_VALIDATION_SEARCH = "not_applicable_no_hyperparameter_search"


def build_pretest_freeze_payload(
    *,
    outer_split_id: str,
    allowlist_sha256: str,
    feature_order_sha256: str,
    weights_by_method: Mapping[str, str],
    preprocessing_config_sha256: str,
    model_config_sha256: str,
    training_data_sha256: str,
    qlib_exchange_config_sha256: str,
    test_dates_sha256: str,
    code_commit_sha: str,
    freeze_timestamp: str,
) -> dict[str, Any]:
    core: dict[str, Any] = {
        "schema_version": 1,
        "outer_split_id": outer_split_id,
        "allowlist_sha256": allowlist_sha256,
        "feature_order_sha256": feature_order_sha256,
        "factor_weights_sha256_by_method": dict(sorted(weights_by_method.items())),
        "preprocessing_config_sha256": preprocessing_config_sha256,
        "fitted_preprocessing_artifact_id": NOT_APPLICABLE_PREPROCESSOR,
        "selected_hyperparameters": {
            "equal_weight": "fixed_equal_weight",
            "stability_weight": "fixed_development_stability_weight",
        },
        "validation_selection_metric": "not_applicable_transparent_baseline",
        "model_config_sha256": model_config_sha256,
        "model_binary_sha256": NOT_APPLICABLE_MODEL_BINARY,
        "final_fit_scope": "not_applicable_stateless_transparent_baseline",
        "training_data_sha256": training_data_sha256,
        "validation_search_sha256": NOT_APPLICABLE_VALIDATION_SEARCH,
        "qlib_exchange_config_sha256": qlib_exchange_config_sha256,
        "test_dates_sha256": test_dates_sha256,
        "code_commit_sha": code_commit_sha,
        "freeze_timestamp": freeze_timestamp,
    }
    return {**core, "freeze_id": f"pre_test_freeze_v1:{canonical_hash(core)}"}


def static_freeze_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in payload.items() if key not in {"freeze_id", "freeze_timestamp"}}


def preserve_or_reject_existing_freeze(path: Path, proposed: dict[str, Any]) -> dict[str, Any]:
    if not path.is_file():
        return proposed
    existing = json.loads(path.read_text(encoding="utf-8"))
    if static_freeze_payload(existing) != static_freeze_payload(proposed):
        raise ValueError(f"immutable pre-test freeze differs from proposed payload: {path}")
    return existing


def validate_pretest_freeze(
    payload: Mapping[str, Any],
    *,
    expected_outer_split_id: str,
    expected_code_commit_sha: str,
    expected_allowlist_sha256: str,
    expected_feature_order_sha256: str,
    expected_weights_by_method: Mapping[str, str],
    expected_preprocessing_config_sha256: str,
    expected_model_config_sha256: str,
    expected_qlib_exchange_config_sha256: str,
    expected_test_dates_sha256: str,
) -> list[str]:
    issues: list[str] = []
    checks = {
        "outer_split_id": expected_outer_split_id,
        "code_commit_sha": expected_code_commit_sha,
        "allowlist_sha256": expected_allowlist_sha256,
        "feature_order_sha256": expected_feature_order_sha256,
        "factor_weights_sha256_by_method": dict(sorted(expected_weights_by_method.items())),
        "preprocessing_config_sha256": expected_preprocessing_config_sha256,
        "model_config_sha256": expected_model_config_sha256,
        "qlib_exchange_config_sha256": expected_qlib_exchange_config_sha256,
        "test_dates_sha256": expected_test_dates_sha256,
        "model_binary_sha256": NOT_APPLICABLE_MODEL_BINARY,
        "fitted_preprocessing_artifact_id": NOT_APPLICABLE_PREPROCESSOR,
        "validation_search_sha256": NOT_APPLICABLE_VALIDATION_SEARCH,
    }
    for field, expected in checks.items():
        if payload.get(field) != expected:
            issues.append(f"{field}: expected {expected!r}, observed {payload.get(field)!r}")
    if not str(payload.get("freeze_id", "")).startswith("pre_test_freeze_v1:"):
        issues.append("freeze_id is absent or malformed")
    else:
        core = {key: value for key, value in payload.items() if key != "freeze_id"}
        expected_id = f"pre_test_freeze_v1:{canonical_hash(core)}"
        if payload["freeze_id"] != expected_id:
            issues.append("freeze_id content hash mismatch")
    return issues


def load_freeze_with_file_hash(path: Path) -> tuple[dict[str, Any], str]:
    return json.loads(path.read_text(encoding="utf-8")), file_sha256(path)


def reserve_test_release(path: Path, core: Mapping[str, Any]) -> dict[str, Any]:
    static_core = dict(core)
    if path.is_file():
        existing = json.loads(path.read_text(encoding="utf-8"))
        existing_core = {
            key: value
            for key, value in existing.items()
            if key not in {"receipt_id", "release_timestamp", "status", "score_artifact_sha256"}
        }
        if existing_core != static_core:
            raise ValueError(f"test release receipt already exists for different frozen inputs: {path}")
        return existing
    timestamp = datetime.now(timezone.utc).isoformat()
    receipt = {
        **static_core,
        "status": "reserved",
        "release_timestamp": timestamp,
    }
    receipt["receipt_id"] = f"test_release_v1:{canonical_hash(receipt)}"
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)
    return receipt


def finalize_test_release(receipt: Mapping[str, Any], *, score_artifact_sha256: str) -> dict[str, Any]:
    finalized = {**dict(receipt), "status": "consumed", "score_artifact_sha256": score_artifact_sha256}
    core = {key: value for key, value in finalized.items() if key != "receipt_id"}
    finalized["receipt_id"] = f"test_release_v1:{canonical_hash(core)}"
    return finalized
