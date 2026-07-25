from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml

from research_validation.feature_matrix import canonical_hash, file_sha256
from research_validation.lineage import (
    capture_code_state,
    load_artifact_manifest,
    write_stage_artifact_manifest,
)
from research_validation.stage_output import StageOutputPublisher

from .gates import assert_research_model_entry_artifact
from .freeze import capture_environment_lock
from .inputs import (
    InputAccessAudit,
    assert_fold_isolation,
    join_labels,
    load_fold_dates,
    load_split_feature_order,
    project_features,
)
from .lineage import resolve_authoritative_parents
from .linear_models import _MemorySampler, _contract
from .preprocessing import daily_equal_weights, fit_weighted_preprocessing
from .protocol import PROJECT_ROOT, parent_paths, resolve
from .protocol_v1_1 import _labels_runtime_path, _matrix_authority
from .targets import eligible_daily_cross_sectional_rank_centered


STAGE_ID = "research_lightgbm_v1"
CANARY_OUTPUTS = (
    "artifact_manifest.json",
    "resolved_config.json",
    "parent_receipts.csv",
    "hyperparameter_candidate_manifest.csv",
    "canary_results.csv",
    "access_audit.csv",
    "resource_summary.csv",
    "contract_status.csv",
    "readiness_summary.csv",
    "run_report.md",
)


def load_lightgbm_config(path: Path) -> dict[str, Any]:
    config = yaml.safe_load(path.read_text(encoding="utf-8"))
    if config.get("stage_id") != STAGE_ID:
        raise ValueError("unexpected LightGBM stage")
    if config.get("experiment_class") != "post_observation_research":
        raise ValueError("LightGBM must be post_observation_research")
    if config.get("early_stopping") is not False:
        raise ValueError("LightGBM early stopping is forbidden")
    if config.get("trainer_metric_authority") != "diagnostic_only":
        raise ValueError("LightGBM L2 metric must be diagnostic only")
    if config.get("official_selection_metric") != "mean_daily_rank_ic":
        raise ValueError("LightGBM selection metric is not frozen")
    if config.get("boosting_round_checkpoints") != [100, 200, 400, 800]:
        raise ValueError("LightGBM checkpoints are not frozen")
    rows = config.get("structural_rows", [])
    if len(rows) != 4 or len({row["structural_row_id"] for row in rows}) != 4:
        raise ValueError("LightGBM requires four unique structural rows")
    if len(rows) * len(config["boosting_round_checkpoints"]) != int(
        config["maximum_candidates_per_split"]
    ):
        raise ValueError("LightGBM candidate count is not 16")
    if int(config["determinism"]["num_threads"]) != 1:
        raise ValueError("LightGBM num_threads must be one")
    if int(config["resources"]["threads"]) != 1:
        raise ValueError("LightGBM resource threads must be one")
    return config


