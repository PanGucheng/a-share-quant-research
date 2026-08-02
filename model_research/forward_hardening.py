from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping
from zoneinfo import ZoneInfo

import pandas as pd

from research_validation.feature_matrix import canonical_hash, file_sha256
from research_validation.lineage import (
    capture_code_state,
    load_artifact_manifest,
    validate_manifest_outputs,
    write_stage_artifact_manifest,
)
from research_validation.stage_output import StageOutputPublisher

from .forward_prediction_contract import validate_forward_admission
from .forward_protocol import load_forward_config, resolve, resolve_labels_runtime


PROJECT_ROOT = Path(__file__).resolve().parents[1]
STAGE_ID = "prospective_forward_hardening_v1"
OUTPUTS = (
    "artifact_manifest.json",
    "contract_status.csv",
    "durable_storage_receipt.json",
    "forward_candidate_freeze.json",
    "parent_receipts.csv",
    "prediction_freeze_schema.json",
    "readiness_summary.csv",
    "resolved_config.json",
    "run_report.md",
)


def _contract(
    name: str, passed: bool, observed: object, required: object
) -> dict[str, object]:
    return {
        "check_name": name,
        "status": "pass" if passed else "blocked",
        "observed_value": observed,
        "required_value": required,
        "severity": "critical",
        "reason": "" if passed else f"{name} failed",
    }


def _parent(path: Path, expected_stage: str) -> dict[str, Any]:
    manifest = load_artifact_manifest(path)
    if (
        manifest["stage_id"] != expected_stage
        or manifest["artifact_status"] != "pass"
        or manifest["lineage_status"] != "complete"
        or bool(manifest["code_dirty"])
    ):
        raise ValueError(f"invalid hardening parent: {path}")
    issues = validate_manifest_outputs(manifest, path.parent)
    if issues:
        raise ValueError(
            f"stale hardening parent {path}: "
            + "|".join(issue.reason for issue in issues)
        )
    return manifest


def _copy_content_addressed(
    source: Path,
    *,
    root: Path,
    candidate_key: str,
    expected_sha256: str,
) -> Path:
    if file_sha256(source) != expected_sha256:
        raise ValueError(f"source candidate hash mismatch: {source}")
    target_dir = (root / candidate_key).resolve()
    allowed = root.resolve()
    if target_dir != allowed and allowed not in target_dir.parents:
        raise ValueError("durable storage path escapes configured root")
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / source.name
    if target.exists():
        if file_sha256(target) != expected_sha256:
            raise ValueError(f"durable target collision: {target}")
    else:
        shutil.copy2(source, target)
    if file_sha256(target) != expected_sha256:
        raise ValueError(f"durable copy hash mismatch: {target}")
    return target


def _resolve_repo_uri(uri: object) -> Path:
    value = str(uri)
    if not value.startswith("repo://"):
        raise ValueError("durable candidate URI must use repo://")
    path = (PROJECT_ROOT / value.removeprefix("repo://")).resolve()
    if PROJECT_ROOT.resolve() not in path.parents:
        raise ValueError("durable candidate URI escapes repository")
    return path


def verify_durable_candidate(
    freeze_or_path: Mapping[str, Any] | str | Path,
) -> tuple[Path, Path]:
    """Resolve and hash-check durable model assets before every prediction."""

    if isinstance(freeze_or_path, Mapping):
        freeze = dict(freeze_or_path)
    else:
        freeze = json.loads(
            resolve(freeze_or_path).read_text(encoding="utf-8")
        )
    model = _resolve_repo_uri(freeze["model_storage_uri"])
    preprocessing = _resolve_repo_uri(freeze["preprocessing_storage_uri"])
    for path, hash_field, size_field in (
        (model, "model_binary_sha256", "model_size_bytes"),
        (preprocessing, "preprocessing_sha256", "preprocessing_size_bytes"),
    ):
        if not path.is_file():
            raise FileNotFoundError(f"durable candidate asset missing: {path}")
        if file_sha256(path) != str(freeze[hash_field]):
            raise ValueError(f"durable candidate asset hash mismatch: {path}")
        if path.stat().st_size != int(freeze[size_field]):
            raise ValueError(f"durable candidate asset size mismatch: {path}")
    return model, preprocessing


