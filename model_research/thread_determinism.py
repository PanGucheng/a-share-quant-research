from __future__ import annotations

import gc
import json
import shutil
import time
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml
from scipy.stats import pearsonr, spearmanr

from research_validation.feature_matrix import canonical_hash, file_sha256

from .development_dry_run import _fit_from_spool
from .execution_profiles import thread_environment, with_lightgbm_threads
from .feature_pool_experiment import _arm_factors, _array_hash
from .feature_pool_policy import load_policy_config
from .inputs import InputAccessAudit, load_fold_dates
from .lightgbm_models import (
    _training_params,
    candidate_grid,
    load_lightgbm_config,
    select_lightgbm_candidate,
)
from .linear_models import (
    _MemorySampler,
    _materialize_fold,
    _preprocessing_payload,
    _validation_metrics,
)
from .lineage import resolve_authoritative_parents
from .protocol import parent_paths, resolve
from .protocol_v1_1 import _labels_runtime_path, _matrix_authority
from .research_cache import get_or_build_projection_spools
from .runtime_timing import RuntimeTimingRecorder


AUDIT_STAGE_ID = "lightgbm_thread_determinism_audit_v1"


def load_thread_audit_config(path: Path) -> dict[str, Any]:
    config = yaml.safe_load(path.read_text(encoding="utf-8"))
    if config.get("stage_id") != AUDIT_STAGE_ID:
        raise ValueError("unexpected thread determinism audit stage")
    threads = [int(value) for value in config.get("thread_counts", [])]
    if not threads or threads[0] != 1 or len(threads) != len(set(threads)):
        raise ValueError("thread audit requires unique thread counts with 1T first")
    if any(value < 1 for value in threads):
        raise ValueError("thread counts must be positive")
    if int(config.get("repeats", 0)) < 2:
        raise ValueError("thread audit requires at least two repeats")
    if config.get("folds") != ["train", "validation"]:
        raise ValueError("thread audit may only read development folds")
    if config.get("test_read_budget") != 0:
        raise ValueError("thread audit test read budget must be zero")
    if not config.get("workloads"):
        raise ValueError("thread audit requires at least one real workload")
    qualification = config.get("full_authoritative_qualification")
    if qualification not in {True, False}:
        raise ValueError("full_authoritative_qualification must be explicit")
    fast_qualification = config.get("fast_mt_qualification")
    if fast_qualification not in {True, False}:
        raise ValueError("fast_mt_qualification must be explicit")
    if qualification and fast_qualification:
        raise ValueError("Full and Fast qualification scopes must be separate runs")
    if fast_qualification:
        expected_scopes = {
            (split_id, policy_id)
            for split_id in ("split_001", "split_002")
            for policy_id in (
                "strict_current_baseline",
                "current_plus_existing_conditional_signal",
                "broad_data_qualified",
            )
        }
        observed_scopes = {
            (str(row["split_id"]), str(row["policy_id"]))
            for row in config["workloads"]
        }
        if observed_scopes != expected_scopes:
            raise ValueError("Fast MT qualification must cover both splits and all policies")
        for workload in config["workloads"]:
            if workload.get("date_counts") != {"train": 120, "validation": 77}:
                raise ValueError("Fast MT qualification date scope changed")
            if workload["structural_row_ids"] != ["structure_01", "structure_04"]:
                raise ValueError("Fast MT qualification candidate structures changed")
            if [int(value) for value in workload["checkpoints"]] != [100, 200]:
                raise ValueError("Fast MT qualification checkpoints changed")
    if qualification:
        expected_policies = {
            "strict_current_baseline",
            "current_plus_existing_conditional_signal",
            "broad_data_qualified",
        }
        if {str(row["policy_id"]) for row in config["workloads"]} != expected_policies:
            raise ValueError("Full qualification must cover strict, conditional, and broad")
        expected_structures = {
            "structure_01", "structure_02", "structure_03", "structure_04"
        }
        for workload in config["workloads"]:
            counts = workload.get("date_counts", {})
            if counts.get("train") is not None or counts.get("validation") is not None:
                raise ValueError("Full qualification must use complete train/validation folds")
            if set(workload["structural_row_ids"]) != expected_structures:
                raise ValueError("Full qualification must cover all structural rows")
            if [int(value) for value in workload["checkpoints"]] != [100, 200, 400, 800]:
                raise ValueError("Full qualification must cover all checkpoints")
    return config