def candidate_grid(config: dict[str, Any]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for structural in config["structural_rows"]:
        for checkpoint in config["boosting_round_checkpoints"]:
            candidate = {
                **structural,
                "method": "lightgbm",
                "num_boost_round": int(checkpoint),
            }
            candidate["candidate_sha256"] = canonical_hash(candidate)
            candidates.append(candidate)
    return candidates


def _array_hash(value: np.ndarray) -> str:
    array = np.ascontiguousarray(np.asarray(value))
    digest = hashlib.sha256()
    digest.update(str(array.dtype).encode("ascii"))
    digest.update(str(array.shape).encode("ascii"))
    digest.update(array.tobytes())
    return digest.hexdigest()


def _training_sample(
    config: dict[str, Any],
    *,
    scope_key: str,
) -> tuple[
    np.ndarray,
    np.ndarray,
    np.ndarray,
    tuple[str, ...],
    InputAccessAudit,
    list[dict[str, object]],
]:
    protocol_config = yaml.safe_load(
        resolve(config["protocol_config"]).read_text(encoding="utf-8")
    )
    resolution = resolve_authoritative_parents(parent_paths(protocol_config))
    canary = config[scope_key]
    split_id = str(canary["split_id"])
    ordered, _ = load_split_feature_order(
        resolve(protocol_config["selection"]["factor_weights"]),
        resolve(protocol_config["selection"]["allowlist_manifest"]),
        outer_split_id=split_id,
    )
    factors = tuple(
        ordered["factor"].astype(str).tolist()[: int(canary["factor_count"])]
    )
    matrix = _matrix_authority(
        protocol_config,
        selected_factors=list(factors),
        verify_hashes=True,
    )
    dates = load_fold_dates(
        parent_paths(protocol_config).selection_date_assignments,
        outer_split_id=split_id,
        fold="train",
        limit=int(canary["train_date_count"]),
    )
    validation_dates = load_fold_dates(
        parent_paths(protocol_config).selection_date_assignments,
        outer_split_id=split_id,
        fold="validation",
    )
    test_dates = load_fold_dates(
        parent_paths(protocol_config).selection_date_assignments,
        outer_split_id=split_id,
        fold="test",
    )
    assert_fold_isolation(dates, validation_dates, test_dates)
    audit = InputAccessAudit()
    joined = join_labels(
        project_features(
            factor_names=list(factors),
            factor_index=matrix.factor_index,
            dates=dates,
            fold="train",
            audit=audit,
        ),
        labels_path=_labels_runtime_path(protocol_config, resolution),
        label_name=protocol_config["target"]["label_id"],
        dates=dates,
        fold="train",
        audit=audit,
    )
    target, _, receipt = eligible_daily_cross_sectional_rank_centered(
        joined,
        label_column=protocol_config["target"]["label_id"],
        feature_columns=list(factors),
        expected_dates=dates,
        minimum_daily_pairs=int(
            protocol_config["target"]["minimum_daily_pairs"]
        ),
    )
    eligible = target.notna()
    selected = joined.loc[eligible].reset_index(drop=True)
    weights = daily_equal_weights(selected["datetime"].to_numpy())
    keys = (
        selected["datetime"].astype(str)
        + "|"
        + selected["instrument"].astype(str)
    ).to_numpy()
    preprocessing = fit_weighted_preprocessing(
        selected[list(factors)].to_numpy(dtype=float),
        weights,
        feature_names=factors,
        canonical_row_keys=keys,
    )
    features = preprocessing.transform(
        selected[list(factors)].to_numpy(dtype=float)
    )
    selected_paths = {matrix.factor_index[factor] for factor in factors}
    partition_receipts = [
        row
        for row in matrix.partition_receipts
        if Path(str(row["partition_path"])) in selected_paths
    ]
    if audit.test_read_count:
        raise AssertionError("LightGBM canary read test payload")
    if not receipt["status"].eq("pass").all():
        raise ValueError("LightGBM canary sample eligibility failed")
    return (
        features,
        target.loc[eligible].to_numpy(dtype=float),
        weights,
        factors,
        audit,
        partition_receipts,
    )


def _training_params(
    config: dict[str, Any], candidate: dict[str, Any]
) -> dict[str, Any]:
    return {
        "objective": config["objective"],
        "metric": config["trainer_metric"],
        "boosting_type": config["boosting_type"],
        "verbosity": -1,
        "feature_pre_filter": False,
        **{
            key: candidate[key]
            for key in (
                "num_leaves",
                "max_depth",
                "min_data_in_leaf",
                "learning_rate",
                "lambda_l1",
                "lambda_l2",
                "feature_fraction",
                "bagging_fraction",
                "bagging_freq",
            )
        },
        **config["determinism"],
    }


def run_lightgbm_canary(
    config: dict[str, Any],
    *,
    output_dir: Path,
    command: str,
    resource_canary: bool = False,
) -> dict[str, Any]:
    import lightgbm as lgb

    protocol_manifest_path = resolve(config["protocol_manifest"])
    assert_research_model_entry_artifact(
        protocol_manifest_path,
        experiment_class=str(config["experiment_class"]),
        operation="canary",
    )
    linear_manifest_path = resolve(config["linear_model_manifest"])
    linear_manifest = load_artifact_manifest(linear_manifest_path)
    if (
        linear_manifest.get("artifact_status") != "pass"
        or linear_manifest.get("lineage_status") != "complete"
    ):
        raise ValueError("LightGBM requires complete/pass linear research")
    code_state = capture_code_state(PROJECT_ROOT)
    if code_state.dirty:
        raise ValueError("LightGBM canary requires clean committed code")
    expected_environment = json.loads(
        resolve(
            "outputs/research_model_protocol_v1_1/current/environment_lock.json"
        ).read_text(encoding="utf-8")
    )
    actual_environment = capture_environment_lock(
        qlib_commit_sha=str(expected_environment["qlib_commit_sha"])
    )
    if actual_environment != expected_environment:
        raise ValueError("LightGBM canary environment differs from frozen lock")
    prior_canary: tuple[str, Path, dict[str, Any]] | None = None
    if resource_canary:
        prior_path = resolve(
            "outputs/research_lightgbm_v1/canary/artifact_manifest.json"
        )
        prior_manifest = load_artifact_manifest(prior_path)
        if (
            prior_manifest.get("artifact_status") != "pass"
            or prior_manifest.get("lineage_status") != "complete"
        ):
            raise ValueError(
                "resource canary requires complete/pass train-only canary"
            )
        prior_canary = (
            "lightgbm_train_only_canary",
            prior_path,
            prior_manifest,
        )

    grid = candidate_grid(config)
    scope_key = "resource_canary" if resource_canary else "canary"
    scope = config[scope_key]
    canary_ids = set(scope["structural_row_ids"])
    checkpoints = (
        {int(value) for value in scope["checkpoints"]}
        if resource_canary
        else {int(scope["checkpoint"])}
    )
    canary_candidates = [
        row
        for row in grid
        if row["structural_row_id"] in canary_ids
        and int(row["num_boost_round"]) in checkpoints
    ]
    expected_candidates = 16 if resource_canary else 2
    if len(canary_candidates) != expected_candidates:
        raise ValueError(
            "LightGBM canary candidate scope mismatch: "
            f"{len(canary_candidates)} != {expected_candidates}"
        )
    features, target, weights, factors, audit, partitions = (
        _training_sample(config, scope_key=scope_key)
    )
    dataset = lgb.Dataset(
        features,
        label=target,
        weight=weights,
        feature_name=list(factors),
        free_raw_data=False,
    )
    results: list[dict[str, Any]] = []
    with _MemorySampler() as memory:
        for candidate in canary_candidates:
            for repeat in range(int(scope["repeats"])):
                started = time.perf_counter()
                booster = lgb.train(
                    _training_params(config, candidate),
                    dataset,
                    num_boost_round=int(candidate["num_boost_round"]),
                )
                prediction = booster.predict(
                    features,
                    num_iteration=int(candidate["num_boost_round"]),
                )
                model_text = booster.model_to_string(
                    num_iteration=int(candidate["num_boost_round"])
                )
                results.append(
                    {
                        "candidate_sha256": candidate["candidate_sha256"],
                        "structural_row_id": candidate["structural_row_id"],
                        "num_boost_round": candidate["num_boost_round"],
                        "repeat": repeat,
                        "model_text_sha256": hashlib.sha256(
                            model_text.encode("utf-8")
                        ).hexdigest(),
                        "prediction_sha256": _array_hash(prediction),
                        "prediction_finite": bool(
                            np.isfinite(prediction).all()
                        ),
                        "wall_seconds": time.perf_counter() - started,
                    }
                )
    result_frame = pd.DataFrame(results)
    reproducible = bool(
        result_frame.groupby("candidate_sha256")[
            ["model_text_sha256", "prediction_sha256"]
        ].nunique().eq(1).all().all()
    )
    peak_rss = float(memory.peak_mb)
    contracts = pd.DataFrame(
        [
            _contract("candidate_manifest_16", len(grid) == 16, len(grid), 16),
            _contract(
                "canary_candidate_scope",
                len(canary_candidates) == expected_candidates,
                len(canary_candidates),
                expected_candidates,
            ),
            _contract(
                "repeated_hashes_stable",
                reproducible,
                reproducible,
                True,
            ),
            _contract(
                "predictions_finite",
                bool(result_frame["prediction_finite"].all()),
                bool(result_frame["prediction_finite"].all()),
                True,
            ),
            _contract(
                "test_read_before_freeze",
                audit.test_read_count == 0,
                audit.test_read_count,
                0,
            ),
            _contract(
                "peak_rss_within_budget",
                peak_rss <= float(config["resources"]["peak_rss_mib"]),
                peak_rss,
                config["resources"]["peak_rss_mib"],
            ),
            _contract(
                "environment_lock_matches",
                actual_environment == expected_environment,
                actual_environment["environment_lock_sha256"],
                expected_environment["environment_lock_sha256"],
            ),
        ]
    )
    if not contracts["status"].eq("pass").all():
        raise ValueError("LightGBM canary contracts failed")
    parent_items = [
        (
            "research_model_protocol_v1_1",
            protocol_manifest_path,
            load_artifact_manifest(protocol_manifest_path),
        ),
        (
            "research_linear_models_v1",
            linear_manifest_path,
            linear_manifest,
        ),
    ]
    if prior_canary is not None:
        parent_items.append(prior_canary)
    parent_receipts = pd.DataFrame(
        [
            {
                "parent_role": role,
                "manifest_path": path.as_posix(),
                "artifact_id": manifest["artifact_id"],
                "artifact_status": manifest["artifact_status"],
                "lineage_status": manifest["lineage_status"],
                "direct_parent": True,
            }
            for role, path, manifest in parent_items
        ]
    )
    resolved_config = {
        **config,
        "executed_command": command,
        "executed_scope": scope_key,
        "feature_order": list(factors),
        "feature_order_sha256": canonical_hash(list(factors)),
        "partition_receipts_sha256": canonical_hash(partitions),
        "lightgbm_version": lgb.__version__,
        "environment_lock": actual_environment,
        "source_sha256": file_sha256(Path(__file__)),
        "output_dir": output_dir.as_posix(),
    }
    with StageOutputPublisher(output_dir, CANARY_OUTPUTS) as publisher:
        pd.DataFrame(grid).to_csv(
            publisher.path("hyperparameter_candidate_manifest.csv"),
            index=False,
        )
        result_frame.to_csv(
            publisher.path("canary_results.csv"), index=False
        )
        pd.DataFrame(audit.rows()).to_csv(
            publisher.path("access_audit.csv"), index=False
        )
        pd.DataFrame(
            [
                {
                    "peak_rss_mib": peak_rss,
                    "sample_rows": len(features),
                    "factor_count": len(factors),
                    "candidate_runs": len(result_frame),
                    "threads": config["resources"]["threads"],
                }
            ]
        ).to_csv(publisher.path("resource_summary.csv"), index=False)
        contracts.to_csv(
            publisher.path("contract_status.csv"), index=False
        )
        pd.DataFrame(
            [
                {
                    "lightgbm_canary_ready": True,
                    "lightgbm_resource_canary_ready": bool(
                        resource_canary
                    ),
                    "lightgbm_model_research_complete": False,
                    "production_model_selected": False,
                    "authoritative_execution": False,
                    "unbiased_final_estimate": False,
                }
            ]
        ).to_csv(publisher.path("readiness_summary.csv"), index=False)
        parent_receipts.to_csv(
            publisher.path("parent_receipts.csv"), index=False
        )
        publisher.path("resolved_config.json").write_text(
            json.dumps(
                resolved_config,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
                default=str,
            )
            + "\n",
            encoding="utf-8",
        )
        publisher.path("run_report.md").write_text(
            "# Research LightGBM V1 Train-only Canary\n\n"
            f"- Samples / factors: {len(features):,} / {len(factors)}.\n"
            f"- Structural rows / repeats: {len(canary_candidates)} / "
            f"{scope['repeats']}.\n"
            f"- Peak RSS: {peak_rss:.1f} MiB.\n"
            "- Candidate and train prediction hashes are repeat-stable.\n"
            "- Validation/test payload reads: 0/0.\n",
            encoding="utf-8",
        )
        output_files = [
            publisher.path(name)
            for name in CANARY_OUTPUTS
            if name != "artifact_manifest.json"
        ]
        write_stage_artifact_manifest(
            project_root=PROJECT_ROOT,
            stage_id=STAGE_ID,
            config=resolved_config,
            output_dir=publisher.staging_dir,
            output_files=output_files,
            code_state=code_state,
            input_manifest_paths=[
                path for _, path, _ in parent_items
            ],
            contract_paths=[publisher.path("contract_status.csv")],
        )
        publisher.publish()
    return {
        "output_dir": output_dir.as_posix(),
        "sample_rows": len(features),
        "factor_count": len(factors),
        "candidate_runs": len(result_frame),
        "peak_rss_mib": peak_rss,
        "scope": scope_key,
    }
