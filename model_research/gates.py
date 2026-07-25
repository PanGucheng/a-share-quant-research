from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

import pandas as pd

from research_validation.lineage import (
    load_artifact_manifest,
    validate_manifest_outputs,
)


RESEARCH_EXPERIMENT_CLASS = "post_observation_research"
BLOCKED_EXPERIMENT_CLASSES = frozenset(
    {"authoritative_oos", "production", "paper", "live"}
)
PROJECT_ROOT = Path(__file__).resolve().parents[1]
RESEARCH_MODEL_PROTOCOL_MANIFEST = (
    PROJECT_ROOT
    / "outputs"
    / "research_model_protocol_v1_1"
    / "current"
    / "artifact_manifest.json"
)
RESEARCH_MODEL_PROTOCOL_STAGE = "research_model_protocol_v1_1"
REQUIRED_ENTRY_CONTRACTS = frozenset(
    {
        "manifest_bound_entry_gate_valid",
        "canary_protocol_binding_valid",
        "sample_eligibility_exact",
        "validation_transform_ready",
        "matrix_runtime_authority_valid",
        "development_dry_run_ready",
        "test_read_count_before_freeze_zero",
    }
)


class ModelScopeBlockedError(RuntimeError):
    """Raised when the scoped model protocol does not authorize an action."""


def _as_bool(value: object, *, field: str) -> bool:
    if isinstance(value, bool):
        return value
    normalized = str(value).strip().lower()
    if normalized in {"true", "1", "yes"}:
        return True
    if normalized in {"false", "0", "no"}:
        return False
    raise ValueError(f"{field} must be boolean, got {value!r}")


def model_scope_blockers(
    readiness: Mapping[str, object],
    *,
    experiment_class: str | None,
    operation: str = "training",
) -> list[str]:
    normalized_class = str(experiment_class or "").strip().lower()
    if not normalized_class:
        return ["experiment_class_unspecified"]
    if normalized_class in BLOCKED_EXPERIMENT_CLASSES:
        return [f"experiment_class_blocked:{normalized_class}"]
    if normalized_class != RESEARCH_EXPERIMENT_CLASS:
        return [f"experiment_class_unknown:{normalized_class}"]

    required = {
        "research_model_protocol_ready",
        "research_model_input_ready",
        "research_model_training_ready",
        "research_model_hard_stop_active",
        "production_model_hard_stop_active",
        "production_model_selected",
    }
    missing = sorted(required - set(readiness))
    if missing:
        return [f"research_model_readiness_missing:{','.join(missing)}"]

    blockers: list[str] = []
    for field in (
        "research_model_protocol_ready",
        "research_model_input_ready",
        "research_model_training_ready",
    ):
        if not _as_bool(readiness[field], field=field):
            blockers.append(f"{field}=false")
    if _as_bool(
        readiness["research_model_hard_stop_active"],
        field="research_model_hard_stop_active",
    ):
        blockers.append("research_model_hard_stop_active=true")
    if not _as_bool(
        readiness["production_model_hard_stop_active"],
        field="production_model_hard_stop_active",
    ):
        blockers.append("production_model_hard_stop_active=false")
    if _as_bool(
        readiness["production_model_selected"],
        field="production_model_selected",
    ):
        blockers.append("production_model_selected=true")
    if operation not in {"input_audit", "canary", "training", "prediction"}:
        blockers.append(f"operation_unknown:{operation}")
    return blockers


def assert_model_scope_allowed(
    readiness: Mapping[str, object],
    *,
    experiment_class: str | None,
    operation: str = "training",
) -> None:
    blockers = model_scope_blockers(
        readiness,
        experiment_class=experiment_class,
        operation=operation,
    )
    if blockers:
        raise ModelScopeBlockedError(
            "model scope blocked: " + "; ".join(blockers)
        )


