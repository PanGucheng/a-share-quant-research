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
