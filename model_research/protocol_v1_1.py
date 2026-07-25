from __future__ import annotations

import json
import time
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

from .inputs import (
    InputAccessAudit,
    assert_feature_order,
    assert_fold_isolation,
    join_labels,
    load_fold_dates,
    load_split_feature_order,
    project_features,
)
from .lineage import (
    AuthoritativeParentResolution,
    MatrixRuntimeAuthority,
    resolve_authoritative_parents,
    resolve_matrix_runtime_authority,
)
from .preprocessing import daily_equal_weights, fit_weighted_preprocessing
from .protocol import (
    PROJECT_ROOT,
    common_payloads,
    contract_row,
    parent_paths,
    resolve,
)
from .schemas import PREDICTION_COLUMNS, prediction_schema_violations
from .targets import (
    TARGET_TRANSFORM_V2_ID,
    eligible_daily_cross_sectional_rank_centered,
)


STAGE_ID = "research_model_protocol_v1_1"
CONTROLLED_OUTPUTS = (
    "artifact_manifest.json",
    "parent_receipts.csv",
    "protocol_binding.json",
    "split_input_manifest.csv",
    "feature_order_manifest.csv",
    "sample_eligibility_receipt.csv",
    "validation_transform_receipt.csv",
    "partition_source_receipt.csv",
    "superseded_artifacts.csv",
    "target_transform_manifest.json",
    "preprocessing_protocol.json",
    "metric_registry.json",
    "prediction_schema.json",
    "environment_lock.json",
    "mutation_results.csv",
    "access_audit.csv",
    "resource_summary.csv",
    "contract_status.csv",
    "readiness_summary.csv",
    "protocol_report.md",
    "resolved_config.json",
)


def _write_json(path: Path, payload: object) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def build_protocol_binding(
    config: dict[str, Any],
    resolution: AuthoritativeParentResolution,
) -> dict[str, Any]:
    parent_payload = [
        {
            "parent_role": item["parent_role"],
            "stage_id": item["stage_id"],
            "artifact_id": item["artifact_id"],
        }
        for item in sorted(
            resolution.receipts, key=lambda row: str(row["parent_role"])
        )
    ]
    selection_payload = {
        "allowlist_manifest_sha256": file_sha256(
            resolve(config["selection"]["allowlist_manifest"])
        ),
        "factor_weights_sha256": file_sha256(
            resolve(config["selection"]["factor_weights"])
        ),
        "date_assignments_sha256": resolution.date_assignment_sha256,
    }
    policy_sections = {
        name: canonical_hash(config[name])
        for name in (
            "target",
            "preprocessing",
            "validation",
            "linear_model",
            "lightgbm",
        )
    }
    payload = {
        "protocol_closure_version": str(config["protocol_closure_version"]),
        "base_protocol_sha256": canonical_hash(config),
        "parent_artifact_ids_sha256": canonical_hash(parent_payload),
        "selection_input_sha256": canonical_hash(selection_payload),
        "parent_artifacts": parent_payload,
        "selection_inputs": selection_payload,
        "policy_section_sha256": policy_sections,
    }
    payload["binding_sha256"] = canonical_hash(payload)
    return payload


def _labels_runtime_path(
    config: dict[str, Any],
    resolution: AuthoritativeParentResolution,
) -> Path:
    manifest_path = parent_paths(config).labels_manifest
    manifest = resolution.manifests["labels"]
    if "resolved_config.json" not in manifest["output_file_hashes"]:
        raise ValueError("labels manifest does not control resolved_config.json")
    resolved = json.loads(
        manifest_path.with_name("resolved_config.json").read_text(encoding="utf-8")
    )
    path = resolve(resolved["runtime_label"])
    if not path.is_file():
        raise ValueError(f"Labels v2 runtime missing: {path}")
    return path