def _selected_dates(
    protocol_config: dict[str, Any],
    *,
    split_id: str,
    fold: str,
    limit: int | None,
) -> pd.DatetimeIndex:
    dates = load_fold_dates(
        parent_paths(protocol_config).selection_date_assignments,
        outer_split_id=split_id,
        fold=fold,
    )
    if limit is None or int(limit) >= len(dates):
        return dates
    count = int(limit)
    if count < 2:
        raise ValueError("date limits must contain at least two dates")
    if fold == "train":
        return dates[np.linspace(0, len(dates) - 1, num=count, dtype=int)]
    return dates[-count:]


def _safe_fresh_runtime(path: Path, root: Path) -> None:
    target = path.resolve()
    allowed = root.resolve()
    if target == allowed or allowed not in target.parents:
        raise ValueError("thread audit runtime escapes controlled root")
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True, exist_ok=False)


def _daily_rank_ic(metadata: pd.DataFrame, prediction: np.ndarray) -> pd.Series:
    frame = metadata.copy()
    frame["prediction"] = np.asarray(prediction, dtype=float)
    finite = np.isfinite(frame["prediction"]) & np.isfinite(frame["__label"])
    rows: dict[str, float] = {}
    for date, group in frame.loc[finite].groupby("datetime", sort=True):
        if len(group) < 2 or group["prediction"].nunique(dropna=True) < 2:
            continue
        value = float(spearmanr(group["prediction"], group["__label"]).statistic)
        if np.isfinite(value):
            rows[pd.Timestamp(date).date().isoformat()] = value
    return pd.Series(rows, dtype=float)


def _daily_prediction_rank_agreement(
    metadata: pd.DataFrame, reference: np.ndarray, observed: np.ndarray
) -> tuple[float, float]:
    frame = metadata[["datetime"]].copy()
    frame["reference"] = reference
    frame["observed"] = observed
    values: list[float] = []
    for _, group in frame.groupby("datetime", sort=True):
        if len(group) < 2:
            continue
        value = float(spearmanr(group["reference"], group["observed"]).statistic)
        if np.isfinite(value):
            values.append(value)
    if not values:
        return float("nan"), float("nan")
    return float(np.mean(values)), float(np.min(values))


def _tree_payload(booster: Any, checkpoint: int) -> dict[str, Any]:
    dump = booster.dump_model(num_iteration=checkpoint)
    topology: list[dict[str, Any]] = []
    leaves: dict[str, float] = {}

    def visit(node: dict[str, Any], path: str) -> dict[str, Any]:
        if "leaf_index" in node:
            leaves[path] = float(node["leaf_value"])
            return {"leaf_index": int(node["leaf_index"])}
        payload = {
            "split_index": int(node["split_index"]),
            "split_feature": int(node["split_feature"]),
            "threshold": node["threshold"],
            "decision_type": node["decision_type"],
            "default_left": bool(node["default_left"]),
            "missing_type": node["missing_type"],
            "left_child": visit(node["left_child"], path + "L"),
            "right_child": visit(node["right_child"], path + "R"),
        }
        return payload

    for tree_index, tree in enumerate(dump["tree_info"]):
        topology.append(
            {
                "tree_index": tree_index,
                "tree_structure": visit(tree["tree_structure"], f"{tree_index}:")
            }
        )
    return {
        "topology_sha256": canonical_hash(topology),
        "leaf_values": leaves,
        "leaf_values_sha256": canonical_hash(leaves),
        "tree_count": len(topology),
    }


def _leaf_difference(reference: dict[str, float], observed: dict[str, float]) -> dict[str, Any]:
    same_paths = reference.keys() == observed.keys()
    if not same_paths:
        return {
            "leaf_paths_identical": False,
            "leaf_value_max_abs_difference": float("inf"),
            "leaf_value_mean_abs_difference": float("inf"),
        }
    differences = np.asarray(
        [abs(reference[key] - observed[key]) for key in reference], dtype=float
    )
    return {
        "leaf_paths_identical": True,
        "leaf_value_max_abs_difference": float(differences.max(initial=0.0)),
        "leaf_value_mean_abs_difference": float(differences.mean()) if len(differences) else 0.0,
    }


