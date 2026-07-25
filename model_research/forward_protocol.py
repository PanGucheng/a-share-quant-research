from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from research_validation.feature_matrix import canonical_hash, file_sha256
from research_validation.lineage import (
    capture_code_state,
    load_artifact_manifest,
    validate_manifest_outputs,
    write_stage_artifact_manifest,
)
from research_validation.stage_output import StageOutputPublisher


PROJECT_ROOT = Path(__file__).resolve().parents[1]
STAGE_ID = "prospective_forward_protocol_v1"
OUTPUTS = (
    "artifact_manifest.json",
    "candidate_spec.json",
    "contract_status.csv",
    "data_availability_audit.csv",
    "forward_protocol_freeze.json",
    "parent_receipts.csv",
    "quarantined_date_inventory.csv",
    "readiness_summary.csv",
    "resolved_config.json",
    "run_report.md",
    "temporal_boundary.json",
)


def resolve(path: str | Path) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else PROJECT_ROOT / candidate


def load_forward_config(path: str | Path) -> dict[str, Any]:
    payload = yaml.safe_load(resolve(path).read_text(encoding="utf-8"))
    if payload["experiment_class"] != "prospective_research_protocol":
        raise ValueError("forward protocol experiment class mismatch")
    if bool(payload["candidate"]["hyperparameter_search_allowed"]):
        raise ValueError("forward candidate search is forbidden")
    governance = payload["governance"]
    for field in (
        "production_model_selected",
        "live_trading_ready",
        "authoritative_historical_execution_ready",
        "unbiased_historical_estimate",
    ):
        if bool(governance[field]):
            raise ValueError(f"forward protocol overclaims {field}")
    if bool(governance["retrospective_extension_prospective_eligible"]):
        raise ValueError("retrospective extension cannot be prospective evidence")
    return payload


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


def _parents(
    config: dict[str, Any],
) -> list[tuple[str, Path, dict[str, Any]]]:
    roles = (
        "historical_comparison_manifest",
        "lightgbm_development_manifest",
        "selection_manifest",
        "matrix_manifest",
        "labels_manifest",
    )
    result = []
    for role in roles:
        path = resolve(config["parents"][role])
        manifest = load_artifact_manifest(path)
        if (
            manifest["artifact_status"] != "pass"
            or manifest["lineage_status"] != "complete"
            or bool(manifest["code_dirty"])
        ):
            raise ValueError(f"invalid forward protocol parent: {role}")
        issues = validate_manifest_outputs(manifest, path.parent)
        if issues:
            raise ValueError(
                f"stale forward protocol parent {role}: "
                + "|".join(issue.reason for issue in issues)
            )
        result.append((role, path, manifest))
    return result


def _candidate_spec(config: dict[str, Any]) -> dict[str, Any]:
    leader = json.loads(
        resolve(config["parents"]["historical_leader"]).read_text(
            encoding="utf-8"
        )
    )
    if leader["historical_oos_research_leader"] != "lightgbm":
        raise ValueError("configured forward candidate differs from historical leader")
    selected = json.loads(
        resolve(config["parents"]["selected_hyperparameters"]).read_text(
            encoding="utf-8"
        )
    )["split_003"]
    configured = config["candidate"]
    expected = {
        "method": configured["method"],
        "structural_row_id": configured["structural_row_id"],
        "num_boost_round": int(configured["num_boost_round"]),
    }
    if any(selected[key] != value for key, value in expected.items()):
        raise ValueError("configured candidate differs from split_003 freeze")
    allowlists = pd.read_csv(
        resolve(config["parents"]["split_allowlist_manifest"])
    )
    row = allowlists.loc[allowlists["outer_split_id"].eq("split_003")]
    if len(row) != 1:
        raise ValueError("split_003 allowlist row missing")
    row = row.iloc[0]
    if (
        int(row["factor_count"]) != int(configured["factor_count"])
        or row["allowlist_sha256"] != configured["allowlist_sha256"]
        or row["feature_order_sha256"] != configured["feature_order_sha256"]
    ):
        raise ValueError("configured split_003 feature identity mismatch")
    payload = {
        "schema_version": 1,
        "candidate_status": "provisional_research_only",
        "selection_source": "historical_oos_post_observation_comparison",
        "method": "lightgbm",
        "source_split_id": "split_003",
        "factor_count": int(configured["factor_count"]),
        "allowlist_sha256": configured["allowlist_sha256"],
        "feature_order_sha256": configured["feature_order_sha256"],
        "selected_hyperparameters": selected,
        "hyperparameter_search_allowed": False,
        "production_model_selected": False,
        "unbiased_selection_estimate": False,
    }
    payload["candidate_spec_sha256"] = canonical_hash(payload)
    return payload


