from __future__ import annotations

import hashlib
import json
import gc
import shutil
import time
from datetime import datetime, timezone
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
from .freeze import capture_environment_lock, validate_pre_test_freeze
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
from .linear_models import (
    _materialize_fold,
    _preprocessing_payload,
    _spool_fold,
    _spool_hash,
    _validation_metrics,
)
from .development_dry_run import _fit_from_spool
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
DEVELOPMENT_OUTPUTS = (
    "artifact_manifest.json",
    "resolved_config.json",
    "parent_receipts.csv",
    "hyperparameter_candidate_manifest.csv",
    "validation_metrics.csv",
    "selected_hyperparameters.json",
    "model_receipt.csv",
    "preprocessing_receipt.csv",
    "feature_importance.csv",
    "sample_eligibility_receipt.csv",
    "mutation_results.csv",
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


def _safe_prepare_development_runtime(path: Path) -> None:
    allowed = resolve("outputs/research_lightgbm_v1/runtime").resolve()
    target = path.resolve()
    if target != allowed and allowed not in target.parents:
        raise ValueError(
            f"LightGBM runtime escapes controlled root: {target}"
        )
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True, exist_ok=False)


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


def select_lightgbm_candidate(metrics: pd.DataFrame) -> pd.Series:
    eligible = metrics.loc[metrics["status"].eq("pass")].copy()
    if eligible.empty:
        raise ValueError("no eligible LightGBM validation candidate")
    return eligible.sort_values(
        [
            "mean_daily_rank_ic",
            "daily_rank_ic_ir",
            "prediction_coverage",
            "num_leaves",
            "max_depth",
            "num_boost_round",
            "candidate_sha256",
        ],
        ascending=[False, False, False, True, True, True, True],
        kind="stable",
    ).iloc[0]


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


