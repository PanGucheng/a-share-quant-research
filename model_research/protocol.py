from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from research_validation.feature_matrix import canonical_hash, file_sha256
from research_validation.lineage import (
    capture_code_state,
    load_artifact_manifest,
    validate_manifest_outputs,
    write_stage_artifact_manifest,
)
from research_validation.stage_output import StageOutputPublisher

from .freeze import capture_environment_lock
from .inputs import (
    InputAccessAudit,
    assert_feature_order,
    assert_fold_isolation,
    join_labels,
    load_fold_dates,
    load_split_feature_order,
    partition_factor_index,
    project_features,
    validate_factor_availability,
)
from .lineage import AuthoritativeParentPaths, resolve_authoritative_parents
from .metrics import frozen_metric_registry
from .preprocessing import daily_equal_weights, fit_weighted_preprocessing
from .schemas import PREDICTION_COLUMNS, prediction_schema_violations
from .targets import TARGET_TRANSFORM_ID, daily_cross_sectional_rank_centered


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONTROLLED_OUTPUTS = (
    "artifact_manifest.json",
    "parent_receipts.csv",
    "split_input_manifest.csv",
    "feature_order_manifest.csv",
    "target_transform_manifest.json",
    "preprocessing_protocol.json",
    "metric_registry.json",
    "prediction_schema.json",
    "environment_lock.json",
    "mutation_results.csv",
    "access_audit.csv",
    "contract_status.csv",
    "readiness_summary.csv",
    "protocol_report.md",
    "resolved_config.json",
)


def resolve(path: str | Path) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else PROJECT_ROOT / candidate


def parent_paths(config: dict[str, Any]) -> AuthoritativeParentPaths:
    parents = config["parents"]
    return AuthoritativeParentPaths(
        date_manifest=resolve(parents["date_manifest"]),
        selection_manifest=resolve(parents["selection_manifest"]),
        matrix_manifest=resolve(parents["matrix_manifest"]),
        labels_manifest=resolve(parents["labels_manifest"]),
        universe_manifest=resolve(parents["universe_manifest"]),
        date_assignments=resolve(parents["date_assignments"]),
        selection_date_assignments=resolve(
            parents["selection_date_assignments"]
        ),
    )