def _candidate_order(metrics: pd.DataFrame) -> list[str]:
    eligible = metrics
    if "status" in metrics:
        eligible = metrics.loc[metrics["status"].eq("pass")]
    return (
        eligible.sort_values(
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
        )["candidate_sha256"]
        .astype(str)
        .tolist()
    )


def _first_divergence(row: dict[str, Any]) -> str:
    checks = (
        ("tree_topology_identical", "tree_topology"),
        ("leaf_values_exact", "leaf_values"),
        ("prediction_exact", "prediction"),
        ("daily_rank_ic_exact", "daily_rank_ic"),
        ("candidate_ordering_identical", "candidate_ordering"),
        ("selected_candidate_identical", "selected_candidate"),
    )
    for field, stage in checks:
        if not bool(row[field]):
            return stage
    return "none"


def _prepare_workload(
    *,
    config: dict[str, Any],
    workload: dict[str, Any],
    policy_config: dict[str, Any],
    protocol_config: dict[str, Any],
    resolution: Any,
    feature_manifest: pd.DataFrame,
    cache_root: Path,
    runtime_dir: Path,
    timing: RuntimeTimingRecorder,
) -> tuple[Any, Any, list[str], dict[str, Any], pd.DataFrame]:
    split_id = str(workload["split_id"])
    policy_id = str(workload["policy_id"])
    factors = _arm_factors(feature_manifest, split_id=split_id, policy_id=policy_id)
    dates = {
        fold: _selected_dates(
            protocol_config,
            split_id=split_id,
            fold=fold,
            limit=workload.get("date_counts", {}).get(fold),
        )
        for fold in config["folds"]
    }
    audit = InputAccessAudit()
    with timing.measure("feature_loading"):
        matrix = _matrix_authority(
            protocol_config, selected_factors=factors, verify_hashes=True
        )
    labels_path = _labels_runtime_path(protocol_config, resolution)
    cached = {
        fold: get_or_build_projection_spools(
            cache_root=cache_root,
            protocol_config=protocol_config,
            resolution=resolution,
            matrix=matrix,
            split_id=split_id,
            fold=fold,
            dates=dates[fold],
            factors=factors,
            labels_path=labels_path,
            audit=audit,
            timing_recorder=timing,
        )
        for fold in config["folds"]
    }
    if audit.test_read_count != int(config["test_read_budget"]):
        raise AssertionError("thread audit exceeded test read budget")
    with timing.measure("preprocessing_fit", fold="train"):
        preprocessing = _fit_from_spool(list(cached["train"].spool_paths), factors)
    with timing.measure("train_transform", fold="train"):
        train = _materialize_fold(
            spool_paths=list(cached["train"].spool_paths),
            factors=factors,
            preprocessing=preprocessing,
            output_dir=runtime_dir,
            name="train",
            keep_metadata=False,
        )
    with timing.measure("validation_transform", fold="validation"):
        validation = _materialize_fold(
            spool_paths=list(cached["validation"].spool_paths),
            factors=factors,
            preprocessing=preprocessing,
            output_dir=runtime_dir,
            name="validation",
            keep_metadata=True,
        )
    if validation.metadata is None:
        raise AssertionError("thread audit validation metadata missing")
    identity = {
        "split_id": split_id,
        "policy_id": policy_id,
        "feature_order": factors,
        "feature_order_sha256": canonical_hash(factors),
        "train_dates_sha256": canonical_hash([value.date().isoformat() for value in dates["train"]]),
        "validation_dates_sha256": canonical_hash([value.date().isoformat() for value in dates["validation"]]),
        "train_feature_sha256": _array_hash(train.features),
        "train_target_sha256": _array_hash(train.target),
        "train_weight_sha256": _array_hash(train.weights),
        "validation_feature_sha256": _array_hash(validation.features),
        "validation_target_sha256": _array_hash(validation.target),
        "validation_weight_sha256": _array_hash(validation.weights),
        "validation_row_key_sha256": canonical_hash(
            validation.metadata[["datetime", "instrument"]].astype(str).to_dict("records")
        ),
        "validation_label_sha256": canonical_hash(
            validation.metadata["__label"].astype(str).tolist()
        ),
        "preprocessing_sha256": canonical_hash(_preprocessing_payload(preprocessing)),
        "cache": {
            fold: {
                "cache_key": value.cache_key,
                "cache_status": value.cache_status,
                "cache_hit": value.cache_hit,
            }
            for fold, value in cached.items()
        },
        "input_variables_constant_across_threads": True,
    }
    return train, validation, factors, identity, pd.DataFrame(audit.rows())