def _matrix_authority(
    config: dict[str, Any],
    *,
    selected_factors: list[str],
    verify_hashes: bool,
) -> MatrixRuntimeAuthority:
    return resolve_matrix_runtime_authority(
        project_root=PROJECT_ROOT,
        matrix_manifest_path=parent_paths(config).matrix_manifest,
        selected_factors=selected_factors,
        verify_selected_partition_hashes=verify_hashes,
    )


def _publish(
    *,
    config: dict[str, Any],
    output_dir: Path,
    resolution: AuthoritativeParentResolution,
    frames: dict[str, pd.DataFrame],
    payloads: dict[str, Any],
    report: str,
    input_manifest_paths: list[Path],
) -> dict[str, Any]:
    code_state = capture_code_state(PROJECT_ROOT)
    with StageOutputPublisher(output_dir, CONTROLLED_OUTPUTS) as publisher:
        for filename, key in (
            ("parent_receipts.csv", "parent_receipts"),
            ("split_input_manifest.csv", "split_input_manifest"),
            ("feature_order_manifest.csv", "feature_order_manifest"),
            ("sample_eligibility_receipt.csv", "sample_eligibility_receipt"),
            ("validation_transform_receipt.csv", "validation_transform_receipt"),
            ("partition_source_receipt.csv", "partition_source_receipt"),
            ("superseded_artifacts.csv", "superseded_artifacts"),
            ("mutation_results.csv", "mutation_results"),
            ("access_audit.csv", "access_audit"),
            ("resource_summary.csv", "resource_summary"),
            ("contract_status.csv", "contract_status"),
            ("readiness_summary.csv", "readiness_summary"),
        ):
            frames[key].to_csv(
                publisher.path(filename), index=False, encoding="utf-8-sig"
            )
        for filename, key in (
            ("protocol_binding.json", "protocol_binding"),
            ("target_transform_manifest.json", "target_transform"),
            ("preprocessing_protocol.json", "preprocessing"),
            ("metric_registry.json", "metrics"),
            ("prediction_schema.json", "prediction_schema"),
            ("environment_lock.json", "environment"),
        ):
            _write_json(publisher.path(filename), payloads[key])
        publisher.path("protocol_report.md").write_text(report, encoding="utf-8")
        _write_json(publisher.path("resolved_config.json"), config)
        contracts = frames["contract_status"]
        passed = contracts["status"].astype(str).eq("pass").all()
        manifest = write_stage_artifact_manifest(
            project_root=PROJECT_ROOT,
            stage_id=STAGE_ID,
            config=config,
            output_dir=publisher.staging_dir,
            output_files=[
                publisher.path(name)
                for name in CONTROLLED_OUTPUTS
                if name != "artifact_manifest.json"
            ],
            code_state=code_state,
            input_manifest_paths=input_manifest_paths,
            universe_artifact_id=resolution.manifests["selection"][
                "universe_artifact_id"
            ],
            split_manifest_id=resolution.manifests["date"]["split_manifest_id"],
            factor_catalog_id=resolution.manifests["matrix"]["factor_catalog_id"],
            factor_frame_id=resolution.manifests["matrix"]["factor_frame_id"],
            start_date=resolution.manifests["date"]["start_date"],
            end_date=resolution.manifests["date"]["end_date"],
            artifact_status="pass" if passed else "blocked",
            blocked_reason="" if passed else "blocked_research_model_protocol_v1_1",
        )
        publisher.publish()
    return manifest


