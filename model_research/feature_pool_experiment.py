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
from research_validation.lineage import capture_code_state

from .feature_pool_policy import POLICY_IDS, load_policy_config
from .gates import assert_research_model_entry_artifact
from .inputs import InputAccessAudit, join_labels, load_fold_dates, project_features
from .lightgbm_models import (
    _training_params,
    candidate_grid,
    load_lightgbm_config,
    select_lightgbm_candidate,
)
from .development_dry_run import _fit_from_spool
from .freeze import load_freeze_before_test, validate_pre_test_freeze
from .inputs import (
    join_test_labels_after_freeze,
    project_test_features_after_freeze,
)
from .linear_models import (
    _MemorySampler,
    _materialize_fold,
    _preprocessing_payload,
    _spool_fold,
    _spool_hash,
    _validation_metrics,
)
from .lineage import resolve_authoritative_parents
from .preprocessing import daily_equal_weights, fit_weighted_preprocessing
from .protocol import parent_paths, resolve
from .protocol_v1_1 import _labels_runtime_path, _matrix_authority
from .targets import eligible_daily_cross_sectional_rank_centered
from .development_dry_run import _date_batches
from .linear_test_release import _daily_ic_frame, _load_preprocessing


def canary_candidates(
    lightgbm_config: dict[str, Any], canary_config: dict[str, Any]
) -> list[dict[str, Any]]:
    structural_ids = set(canary_config["structural_row_ids"])
    checkpoint = int(canary_config["checkpoint"])
    selected = [
        row
        for row in candidate_grid(lightgbm_config)
        if row["structural_row_id"] in structural_ids
        and int(row["num_boost_round"]) == checkpoint
    ]
    if len(selected) != len(structural_ids):
        raise ValueError("canary candidate table does not match requested structural rows")
    return selected


def _array_hash(value: np.ndarray) -> str:
    array = np.ascontiguousarray(np.asarray(value))
    digest = hashlib.sha256()
    digest.update(str(array.dtype).encode("ascii"))
    digest.update(str(array.shape).encode("ascii"))
    digest.update(array.tobytes())
    return digest.hexdigest()


def _prepare_fold(
    *,
    protocol_config: dict[str, Any],
    resolution: Any,
    factor_names: list[str],
    split_id: str,
    fold: str,
    date_limit: int,
    date_selection: str,
    audit: InputAccessAudit,
) -> tuple[pd.DataFrame, pd.Series, pd.DataFrame]:
    full_dates = load_fold_dates(
        parent_paths(protocol_config).selection_date_assignments,
        outer_split_id=split_id,
        fold=fold,
    )
    if date_selection != "evenly_spaced_within_fold":
        raise ValueError("canary dates must be evenly_spaced_within_fold")
    if date_limit > len(full_dates):
        raise ValueError(f"canary date limit exceeds {fold} fold")
    positions = np.linspace(0, len(full_dates) - 1, num=date_limit, dtype=int)
    dates = full_dates[positions]
    matrix = _matrix_authority(
        protocol_config, selected_factors=factor_names, verify_hashes=True
    )
    joined = join_labels(
        project_features(
            factor_names=factor_names,
            factor_index=matrix.factor_index,
            dates=dates,
            fold=fold,
            audit=audit,
        ),
        labels_path=_labels_runtime_path(protocol_config, resolution),
        label_name=protocol_config["target"]["label_id"],
        dates=dates,
        fold=fold,
        audit=audit,
    )
    target, _, receipt = eligible_daily_cross_sectional_rank_centered(
        joined,
        label_column=protocol_config["target"]["label_id"],
        feature_columns=factor_names,
        expected_dates=dates,
        minimum_daily_pairs=int(protocol_config["target"]["minimum_daily_pairs"]),
    )
    selected = joined.loc[target.notna()].reset_index(drop=True)
    selected_target = target.loc[target.notna()].reset_index(drop=True)
    if selected.empty:
        raise ValueError(f"canary has no eligible {fold} rows")
    return selected, selected_target, receipt