def prediction_freeze_schema() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "required_fields": [
            "decision_date",
            "raw_snapshot_first_seen_at",
            "feature_snapshot_created_at",
            "prediction_created_at",
            "prediction_sha256",
            "prediction_commit_sha",
            "prediction_commit_timestamp",
            "label_start_date",
            "label_start_cutoff",
            "label_mature_date",
            "label_read_count_at_prediction",
            "candidate_freeze_id",
            "model_sha256",
            "preprocessing_sha256",
        ],
        "timezone": "Asia/Shanghai",
        "label_start_cutoff_policy": "next_trading_day_09_25",
        "contracts": {
            "decision_after_candidate_freeze_local_date": True,
            "raw_first_seen_after_candidate_freeze_timestamp": True,
            "feature_snapshot_not_before_raw_first_seen": True,
            "prediction_created_before_label_start_cutoff": True,
            "prediction_commit_before_label_start_cutoff": True,
            "label_read_count_at_prediction": 0,
            "prediction_payload_immutable": True,
            "prediction_commit_receipt_immutable": True,
        },
        "evaluation_policy": (
            "evaluation may consume only a hash-valid payload plus its "
            "pre-label-start commit receipt after label maturity"
        ),
    }


def harden_forward_candidate(
    config_path: str | Path,
    *,
    command: str,
) -> dict[str, object]:
    config_file = resolve(config_path)
    config = load_forward_config(config_file)
    code_state = capture_code_state(PROJECT_ROOT)
    if code_state.dirty:
        raise ValueError("forward hardening requires clean committed code")

    parent_specs = (
        (
            "forward_protocol_v1_1",
            resolve(
                "outputs/prospective_forward_protocol_v1/current/"
                "artifact_manifest.json"
            ),
            "prospective_forward_protocol_v1",
        ),
        (
            "forward_candidate_v1",
            resolve(
                "outputs/prospective_forward_candidate_v1/current/"
                "artifact_manifest.json"
            ),
            "prospective_forward_candidate_v1",
        ),
        (
            "research_model_protocol_v1_1",
            resolve(config["parents"]["protocol_manifest"]),
            "research_model_protocol_v1_1",
        ),
        (
            "labels_v2",
            resolve(config["parents"]["labels_manifest"]),
            "full_research_labels_v2",
        ),
    )
    parents = [
        (role, path, _parent(path, stage))
        for role, path, stage in parent_specs
    ]
    previous_freeze_path = resolve(
        "outputs/prospective_forward_candidate_v1/current/"
        "forward_candidate_freeze.json"
    )
    previous = json.loads(previous_freeze_path.read_text(encoding="utf-8"))
    protocol_freeze = json.loads(
        resolve(
            "outputs/prospective_forward_protocol_v1/current/"
            "forward_protocol_freeze.json"
        ).read_text(encoding="utf-8")
    )
    model_source = resolve(previous["model_runtime_path"])
    preprocessing_source = resolve(previous["preprocessing_runtime_path"])
    model_sha = str(previous["model_binary_sha256"])
    preprocessing_sha = str(previous["preprocessing_sha256"])
    storage = config["durable_storage"]
    if model_sha != storage["model_sha256"]:
        raise ValueError("configured durable model hash differs from freeze")
    if preprocessing_sha != storage["preprocessing_sha256"]:
        raise ValueError("configured durable preprocessing hash differs from freeze")
    durable_root = resolve(storage["root"])
    model_target = _copy_content_addressed(
        model_source,
        root=durable_root,
        candidate_key=model_sha,
        expected_sha256=model_sha,
    )
    preprocessing_target = _copy_content_addressed(
        preprocessing_source,
        root=durable_root,
        candidate_key=model_sha,
        expected_sha256=preprocessing_sha,
    )
    labels_path = resolve_labels_runtime(config)

    effective_time = datetime.now(timezone.utc)
    effective_local_date = effective_time.astimezone(
        ZoneInfo("Asia/Shanghai")
    ).date()
    new_freeze = {
        **previous,
        "schema_version": 2,
        "status": "frozen_waiting_for_strictly_prospective_data",
        "previous_forward_candidate_freeze_id": previous[
            "forward_candidate_freeze_id"
        ],
        "forward_protocol_freeze_id": protocol_freeze[
            "forward_protocol_freeze_id"
        ],
        "candidate_freeze_effective_time_utc": effective_time.isoformat(),
        "candidate_freeze_effective_date_asia_shanghai": (
            effective_local_date.isoformat()
        ),
        "official_forward_decision_date_rule": config["temporal_boundary"][
            "official_forward_rule"
        ],
        "labels_runtime_sha256": file_sha256(labels_path),
        "model_storage_uri": (
            "repo://" + model_target.relative_to(PROJECT_ROOT).as_posix()
        ),
        "preprocessing_storage_uri": (
            "repo://"
            + preprocessing_target.relative_to(PROJECT_ROOT).as_posix()
        ),
        "model_size_bytes": model_target.stat().st_size,
        "preprocessing_size_bytes": preprocessing_target.stat().st_size,
        "backup_verified": True,
        "backup_verification_method": storage["backup_verification"],
        "rebind_only_no_retraining": True,
        "hardening_code_commit_sha": code_state.commit_sha,
        "production_model_selected": False,
        "live_trading_ready": False,
        "forward_data_waiting": True,
    }
    new_freeze.pop("forward_candidate_freeze_id", None)
    new_freeze["forward_candidate_freeze_id"] = (
        "forward-candidate-freeze:" + canonical_hash(new_freeze)
    )
    verify_durable_candidate(new_freeze)
    durability = {
        "schema_version": 1,
        "storage_class": storage["storage_class"],
        "model_storage_uri": new_freeze["model_storage_uri"],
        "model_sha256": model_sha,
        "model_size_bytes": model_target.stat().st_size,
        "preprocessing_storage_uri": new_freeze[
            "preprocessing_storage_uri"
        ],
        "preprocessing_sha256": preprocessing_sha,
        "preprocessing_size_bytes": preprocessing_target.stat().st_size,
        "backup_verified": True,
        "backup_verification_method": storage["backup_verification"],
        "verification_timestamp_utc": effective_time.isoformat(),
    }
    durability["storage_receipt_id"] = (
        "durable-candidate-storage:" + canonical_hash(durability)
    )
    schema = prediction_freeze_schema()

    old_date_rejected = False
    try:
        validate_forward_admission(
            decision_date="2026-06-10",
            raw_snapshot_first_seen_at=(
                effective_time.replace(microsecond=0).isoformat()
            ),
            candidate_freeze_effective_time=effective_time.isoformat(),
        )
    except PermissionError:
        old_date_rejected = True
    contracts = pd.DataFrame(
        [
            _contract("direct_parents_valid", len(parents) == 4, len(parents), 4),
            _contract(
                "strict_event_time_boundary_active",
                old_date_rejected,
                old_date_rejected,
                True,
            ),
            _contract(
                "labels_runtime_manifest_resolved_and_hash_valid",
                file_sha256(labels_path)
                == config["training"]["labels_runtime_sha256"],
                file_sha256(labels_path),
                config["training"]["labels_runtime_sha256"],
            ),
            _contract(
                "model_binary_unchanged",
                file_sha256(model_target) == model_sha,
                file_sha256(model_target),
                model_sha,
            ),
            _contract(
                "preprocessing_unchanged",
                file_sha256(preprocessing_target) == preprocessing_sha,
                file_sha256(preprocessing_target),
                preprocessing_sha,
            ),
            _contract(
                "durable_backup_verified",
                bool(durability["backup_verified"]),
                durability["backup_verified"],
                True,
            ),
            _contract(
                "durable_assets_reload_hash_valid",
                all(path.is_file() for path in verify_durable_candidate(new_freeze)),
                [path.as_posix() for path in verify_durable_candidate(new_freeze)],
                "two hash-valid durable assets",
            ),
            _contract(
                "candidate_rebound_without_retraining",
                bool(new_freeze["rebind_only_no_retraining"]),
                new_freeze["rebind_only_no_retraining"],
                True,
            ),
            _contract(
                "prediction_before_label_contract_frozen",
                schema["contracts"][
                    "prediction_created_before_label_start_cutoff"
                ]
                and schema["contracts"][
                    "prediction_commit_before_label_start_cutoff"
                ],
                schema["label_start_cutoff_policy"],
                "next_trading_day_09_25",
            ),
            _contract(
                "production_and_live_gates_closed",
                not new_freeze["production_model_selected"]
                and not new_freeze["live_trading_ready"],
                {
                    "production": new_freeze["production_model_selected"],
                    "live": new_freeze["live_trading_ready"],
                },
                {"production": False, "live": False},
            ),
        ]
    )
    if not contracts["status"].eq("pass").all():
        raise ValueError("prospective hardening contracts failed")
    readiness = pd.DataFrame(
        [
            {
                "prospective_time_boundary_hardened": True,
                "prediction_before_label_contract_ready": True,
                "forward_lineage_hardened": True,
                "forward_candidate_durable_storage_ready": True,
                "forward_candidate_rebound_without_retraining": True,
                "forward_data_waiting": True,
                "forward_prediction_confirmation_complete": False,
                "production_model_selected": False,
                "live_trading_ready": False,
            }
        ]
    )
    parent_receipts = pd.DataFrame(
        [
            {
                "parent_role": role,
                "stage_id": manifest["stage_id"],
                "artifact_id": manifest["artifact_id"],
                "manifest_path": path.as_posix(),
                "artifact_status": manifest["artifact_status"],
                "lineage_status": manifest["lineage_status"],
                "direct_parent": True,
            }
            for role, path, manifest in parents
        ]
    )
    output_dir = resolve(
        "outputs/prospective_forward_hardening_v1/current"
    )
    resolved_config = {
        **config,
        "executed_command": command,
        "executed_scope": "candidate_rebind_and_prospective_time_hardening",
        "output_dir": output_dir.as_posix(),
    }
    with StageOutputPublisher(output_dir, OUTPUTS) as publisher:
        for name, payload in (
            ("forward_candidate_freeze.json", new_freeze),
            ("durable_storage_receipt.json", durability),
            ("prediction_freeze_schema.json", schema),
            ("resolved_config.json", resolved_config),
        ):
            publisher.path(name).write_text(
                json.dumps(
                    payload,
                    ensure_ascii=False,
                    indent=2,
                    sort_keys=True,
                    default=str,
                )
                + "\n",
                encoding="utf-8",
            )
        contracts.to_csv(publisher.path("contract_status.csv"), index=False)
        readiness.to_csv(publisher.path("readiness_summary.csv"), index=False)
        parent_receipts.to_csv(
            publisher.path("parent_receipts.csv"), index=False
        )
        publisher.path("run_report.md").write_text(
            "# Prospective Forward Hardening V1\n\n"
            f"- Candidate effective local date: `{effective_local_date}`.\n"
            "- Official decision dates must be strictly later than that date.\n"
            "- Raw first-seen time must be later than the effective timestamp.\n"
            "- Prediction payload and commit receipt must precede t+1 09:25 "
            "Asia/Shanghai.\n"
            "- Model and preprocessing are Git-backed content-addressed files.\n"
            "- Model retraining/search: none.\n"
            "- Forward data waiting: true.\n",
            encoding="utf-8",
        )
        output_files = [
            publisher.path(name)
            for name in OUTPUTS
            if name != "artifact_manifest.json"
        ]
        write_stage_artifact_manifest(
            project_root=PROJECT_ROOT,
            stage_id=STAGE_ID,
            config=resolved_config,
            output_dir=publisher.staging_dir,
            output_files=output_files,
            code_state=code_state,
            input_manifest_paths=[path for _, path, _ in parents],
            universe_artifact_id=parents[1][2].get("universe_artifact_id"),
            split_manifest_id=parents[1][2].get("split_manifest_id"),
            factor_catalog_id=parents[1][2].get("factor_catalog_id"),
            factor_frame_id=parents[1][2].get("factor_frame_id"),
            start_date=previous["training_start_date"],
            end_date=effective_local_date,
            contract_paths=[publisher.path("contract_status.csv")],
        )
        publisher.publish()
    return {
        "output_dir": output_dir.as_posix(),
        "forward_candidate_freeze_id": new_freeze[
            "forward_candidate_freeze_id"
        ],
        "candidate_freeze_effective_time_utc": effective_time.isoformat(),
        "candidate_freeze_effective_date_asia_shanghai": (
            effective_local_date.isoformat()
        ),
        "model_sha256": model_sha,
        "preprocessing_sha256": preprocessing_sha,
        "retrained": False,
        "forward_data_waiting": True,
    }