def run_lightgbm_development(
    config: dict[str, Any],
    *,
    output_dir: Path,
    runtime_dir: Path,
    split_ids: list[str],
    command: str,
    factor_limit: int | None = None,
    train_date_limit: int | None = None,
    validation_date_limit: int | None = None,
    candidate_limit: int | None = None,
) -> dict[str, Any]:
    import lightgbm as lgb

    frozen_splits = [str(value) for value in config["split_ids"]]
    if not split_ids or any(value not in frozen_splits for value in split_ids):
        raise ValueError("LightGBM development split scope is invalid")
    if split_ids != [value for value in frozen_splits if value in split_ids]:
        raise ValueError("LightGBM development splits must preserve order")
    protocol_manifest_path = resolve(config["protocol_manifest"])
    assert_research_model_entry_artifact(
        protocol_manifest_path,
        experiment_class=str(config["experiment_class"]),
        operation="training",
    )
    linear_manifest_path = resolve(config["linear_model_manifest"])
    resource_manifest_path = resolve(
        "outputs/research_lightgbm_v1/resource_canary/"
        "artifact_manifest.json"
    )
    parent_items: list[tuple[str, Path, dict[str, Any]]] = []
    for role, path in (
        ("research_model_protocol_v1_1", protocol_manifest_path),
        ("research_linear_models_v1", linear_manifest_path),
        ("lightgbm_resource_canary", resource_manifest_path),
    ):
        manifest = load_artifact_manifest(path)
        if (
            manifest.get("artifact_status") != "pass"
            or manifest.get("lineage_status") != "complete"
        ):
            raise ValueError(f"LightGBM development parent blocked: {role}")
        parent_items.append((role, path, manifest))
    if "split_001" not in split_ids:
        split_one_path = resolve(
            "outputs/research_lightgbm_v1/split_001/"
            "artifact_manifest.json"
        )
        split_one_manifest = load_artifact_manifest(split_one_path)
        if (
            split_one_manifest.get("artifact_status") != "pass"
            or split_one_manifest.get("lineage_status") != "complete"
        ):
            raise ValueError(
                "remaining LightGBM splits require complete/pass split_001"
            )
        parent_items.append(
            (
                "lightgbm_split_001_development",
                split_one_path,
                split_one_manifest,
            )
        )
    code_state = capture_code_state(PROJECT_ROOT)
    if code_state.dirty:
        raise ValueError(
            "LightGBM development requires clean committed code"
        )
    expected_environment = json.loads(
        resolve(
            "outputs/research_model_protocol_v1_1/current/"
            "environment_lock.json"
        ).read_text(encoding="utf-8")
    )
    actual_environment = capture_environment_lock(
        qlib_commit_sha=str(expected_environment["qlib_commit_sha"])
    )
    if actual_environment != expected_environment:
        raise ValueError(
            "LightGBM development environment differs from frozen lock"
        )
    _safe_prepare_development_runtime(runtime_dir)
    protocol_config = yaml.safe_load(
        resolve(config["protocol_config"]).read_text(encoding="utf-8")
    )
    resolution = resolve_authoritative_parents(
        parent_paths(protocol_config)
    )
    factor_orders: dict[str, list[str]] = {}
    allowlist_rows: dict[str, pd.Series] = {}
    all_factors: list[str] = []
    for split_id in split_ids:
        ordered, receipt = load_split_feature_order(
            resolve(protocol_config["selection"]["factor_weights"]),
            resolve(protocol_config["selection"]["allowlist_manifest"]),
            outer_split_id=split_id,
        )
        factors = ordered["factor"].astype(str).tolist()
        if factor_limit is not None:
            factors = factors[:factor_limit]
        factor_orders[split_id] = factors
        allowlist_rows[split_id] = receipt
        all_factors.extend(factors)
    matrix = _matrix_authority(
        protocol_config,
        selected_factors=sorted(set(all_factors)),
        verify_hashes=True,
    )
    full_grid = candidate_grid(config)
    grid = (
        full_grid
        if candidate_limit is None
        else full_grid[:candidate_limit]
    )
    candidate_rows = [
        {"outer_split_id": split_id, **candidate}
        for split_id in split_ids
        for candidate in grid
    ]
    candidate_frame = pd.DataFrame(candidate_rows)
    candidate_runtime_path = (
        runtime_dir / "hyperparameter_candidate_manifest.csv"
    )
    candidate_frame.to_csv(candidate_runtime_path, index=False)
    candidate_manifest_sha = file_sha256(candidate_runtime_path)
    candidate_frozen_at = datetime.now(timezone.utc).isoformat()

    access = InputAccessAudit()
    metric_rows: list[dict[str, Any]] = []
    selected_payload: dict[str, Any] = {}
    model_rows: list[dict[str, Any]] = []
    preprocessing_rows: list[dict[str, Any]] = []
    importance_rows: list[dict[str, Any]] = []
    eligibility_rows: list[pd.DataFrame] = []
    mutation_rows: list[dict[str, Any]] = []
    resource_rows: list[dict[str, Any]] = []
    freeze_payloads: dict[str, dict[str, Any]] = {}
    peak_rss = 0.0
    first_fit_started_at = ""
    model_dir = runtime_dir / "models"
    model_dir.mkdir()

    for split_id in split_ids:
        split_started = time.perf_counter()
        factors = factor_orders[split_id]
        train_dates = load_fold_dates(
            parent_paths(protocol_config).selection_date_assignments,
            outer_split_id=split_id,
            fold="train",
            limit=train_date_limit,
        )
        validation_dates = load_fold_dates(
            parent_paths(protocol_config).selection_date_assignments,
            outer_split_id=split_id,
            fold="validation",
            limit=validation_date_limit,
        )
        test_dates = load_fold_dates(
            parent_paths(protocol_config).selection_date_assignments,
            outer_split_id=split_id,
            fold="test",
        )
        assert_fold_isolation(
            train_dates, validation_dates, test_dates
        )
        split_runtime = runtime_dir / split_id
        split_runtime.mkdir()
        train_spools, train_receipt = _spool_fold(
            protocol_config=protocol_config,
            resolution=resolution,
            matrix=matrix,
            split_id=split_id,
            fold="train",
            dates=train_dates,
            factors=factors,
            output_dir=split_runtime,
            audit=access,
        )
        validation_spools, validation_receipt = _spool_fold(
            protocol_config=protocol_config,
            resolution=resolution,
            matrix=matrix,
            split_id=split_id,
            fold="validation",
            dates=validation_dates,
            factors=factors,
            output_dir=split_runtime,
            audit=access,
        )
        eligibility_rows.extend([train_receipt, validation_receipt])
        train_preprocessing = _fit_from_spool(
            train_spools, factors
        )
        train_data = _materialize_fold(
            spool_paths=train_spools,
            factors=factors,
            preprocessing=train_preprocessing,
            output_dir=split_runtime,
            name="train",
            keep_metadata=False,
        )
        validation_data = _materialize_fold(
            spool_paths=validation_spools,
            factors=factors,
            preprocessing=train_preprocessing,
            output_dir=split_runtime,
            name="validation",
            keep_metadata=True,
        )
        if validation_data.metadata is None:
            raise AssertionError("LightGBM validation metadata missing")
        validation_label_sha = canonical_hash(
            validation_data.metadata[
                ["datetime", "instrument", "__label"]
            ]
            .astype(str)
            .to_dict("records")
        )
        train_dataset = lgb.Dataset(
            train_data.features,
            label=train_data.target,
            weight=train_data.weights,
            feature_name=factors,
            free_raw_data=False,
            params={"feature_pre_filter": False},
        )
        split_metrics: list[dict[str, Any]] = []
        active_structural_ids = list(
            dict.fromkeys(
                row["structural_row_id"] for row in grid
            )
        )
        for structural_id in active_structural_ids:
            structural = next(
                row
                for row in config["structural_rows"]
                if row["structural_row_id"] == structural_id
            )
            active_checkpoints = [
                int(row["num_boost_round"])
                for row in grid
                if row["structural_row_id"] == structural_id
            ]
            if not first_fit_started_at:
                first_fit_started_at = datetime.now(
                    timezone.utc
                ).isoformat()
            with _MemorySampler() as sampler:
                booster = lgb.train(
                    _training_params(
                        config,
                        {
                            **structural,
                            "num_boost_round": max(active_checkpoints),
                        },
                    ),
                    train_dataset,
                    num_boost_round=max(active_checkpoints),
                )
                for checkpoint in active_checkpoints:
                    candidate = next(
                        row
                        for row in grid
                        if row["structural_row_id"]
                        == structural["structural_row_id"]
                        and int(row["num_boost_round"])
                        == int(checkpoint)
                    )
                    prediction = booster.predict(
                        validation_data.features,
                        num_iteration=int(checkpoint),
                    )
                    metrics = _validation_metrics(
                        validation_data.metadata,
                        prediction,
                    )
                    status = (
                        "pass"
                        if metrics["prediction_coverage"]
                        >= float(
                            config["validation"][
                                "minimum_prediction_coverage"
                            ]
                        )
                        and int(metrics["daily_ic_count"]) > 0
                        and np.isfinite(
                            metrics["mean_daily_rank_ic"]
                        )
                        and np.isfinite(metrics["daily_rank_ic_ir"])
                        else "blocked"
                    )
                    row = {
                        "outer_split_id": split_id,
                        **candidate,
                        **metrics,
                        "validation_prediction_sha256": _array_hash(
                            prediction
                        ),
                        "validation_label_sha256": (
                            validation_label_sha
                        ),
                        "status": status,
                    }
                    split_metrics.append(row)
                    metric_rows.append(row)
                    del prediction
            peak_rss = float(max(peak_rss, sampler.peak_mb))
            del booster
            gc.collect()
        metrics_frame = pd.DataFrame(split_metrics)
        selected = select_lightgbm_candidate(metrics_frame)
        selected_candidate = next(
            row
            for row in grid
            if row["candidate_sha256"]
            == selected["candidate_sha256"]
        )
        validation_search_sha = canonical_hash(
            metrics_frame.to_dict("records")
        )
        mutated_metadata = validation_data.metadata.copy()
        mutated_metadata["__label"] = mutated_metadata.groupby(
            "datetime", sort=False
        )["__label"].transform(
            lambda values: values.iloc[::-1].to_numpy()
        )
        selected_booster = lgb.train(
            _training_params(config, selected_candidate),
            train_dataset,
            num_boost_round=int(
                selected_candidate["num_boost_round"]
            ),
        )
        selected_prediction = selected_booster.predict(
            validation_data.features,
            num_iteration=int(
                selected_candidate["num_boost_round"]
            ),
        )
        original_metric = {
            key: selected[key]
            for key in (
                "mean_daily_rank_ic",
                "daily_rank_ic_ir",
                "prediction_coverage",
                "daily_ic_count",
            )
        }
        mutated_metric = _validation_metrics(
            mutated_metadata, selected_prediction
        )
        mutated_label_sha = canonical_hash(
            mutated_metadata[
                ["datetime", "instrument", "__label"]
            ]
            .astype(str)
            .to_dict("records")
        )
        original_metric_sha = canonical_hash(original_metric)
        mutated_metric_sha = canonical_hash(mutated_metric)
        mutated_search_sha = canonical_hash(
            {
                "original_search_sha256": validation_search_sha,
                "mutated_label_sha256": mutated_label_sha,
                "mutated_metric_sha256": mutated_metric_sha,
            }
        )
        mutation_pass = (
            mutated_label_sha != validation_label_sha
            and mutated_metric_sha != original_metric_sha
            and mutated_search_sha != validation_search_sha
        )
        mutation_rows.append(
            {
                "outer_split_id": split_id,
                "method": "lightgbm",
                "validation_label_sha256": validation_label_sha,
                "mutated_validation_label_sha256": mutated_label_sha,
                "validation_metric_sha256": original_metric_sha,
                "mutated_validation_metric_sha256": mutated_metric_sha,
                "validation_search_sha256": validation_search_sha,
                "mutated_validation_search_sha256": (
                    mutated_search_sha
                ),
                "selected_candidate_change_required": False,
                "status": "pass" if mutation_pass else "blocked",
            }
        )
        del selected_booster, selected_prediction
        gc.collect()

        combined_spools = train_spools + validation_spools
        final_preprocessing = _fit_from_spool(
            combined_spools, factors
        )
        final_data = _materialize_fold(
            spool_paths=combined_spools,
            factors=factors,
            preprocessing=final_preprocessing,
            output_dir=split_runtime,
            name="final",
            keep_metadata=False,
        )
        final_dataset = lgb.Dataset(
            final_data.features,
            label=final_data.target,
            weight=final_data.weights,
            feature_name=factors,
            free_raw_data=False,
            params={"feature_pre_filter": False},
        )
        with _MemorySampler() as sampler:
            final_booster = lgb.train(
                _training_params(config, selected_candidate),
                final_dataset,
                num_boost_round=int(
                    selected_candidate["num_boost_round"]
                ),
            )
        peak_rss = float(max(peak_rss, sampler.peak_mb))
        model_path = model_dir / f"{split_id}_lightgbm.txt"
        final_booster.save_model(
            model_path,
            num_iteration=int(
                selected_candidate["num_boost_round"]
            ),
        )
        model_sha = file_sha256(model_path)
        preprocessing_payload = _preprocessing_payload(
            final_preprocessing
        )
        preprocessing_path = (
            model_dir / f"{split_id}_lightgbm_preprocessing.json"
        )
        preprocessing_path.write_text(
            json.dumps(
                preprocessing_payload,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        preprocessing_sha = file_sha256(preprocessing_path)
        training_data_sha = _spool_hash(combined_spools)
        for importance_type in ("gain", "split"):
            values = final_booster.feature_importance(
                importance_type=importance_type
            )
            for feature_order, (factor, value) in enumerate(
                zip(factors, values)
            ):
                importance_rows.append(
                    {
                        "outer_split_id": split_id,
                        "method": "lightgbm",
                        "importance_type": importance_type,
                        "factor": factor,
                        "feature_order": feature_order,
                        "importance": float(value),
                        "selection_authority": "diagnostic_only",
                    }
                )
        selected_payload[split_id] = selected_candidate
        preprocessing_rows.append(
            {
                "outer_split_id": split_id,
                "method": "lightgbm",
                "preprocessing_artifact_id": (
                    preprocessing_payload[
                        "preprocessing_artifact_id"
                    ]
                ),
                "preprocessing_sha256": preprocessing_sha,
                "feature_count": len(factors),
                "fit_scope": "outer_train_plus_validation",
                "runtime_path": preprocessing_path.as_posix(),
            }
        )
        model_rows.append(
            {
                "outer_split_id": split_id,
                "method": "lightgbm",
                "model_binary_sha256": model_sha,
                "model_config_sha256": canonical_hash(
                    selected_candidate
                ),
                "training_data_sha256": training_data_sha,
                "validation_search_sha256": validation_search_sha,
                "fit_row_count": final_data.row_count,
                "runtime_path": model_path.as_posix(),
            }
        )
        allowlist = allowlist_rows[split_id]
        scope_is_exact = (
            factor_limit is None
            and train_date_limit is None
            and validation_date_limit is None
            and candidate_limit is None
        )
        freeze = {
            "outer_split_id": split_id,
            "method": "lightgbm",
            "experiment_class": "post_observation_research",
            "allowlist_sha256": str(
                allowlist["allowlist_sha256"]
            ),
            "feature_order_sha256": str(
                allowlist["feature_order_sha256"]
            ),
            "training_target_transform_sha256": file_sha256(
                resolve(
                    "outputs/research_model_protocol_v1_1/current/"
                    "target_transform_manifest.json"
                )
            ),
            "preprocessing_config_sha256": canonical_hash(
                protocol_config["preprocessing"]
            ),
            "fitted_preprocessing_artifact_id": (
                preprocessing_payload["preprocessing_artifact_id"]
            ),
            "selected_hyperparameters": selected_candidate,
            "model_config_sha256": canonical_hash(
                selected_candidate
            ),
            "model_binary_sha256": model_sha,
            "training_data_sha256": training_data_sha,
            "train_validation_date_sha256": canonical_hash(
                {
                    "train": [
                        value.date().isoformat()
                        for value in train_dates
                    ],
                    "validation": [
                        value.date().isoformat()
                        for value in validation_dates
                    ],
                }
            ),
            "validation_search_sha256": validation_search_sha,
            "metric_registry_sha256": file_sha256(
                resolve(
                    "outputs/research_model_protocol_v1_1/current/"
                    "metric_registry.json"
                )
            ),
            "random_seed": int(config["determinism"]["seed"]),
            "code_commit_sha": code_state.commit_sha,
            "freeze_timestamp": datetime.now(
                timezone.utc
            ).isoformat(),
            **actual_environment,
            "historical_test_already_observed": True,
            "authoritative_execution": False,
            "unbiased_final_estimate": False,
        }
        if scope_is_exact:
            validate_pre_test_freeze(freeze)
            freeze_payloads[split_id] = freeze
        resource_rows.append(
            {
                "outer_split_id": split_id,
                "factor_count": len(factors),
                "train_date_count": len(train_dates),
                "validation_date_count": len(validation_dates),
                "train_fit_row_count": train_data.row_count,
                "validation_row_count": validation_data.row_count,
                "final_fit_row_count": final_data.row_count,
                "runtime_seconds": time.perf_counter()
                - split_started,
                "peak_rss_mib_observed": peak_rss,
                "test_read_count": access.test_read_count,
            }
        )
        del (
            final_booster,
            final_dataset,
            final_data,
            train_dataset,
            train_data,
            validation_data,
        )
        gc.collect()
        shutil.rmtree(split_runtime)

    metrics = pd.DataFrame(metric_rows)
    mutations = pd.DataFrame(mutation_rows)
    exact_counts = all(
        len(
            candidate_frame.loc[
                candidate_frame["outer_split_id"].eq(split_id)
            ]
        )
        == len(grid)
        and len(
            metrics.loc[metrics["outer_split_id"].eq(split_id)]
        )
        == len(grid)
        for split_id in split_ids
    )
    all_selected = len(selected_payload) == len(split_ids)
    all_metrics_have_pass = all(
        metrics.loc[metrics["outer_split_id"].eq(split_id), "status"]
        .eq("pass")
        .any()
        for split_id in split_ids
    )
    contracts = pd.DataFrame(
        [
            _contract(
                "candidate_manifest_written_before_fit",
                bool(
                    candidate_frozen_at
                    and first_fit_started_at
                    and candidate_frozen_at < first_fit_started_at
                ),
                {
                    "candidate_frozen_at": candidate_frozen_at,
                    "first_fit_started_at": first_fit_started_at,
                },
                "candidate_frozen_at < first_fit_started_at",
            ),
            _contract(
                "candidate_grid_exact",
                exact_counts,
                len(metrics),
                len(split_ids) * len(grid),
            ),
            _contract(
                "validation_candidates_eligible",
                all_metrics_have_pass,
                int(metrics["status"].eq("pass").sum()),
                ">=1 per split",
            ),
            _contract(
                "final_refit_train_plus_validation",
                all_selected
                and len(model_rows) == len(split_ids),
                len(model_rows),
                len(split_ids),
            ),
            _contract(
                "validation_label_mutation_sensitive",
                not mutations.empty
                and mutations["status"].eq("pass").all(),
                mutations["status"].tolist(),
                "all pass",
            ),
            _contract(
                "test_read_count_before_freeze_zero",
                access.test_read_count == 0,
                access.test_read_count,
                0,
            ),
            _contract(
                "pre_test_freeze_valid",
                len(freeze_payloads)
                == (len(split_ids) if scope_is_exact else 0),
                len(freeze_payloads),
                len(split_ids) if scope_is_exact else 0,
            ),
            _contract(
                "peak_rss_within_budget",
                peak_rss
                <= float(config["resources"]["peak_rss_mib"]),
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
        raise ValueError("LightGBM development contracts failed")
    full_complete = split_ids == frozen_splits and scope_is_exact
    readiness = pd.DataFrame(
        [
            {
                "lightgbm_development_ready": True,
                "lightgbm_split_count_complete": len(split_ids),
                "lightgbm_model_research_complete": full_complete,
                "research_model_experiment_started": True,
                "model_training_started": True,
                "test_read_count_before_freeze": (
                    access.test_read_count
                ),
                "production_model_selected": False,
                "authoritative_execution": False,
                "unbiased_final_estimate": False,
            }
        ]
    )
    parent_receipts = pd.DataFrame(
        [
            {
                "parent_role": role,
                "manifest_path": path.as_posix(),
                "stage_id": manifest["stage_id"],
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
        "executed_scope": "development",
        "selected_splits": split_ids,
        "factor_limit": factor_limit,
        "train_date_limit": train_date_limit,
        "validation_date_limit": validation_date_limit,
        "candidate_limit": candidate_limit,
        "candidate_manifest_sha256": candidate_manifest_sha,
        "candidate_frozen_at": candidate_frozen_at,
        "first_fit_started_at": first_fit_started_at,
        "environment_lock": actual_environment,
        "runtime_dir": runtime_dir.as_posix(),
        "output_dir": output_dir.as_posix(),
    }
    controlled = DEVELOPMENT_OUTPUTS + tuple(
        f"pre_test_freezes/{split_id}_lightgbm.json"
        for split_id in split_ids
    )
    with StageOutputPublisher(output_dir, controlled) as publisher:
        candidate_frame.to_csv(
            publisher.path(
                "hyperparameter_candidate_manifest.csv"
            ),
            index=False,
        )
        metrics.to_csv(
            publisher.path("validation_metrics.csv"), index=False
        )
        publisher.path("selected_hyperparameters.json").write_text(
            json.dumps(
                selected_payload,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        pd.DataFrame(model_rows).to_csv(
            publisher.path("model_receipt.csv"), index=False
        )
        pd.DataFrame(preprocessing_rows).to_csv(
            publisher.path("preprocessing_receipt.csv"), index=False
        )
        pd.DataFrame(importance_rows).to_csv(
            publisher.path("feature_importance.csv"), index=False
        )
        pd.concat(eligibility_rows, ignore_index=True).to_csv(
            publisher.path("sample_eligibility_receipt.csv"),
            index=False,
        )
        mutations.to_csv(
            publisher.path("mutation_results.csv"), index=False
        )
        pd.DataFrame(access.rows()).to_csv(
            publisher.path("access_audit.csv"), index=False
        )
        pd.DataFrame(resource_rows).to_csv(
            publisher.path("resource_summary.csv"), index=False
        )
        contracts.to_csv(
            publisher.path("contract_status.csv"), index=False
        )
        readiness.to_csv(
            publisher.path("readiness_summary.csv"), index=False
        )
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
        for split_id, freeze in freeze_payloads.items():
            publisher.path(
                f"pre_test_freezes/{split_id}_lightgbm.json"
            ).write_text(
                json.dumps(
                    freeze,
                    ensure_ascii=False,
                    indent=2,
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )
        publisher.path("run_report.md").write_text(
            "# Research LightGBM V1 Development\n\n"
            f"- Splits: {', '.join(split_ids)}.\n"
            f"- Candidate rows: {len(metrics)}.\n"
            f"- Selected models/freezes: {len(model_rows)} / "
            f"{len(freeze_payloads)}.\n"
            f"- Peak RSS: {peak_rss:.1f} MiB.\n"
            "- Selection used outer validation daily Rank IC only.\n"
            "- Test payload reads before freeze: 0.\n"
            "- Feature importance is diagnostic-only.\n",
            encoding="utf-8",
        )
        output_files = [
            publisher.path(name)
            for name in controlled
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
            contract_paths=[
                publisher.path("contract_status.csv")
            ],
        )
        publisher.publish()
    return {
        "output_dir": output_dir.as_posix(),
        "split_ids": split_ids,
        "candidate_rows": len(metrics),
        "model_count": len(model_rows),
        "peak_rss_mib": peak_rss,
        "test_read_count": access.test_read_count,
        "scope_is_exact": scope_is_exact,
    }