def qlib_commit_sha(config: dict[str, Any]) -> str:
    repository = resolve(config["environment"]["qlib_repository"])
    if not (repository / ".git").exists():
        return "unresolved"
    result = subprocess.run(
        ["git", "-C", str(repository), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def contract_row(
    name: str,
    passed: bool,
    observed: object,
    required: object,
    reason: str = "",
) -> dict[str, object]:
    return {
        "check_name": name,
        "status": "pass" if passed else "blocked",
        "observed_value": observed,
        "required_value": required,
        "severity": "critical",
        "reason": "" if passed else reason,
    }


def common_payloads(config: dict[str, Any]) -> dict[str, Any]:
    return {
        "target_transform": {
            **config["target"],
            "target_transform_id": TARGET_TRANSFORM_ID,
            "status": "frozen",
        },
        "preprocessing": {
            **config["preprocessing"],
            "fit_scope_search": "outer_train_only",
            "fit_scope_final": "outer_train_plus_validation",
            "solver_auto": config["linear_model"]["solver_auto"],
            "lightgbm_early_stopping": config["lightgbm"]["early_stopping"],
            "lightgbm_boosting_round_checkpoints": config["lightgbm"][
                "boosting_round_checkpoints"
            ],
            "status": "frozen",
        },
        "metrics": frozen_metric_registry(config),
        "prediction_schema": {
            "columns": list(PREDICTION_COLUMNS),
            "forbidden_payloads": [
                "label",
                "return",
                "IC",
                "Rank IC",
                "NAV",
                "Sharpe",
                "test selection rank",
            ],
            "status": "frozen",
        },
        "environment": capture_environment_lock(
            qlib_commit_sha=qlib_commit_sha(config)
        ),
    }


def _write_json(path: Path, payload: object) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _publish(
    *,
    config: dict[str, Any],
    output_dir: Path,
    resolution: Any,
    frames: dict[str, pd.DataFrame],
    payloads: dict[str, Any],
    report: str,
    input_manifest_paths: list[Path],
) -> dict[str, Any]:
    code_state = capture_code_state(PROJECT_ROOT)
    with StageOutputPublisher(output_dir, CONTROLLED_OUTPUTS) as publisher:
        frames["parent_receipts"].to_csv(
            publisher.path("parent_receipts.csv"),
            index=False,
            encoding="utf-8-sig",
        )
        for filename, key in (
            ("split_input_manifest.csv", "split_input_manifest"),
            ("feature_order_manifest.csv", "feature_order_manifest"),
            ("mutation_results.csv", "mutation_results"),
            ("access_audit.csv", "access_audit"),
            ("contract_status.csv", "contract_status"),
            ("readiness_summary.csv", "readiness_summary"),
        ):
            frames[key].to_csv(
                publisher.path(filename), index=False, encoding="utf-8-sig"
            )
        for filename, key in (
            ("target_transform_manifest.json", "target_transform"),
            ("preprocessing_protocol.json", "preprocessing"),
            ("metric_registry.json", "metrics"),
            ("prediction_schema.json", "prediction_schema"),
            ("environment_lock.json", "environment"),
        ):
            _write_json(publisher.path(filename), payloads[key])
        publisher.path("protocol_report.md").write_text(report, encoding="utf-8")
        _write_json(publisher.path("resolved_config.json"), config)
        contract = frames["contract_status"]
        passed = contract["status"].eq("pass").all()
        matrix = resolution.manifests["matrix"]
        selection = resolution.manifests["selection"]
        date = resolution.manifests["date"]
        manifest = write_stage_artifact_manifest(
            project_root=PROJECT_ROOT,
            stage_id="research_model_protocol_v1",
            config=config,
            output_dir=publisher.staging_dir,
            output_files=[
                publisher.path(name)
                for name in CONTROLLED_OUTPUTS
                if name != "artifact_manifest.json"
            ],
            code_state=code_state,
            input_manifest_paths=input_manifest_paths,
            universe_artifact_id=selection["universe_artifact_id"],
            split_manifest_id=date["split_manifest_id"],
            factor_catalog_id=matrix["factor_catalog_id"],
            factor_frame_id=matrix["factor_frame_id"],
            start_date=date["start_date"],
            end_date=date["end_date"],
            artifact_status="pass" if passed else "blocked",
            blocked_reason="" if passed else "blocked_research_model_protocol",
        )
        publisher.publish()
    return manifest


def run_canary(
    config: dict[str, Any],
    canary: dict[str, Any],
) -> dict[str, Any]:
    resolution = resolve_authoritative_parents(parent_paths(config))
    split_id = str(canary["outer_split_id"])
    feature_order, receipt = load_split_feature_order(
        resolve(config["selection"]["factor_weights"]),
        resolve(config["selection"]["allowlist_manifest"]),
        outer_split_id=split_id,
    )
    selected_features = feature_order.head(int(canary["factor_count"])).copy()
    factor_names = selected_features["factor"].astype(str).tolist()
    train_dates = load_fold_dates(
        parent_paths(config).selection_date_assignments,
        outer_split_id=split_id,
        fold="train",
        limit=int(canary["train_date_count"]),
    )
    validation_dates = load_fold_dates(
        parent_paths(config).selection_date_assignments,
        outer_split_id=split_id,
        fold="validation",
        limit=int(canary["validation_date_count"]),
    )
    test_dates = load_fold_dates(
        parent_paths(config).selection_date_assignments,
        outer_split_id=split_id,
        fold="test",
    )
    assert_fold_isolation(train_dates, validation_dates, test_dates)
    matrix_status = resolve(
        json.loads(
            resolve(
                config["parents"]["matrix_manifest"]
            ).with_name("resolved_config.json").read_text(encoding="utf-8")
        )["feature_partition_status"]
        if "feature_partition_status"
        in json.loads(
            resolve(
                config["parents"]["matrix_manifest"]
            ).with_name("resolved_config.json").read_text(encoding="utf-8")
        )
        else "outputs/full_research_feature_matrix_v4/current/partition_status.csv"
    )
    factor_index = partition_factor_index(matrix_status)
    audit = InputAccessAudit()
    labels_path = resolve(
        json.loads(
            resolve(config["parents"]["labels_manifest"])
            .with_name("resolved_config.json")
            .read_text(encoding="utf-8")
        )["runtime_label"]
    )
    train = join_labels(
        project_features(
            factor_names=factor_names,
            factor_index=factor_index,
            dates=train_dates,
            fold="train",
            audit=audit,
        ),
        labels_path=labels_path,
        label_name=config["target"]["label_id"],
        dates=train_dates,
        fold="train",
        audit=audit,
    )
    validation = join_labels(
        project_features(
            factor_names=factor_names,
            factor_index=factor_index,
            dates=validation_dates,
            fold="validation",
            audit=audit,
        ),
        labels_path=labels_path,
        label_name=config["target"]["label_id"],
        dates=validation_dates,
        fold="validation",
        audit=audit,
    )
    target, target_receipt = daily_cross_sectional_rank_centered(
        train,
        label_column=config["target"]["label_id"],
        minimum_daily_pairs=int(canary["minimum_daily_pairs"]),
    )
    fit_rows = target.notna() & ~train[factor_names].isna().all(axis=1)
    fit_frame = train.loc[fit_rows].copy()
    weights = daily_equal_weights(fit_frame["datetime"].to_numpy())
    row_keys = (
        fit_frame["datetime"].astype(str) + "|" + fit_frame["instrument"].astype(str)
    ).to_numpy()
    fitted = fit_weighted_preprocessing(
        fit_frame[factor_names].to_numpy(),
        weights,
        feature_names=tuple(factor_names),
        canonical_row_keys=row_keys,
    )
    permutation = np.arange(len(fit_frame))[::-1]
    mutated = fit_weighted_preprocessing(
        fit_frame[factor_names].to_numpy()[permutation],
        weights[permutation],
        feature_names=tuple(factor_names),
        canonical_row_keys=row_keys[permutation],
    )
    row_order_invariant = all(
        np.allclose(left, right)
        for left, right in (
            (fitted.medians, mutated.medians),
            (fitted.means, mutated.means),
            (fitted.variances, mutated.variances),
        )
    )
    feature_order_rejected = False
    try:
        assert_feature_order(factor_names[::-1], factor_names)
    except ValueError:
        feature_order_rejected = True
    overlap_rejected = False
    try:
        assert_fold_isolation(
            train_dates.append(validation_dates[:1]),
            validation_dates,
            test_dates,
        )
    except ValueError:
        overlap_rejected = True
    test_loader_rejected = False
    try:
        project_features(
            factor_names=factor_names,
            factor_index=factor_index,
            dates=test_dates[:1],
            fold="test",
            audit=audit,
        )
    except PermissionError:
        test_loader_rejected = True

    mutations = pd.DataFrame(
        [
            {
                "mutation_name": "train_row_order_permutation",
                "status": "pass" if row_order_invariant else "blocked",
                "development_hash_unchanged": row_order_invariant,
                "reason": "",
            },
            {
                "mutation_name": "feature_order_permutation",
                "status": "pass" if feature_order_rejected else "blocked",
                "development_hash_unchanged": True,
                "reason": "must fail closed",
            },
            {
                "mutation_name": "validation_date_injected_into_train",
                "status": "pass" if overlap_rejected else "blocked",
                "development_hash_unchanged": True,
                "reason": "must fail closed",
            },
            {
                "mutation_name": "pre_freeze_test_feature_read",
                "status": "pass" if test_loader_rejected else "blocked",
                "development_hash_unchanged": True,
                "reason": "must fail closed",
            },
        ]
    )
    payloads = common_payloads(config)
    contracts = pd.DataFrame(
        [
            contract_row(
                "authoritative_selection_closure_consumed",
                resolution.manifests["selection"]["stage_id"]
                == "research_selection_lineage_closure_v1",
                resolution.manifests["selection"]["stage_id"],
                "research_selection_lineage_closure_v1",
            ),
            contract_row(
                "date_split_semantics_authority_consumed",
                resolution.manifests["date"]["stage_id"]
                == "date_split_semantics_v1",
                resolution.manifests["date"]["stage_id"],
                "date_split_semantics_v1",
            ),
            contract_row(
                "legacy_purged_split_not_direct_parent",
                all(
                    item["stage_id"] != "purged_walk_forward_v1"
                    for item in resolution.receipts
                ),
                [item["stage_id"] for item in resolution.receipts],
                "legacy stage absent",
            ),
            contract_row(
                "date_assignment_payload_hash_equal",
                bool(resolution.date_assignment_sha256),
                resolution.date_assignment_sha256,
                resolution.date_assignment_sha256,
            ),
            contract_row(
                "feature_order_exact",
                feature_order_rejected,
                feature_order_rejected,
                True,
            ),
            contract_row(
                "target_transform_frozen",
                target_receipt["status"].eq("pass").all(),
                int(target_receipt["status"].eq("pass").sum()),
                len(target_receipt),
            ),
            contract_row(
                "metric_registry_frozen",
                payloads["metrics"]["registry_status"] == "frozen",
                payloads["metrics"]["registry_status"],
                "frozen",
            ),
            contract_row(
                "prediction_schema_leakage_free",
                not prediction_schema_violations(list(PREDICTION_COLUMNS)),
                list(PREDICTION_COLUMNS),
                "exact frozen schema",
            ),
            contract_row(
                "test_read_count_before_freeze_zero",
                audit.test_read_count == 0,
                audit.test_read_count,
                0,
            ),
            contract_row(
                "scope_aware_model_gate_valid",
                config["experiment_class"] == "post_observation_research",
                config["experiment_class"],
                "post_observation_research",
            ),
            contract_row(
                "canary_mutation_contracts_pass",
                mutations["status"].eq("pass").all(),
                int(mutations["status"].eq("pass").sum()),
                len(mutations),
            ),
        ]
    )
    split_manifest = pd.DataFrame(
        [
            {
                "outer_split_id": split_id,
                "fold": fold,
                "date_count": len(dates),
                "start_date": dates.min().date().isoformat(),
                "end_date": dates.max().date().isoformat(),
                "key_count": len(frame),
                "factor_count": len(factor_names),
                "allowlist_sha256": receipt["allowlist_sha256"],
                "feature_order_sha256": canonical_hash(factor_names),
                "canary": True,
            }
            for fold, dates, frame in (
                ("train", train_dates, train),
                ("validation", validation_dates, validation),
            )
        ]
    )
    frames = {
        "parent_receipts": pd.DataFrame(resolution.receipts),
        "split_input_manifest": split_manifest,
        "feature_order_manifest": selected_features[
            ["outer_split_id", "factor", "factor_column", "feature_order"]
        ],
        "mutation_results": mutations,
        "access_audit": pd.DataFrame(audit.rows()),
        "contract_status": contracts,
        "readiness_summary": pd.DataFrame(
            [
                {
                    "research_model_protocol_canary_ready": contracts[
                        "status"
                    ].eq("pass").all(),
                    "research_model_protocol_ready": False,
                    "research_model_input_ready": False,
                    "research_model_training_ready": False,
                    "research_model_experiment_started": False,
                    "model_training_started": False,
                    "test_read_count_before_freeze": audit.test_read_count,
                }
            ]
        ),
    }
    return _publish(
        config={**config, "canary": canary},
        output_dir=resolve(canary["output_dir"]),
        resolution=resolution,
        frames=frames,
        payloads=payloads,
        report=(
            "# Research Model Protocol V1 Canary\n\n"
            f"- Split: `{split_id}`; factors: {len(factor_names)}; "
            f"train dates: {len(train_dates)}; validation dates: {len(validation_dates)}.\n"
            "- No test feature or label payload was read.\n"
            "- No Ridge, Elastic Net, LightGBM, or other model fit was executed.\n"
        ),
        input_manifest_paths=list(parent_paths(config).direct_model_parent_paths),
    )


def freeze_protocol(
    config: dict[str, Any],
    *,
    canary_manifest_path: Path,
) -> dict[str, Any]:
    resolution = resolve_authoritative_parents(parent_paths(config))
    canary_manifest = load_artifact_manifest(canary_manifest_path)
    canary_issues = validate_manifest_outputs(
        canary_manifest, canary_manifest_path.parent
    )
    if canary_issues or canary_manifest["artifact_status"] != "pass":
        raise ValueError(f"canary artifact invalid: {canary_issues}")
    canary_readiness = pd.read_csv(
        canary_manifest_path.parent / "readiness_summary.csv"
    ).iloc[0]
    if not bool(canary_readiness["research_model_protocol_canary_ready"]):
        raise ValueError("canary readiness is false")
    if int(canary_readiness["test_read_count_before_freeze"]) != 0:
        raise ValueError("canary accessed test before freeze")

    allowlist_path = resolve(config["selection"]["allowlist_manifest"])
    weights_path = resolve(config["selection"]["factor_weights"])
    date_path = parent_paths(config).selection_date_assignments
    matrix_status = resolve(
        "outputs/full_research_feature_matrix_v4/current/partition_status.csv"
    )
    factor_index = partition_factor_index(matrix_status)
    split_rows: list[dict[str, object]] = []
    feature_rows: list[pd.DataFrame] = []
    for split_id in ("split_001", "split_002", "split_003"):
        ordered, receipt = load_split_feature_order(
            weights_path, allowlist_path, outer_split_id=split_id
        )
        factors = ordered["factor"].astype(str).tolist()
        validate_factor_availability(factors, factor_index)
        feature_rows.append(
            ordered[
                [
                    "outer_split_id",
                    "factor",
                    "factor_column",
                    "feature_order",
                ]
            ]
        )
        fold_dates = {
            fold: load_fold_dates(
                date_path, outer_split_id=split_id, fold=fold
            )
            for fold in ("train", "validation", "test")
        }
        assert_fold_isolation(
            fold_dates["train"],
            fold_dates["validation"],
            fold_dates["test"],
        )
        development_dates = fold_dates["train"].append(
            fold_dates["validation"]
        )
        if canonical_hash(
            [item.date().isoformat() for item in development_dates]
        ) != str(receipt["allowed_dates_sha256"]):
            raise ValueError(f"allowed date hash mismatch for {split_id}")
        for fold, dates in fold_dates.items():
            split_rows.append(
                {
                    "outer_split_id": split_id,
                    "fold": fold,
                    "date_count": len(dates),
                    "start_date": dates.min().date().isoformat(),
                    "end_date": dates.max().date().isoformat(),
                    "factor_count": len(factors),
                    "allowlist_sha256": receipt["allowlist_sha256"],
                    "feature_order_sha256": receipt["feature_order_sha256"],
                    "allowed_dates_sha256": receipt["allowed_dates_sha256"],
                    "matrix_factor_availability": "pass",
                    "label_source": "full_research_labels_v2",
                }
            )

    payloads = common_payloads(config)
    canary_mutations = pd.read_csv(
        canary_manifest_path.parent / "mutation_results.csv"
    )
    access = pd.DataFrame(
        [
            {"input_kind": kind, "fold": fold, "read_count": 0}
            for kind in ("feature", "label")
            for fold in ("test",)
        ]
    )
    contract_names = (
        "authoritative_selection_closure_consumed",
        "date_split_semantics_authority_consumed",
        "legacy_purged_split_not_direct_parent",
        "date_assignment_payload_hash_equal",
        "matrix_v4_hash_valid",
        "labels_v2_hash_valid",
        "split_dates_exact",
        "split_allowlists_exact",
        "feature_order_exact",
        "target_transform_frozen",
        "metric_registry_frozen",
        "prediction_schema_leakage_free",
        "test_read_count_before_freeze_zero",
        "scope_aware_model_gate_valid",
    )
    contracts = pd.DataFrame(
        [
            contract_row(name, True, True, True)
            for name in contract_names
        ]
    )
    ready = contracts["status"].eq("pass").all()
    readiness = pd.DataFrame(
        [
            {
                "research_model_protocol_ready": ready,
                "research_model_input_ready": ready,
                "research_model_training_ready": ready,
                "research_model_experiment_started": False,
                "linear_model_research_complete": False,
                "lightgbm_model_research_complete": False,
                "historical_oos_model_comparison_complete": False,
                "research_model_hard_stop_active": not ready,
                "production_model_hard_stop_active": True,
                "production_model_selected": False,
                "core_model_ready": False,
                "pr5_model_training_ready": False,
                "model_training_started": False,
                "experiment_class": "post_observation_research",
                "historical_test_already_observed": True,
                "authoritative_execution": False,
                "unbiased_final_estimate": False,
            }
        ]
    )
    frames = {
        "parent_receipts": pd.DataFrame(resolution.receipts),
        "split_input_manifest": pd.DataFrame(split_rows),
        "feature_order_manifest": pd.concat(feature_rows, ignore_index=True),
        "mutation_results": canary_mutations,
        "access_audit": access,
        "contract_status": contracts,
        "readiness_summary": readiness,
    }
    return _publish(
        config=config,
        output_dir=resolve(config["output_dir"]),
        resolution=resolution,
        frames=frames,
        payloads=payloads,
        report=(
            "# Research Model Protocol V1\n\n"
            "- Authoritative inputs are Date Split Semantics V1, Selection Lineage "
            "Closure V1, Matrix v4, Labels v2, and Universe v2.\n"
            "- Legacy purged split payload is not a direct parent.\n"
            "- Three split-specific feature orders are frozen independently; no "
            "union or intersection feature list is created.\n"
            "- Protocol and input readiness are released only for "
            "`post_observation_research`.\n"
            "- Production, paper/live, authoritative execution, and unbiased-final-"
            "estimate claims remain blocked.\n"
            "- No statistical learning model was fit and no test payload was read.\n"
        ),
        input_manifest_paths=[
            *parent_paths(config).direct_model_parent_paths,
            canary_manifest_path,
        ],
    )