def run_thread_determinism_audit(
    *,
    config_path: Path,
    output_dir: Path,
    cache_root: Path,
    runtime_root: Path,
) -> dict[str, Any]:
    import lightgbm as lgb

    config = load_thread_audit_config(config_path)
    if output_dir.exists():
        raise FileExistsError("thread audit outputs are immutable; refusing overwrite")
    frozen_lightgbm_path = resolve(config["parents"]["lightgbm_config"])
    frozen_lightgbm = load_lightgbm_config(frozen_lightgbm_path)
    policy_config_path = resolve(config["parents"]["policy_config"])
    policy_config = load_policy_config(policy_config_path)
    protocol_config = yaml.safe_load(
        resolve(frozen_lightgbm["protocol_config"]).read_text(encoding="utf-8")
    )
    resolution = resolve_authoritative_parents(parent_paths(protocol_config))
    feature_manifest_path = resolve(config["parents"]["feature_manifest"])
    feature_manifest = pd.read_csv(feature_manifest_path)
    all_metrics: list[dict[str, Any]] = []
    all_runs: list[dict[str, Any]] = []
    all_parity: list[dict[str, Any]] = []
    all_timing: list[pd.DataFrame] = []
    identities: list[dict[str, Any]] = []
    access_frames: list[pd.DataFrame] = []
    scientific = config["scientific_parity"]

    for workload in config["workloads"]:
        split_id = str(workload["split_id"])
        policy_id = str(workload["policy_id"])
        workload_id = f"{split_id}__{policy_id}"
        runtime_dir = runtime_root / workload_id
        _safe_fresh_runtime(runtime_dir, runtime_root)
        timing = RuntimeTimingRecorder(
            execution_class="diagnostic_thread_audit",
            execution_profile=AUDIT_STAGE_ID,
            outer_split_id=split_id,
            policy_id=policy_id,
            execution_dtype="float64",
        )
        train, validation, factors, identity, access = _prepare_workload(
            config=config,
            workload=workload,
            policy_config=policy_config,
            protocol_config=protocol_config,
            resolution=resolution,
            feature_manifest=feature_manifest,
            cache_root=cache_root,
            runtime_dir=runtime_dir,
            timing=timing,
        )
        identity["workload_id"] = workload_id
        identities.append(identity)
        access.insert(0, "workload_id", workload_id)
        access_frames.append(access)
        structural_ids = set(workload["structural_row_ids"])
        checkpoints = sorted({int(value) for value in workload["checkpoints"]})
        candidates = [
            row for row in candidate_grid(frozen_lightgbm)
            if row["structural_row_id"] in structural_ids
            and int(row["num_boost_round"]) in checkpoints
        ]
        if len(candidates) != len(structural_ids) * len(checkpoints):
            raise ValueError(f"incomplete candidate scope for {workload_id}")
        predictions: dict[tuple[int, int, str], np.ndarray] = {}
        daily_ics: dict[tuple[int, int, str], pd.Series] = {}
        trees: dict[tuple[int, int, str], dict[str, Any]] = {}
        metric_frames: dict[tuple[int, int], pd.DataFrame] = {}
        ordering: dict[tuple[int, int], list[str]] = {}
        selected: dict[tuple[int, int], str] = {}

        for thread_count in [int(value) for value in config["thread_counts"]]:
            execution_config = with_lightgbm_threads(frozen_lightgbm, thread_count)
            for repeat in range(int(config["repeats"])):
                run_id = f"{workload_id}__{thread_count}t__r{repeat}"
                run_metric_rows: list[dict[str, Any]] = []
                run_started = time.perf_counter()
                run_cpu_started = time.process_time()
                run_peak = 0.0
                for structural_id in sorted(structural_ids):
                    structural = next(
                        row for row in frozen_lightgbm["structural_rows"]
                        if row["structural_row_id"] == structural_id
                    )
                    structural_checkpoints = [
                        value for value in checkpoints
                        if any(
                            row["structural_row_id"] == structural_id
                            and int(row["num_boost_round"]) == value
                            for row in candidates
                        )
                    ]
                    with timing.measure(
                        "lightgbm_dataset_build",
                        structural_row_id=structural_id,
                        train_rows=train.row_count,
                        thread_count=thread_count,
                        repeat=repeat,
                    ):
                        dataset = lgb.Dataset(
                            train.features,
                            label=train.target,
                            weight=train.weights,
                            feature_name=factors,
                            free_raw_data=False,
                            params={
                                "feature_pre_filter": False,
                                "data_random_seed": int(
                                    frozen_lightgbm["determinism"]["data_random_seed"]
                                ),
                            },
                        )
                        dataset.construct()
                    with _MemorySampler() as sampler:
                        with timing.measure(
                            "lightgbm_training",
                            structural_row_id=structural_id,
                            boosting_round=max(structural_checkpoints),
                            train_rows=train.row_count,
                            thread_count=thread_count,
                            repeat=repeat,
                        ):
                            booster = lgb.train(
                                _training_params(
                                    execution_config,
                                    {**structural, "num_boost_round": max(structural_checkpoints)},
                                ),
                                dataset,
                                num_boost_round=max(structural_checkpoints),
                            )
                    run_peak = max(run_peak, float(sampler.peak_mb))
                    for checkpoint in structural_checkpoints:
                        candidate = next(
                            row for row in candidates
                            if row["structural_row_id"] == structural_id
                            and int(row["num_boost_round"]) == checkpoint
                        )
                        key = (thread_count, repeat, str(candidate["candidate_sha256"]))
                        prediction = np.asarray(
                            booster.predict(
                                validation.features,
                                num_iteration=checkpoint,
                                num_threads=thread_count,
                            ),
                            dtype=float,
                        )
                        metrics = _validation_metrics(validation.metadata, prediction)
                        tree = _tree_payload(booster, checkpoint)
                        predictions[key] = prediction
                        daily_ics[key] = _daily_rank_ic(validation.metadata, prediction)
                        trees[key] = tree
                        passed = (
                            metrics["prediction_coverage"]
                            >= float(
                                frozen_lightgbm["validation"][
                                    "minimum_prediction_coverage"
                                ]
                            )
                            and int(metrics["daily_ic_count"]) > 0
                            and np.isfinite(metrics["mean_daily_rank_ic"])
                            and np.isfinite(metrics["daily_rank_ic_ir"])
                        )
                        row = {
                            "workload_id": workload_id,
                            "run_id": run_id,
                            "thread_count": thread_count,
                            "repeat": repeat,
                            **candidate,
                            **metrics,
                            "prediction_sha256": _array_hash(prediction),
                            "tree_topology_sha256": tree["topology_sha256"],
                            "leaf_values_sha256": tree["leaf_values_sha256"],
                            "tree_count": tree["tree_count"],
                            "status": "pass" if passed else "blocked",
                        }
                        run_metric_rows.append(row)
                        all_metrics.append(row)
                    del booster, dataset
                    gc.collect()
                run_metrics = pd.DataFrame(run_metric_rows)
                metric_frames[(thread_count, repeat)] = run_metrics
                ordering[(thread_count, repeat)] = _candidate_order(run_metrics)
                selected[(thread_count, repeat)] = str(
                    select_lightgbm_candidate(run_metrics)["candidate_sha256"]
                )
                wall_seconds = time.perf_counter() - run_started
                cpu_seconds = time.process_time() - run_cpu_started
                all_runs.append(
                    {
                        "workload_id": workload_id,
                        "run_id": run_id,
                        "thread_count": thread_count,
                        "repeat": repeat,
                        "wall_seconds": wall_seconds,
                        "cpu_seconds": cpu_seconds,
                        "cpu_core_equivalent": cpu_seconds / wall_seconds if wall_seconds else 0.0,
                        "peak_rss_mib": run_peak,
                        "candidate_order_sha256": canonical_hash(ordering[(thread_count, repeat)]),
                        "selected_candidate_sha256": selected[(thread_count, repeat)],
                    }
                )

        reference_run = (1, 0)
        for (thread_count, repeat), observed_metrics_frame in metric_frames.items():
            comparison_run = (
                (thread_count, 0) if repeat > 0 else reference_run
            )
            reference_metrics = metric_frames[comparison_run].set_index("candidate_sha256")
            observed_metrics = observed_metrics_frame.set_index("candidate_sha256")
            for candidate_sha in reference_metrics.index.astype(str):
                reference_key = (*comparison_run, candidate_sha)
                observed_key = (thread_count, repeat, candidate_sha)
                reference_prediction = predictions[reference_key]
                observed_prediction = predictions[observed_key]
                difference = observed_prediction - reference_prediction
                pearson = float(pearsonr(reference_prediction, observed_prediction).statistic)
                spearman = float(spearmanr(reference_prediction, observed_prediction).statistic)
                daily_mean, daily_min = _daily_prediction_rank_agreement(
                    validation.metadata, reference_prediction, observed_prediction
                )
                reference_ic = daily_ics[reference_key]
                observed_ic = daily_ics[observed_key].reindex(reference_ic.index)
                ic_difference = (observed_ic - reference_ic).abs()
                leaf = _leaf_difference(
                    trees[reference_key]["leaf_values"], trees[observed_key]["leaf_values"]
                )
                mean_ic_difference = abs(
                    float(observed_metrics.at[candidate_sha, "mean_daily_rank_ic"])
                    - float(reference_metrics.at[candidate_sha, "mean_daily_rank_ic"])
                )
                icir_difference = abs(
                    float(observed_metrics.at[candidate_sha, "daily_rank_ic_ir"])
                    - float(reference_metrics.at[candidate_sha, "daily_rank_ic_ir"])
                )
                row: dict[str, Any] = {
                    "workload_id": workload_id,
                    "thread_count": thread_count,
                    "repeat": repeat,
                    "candidate_sha256": candidate_sha,
                    "reference_thread_count": comparison_run[0],
                    "reference_repeat": comparison_run[1],
                    "comparison_kind": "reference" if (thread_count, repeat) == reference_run else (
                        "same_thread_repeat" if repeat > 0 else "cross_thread"
                    ),
                    "tree_topology_identical": trees[reference_key]["topology_sha256"] == trees[observed_key]["topology_sha256"],
                    **leaf,
                    "leaf_values_exact": trees[reference_key]["leaf_values_sha256"] == trees[observed_key]["leaf_values_sha256"],
                    "prediction_exact": bool(np.array_equal(reference_prediction, observed_prediction)),
                    "prediction_max_abs_difference": float(np.max(np.abs(difference), initial=0.0)),
                    "prediction_mean_abs_difference": float(np.mean(np.abs(difference))),
                    "prediction_rmse": float(np.sqrt(np.mean(difference**2))),
                    "prediction_pearson": pearson,
                    "prediction_spearman": spearman,
                    "daily_prediction_rank_agreement_mean": daily_mean,
                    "daily_prediction_rank_agreement_min": daily_min,
                    "daily_rank_ic_exact": bool(reference_ic.equals(observed_ic)),
                    "daily_rank_ic_max_abs_difference": float(ic_difference.max()) if len(ic_difference) else 0.0,
                    "mean_daily_rank_ic_abs_difference": mean_ic_difference,
                    "daily_rank_ic_ir_abs_difference": icir_difference,
                    "candidate_ordering_identical": ordering[comparison_run] == ordering[(thread_count, repeat)],
                    "selected_candidate_identical": selected[comparison_run] == selected[(thread_count, repeat)],
                }
                row["exact_parity"] = bool(
                    row["tree_topology_identical"]
                    and row["leaf_values_exact"]
                    and row["prediction_exact"]
                    and row["daily_rank_ic_exact"]
                    and row["candidate_ordering_identical"]
                    and row["selected_candidate_identical"]
                )
                row["scientific_parity"] = bool(
                    spearman >= float(scientific["minimum_prediction_spearman"])
                    and mean_ic_difference <= float(scientific["maximum_mean_rank_ic_difference"])
                    and icir_difference <= float(scientific["maximum_icir_difference"])
                    and row["selected_candidate_identical"]
                )
                row["first_divergence"] = _first_divergence(row)
                all_parity.append(row)
        del train, validation
        gc.collect()
        shutil.rmtree(runtime_dir)
        all_timing.append(timing.frame())

    runs = pd.DataFrame(all_runs)
    metrics = pd.DataFrame(all_metrics)
    parity = pd.DataFrame(all_parity)
    comparisons = parity.loc[parity["comparison_kind"].ne("reference")]
    cross_thread = comparisons.loc[comparisons["comparison_kind"].eq("cross_thread")]
    repeat_rows = comparisons.loc[comparisons["comparison_kind"].eq("same_thread_repeat")]
    stable_threads = {
        int(value): bool(
            repeat_rows.loc[repeat_rows["thread_count"].eq(value), "exact_parity"].all()
        )
        for value in config["thread_counts"]
    }
    exact_threads = [
        int(value) for value in config["thread_counts"]
        if stable_threads[int(value)] and (
            value == 1 or bool(
                cross_thread.loc[cross_thread["thread_count"].eq(value), "exact_parity"].all()
            )
        )
    ]
    scientific_threads = [
        int(value) for value in config["thread_counts"]
        if stable_threads[int(value)] and (
            value == 1 or bool(
                cross_thread.loc[cross_thread["thread_count"].eq(value), "scientific_parity"].all()
            )
        )
    ]
    mean_walls = runs.groupby("thread_count", sort=True)["wall_seconds"].mean()
    reference_wall = float(mean_walls.loc[1])
    scaling = pd.DataFrame(
        [
            {
                "thread_count": int(thread_count),
                "mean_wall_seconds": float(wall),
                "speedup_vs_1t": reference_wall / float(wall),
                "exact_parity_all": int(thread_count) in exact_threads,
                "scientific_parity_all": int(thread_count) in scientific_threads,
            }
            for thread_count, wall in mean_walls.items()
        ]
    )
    eligible = scaling.loc[scaling["exact_parity_all"]]
    fastest_exact = int(eligible.sort_values("mean_wall_seconds").iloc[0]["thread_count"])
    summary = {
        "schema_version": 1,
        "stage_id": AUDIT_STAGE_ID,
        "decision_authority": "execution_protocol_evidence_only",
        "scientific_model_selection_authorized": False,
        "strategy_v2_authorized": False,
        "frozen_lightgbm_config_sha256": canonical_hash(frozen_lightgbm),
        "audit_config_sha256": canonical_hash(config),
        "lightgbm_version": lgb.__version__,
        "thread_environment": thread_environment(),
        "input_identity_constant": True,
        "same_thread_repeats_exact": bool(repeat_rows["exact_parity"].all()),
        "exact_thread_counts": exact_threads,
        "scientifically_equivalent_thread_counts": scientific_threads,
        "fastest_exact_thread_count": fastest_exact,
        "full_authoritative_qualification_scope": bool(
            config["full_authoritative_qualification"]
        ),
        "fast_mt_qualification_scope": bool(config["fast_mt_qualification"]),
        "workload_ids": sorted(identity["workload_id"] for identity in identities),
        "full_authoritative_eligible": bool(
            config["full_authoritative_qualification"] and fastest_exact > 1
        ),
        "qualification_rule": "exact_parity_only",
    }
    output_frames = {
        "runs.csv": runs,
        "candidate_metrics.csv": metrics,
        "parity.csv": parity,
        "thread_scaling.csv": scaling,
        "runtime_timing.csv": pd.DataFrame(
            [row for frame in all_timing for row in frame.to_dict("records")],
            columns=all_timing[0].columns,
        ),
        "access_audit.csv": pd.concat(access_frames, ignore_index=True),
    }
    output_dir.mkdir(parents=True, exist_ok=False)
    for name, frame in output_frames.items():
        frame.to_csv(output_dir / name, index=False)
    (output_dir / "input_identity.json").write_text(
        json.dumps(identities, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    summary["output_sha256"] = {
        name: file_sha256(output_dir / name) for name in output_frames
    }
    summary["output_sha256"]["input_identity.json"] = file_sha256(
        output_dir / "input_identity.json"
    )
    summary["summary_sha256"] = canonical_hash(summary)
    (output_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return summary