def run_policy_canary(
    *,
    policy_config_path: Path,
    policy_manifest_path: Path,
    feature_manifest_path: Path,
    output_dir: Path,
) -> dict[str, pd.DataFrame]:
    import lightgbm as lgb

    config = load_policy_config(policy_config_path)
    lightgbm_path = resolve(config["parents"]["lightgbm_config"])
    lightgbm_config = load_lightgbm_config(lightgbm_path)
    assert_research_model_entry_artifact(
        resolve(lightgbm_config["protocol_manifest"]),
        experiment_class=str(lightgbm_config["experiment_class"]),
        operation="canary",
    )
    protocol_config = yaml.safe_load(
        resolve(lightgbm_config["protocol_config"]).read_text(encoding="utf-8")
    )
    resolution = resolve_authoritative_parents(parent_paths(protocol_config))
    policy_manifest = pd.read_csv(policy_manifest_path)
    feature_manifest = pd.read_csv(feature_manifest_path)
    canary = config["canary"]
    split_id = str(canary["split_id"])
    candidates = canary_candidates(lightgbm_config, canary)
    expected_candidate_hash = canonical_hash(
        [row["candidate_sha256"] for row in candidates]
    )
    result_rows: list[dict[str, Any]] = []
    resource_rows: list[dict[str, Any]] = []
    audit_rows: list[dict[str, Any]] = []
    for policy_id in POLICY_IDS:
        policy_row = policy_manifest.loc[
            policy_manifest["outer_split_id"].astype(str).eq(split_id)
            & policy_manifest["policy_id"].astype(str).eq(policy_id)
        ]
        if len(policy_row) != 1:
            raise ValueError(f"missing unique canary policy manifest: {policy_id}")
        if not policy_row["decision_authority"].eq("diagnostic_only").all():
            raise ValueError("canary input policy is not diagnostic_only")
        selected = feature_manifest.loc[
            feature_manifest["outer_split_id"].astype(str).eq(split_id)
            & feature_manifest["policy_id"].astype(str).eq(policy_id)
        ].sort_values("feature_order", kind="stable")
        factors = selected["factor"].astype(str).tolist()
        if len(factors) != int(policy_row.iloc[0]["factor_count"]):
            raise ValueError(f"canary policy feature count mismatch: {policy_id}")
        audit = InputAccessAudit()
        started = time.perf_counter()
        train, train_target, train_receipt = _prepare_fold(
            protocol_config=protocol_config,
            resolution=resolution,
            factor_names=factors,
            split_id=split_id,
            fold="train",
            date_limit=int(canary["train_date_count"]),
            date_selection=str(canary["date_selection"]),
            audit=audit,
        )
        validation, validation_target, validation_receipt = _prepare_fold(
            protocol_config=protocol_config,
            resolution=resolution,
            factor_names=factors,
            split_id=split_id,
            fold="validation",
            date_limit=int(canary["validation_date_count"]),
            date_selection=str(canary["date_selection"]),
            audit=audit,
        )
        train_weights = daily_equal_weights(train["datetime"].to_numpy())
        keys = (
            train["datetime"].astype(str) + "|" + train["instrument"].astype(str)
        ).to_numpy()
        preprocessing = fit_weighted_preprocessing(
            train[factors].to_numpy(dtype=float),
            train_weights,
            feature_names=tuple(factors),
            canonical_row_keys=keys,
        )
        train_x = preprocessing.transform(train[factors].to_numpy(dtype=float))
        validation_x = preprocessing.transform(validation[factors].to_numpy(dtype=float))
        metadata = validation[["datetime", "instrument"]].copy()
        metadata["__label"] = validation_target.to_numpy(dtype=float)
        for candidate in candidates:
            prediction_hashes: list[str] = []
            for repeat in range(int(canary["repeats"])):
                model = lgb.train(
                    _training_params(lightgbm_config, candidate),
                    lgb.Dataset(
                        train_x,
                        label=train_target.to_numpy(dtype=float),
                        weight=train_weights,
                        feature_name=factors,
                        free_raw_data=False,
                    ),
                    num_boost_round=int(candidate["num_boost_round"]),
                )
                prediction = model.predict(validation_x)
                metrics = _validation_metrics(metadata, prediction)
                prediction_hash = _array_hash(prediction)
                prediction_hashes.append(prediction_hash)
                result_rows.append(
                    {
                        "outer_split_id": split_id,
                        "policy_id": policy_id,
                        "candidate_sha256": candidate["candidate_sha256"],
                        "candidate_table_sha256": expected_candidate_hash,
                        "structural_row_id": candidate["structural_row_id"],
                        "num_boost_round": candidate["num_boost_round"],
                        "repeat": repeat,
                        "feature_count": len(factors),
                        "train_row_count": len(train),
                        "validation_row_count": len(validation),
                        "prediction_sha256": prediction_hash,
                        **metrics,
                        "status": "pass"
                        if np.isfinite(metrics["mean_daily_rank_ic"])
                        else "fail_nonfinite_metric",
                        "decision_authority": "diagnostic_only",
                        "selection_authorized": False,
                        "strategy_v2_authorized": False,
                    }
                )
            if len(set(prediction_hashes)) != 1:
                raise AssertionError(
                    f"non-deterministic canary predictions: {policy_id}/"
                    f"{candidate['candidate_sha256']}"
                )
        if audit.test_read_count != int(canary["test_read_budget"]):
            raise AssertionError("policy canary exceeded test read budget")
        resource_rows.append(
            {
                "outer_split_id": split_id,
                "policy_id": policy_id,
                "feature_count": len(factors),
                "train_matrix_gib": train_x.nbytes / 1024**3,
                "validation_matrix_gib": validation_x.nbytes / 1024**3,
                "wall_seconds": time.perf_counter() - started,
                "train_receipt_pass_dates": int(train_receipt["status"].eq("pass").sum()),
                "validation_receipt_pass_dates": int(
                    validation_receipt["status"].eq("pass").sum()
                ),
            }
        )
        for row in audit.rows():
            audit_rows.append({"outer_split_id": split_id, "policy_id": policy_id, **row})

    frames = {
        "canary_results.csv": pd.DataFrame(result_rows),
        "resource_summary.csv": pd.DataFrame(resource_rows),
        "access_audit.csv": pd.DataFrame(audit_rows),
        "canary_candidate_manifest.csv": pd.DataFrame(candidates),
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    if any((output_dir / name).exists() for name in frames):
        raise FileExistsError("policy canary outputs are immutable; refusing overwrite")
    for name, frame in frames.items():
        frame.to_csv(output_dir / name, index=False, encoding="utf-8-sig")
    receipt = {
        "schema_version": 1,
        "stage_id": "ml_feature_pool_mvp_v1_canary",
        "decision_authority": "diagnostic_only",
        "selection_authorized": False,
        "strategy_v2_authorized": False,
        "policy_ids": list(POLICY_IDS),
        "candidate_table_sha256": expected_candidate_hash,
        "test_read_count": int(frames["access_audit.csv"].loc[
            frames["access_audit.csv"]["fold"].eq("test"), "read_count"
        ].sum()),
    }
    (output_dir / "canary_receipt.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return frames


def _safe_fresh_runtime(path: Path, *, allowed_root: Path) -> None:
    target = path.resolve()
    allowed = allowed_root.resolve()
    if target == allowed or allowed not in target.parents:
        raise ValueError(f"runtime path escapes or equals controlled root: {target}")
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True, exist_ok=False)


def _arm_factors(
    feature_manifest: pd.DataFrame, *, split_id: str, policy_id: str
) -> list[str]:
    selected = feature_manifest.loc[
        feature_manifest["outer_split_id"].astype(str).eq(split_id)
        & feature_manifest["policy_id"].astype(str).eq(policy_id)
    ].copy()
    selected["feature_order"] = pd.to_numeric(
        selected["feature_order"], errors="raise"
    ).astype(int)
    selected = selected.sort_values("feature_order", kind="stable")
    if selected["feature_order"].tolist() != list(range(len(selected))):
        raise ValueError(f"non-contiguous policy feature order: {split_id}/{policy_id}")
    if selected["factor"].duplicated().any() or selected.empty:
        raise ValueError(f"invalid policy factors: {split_id}/{policy_id}")
    return selected["factor"].astype(str).tolist()


def _development_arm_complete(arm_dir: Path) -> bool:
    receipt_path = arm_dir / "arm_receipt.json"
    if not receipt_path.is_file():
        return False
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    for name, expected in receipt.get("output_sha256", {}).items():
        path = arm_dir / name
        if not path.is_file() or file_sha256(path) != expected:
            return False
    freeze_path = arm_dir / "freeze.json"
    freeze = (
        json.loads(freeze_path.read_text(encoding="utf-8"))
        if freeze_path.is_file()
        else {}
    )
    return (
        receipt.get("status") == "pass"
        and receipt.get("test_read_count") == 0
        and bool(freeze.get("code_diff_sha256"))
    )


def run_development_arm(
    *,
    policy_config_path: Path,
    feature_manifest_path: Path,
    split_id: str,
    policy_id: str,
    development_root: Path,
    runtime_root: Path,
) -> dict[str, Any]:
    import lightgbm as lgb

    config = load_policy_config(policy_config_path)
    if split_id not in [str(value) for value in config["split_ids"]]:
        raise ValueError(f"unknown development split: {split_id}")
    if policy_id not in POLICY_IDS:
        raise ValueError(f"unknown development policy: {policy_id}")
    arm_dir = development_root / split_id / policy_id
    if _development_arm_complete(arm_dir):
        return json.loads((arm_dir / "arm_receipt.json").read_text(encoding="utf-8"))
    if arm_dir.exists():
        raise FileExistsError(f"incomplete development arm requires manual review: {arm_dir}")

    lightgbm_config = load_lightgbm_config(
        resolve(config["parents"]["lightgbm_config"])
    )
    protocol_manifest_path = resolve(lightgbm_config["protocol_manifest"])
    assert_research_model_entry_artifact(
        protocol_manifest_path,
        experiment_class=str(lightgbm_config["experiment_class"]),
        operation="training",
    )
    protocol_config = yaml.safe_load(
        resolve(lightgbm_config["protocol_config"]).read_text(encoding="utf-8")
    )
    resolution = resolve_authoritative_parents(parent_paths(protocol_config))
    factors = _arm_factors(
        pd.read_csv(feature_manifest_path), split_id=split_id, policy_id=policy_id
    )
    matrix = _matrix_authority(
        protocol_config, selected_factors=factors, verify_hashes=True
    )
    train_dates = load_fold_dates(
        parent_paths(protocol_config).selection_date_assignments,
        outer_split_id=split_id,
        fold="train",
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
    runtime_dir = runtime_root / split_id / policy_id
    _safe_fresh_runtime(runtime_dir, allowed_root=runtime_root)
    staging = development_root / ".staging" / split_id / policy_id
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True, exist_ok=False)
    started = time.perf_counter()
    audit = InputAccessAudit()
    train_spools, train_receipt = _spool_fold(
        protocol_config=protocol_config,
        resolution=resolution,
        matrix=matrix,
        split_id=split_id,
        fold="train",
        dates=train_dates,
        factors=factors,
        output_dir=runtime_dir,
        audit=audit,
    )
    validation_spools, validation_receipt = _spool_fold(
        protocol_config=protocol_config,
        resolution=resolution,
        matrix=matrix,
        split_id=split_id,
        fold="validation",
        dates=validation_dates,
        factors=factors,
        output_dir=runtime_dir,
        audit=audit,
    )
    if audit.test_read_count:
        raise AssertionError("development arm read test payload before freeze")
    train_preprocessing = _fit_from_spool(train_spools, factors)
    train_data = _materialize_fold(
        spool_paths=train_spools,
        factors=factors,
        preprocessing=train_preprocessing,
        output_dir=runtime_dir,
        name="train",
        keep_metadata=False,
    )
    validation_data = _materialize_fold(
        spool_paths=validation_spools,
        factors=factors,
        preprocessing=train_preprocessing,
        output_dir=runtime_dir,
        name="validation",
        keep_metadata=True,
    )
    if validation_data.metadata is None:
        raise AssertionError("development validation metadata missing")
    train_dataset = lgb.Dataset(
        train_data.features,
        label=train_data.target,
        weight=train_data.weights,
        feature_name=factors,
        free_raw_data=False,
        params={"feature_pre_filter": False},
    )
    grid = candidate_grid(lightgbm_config)
    candidate_table_hash = canonical_hash(
        [row["candidate_sha256"] for row in grid]
    )
    validation_label_hash = canonical_hash(
        validation_data.metadata[["datetime", "instrument", "__label"]]
        .astype(str)
        .to_dict("records")
    )
    metric_rows: list[dict[str, Any]] = []
    peak_rss = 0.0
    for structural in lightgbm_config["structural_rows"]:
        checkpoints = [
            int(row["num_boost_round"])
            for row in grid
            if row["structural_row_id"] == structural["structural_row_id"]
        ]
        with _MemorySampler() as sampler:
            booster = lgb.train(
                _training_params(
                    lightgbm_config,
                    {**structural, "num_boost_round": max(checkpoints)},
                ),
                train_dataset,
                num_boost_round=max(checkpoints),
            )
            for checkpoint in checkpoints:
                candidate = next(
                    row
                    for row in grid
                    if row["structural_row_id"] == structural["structural_row_id"]
                    and int(row["num_boost_round"]) == checkpoint
                )
                prediction = booster.predict(
                    validation_data.features, num_iteration=checkpoint
                )
                metrics = _validation_metrics(validation_data.metadata, prediction)
                passed = (
                    metrics["prediction_coverage"]
                    >= float(
                        lightgbm_config["validation"]["minimum_prediction_coverage"]
                    )
                    and int(metrics["daily_ic_count"]) > 0
                    and np.isfinite(metrics["mean_daily_rank_ic"])
                    and np.isfinite(metrics["daily_rank_ic_ir"])
                )
                metric_rows.append(
                    {
                        "outer_split_id": split_id,
                        "policy_id": policy_id,
                        **candidate,
                        **metrics,
                        "validation_prediction_sha256": _array_hash(prediction),
                        "validation_label_sha256": validation_label_hash,
                        "candidate_table_sha256": candidate_table_hash,
                        "status": "pass" if passed else "blocked",
                        "decision_authority": "diagnostic_only",
                    }
                )
        peak_rss = max(peak_rss, sampler.peak_mb)
        del booster
        gc.collect()
    metrics_frame = pd.DataFrame(metric_rows)
    if len(metrics_frame) != 16:
        raise AssertionError("development arm did not evaluate all 16 candidates")
    selected = select_lightgbm_candidate(metrics_frame)
    selected_candidate = next(
        row for row in grid if row["candidate_sha256"] == selected["candidate_sha256"]
    )
    validation_search_hash = canonical_hash(metrics_frame.to_dict("records"))

    selected_booster = lgb.train(
        _training_params(lightgbm_config, selected_candidate),
        train_dataset,
        num_boost_round=int(selected_candidate["num_boost_round"]),
    )
    selected_prediction = selected_booster.predict(
        validation_data.features,
        num_iteration=int(selected_candidate["num_boost_round"]),
    )
    mutated = validation_data.metadata.copy()
    mutated["__label"] = mutated.groupby("datetime", sort=False)["__label"].transform(
        lambda values: values.iloc[::-1].to_numpy()
    )
    original_metric = _validation_metrics(
        validation_data.metadata, selected_prediction
    )
    mutated_metric = _validation_metrics(mutated, selected_prediction)
    mutation_pass = canonical_hash(original_metric) != canonical_hash(mutated_metric)
    if not mutation_pass:
        raise AssertionError("validation label mutation did not change metrics")
    del selected_booster, selected_prediction, mutated
    gc.collect()

    combined_spools = train_spools + validation_spools
    final_preprocessing = _fit_from_spool(combined_spools, factors)
    final_data = _materialize_fold(
        spool_paths=combined_spools,
        factors=factors,
        preprocessing=final_preprocessing,
        output_dir=runtime_dir,
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
            _training_params(lightgbm_config, selected_candidate),
            final_dataset,
            num_boost_round=int(selected_candidate["num_boost_round"]),
        )
    peak_rss = max(peak_rss, sampler.peak_mb)
    model_path = staging / "model.txt"
    final_booster.save_model(
        model_path, num_iteration=int(selected_candidate["num_boost_round"])
    )
    preprocessing_payload = _preprocessing_payload(final_preprocessing)
    preprocessing_path = staging / "preprocessing.json"
    preprocessing_path.write_text(
        json.dumps(preprocessing_payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    environment = json.loads(
        resolve(
            "outputs/research_model_protocol_v1_1/current/environment_lock.json"
        ).read_text(encoding="utf-8")
    )
    code_state = capture_code_state(Path(__file__).resolve().parents[1])
    feature_order_hash = canonical_hash(factors)
    freeze = {
        "outer_split_id": split_id,
        "policy_id": policy_id,
        "method": "lightgbm",
        "experiment_class": "post_observation_research",
        "allowlist_sha256": feature_order_hash,
        "feature_order_sha256": feature_order_hash,
        "training_target_transform_sha256": file_sha256(
            resolve(
                "outputs/research_model_protocol_v1_1/current/target_transform_manifest.json"
            )
        ),
        "preprocessing_config_sha256": canonical_hash(
            protocol_config["preprocessing"]
        ),
        "fitted_preprocessing_artifact_id": preprocessing_payload[
            "preprocessing_artifact_id"
        ],
        "selected_hyperparameters": selected_candidate,
        "model_config_sha256": canonical_hash(selected_candidate),
        "model_binary_sha256": file_sha256(model_path),
        "preprocessing_sha256": file_sha256(preprocessing_path),
        "training_data_sha256": _spool_hash(combined_spools),
        "train_validation_date_sha256": canonical_hash(
            {
                "train": [value.date().isoformat() for value in train_dates],
                "validation": [
                    value.date().isoformat() for value in validation_dates
                ],
            }
        ),
        "test_dates_sha256": canonical_hash(
            [value.date().isoformat() for value in test_dates]
        ),
        "validation_search_sha256": validation_search_hash,
        "metric_registry_sha256": file_sha256(
            resolve("outputs/research_model_protocol_v1_1/current/metric_registry.json")
        ),
        "random_seed": int(lightgbm_config["determinism"]["seed"]),
        "code_commit_sha": code_state.commit_sha,
        "code_dirty_at_run": code_state.dirty,
        "code_diff_sha256": code_state.diff_sha256,
        "freeze_timestamp": datetime.now(timezone.utc).isoformat(),
        **environment,
        "historical_test_already_observed": True,
        "authoritative_execution": False,
        "unbiased_final_estimate": False,
        "decision_authority": "diagnostic_only",
        "selection_authorized": False,
        "strategy_v2_authorized": False,
    }
    freeze["freeze_id"] = "ml-feature-pool-freeze:" + canonical_hash(freeze)
    validate_pre_test_freeze(freeze)
    (staging / "freeze.json").write_text(
        json.dumps(freeze, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    metrics_frame.to_csv(staging / "validation_metrics.csv", index=False)
    pd.DataFrame(
        [{"outer_split_id": split_id, "policy_id": policy_id, **row} for row in grid]
    ).to_csv(staging / "candidate_manifest.csv", index=False)
    pd.concat([train_receipt, validation_receipt], ignore_index=True).to_csv(
        staging / "sample_eligibility_receipt.csv", index=False
    )
    pd.DataFrame(audit.rows()).to_csv(staging / "access_audit.csv", index=False)
    selected_payload = {
        "outer_split_id": split_id,
        "policy_id": policy_id,
        "selected_hyperparameters": selected_candidate,
        "decision_authority": "diagnostic_only",
        "selection_authorized": False,
        "strategy_v2_authorized": False,
    }
    (staging / "selected_hyperparameters.json").write_text(
        json.dumps(selected_payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    resource = pd.DataFrame(
        [
            {
                "outer_split_id": split_id,
                "policy_id": policy_id,
                "factor_count": len(factors),
                "train_rows": train_data.row_count,
                "validation_rows": validation_data.row_count,
                "final_fit_rows": final_data.row_count,
                "peak_rss_mib": peak_rss,
                "wall_seconds": time.perf_counter() - started,
                "test_read_count": audit.test_read_count,
            }
        ]
    )
    resource.to_csv(staging / "resource_summary.csv", index=False)
    output_names = [
        "model.txt",
        "preprocessing.json",
        "freeze.json",
        "validation_metrics.csv",
        "candidate_manifest.csv",
        "sample_eligibility_receipt.csv",
        "access_audit.csv",
        "selected_hyperparameters.json",
        "resource_summary.csv",
    ]
    receipt = {
        "schema_version": 1,
        "status": "pass",
        "outer_split_id": split_id,
        "policy_id": policy_id,
        "candidate_count": 16,
        "candidate_table_sha256": candidate_table_hash,
        "test_read_count": audit.test_read_count,
        "decision_authority": "diagnostic_only",
        "selection_authorized": False,
        "strategy_v2_authorized": False,
        "output_sha256": {
            name: file_sha256(staging / name) for name in output_names
        },
    }
    (staging / "arm_receipt.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    del final_booster, final_dataset, final_data, train_dataset, train_data, validation_data
    gc.collect()
    shutil.rmtree(runtime_dir)
    arm_dir.parent.mkdir(parents=True, exist_ok=True)
    staging.replace(arm_dir)
    return receipt


def run_all_development_arms(
    *,
    policy_config_path: Path,
    feature_manifest_path: Path,
    development_root: Path,
    runtime_root: Path,
) -> pd.DataFrame:
    config = load_policy_config(policy_config_path)
    rows: list[dict[str, Any]] = []
    for split_id in [str(value) for value in config["split_ids"]]:
        for policy_id in POLICY_IDS:
            receipt = run_development_arm(
                policy_config_path=policy_config_path,
                feature_manifest_path=feature_manifest_path,
                split_id=split_id,
                policy_id=policy_id,
                development_root=development_root,
                runtime_root=runtime_root,
            )
            rows.append(
                {
                    "outer_split_id": split_id,
                    "policy_id": policy_id,
                    "freeze_path": str(
                        development_root / split_id / policy_id / "freeze.json"
                    ),
                    "freeze_sha256": file_sha256(
                        development_root / split_id / policy_id / "freeze.json"
                    ),
                    "candidate_count": receipt["candidate_count"],
                    "candidate_table_sha256": receipt["candidate_table_sha256"],
                    "test_read_count": receipt["test_read_count"],
                    "decision_authority": "diagnostic_only",
                    "selection_authorized": False,
                    "strategy_v2_authorized": False,
                }
            )
    index = pd.DataFrame(rows)
    if len(index) != 9 or index["test_read_count"].sum() != 0:
        raise AssertionError("nine-arm development freeze gate failed")
    if index["candidate_table_sha256"].nunique() != 1:
        raise AssertionError("development arms did not share one candidate table")
    index_path = development_root / "freeze_index.csv"
    if index_path.exists():
        observed = pd.read_csv(index_path)
        if canonical_hash(observed.to_dict("records")) != canonical_hash(
            index.to_dict("records")
        ):
            raise FileExistsError("existing freeze index differs")
    else:
        index.to_csv(index_path, index=False, encoding="utf-8-sig")
    return index


def run_coordinated_historical_replay(
    *,
    policy_config_path: Path,
    feature_manifest_path: Path,
    development_root: Path,
    replay_root: Path,
) -> dict[str, pd.DataFrame]:
    import lightgbm as lgb

    if replay_root.exists():
        raise PermissionError("coordinated historical replay is single-release and already exists")
    config = load_policy_config(policy_config_path)
    lightgbm_config = load_lightgbm_config(
        resolve(config["parents"]["lightgbm_config"])
    )
    assert_research_model_entry_artifact(
        resolve(lightgbm_config["protocol_manifest"]),
        experiment_class=str(lightgbm_config["experiment_class"]),
        operation="prediction",
    )
    index_path = development_root / "freeze_index.csv"
    if not index_path.is_file():
        raise PermissionError("historical replay blocked until the nine-arm freeze index exists")
    freeze_index = pd.read_csv(index_path)
    expected_pairs = {
        (split_id, policy_id)
        for split_id in [str(value) for value in config["split_ids"]]
        for policy_id in POLICY_IDS
    }
    observed_pairs = set(
        zip(
            freeze_index["outer_split_id"].astype(str),
            freeze_index["policy_id"].astype(str),
        )
    )
    if len(freeze_index) != 9 or observed_pairs != expected_pairs:
        raise PermissionError("historical replay requires exactly all nine frozen arms")
    if freeze_index["test_read_count"].sum() != 0:
        raise PermissionError("development freeze index reports pre-freeze test reads")

    protocol_config = yaml.safe_load(
        resolve(lightgbm_config["protocol_config"]).read_text(encoding="utf-8")
    )
    resolution = resolve_authoritative_parents(parent_paths(protocol_config))
    feature_manifest = pd.read_csv(feature_manifest_path)
    arm_payloads: dict[tuple[str, str], dict[str, Any]] = {}
    all_factors: set[str] = set()
    for split_id, policy_id in sorted(expected_pairs):
        arm_dir = development_root / split_id / policy_id
        if not _development_arm_complete(arm_dir):
            raise PermissionError(f"development arm is incomplete: {split_id}/{policy_id}")
        freeze_path = arm_dir / "freeze.json"
        freeze = load_freeze_before_test(freeze_path)
        index_row = freeze_index.loc[
            freeze_index["outer_split_id"].astype(str).eq(split_id)
            & freeze_index["policy_id"].astype(str).eq(policy_id)
        ].iloc[0]
        if file_sha256(freeze_path) != str(index_row["freeze_sha256"]):
            raise ValueError(f"freeze index hash mismatch: {split_id}/{policy_id}")
        factors = _arm_factors(
            feature_manifest, split_id=split_id, policy_id=policy_id
        )
        if canonical_hash(factors) != freeze["feature_order_sha256"]:
            raise ValueError(f"frozen feature order mismatch: {split_id}/{policy_id}")
        model_path = arm_dir / "model.txt"
        preprocessing_path = arm_dir / "preprocessing.json"
        if file_sha256(model_path) != freeze["model_binary_sha256"]:
            raise ValueError(f"frozen model hash mismatch: {split_id}/{policy_id}")
        if file_sha256(preprocessing_path) != freeze["preprocessing_sha256"]:
            raise ValueError(f"frozen preprocessing hash mismatch: {split_id}/{policy_id}")
        arm_payloads[(split_id, policy_id)] = {
            "freeze_path": freeze_path,
            "freeze": freeze,
            "factors": factors,
            "model": lgb.Booster(model_file=str(model_path)),
            "preprocessing": _load_preprocessing(preprocessing_path),
        }
        all_factors.update(factors)
    matrix = _matrix_authority(
        protocol_config,
        selected_factors=sorted(all_factors),
        verify_hashes=True,
    )
    labels_path = _labels_runtime_path(protocol_config, resolution)
    staging = replay_root.parent / ".staging_historical_replay"
    if staging.exists():
        shutil.rmtree(staging)
    (staging / "predictions").mkdir(parents=True, exist_ok=False)
    audit = InputAccessAudit()
    metric_rows: list[dict[str, Any]] = []
    daily_frames: list[pd.DataFrame] = []
    receipt_rows: list[dict[str, Any]] = []
    for split_id in [str(value) for value in config["split_ids"]]:
        test_dates = load_fold_dates(
            parent_paths(protocol_config).selection_date_assignments,
            outer_split_id=split_id,
            fold="test",
        )
        for policy_id in POLICY_IDS:
            payload = arm_payloads[(split_id, policy_id)]
            freeze = payload["freeze"]
            factors = payload["factors"]
            prediction_parts: list[pd.DataFrame] = []
            evaluation_parts: list[pd.DataFrame] = []
            for dates in _date_batches(
                test_dates,
                int(protocol_config["development_dry_run"]["date_batch_size"]),
            ):
                features = project_test_features_after_freeze(
                    factor_names=factors,
                    factor_index=matrix.factor_index,
                    dates=dates,
                    audit=audit,
                    freeze_manifest_path=payload["freeze_path"],
                    outer_split_id=split_id,
                    authorized_dates=test_dates,
                )
                joined = join_test_labels_after_freeze(
                    features,
                    labels_path=labels_path,
                    label_name=protocol_config["target"]["label_id"],
                    dates=dates,
                    audit=audit,
                    freeze_manifest_path=payload["freeze_path"],
                    outer_split_id=split_id,
                    authorized_dates=test_dates,
                ).rename(columns={protocol_config["target"]["label_id"]: "__label"})
                eligible = (
                    joined[factors]
                    .replace([np.inf, -np.inf], np.nan)
                    .notna()
                    .any(axis=1)
                )
                selected = joined.loc[eligible].reset_index(drop=True)
                transformed = payload["preprocessing"].transform(
                    selected[factors].to_numpy(dtype=float)
                )
                prediction = payload["model"].predict(
                    transformed,
                    num_iteration=int(
                        freeze["selected_hyperparameters"]["num_boost_round"]
                    ),
                )
                prediction_parts.append(
                    pd.DataFrame(
                        {
                            "outer_split_id": split_id,
                            "policy_id": policy_id,
                            "datetime": selected["datetime"].to_numpy(),
                            "instrument": selected["instrument"].to_numpy(),
                            "prediction": prediction,
                            "model_freeze_id": freeze["freeze_id"],
                            "experiment_class": "post_observation_research",
                            "decision_authority": "diagnostic_only",
                        }
                    )
                )
                evaluation_parts.append(
                    pd.DataFrame(
                        {
                            "datetime": selected["datetime"].to_numpy(),
                            "instrument": selected["instrument"].to_numpy(),
                            "__label": selected["__label"].to_numpy(),
                            "prediction": prediction,
                        }
                    )
                )
            predictions = pd.concat(prediction_parts, ignore_index=True).sort_values(
                ["datetime", "instrument"], kind="stable"
            )
            evaluation = pd.concat(evaluation_parts, ignore_index=True).sort_values(
                ["datetime", "instrument"], kind="stable"
            )
            metrics = _validation_metrics(evaluation, evaluation["prediction"])
            if not np.isfinite(metrics["mean_daily_rank_ic"]):
                raise ValueError(f"nonfinite replay metric: {split_id}/{policy_id}")
            prediction_path = staging / "predictions" / f"{split_id}__{policy_id}.parquet"
            predictions.to_parquet(prediction_path, index=False, compression="zstd")
            metric_rows.append(
                {
                    "outer_split_id": split_id,
                    "policy_id": policy_id,
                    **metrics,
                    "decision_authority": "diagnostic_only",
                    "selection_authorized": False,
                    "strategy_v2_authorized": False,
                }
            )
            daily = _daily_ic_frame(
                evaluation, split_id=split_id, method=policy_id
            ).rename(columns={"method": "policy_id"})
            daily["decision_authority"] = "diagnostic_only"
            daily_frames.append(daily)
            receipt_rows.append(
                {
                    "outer_split_id": split_id,
                    "policy_id": policy_id,
                    "freeze_id": freeze["freeze_id"],
                    "freeze_sha256": file_sha256(payload["freeze_path"]),
                    "prediction_path": str(
                        replay_root / "predictions" / prediction_path.name
                    ),
                    "prediction_sha256": file_sha256(prediction_path),
                    "prediction_row_count": len(predictions),
                    "test_dates_sha256": freeze["test_dates_sha256"],
                    "decision_authority": "diagnostic_only",
                    "selection_authorized": False,
                    "strategy_v2_authorized": False,
                }
            )
    metrics_frame = pd.DataFrame(metric_rows)
    daily_frame = pd.concat(daily_frames, ignore_index=True)
    receipts = pd.DataFrame(receipt_rows)
    access = pd.DataFrame(audit.rows())
    if len(metrics_frame) != 9 or len(receipts) != 9:
        raise AssertionError("coordinated replay did not release all nine arms")
    metrics_frame.to_csv(staging / "test_metrics.csv", index=False)
    daily_frame.to_csv(staging / "test_daily_ic.csv", index=False)
    receipts.to_csv(staging / "prediction_receipts.csv", index=False)
    access.to_csv(staging / "access_audit.csv", index=False)
    release = {
        "schema_version": 1,
        "status": "pass",
        "released_arm_count": 9,
        "historical_test_already_observed": True,
        "decision_authority": "diagnostic_only",
        "selection_authorized": False,
        "strategy_v2_authorized": False,
        "partial_release_allowed": False,
        "development_freeze_index_sha256": file_sha256(index_path),
    }
    (staging / "replay_receipt.json").write_text(
        json.dumps(release, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    staging.replace(replay_root)
    return {
        "test_metrics": metrics_frame,
        "test_daily_ic": daily_frame,
        "prediction_receipts": receipts,
        "access_audit": access,
    }