def run_canary(
    config: dict[str, Any],
    canary: dict[str, Any],
) -> dict[str, Any]:
    started = time.perf_counter()
    resolution = resolve_authoritative_parents(parent_paths(config))
    binding = build_protocol_binding(config, resolution)
    split_id = str(canary["outer_split_id"])
    ordered, allowlist_receipt = load_split_feature_order(
        resolve(config["selection"]["factor_weights"]),
        resolve(config["selection"]["allowlist_manifest"]),
        outer_split_id=split_id,
    )
    selected = ordered.head(int(canary["factor_count"])).copy()
    factors = selected["factor"].astype(str).tolist()
    matrix = _matrix_authority(
        config, selected_factors=factors, verify_hashes=True
    )
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
    audit = InputAccessAudit()
    labels_path = _labels_runtime_path(config, resolution)
    train = join_labels(
        project_features(
            factor_names=factors,
            factor_index=matrix.factor_index,
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
            factor_names=factors,
            factor_index=matrix.factor_index,
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
    train_target, train_eligible, train_receipt = (
        eligible_daily_cross_sectional_rank_centered(
            train,
            label_column=config["target"]["label_id"],
            feature_columns=factors,
            expected_dates=train_dates,
            minimum_daily_pairs=int(canary["minimum_daily_pairs"]),
        )
    )
    _, validation_eligible, validation_receipt = (
        eligible_daily_cross_sectional_rank_centered(
            validation,
            label_column=config["target"]["label_id"],
            feature_columns=factors,
            expected_dates=validation_dates,
            minimum_daily_pairs=int(canary["minimum_daily_pairs"]),
        )
    )
    fit_rows = train_target.notna()
    fit_frame = train.loc[fit_rows].copy()
    weights = daily_equal_weights(fit_frame["datetime"].to_numpy())
    row_keys = (
        fit_frame["datetime"].astype(str)
        + "|"
        + fit_frame["instrument"].astype(str)
    ).to_numpy()
    fitted = fit_weighted_preprocessing(
        fit_frame[factors].to_numpy(),
        weights,
        feature_names=tuple(factors),
        canonical_row_keys=row_keys,
    )
    validation_feature_eligible = (
        validation[factors]
        .replace([np.inf, -np.inf], np.nan)
        .notna()
        .any(axis=1)
    )
    transform_frame = validation.loc[validation_feature_eligible]
    assert_feature_order(list(transform_frame[factors].columns), factors)
    transformed_validation = fitted.transform(
        transform_frame[factors].to_numpy()
    )
    width_valid = transformed_validation.shape[1] == len(factors)
    transform_coverage = float(validation_feature_eligible.mean())
    minimum_transform_coverage = float(
        config["validation"]["minimum_transform_coverage"]
    )

    permutation = np.arange(len(fit_frame))[::-1]
    mutated = fit_weighted_preprocessing(
        fit_frame[factors].to_numpy()[permutation],
        weights[permutation],
        feature_names=tuple(factors),
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
        assert_feature_order(factors[::-1], factors)
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
            factor_names=factors,
            factor_index=matrix.factor_index,
            dates=test_dates[:1],
            fold="test",
            audit=audit,
        )
    except PermissionError:
        test_loader_rejected = True

    mutations = pd.DataFrame(
        [
            {
                "mutation_name": name,
                "status": "pass" if passed else "blocked",
                "development_hash_unchanged": invariant,
                "reason": reason,
            }
            for name, passed, invariant, reason in (
                (
                    "train_row_order_permutation",
                    row_order_invariant,
                    row_order_invariant,
                    "",
                ),
                (
                    "feature_order_permutation",
                    feature_order_rejected,
                    True,
                    "must fail closed",
                ),
                (
                    "validation_date_injected_into_train",
                    overlap_rejected,
                    True,
                    "must fail closed",
                ),
                (
                    "pre_freeze_test_feature_read",
                    test_loader_rejected,
                    True,
                    "must fail closed",
                ),
            )
        ]
    )
    payloads = common_payloads(config)
    payloads["target_transform"]["target_transform_id"] = TARGET_TRANSFORM_V2_ID
    payloads["protocol_binding"] = binding
    eligibility = pd.concat(
        [
            train_receipt.assign(outer_split_id=split_id, fold="train"),
            validation_receipt.assign(
                outer_split_id=split_id, fold="validation"
            ),
        ],
        ignore_index=True,
    )[
        [
            "outer_split_id",
            "fold",
            "datetime",
            "valid_pair_count",
            "status",
        ]
    ]
    validation_transform = pd.DataFrame(
        [
            {
                "outer_split_id": split_id,
                "factor_count": len(factors),
                "input_row_count": len(validation),
                "feature_eligible_row_count": int(
                    validation_feature_eligible.sum()
                ),
                "all_nan_row_count": int(
                    (~validation_feature_eligible).sum()
                ),
                "label_and_feature_eligible_row_count": int(
                    validation_eligible.sum()
                ),
                "output_row_count": transformed_validation.shape[0],
                "output_feature_count": transformed_validation.shape[1],
                "feature_order_valid": True,
                "transform_coverage": transform_coverage,
                "minimum_transform_coverage": minimum_transform_coverage,
                "status": (
                    "pass"
                    if width_valid
                    and transform_coverage >= minimum_transform_coverage
                    else "blocked"
                ),
            }
        ]
    )
    partition_receipts = pd.DataFrame(matrix.partition_receipts)
    selected_paths = {matrix.factor_index[name].as_posix() for name in factors}
    partition_receipts = partition_receipts.loc[
        partition_receipts["partition_path"].isin(selected_paths)
    ].reset_index(drop=True)
    matrix_hashes_valid = (
        not partition_receipts.empty
        and partition_receipts["hash_verified"].astype(bool).all()
    )
    target_exact = (
        len(eligibility) == len(train_dates) + len(validation_dates)
        and int(train_eligible.sum()) >= int(train_target.notna().sum())
    )
    validation_ready = validation_transform["status"].eq("pass").all()
    contracts = pd.DataFrame(
        [
            contract_row(
                "canary_protocol_binding_valid",
                bool(binding["binding_sha256"]),
                binding["binding_sha256"],
                "non-empty canonical binding",
            ),
            contract_row(
                "sample_eligibility_exact",
                target_exact,
                {
                    "receipt_dates": len(eligibility),
                    "train_eligible_rows": int(train_eligible.sum()),
                    "train_fit_rows": int(train_target.notna().sum()),
                },
                {
                    "receipt_dates": len(train_dates) + len(validation_dates),
                    "rank_within_final_eligible_sample": True,
                },
            ),
            contract_row(
                "validation_transform_ready",
                validation_ready,
                validation_transform.iloc[0].to_dict(),
                {
                    "minimum_transform_coverage": minimum_transform_coverage,
                    "feature_order_and_width_exact": True,
                },
            ),
            contract_row(
                "matrix_runtime_authority_valid",
                matrix_hashes_valid,
                partition_receipts[
                    [
                        "batch_id",
                        "recorded_sha256",
                        "observed_sha256",
                        "hash_verified",
                    ]
                ].to_dict("records"),
                "all selected partitions hash-verified",
            ),
            contract_row(
                "test_read_count_before_freeze_zero",
                audit.test_read_count == int(canary["test_read_budget"]),
                audit.test_read_count,
                int(canary["test_read_budget"]),
            ),
            contract_row(
                "canary_mutation_contracts_pass",
                mutations["status"].eq("pass").all(),
                int(mutations["status"].eq("pass").sum()),
                len(mutations),
            ),
        ]
    )
    ready = contracts["status"].eq("pass").all()
    frames = {
        "parent_receipts": pd.DataFrame(resolution.receipts),
        "split_input_manifest": pd.DataFrame(
            [
                {
                    "outer_split_id": split_id,
                    "fold": fold,
                    "date_count": len(dates),
                    "start_date": dates.min().date().isoformat(),
                    "end_date": dates.max().date().isoformat(),
                    "key_count": len(frame),
                    "factor_count": len(factors),
                    "allowlist_sha256": allowlist_receipt["allowlist_sha256"],
                    "feature_order_sha256": canonical_hash(factors),
                    "canary": True,
                }
                for fold, dates, frame in (
                    ("train", train_dates, train),
                    ("validation", validation_dates, validation),
                )
            ]
        ),
        "feature_order_manifest": selected[
            ["outer_split_id", "factor", "factor_column", "feature_order"]
        ],
        "sample_eligibility_receipt": eligibility,
        "validation_transform_receipt": validation_transform,
        "partition_source_receipt": partition_receipts,
        "superseded_artifacts": pd.DataFrame(
            columns=[
                "artifact_id",
                "stage_id",
                "disposition",
                "reason",
            ]
        ),
        "mutation_results": mutations,
        "access_audit": pd.DataFrame(audit.rows()),
        "resource_summary": pd.DataFrame(
            [
                {
                    "stage": "canary",
                    "runtime_seconds": time.perf_counter() - started,
                    "runtime_parquet_committed": False,
                    "model_fit_count": 0,
                    "test_read_count": audit.test_read_count,
                }
            ]
        ),
        "contract_status": contracts,
        "readiness_summary": pd.DataFrame(
            [
                {
                    "protocol_closure_version": "1.1",
                    "research_model_protocol_canary_ready": ready,
                    "research_model_protocol_ready": False,
                    "research_model_input_protocol_ready": ready,
                    "research_model_input_ready": False,
                    "research_model_training_ready": False,
                    "research_model_hard_stop_active": True,
                    "production_model_hard_stop_active": True,
                    "production_model_selected": False,
                    "research_model_experiment_started": False,
                    "model_training_started": False,
                    "experiment_class": "post_observation_research",
                    "historical_test_already_observed": True,
                    "authoritative_execution": False,
                    "unbiased_final_estimate": False,
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
            "# Research Model Protocol V1.1 Canary\n\n"
            f"- `{split_id}`; {len(factors)} factors; {len(train_dates)} train "
            f"dates; {len(validation_dates)} validation dates.\n"
            "- Target ranks are computed only inside the final eligible sample.\n"
            "- Validation is transformed by train-only preprocessing.\n"
            "- Test feature and label payload reads: 0. Model fits: 0.\n"
        ),
        input_manifest_paths=list(parent_paths(config).direct_model_parent_paths),
    )


def validate_canary_binding(
    *,
    config: dict[str, Any],
    resolution: AuthoritativeParentResolution,
    canary_manifest_path: Path,
) -> dict[str, Any]:
    manifest = load_artifact_manifest(canary_manifest_path)
    issues = validate_manifest_outputs(manifest, canary_manifest_path.parent)
    if issues or manifest.get("stage_id") != STAGE_ID:
        raise ValueError(f"invalid V1.1 canary artifact: {issues}")
    observed = json.loads(
        (canary_manifest_path.parent / "protocol_binding.json").read_text(
            encoding="utf-8"
        )
    )
    expected = build_protocol_binding(config, resolution)
    if observed != expected:
        raise ValueError(
            "canary protocol binding differs from current base protocol"
        )
    return expected


def freeze_protocol(
    config: dict[str, Any],
    *,
    canary_manifest_path: Path,
    dry_run_manifest_path: Path,
    superseded_manifest_path: Path,
) -> dict[str, Any]:
    resolution = resolve_authoritative_parents(parent_paths(config))
    binding = validate_canary_binding(
        config=config,
        resolution=resolution,
        canary_manifest_path=canary_manifest_path,
    )
    dry_manifest = load_artifact_manifest(dry_run_manifest_path)
    dry_issues = validate_manifest_outputs(
        dry_manifest, dry_run_manifest_path.parent
    )
    if (
        dry_issues
        or dry_manifest.get("stage_id") != STAGE_ID
        or dry_manifest.get("artifact_status") != "pass"
        or dry_manifest.get("lineage_status") != "complete"
        or bool(dry_manifest.get("code_dirty"))
    ):
        raise ValueError(f"invalid development dry-run artifact: {dry_issues}")
    observed_dry_binding = json.loads(
        (dry_run_manifest_path.parent / "protocol_binding.json").read_text(
            encoding="utf-8"
        )
    )
    if observed_dry_binding != binding:
        raise ValueError("development dry-run binding differs from current protocol")
    dry_contracts = pd.read_csv(
        dry_run_manifest_path.parent / "contract_status.csv"
    )
    dry_contract_map = dry_contracts.set_index("check_name")["status"].to_dict()
    if dry_contract_map.get("development_dry_run_ready") != "pass":
        raise ValueError("full development dry-run is not ready")
    dry_readiness = pd.read_csv(
        dry_run_manifest_path.parent / "readiness_summary.csv"
    )
    if len(dry_readiness) != 1 or not bool(
        dry_readiness.iloc[0]["development_dry_run_ready"]
    ):
        raise ValueError("development dry-run readiness is false")

    superseded = load_artifact_manifest(superseded_manifest_path)
    superseded_issues = validate_manifest_outputs(
        superseded, superseded_manifest_path.parent
    )
    if superseded_issues:
        raise ValueError(f"superseded V1 artifact is invalid: {superseded_issues}")

    split_inputs = pd.read_csv(
        dry_run_manifest_path.parent / "split_input_manifest.csv"
    )
    feature_order = pd.read_csv(
        dry_run_manifest_path.parent / "feature_order_manifest.csv"
    )
    eligibility = pd.read_csv(
        dry_run_manifest_path.parent / "sample_eligibility_receipt.csv"
    )
    validation = pd.read_csv(
        dry_run_manifest_path.parent / "validation_transform_receipt.csv"
    )
    partitions = pd.read_csv(
        dry_run_manifest_path.parent / "partition_source_receipt.csv"
    )
    access = pd.read_csv(dry_run_manifest_path.parent / "access_audit.csv")
    resources = pd.read_csv(
        dry_run_manifest_path.parent / "resource_summary.csv"
    )
    mutations = pd.read_csv(canary_manifest_path.parent / "mutation_results.csv")
    allowlists = pd.read_csv(resolve(config["selection"]["allowlist_manifest"]))
    expected_split_ids = [str(item) for item in config["development_dry_run"]["split_ids"]]

    split_hashes_valid = True
    split_observed: list[dict[str, object]] = []
    for split_id in expected_split_ids:
        expected = allowlists.loc[
            allowlists["outer_split_id"].astype(str).eq(split_id)
        ]
        observed = split_inputs.loc[
            split_inputs["outer_split_id"].astype(str).eq(split_id)
        ]
        if len(expected) != 1 or len(observed) != 2:
            split_hashes_valid = False
            continue
        expected_row = expected.iloc[0]
        current = {
            "outer_split_id": split_id,
            "factor_count": int(observed["factor_count"].iloc[0]),
            "allowlist_sha256": str(observed["allowlist_sha256"].iloc[0]),
            "feature_order_sha256": str(
                observed["feature_order_sha256"].iloc[0]
            ),
        }
        split_observed.append(current)
        split_hashes_valid = split_hashes_valid and (
            current["factor_count"] == int(expected_row["factor_count"])
            and current["allowlist_sha256"]
            == str(expected_row["allowlist_sha256"])
            and current["feature_order_sha256"]
            == str(expected_row["feature_order_sha256"])
        )
    date_assignments = pd.read_csv(
        parent_paths(config).selection_date_assignments
    )
    expected_date_count = int(
        date_assignments.loc[
            date_assignments["split_id"].astype(str).isin(expected_split_ids)
            & date_assignments["fold"]
            .astype(str)
            .isin(["train", "validation"])
        ].shape[0]
    )
    sample_exact = (
        len(eligibility) == expected_date_count
        and eligibility["datetime"].notna().all()
        and eligibility["status"].astype(str).eq("pass").all()
    )
    validation_ready = (
        set(validation["outer_split_id"].astype(str)) == set(expected_split_ids)
        and validation["status"].astype(str).eq("pass").all()
        and (
            pd.to_numeric(validation["transform_coverage"])
            >= float(config["validation"]["minimum_transform_coverage"])
        ).all()
    )
    matrix_ready = (
        not partitions.empty
        and partitions["hash_verified"].astype(bool).all()
        and partitions["observed_sha256"].astype(str).eq(
            partitions["recorded_sha256"].astype(str)
        ).all()
    )
    test_reads = int(
        pd.to_numeric(
            access.loc[access["fold"].astype(str).eq("test"), "read_count"]
        ).sum()
    )
    parent_stages = [str(item["stage_id"]) for item in resolution.receipts]
    matrix_issues = validate_manifest_outputs(
        resolution.manifests["matrix"], parent_paths(config).matrix_manifest.parent
    )
    labels_issues = validate_manifest_outputs(
        resolution.manifests["labels"], parent_paths(config).labels_manifest.parent
    )
    policy_valid = (
        config["linear_model"]["solver_auto"] == "forbidden"
        and config["lightgbm"]["early_stopping"] is False
        and config["lightgbm"]["boosting_round_checkpoints"]
        == [100, 200, 400, 800]
    )
    contracts = pd.DataFrame(
        [
            contract_row(
                "manifest_bound_entry_gate_valid",
                config["stage_id"] == STAGE_ID
                and str(config["protocol_closure_version"]) == "1.1",
                {
                    "stage_id": config["stage_id"],
                    "protocol_closure_version": config[
                        "protocol_closure_version"
                    ],
                    "entry_type": "artifact_manifest_only",
                },
                {
                    "stage_id": STAGE_ID,
                    "protocol_closure_version": "1.1",
                    "entry_type": "artifact_manifest_only",
                },
            ),
            contract_row(
                "authoritative_selection_closure_consumed",
                "research_selection_lineage_closure_v1" in parent_stages,
                parent_stages,
                "research_selection_lineage_closure_v1 present",
            ),
            contract_row(
                "date_split_semantics_authority_consumed",
                "date_split_semantics_v1" in parent_stages,
                parent_stages,
                "date_split_semantics_v1 present",
            ),
            contract_row(
                "legacy_purged_split_not_direct_parent",
                "purged_walk_forward_v1" not in parent_stages,
                parent_stages,
                "legacy stage absent",
            ),
            contract_row(
                "date_assignment_payload_hash_equal",
                bool(resolution.date_assignment_sha256),
                resolution.date_assignment_sha256,
                resolution.date_assignment_sha256,
            ),
            contract_row(
                "canary_protocol_binding_valid",
                observed_dry_binding == binding,
                binding["binding_sha256"],
                binding["binding_sha256"],
            ),
            contract_row(
                "matrix_v4_hash_valid",
                not matrix_issues,
                [issue.reason for issue in matrix_issues],
                [],
            ),
            contract_row(
                "labels_v2_hash_valid",
                not labels_issues,
                [issue.reason for issue in labels_issues],
                [],
            ),
            contract_row(
                "split_allowlists_exact",
                split_hashes_valid,
                split_observed,
                [
                    {
                        "outer_split_id": row.outer_split_id,
                        "factor_count": int(row.factor_count),
                        "allowlist_sha256": row.allowlist_sha256,
                        "feature_order_sha256": row.feature_order_sha256,
                    }
                    for row in allowlists.loc[
                        allowlists["outer_split_id"].astype(str).isin(
                            expected_split_ids
                        )
                    ].itertuples(index=False)
                ],
            ),
            contract_row(
                "sample_eligibility_exact",
                sample_exact,
                {
                    "receipt_date_count": len(eligibility),
                    "all_dates_pass": eligibility["status"]
                    .astype(str)
                    .eq("pass")
                    .all(),
                },
                {
                    "receipt_date_count": expected_date_count,
                    "all_dates_pass": True,
                },
            ),
            contract_row(
                "validation_transform_ready",
                validation_ready,
                validation[
                    ["outer_split_id", "transform_coverage", "status"]
                ].to_dict("records"),
                "all three split transforms pass",
            ),
            contract_row(
                "matrix_runtime_authority_valid",
                matrix_ready,
                partitions[
                    ["batch_id", "hash_verified", "observed_sha256"]
                ].to_dict("records"),
                "all selected partitions hash-verified",
            ),
            contract_row(
                "development_dry_run_ready",
                dry_contract_map.get("development_dry_run_ready") == "pass",
                dry_contract_map.get("development_dry_run_ready"),
                "pass",
            ),
            contract_row(
                "target_transform_frozen",
                config["target"]["training_transform"]
                == "daily_cross_sectional_rank_centered_v2",
                config["target"]["training_transform"],
                "daily_cross_sectional_rank_centered_v2",
            ),
            contract_row(
                "metric_and_model_policy_frozen",
                policy_valid,
                {
                    "solver_auto": config["linear_model"]["solver_auto"],
                    "early_stopping": config["lightgbm"]["early_stopping"],
                    "checkpoints": config["lightgbm"][
                        "boosting_round_checkpoints"
                    ],
                },
                {
                    "solver_auto": "forbidden",
                    "early_stopping": False,
                    "checkpoints": [100, 200, 400, 800],
                },
            ),
            contract_row(
                "test_read_count_before_freeze_zero",
                test_reads == 0,
                test_reads,
                0,
            ),
        ]
    )
    ready = contracts["status"].eq("pass").all()
    payloads = common_payloads(config)
    payloads["target_transform"]["target_transform_id"] = (
        TARGET_TRANSFORM_V2_ID
    )
    payloads["protocol_binding"] = binding
    frames = {
        "parent_receipts": pd.DataFrame(resolution.receipts),
        "split_input_manifest": split_inputs,
        "feature_order_manifest": feature_order,
        "sample_eligibility_receipt": eligibility,
        "validation_transform_receipt": validation,
        "partition_source_receipt": partitions,
        "superseded_artifacts": pd.DataFrame(
            [
                {
                    "artifact_id": superseded["artifact_id"],
                    "stage_id": superseded["stage_id"],
                    "disposition": "superseded_for_model_entry",
                    "reason": (
                        "V1 entry was CSV-based and lacked exact canary/config "
                        "binding and development dry-run closure."
                    ),
                }
            ]
        ),
        "mutation_results": mutations,
        "access_audit": access,
        "resource_summary": resources,
        "contract_status": contracts,
        "readiness_summary": pd.DataFrame(
            [
                {
                    "protocol_closure_version": "1.1",
                    "research_model_protocol_ready": ready,
                    "research_model_input_protocol_ready": ready,
                    "research_model_input_ready": ready,
                    "research_model_training_ready": ready,
                    "research_model_hard_stop_active": not ready,
                    "production_model_hard_stop_active": True,
                    "production_model_selected": False,
                    "research_model_experiment_started": False,
                    "linear_model_research_complete": False,
                    "lightgbm_model_research_complete": False,
                    "historical_oos_model_comparison_complete": False,
                    "core_model_ready": False,
                    "pr5_model_training_ready": False,
                    "model_training_started": False,
                    "experiment_class": "post_observation_research",
                    "historical_test_already_observed": True,
                    "authoritative_execution": False,
                    "unbiased_final_estimate": False,
                    "development_dry_run_ready": ready,
                    "test_read_count_before_freeze": test_reads,
                }
            ]
        ),
    }
    return _publish(
        config=config,
        output_dir=resolve(config["output_dir"]),
        resolution=resolution,
        frames=frames,
        payloads=payloads,
        report=(
            "# Research Model Protocol V1.1 Closure\n\n"
            "- Model entry is bound to this artifact manifest; direct readiness "
            "CSV entry is forbidden.\n"
            "- Canary and full freeze share exact protocol, parent and selection "
            "bindings.\n"
            "- Target ranks are calculated inside final eligible samples.\n"
            "- All three full development splits passed train-only preprocessing "
            "and validation transform dry-runs.\n"
            "- V1 is superseded for model entry. Test reads: 0. Model fits: 0.\n"
        ),
        input_manifest_paths=[
            *parent_paths(config).direct_model_parent_paths,
            canary_manifest_path,
            dry_run_manifest_path,
            superseded_manifest_path,
        ],
    )