def assert_research_model_entry_artifact(
    manifest_path: Path = RESEARCH_MODEL_PROTOCOL_MANIFEST,
    *,
    experiment_class: str | None,
    operation: str = "training",
) -> None:
    if not manifest_path.is_file():
        raise ModelScopeBlockedError(
            f"model scope blocked: missing protocol manifest: {manifest_path}"
        )
    try:
        manifest = load_artifact_manifest(manifest_path)
    except (OSError, ValueError) as exc:
        raise ModelScopeBlockedError(
            f"model scope blocked: invalid protocol manifest: {exc}"
        ) from exc
    manifest_blockers: list[str] = []
    if manifest.get("stage_id") != RESEARCH_MODEL_PROTOCOL_STAGE:
        manifest_blockers.append(
            f"stage_id={manifest.get('stage_id')!r}"
        )
    if manifest.get("artifact_status") != "pass":
        manifest_blockers.append(
            f"artifact_status={manifest.get('artifact_status')!r}"
        )
    if manifest.get("lineage_status") != "complete":
        manifest_blockers.append(
            f"lineage_status={manifest.get('lineage_status')!r}"
        )
    if manifest.get("profile_type") != "full_research":
        manifest_blockers.append(
            f"profile_type={manifest.get('profile_type')!r}"
        )
    if bool(manifest.get("code_dirty")):
        manifest_blockers.append("code_dirty=true")
    issues = validate_manifest_outputs(manifest, manifest_path.parent)
    manifest_blockers.extend(
        f"{issue.check_name}:{issue.reason}" for issue in issues
    )
    if manifest_blockers:
        raise ModelScopeBlockedError(
            "model scope blocked: " + "; ".join(manifest_blockers)
        )

    readiness_path = manifest_path.parent / "readiness_summary.csv"
    contract_path = manifest_path.parent / "contract_status.csv"
    output_hashes = dict(manifest.get("output_file_hashes", {}))
    for required_path in (readiness_path, contract_path):
        if required_path.name not in output_hashes:
            raise ModelScopeBlockedError(
                f"model scope blocked: manifest does not control {required_path.name}"
            )
    readiness = pd.read_csv(readiness_path)
    if len(readiness) != 1:
        raise ModelScopeBlockedError(
            f"model scope blocked: scoped readiness rows={len(readiness)}"
        )
    contracts = pd.read_csv(contract_path)
    required_columns = {"check_name", "status", "severity"}
    if not required_columns.issubset(contracts.columns):
        raise ModelScopeBlockedError(
            "model scope blocked: malformed contract_status.csv"
        )
    critical = contracts.loc[
        contracts["severity"].astype(str).str.lower().eq("critical")
    ]
    if not critical["status"].astype(str).str.lower().eq("pass").all():
        raise ModelScopeBlockedError(
            "model scope blocked: critical protocol contract failed"
        )
    contract_names = set(contracts["check_name"].astype(str))
    missing_contracts = sorted(REQUIRED_ENTRY_CONTRACTS - contract_names)
    if missing_contracts:
        raise ModelScopeBlockedError(
            f"model scope blocked: missing closure contracts: {missing_contracts}"
        )

    row = readiness.iloc[0].to_dict()
    if str(row.get("protocol_closure_version")) != "1.1":
        raise ModelScopeBlockedError(
            "model scope blocked: protocol_closure_version is not 1.1"
        )
    normalized_class = str(experiment_class or "").strip().lower()
    if str(row.get("experiment_class", "")).strip().lower() != normalized_class:
        raise ModelScopeBlockedError(
            "model scope blocked: readiness experiment_class does not match caller"
        )
    for field, expected in (
        ("historical_test_already_observed", True),
        ("authoritative_execution", False),
        ("unbiased_final_estimate", False),
        ("production_model_hard_stop_active", True),
        ("production_model_selected", False),
    ):
        try:
            observed = _as_bool(row.get(field), field=field)
        except ValueError as exc:
            raise ModelScopeBlockedError(
                f"model scope blocked: invalid {field}: {exc}"
            ) from exc
        if observed is not expected:
            raise ModelScopeBlockedError(
                f"model scope blocked: {field} must be {str(expected).lower()}"
            )
    assert_model_scope_allowed(
        row,
        experiment_class=experiment_class,
        operation=operation,
    )


def assert_research_model_entry_file(
    readiness_path: Path,
    *,
    experiment_class: str | None,
    operation: str = "training",
) -> None:
    del readiness_path, experiment_class, operation
    raise ModelScopeBlockedError(
        "model scope blocked: direct readiness CSV entry is forbidden; "
        "provide the protocol artifact manifest"
    )