def freeze_forward_protocol(
    config_path: str | Path,
    *,
    command: str,
) -> dict[str, object]:
    config_file = resolve(config_path)
    config = load_forward_config(config_file)
    parents = _parents(config)
    code_state = capture_code_state(PROJECT_ROOT)
    if code_state.dirty:
        raise ValueError("forward protocol freeze requires clean committed code")
    candidate = _candidate_spec(config)
    boundary = config["temporal_boundary"]
    labels_path = resolve(config["parents"]["labels_runtime"])
    labels = pd.read_parquet(
        labels_path,
        columns=["datetime", "instrument", config["training"]["label_name"]],
    )
    labels["datetime"] = pd.to_datetime(labels["datetime"]).dt.normalize()
    counts = (
        labels.groupby("datetime")[config["training"]["label_name"]]
        .count()
        .rename("label_count")
        .reset_index()
    )
    minimum_pairs = int(config["training"]["minimum_daily_pairs"])
    label_mature = counts.loc[counts["label_count"].ge(minimum_pairs)]
    latest_mature = pd.Timestamp(label_mature["datetime"].max())
    matrix_end = pd.Timestamp(
        next(item[2] for item in parents if item[0] == "matrix_manifest")[
            "end_date"
        ]
    )
    retrospective_start = pd.Timestamp(boundary["retrospective_extension_start"])
    snapshot_end = pd.Timestamp(boundary["current_snapshot_end"])
    quarantine = counts.loc[
        counts["datetime"].between(retrospective_start, snapshot_end)
    ].copy()
    quarantine["evidence_class"] = "retrospective_extension_quarantine"
    quarantine["prospective_evidence_eligible"] = False
    quarantine["reason"] = "available_before_forward_protocol_freeze"
    quarantine["label_mature"] = quarantine["label_count"].ge(minimum_pairs)
    quarantine["datetime"] = quarantine["datetime"].dt.date.astype(str)

    temporal = {
        "schema_version": 1,
        **boundary,
        "observed_matrix_end": matrix_end.date().isoformat(),
        "observed_latest_label_mature_date": latest_mature.date().isoformat(),
        "official_forward_first_date": None,
        "official_forward_status": "waiting_for_post_freeze_new_data",
        "retrospective_extension_prospective_eligible": False,
    }
    temporal["temporal_boundary_sha256"] = canonical_hash(temporal)
    availability = pd.DataFrame(
        [
            {
                "data_scope": "current_matrix_snapshot",
                "start_date": parents[3][2]["start_date"],
                "end_date": matrix_end.date().isoformat(),
                "first_seen_after_freeze": False,
                "prospective_evidence_eligible": False,
                "status": "frozen_training_or_quarantine_input",
            },
            {
                "data_scope": "retrospective_extension",
                "start_date": pd.Timestamp(
                    boundary["retrospective_extension_start"]
                ).date().isoformat(),
                "end_date": snapshot_end.date().isoformat(),
                "first_seen_after_freeze": False,
                "prospective_evidence_eligible": False,
                "status": "quarantined",
            },
            {
                "data_scope": "official_forward",
                "start_date": f">{snapshot_end.date().isoformat()}",
                "end_date": "",
                "first_seen_after_freeze": True,
                "prospective_evidence_eligible": True,
                "status": "waiting_for_new_data",
            },
        ]
    )
    freeze = {
        "schema_version": 1,
        "status": "frozen_waiting_for_new_data",
        "candidate_spec_sha256": candidate["candidate_spec_sha256"],
        "temporal_boundary_sha256": temporal["temporal_boundary_sha256"],
        "config_file_sha256": file_sha256(config_file),
        "code_commit_sha": code_state.commit_sha,
        "current_snapshot_end": snapshot_end.date().isoformat(),
        "latest_label_mature_training_date": latest_mature.date().isoformat(),
        "official_forward_rule": boundary["official_forward_rule"],
        "minimum_label_mature_dates_for_primary_confirmation": int(
            boundary["minimum_label_mature_dates_for_primary_confirmation"]
        ),
        "forward_data_waiting": True,
        "production_model_selected": False,
        "live_trading_ready": False,
    }
    freeze["forward_protocol_freeze_id"] = (
        "forward-protocol-freeze:" + canonical_hash(freeze)
    )
    contracts = pd.DataFrame(
        [
            _contract(
                "direct_parents_valid", len(parents) == 5, len(parents), 5
            ),
            _contract(
                "historical_leader_is_research_only",
                candidate["production_model_selected"] is False,
                candidate["production_model_selected"],
                False,
            ),
            _contract(
                "candidate_feature_identity_frozen",
                candidate["factor_count"] == 52,
                candidate["factor_count"],
                52,
            ),
            _contract(
                "matrix_snapshot_end_frozen",
                matrix_end == snapshot_end,
                matrix_end.date().isoformat(),
                snapshot_end.date().isoformat(),
            ),
            _contract(
                "latest_training_label_mature_date_frozen",
                latest_mature
                == pd.Timestamp(boundary["latest_label_mature_training_date"]),
                latest_mature.date().isoformat(),
                boundary["latest_label_mature_training_date"],
            ),
            _contract(
                "training_label_window_ends_before_forward_boundary",
                latest_mature < snapshot_end,
                latest_mature.date().isoformat(),
                f"<{snapshot_end.date().isoformat()}",
            ),
            _contract(
                "retrospective_extension_quarantined",
                not quarantine["prospective_evidence_eligible"].any(),
                bool(quarantine["prospective_evidence_eligible"].any()),
                False,
            ),
            _contract(
                "official_forward_waiting_fail_closed",
                freeze["forward_data_waiting"] is True,
                freeze["forward_data_waiting"],
                True,
            ),
        ]
    )
    if not contracts["status"].eq("pass").all():
        raise ValueError(
            "forward protocol contracts failed: "
            + ",".join(
                contracts.loc[
                    ~contracts["status"].eq("pass"), "check_name"
                ].astype(str)
            )
        )
    readiness = pd.DataFrame(
        [
            {
                "forward_protocol_ready": True,
                "forward_candidate_spec_frozen": True,
                "forward_candidate_refit_complete": False,
                "forward_candidate_freeze_ready": False,
                "forward_data_waiting": True,
                "forward_prediction_confirmation_complete": False,
                "provisional_candidate_confirmed": False,
                "production_model_selected": False,
                "live_trading_ready": False,
                "authoritative_historical_execution_ready": False,
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
    resolved_config = {
        **config,
        "config_file_sha256": file_sha256(config_file),
        "executed_command": command,
        "executed_scope": "prospective_protocol_and_temporal_boundary_freeze",
        "output_dir": resolve(config["output_dir"]).as_posix(),
    }
    output_dir = resolve(config["output_dir"])
    with StageOutputPublisher(output_dir, OUTPUTS) as publisher:
        for name, payload in (
            ("candidate_spec.json", candidate),
            ("temporal_boundary.json", temporal),
            ("forward_protocol_freeze.json", freeze),
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
        quarantine.to_csv(
            publisher.path("quarantined_date_inventory.csv"), index=False
        )
        availability.to_csv(
            publisher.path("data_availability_audit.csv"), index=False
        )
        contracts.to_csv(publisher.path("contract_status.csv"), index=False)
        readiness.to_csv(publisher.path("readiness_summary.csv"), index=False)
        parent_receipts.to_csv(
            publisher.path("parent_receipts.csv"), index=False
        )
        publisher.path("run_report.md").write_text(
            "# Prospective Forward Protocol V1\n\n"
            "- Provisional candidate: LightGBM split_003 frozen specification.\n"
            "- Existing 2026-02-05—2026-06-09 extension: quarantined.\n"
            "- Official forward data: waiting for dates after 2026-06-09 "
            "first seen after this freeze.\n"
            "- Production model selected: false.\n"
            "- Live trading ready: false.\n",
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
            universe_artifact_id=parents[2][2].get("universe_artifact_id"),
            split_manifest_id=parents[2][2].get("split_manifest_id"),
            factor_catalog_id=parents[2][2].get("factor_catalog_id"),
            factor_frame_id=parents[2][2].get("factor_frame_id"),
            start_date=config["training"]["start_date"],
            end_date=boundary["current_snapshot_end"],
            contract_paths=[publisher.path("contract_status.csv")],
        )
        publisher.publish()
    return {
        "output_dir": output_dir.as_posix(),
        "forward_protocol_freeze_id": freeze["forward_protocol_freeze_id"],
        "quarantined_date_count": len(quarantine),
        "forward_data_waiting": True,
    }
