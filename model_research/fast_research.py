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

from research_validation.feature_matrix import canonical_hash, file_sha256

from .development_dry_run import _fit_from_spool
from .feature_pool_experiment import _arm_factors, _array_hash
from .feature_pool_policy import load_policy_config
from .inputs import InputAccessAudit, load_fold_dates
from .lightgbm_models import (
    _training_params,
    candidate_grid,
    load_lightgbm_config,
    select_lightgbm_candidate,
)
from .linear_models import _MemorySampler, _materialize_fold, _validation_metrics
from .lineage import resolve_authoritative_parents
from .protocol import PROJECT_ROOT, parent_paths, resolve
from .protocol_v1_1 import _labels_runtime_path, _matrix_authority
from .research_cache import get_or_build_projection_spools
from .runtime_timing import RuntimeTimingRecorder


FAST_PROFILE_ID = "fast_research_v1"
EXECUTION_CLASS = "exploratory_fast"
FAST_PROFILE_CONFIG_SHA256 = "d3b7d6c8b02d00132739dad2c23f1ea01d45f27d227ebb0b2f44bb3e43d83e92"


def load_fast_research_config(path: Path) -> dict[str, Any]:
    config = yaml.safe_load(path.read_text(encoding="utf-8"))
    required_false = (
        "authoritative_execution",
        "selection_authorized",
        "production_model_selected",
        "strategy_v2_authorized",
    )
    if config.get("profile_id") != FAST_PROFILE_ID:
        raise ValueError("fast research profile id is not frozen v1")
    if config.get("execution_class") != EXECUTION_CLASS:
        raise ValueError("fast research execution class mismatch")
    if any(config.get(field) is not False for field in required_false):
        raise ValueError("fast research authority flags must all remain false")
    if config.get("date_selection") != "fixed_evenly_spaced_train_full_validation":
        raise ValueError("fast research v1 date selection changed")
    if config.get("test_read_budget") != 0:
        raise ValueError("fast research test read budget must be zero")
    if config.get("historical_replay_budget") != 0:
        raise ValueError("fast research historical replay budget must be zero")
    if config.get("portfolio_test_release_budget") != 0:
        raise ValueError("fast research portfolio test release budget must be zero")
    if config.get("split_ids") != ["split_001", "split_002"]:
        raise ValueError("fast research v1 split scope changed")
    if canonical_hash(config) != FAST_PROFILE_CONFIG_SHA256:
        raise ValueError("fast research v1 config changed; create a new profile version")
    return config


def _profile_dates(
    *,
    profile: dict[str, Any],
    protocol_config: dict[str, Any],
    split_id: str,
    fold: str,
) -> pd.DatetimeIndex:
    if fold not in {"train", "validation"}:
        raise PermissionError("fast research only exposes development folds")
    full = load_fold_dates(
        parent_paths(protocol_config).selection_date_assignments,
        outer_split_id=split_id,
        fold=fold,
    )
    count = int(profile["date_counts"][fold])
    if fold == "train":
        positions = np.linspace(0, len(full) - 1, num=count, dtype=int)
        dates = full[positions]
    else:
        dates = full[-count:]
    expected = profile["date_scope"][split_id][fold]
    values = [value.date().isoformat() for value in dates]
    observed = {
        "count": len(values),
        "start": values[0],
        "end": values[-1],
        "sha256": canonical_hash(values),
    }
    if observed != expected:
        raise ValueError(f"frozen fast date scope mismatch: {split_id}/{fold}")
    return dates


def _fast_candidates(
    lightgbm_config: dict[str, Any], profile: dict[str, Any]
) -> list[dict[str, Any]]:
    structural_ids = list(profile["candidate_subset"]["structural_row_ids"])
    checkpoints = [int(value) for value in profile["candidate_subset"]["checkpoints"]]
    selected = [
        row
        for row in candidate_grid(lightgbm_config)
        if row["structural_row_id"] in structural_ids
        and int(row["num_boost_round"]) in checkpoints
    ]
    if len(selected) != len(structural_ids) * len(checkpoints):
        raise ValueError("fast candidate subset is not contained in full candidate table")
    return selected


def _fresh_runtime(path: Path, root: Path) -> None:
    target = path.resolve()
    allowed = root.resolve()
    if target == allowed or allowed not in target.parents:
        raise ValueError("fast runtime path escapes controlled root")
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True, exist_ok=False)


def _require_child_path(path: Path, configured_root: str, purpose: str) -> None:
    allowed = resolve(configured_root).resolve()
    target = path.resolve()
    if target == allowed or allowed not in target.parents:
        raise ValueError(f"fast {purpose} path escapes configured non-authoritative root")


def _run_fast_arm(
    *,
    profile: dict[str, Any],
    policy_config: dict[str, Any],
    protocol_config: dict[str, Any],
    resolution: Any,
    lightgbm_config: dict[str, Any],
    feature_manifest: pd.DataFrame,
    split_id: str,
    policy_id: str,
    cache_root: Path,
    runtime_root: Path,
) -> tuple[pd.DataFrame, dict[str, Any], pd.DataFrame, pd.DataFrame]:
    import lightgbm as lgb

    factors = _arm_factors(feature_manifest, split_id=split_id, policy_id=policy_id)
    dates = {
        fold: _profile_dates(
            profile=profile,
            protocol_config=protocol_config,
            split_id=split_id,
            fold=fold,
        )
        for fold in ("train", "validation")
    }
    timing = RuntimeTimingRecorder(
        execution_class=EXECUTION_CLASS,
        execution_profile=FAST_PROFILE_ID,
        outer_split_id=split_id,
        policy_id=policy_id,
        feature_count=len(factors),
        execution_dtype="float64",
        thread_count=int(lightgbm_config["determinism"]["num_threads"]),
    )
    audit = InputAccessAudit()
    with timing.measure("feature_loading"):
        matrix = _matrix_authority(
            protocol_config, selected_factors=factors, verify_hashes=True
        )
    labels_path = _labels_runtime_path(protocol_config, resolution)
    runtime_dir = runtime_root / split_id / policy_id
    _fresh_runtime(runtime_dir, runtime_root)
    started = time.perf_counter()
    with _MemorySampler() as sampler:
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
            for fold in ("train", "validation")
        }
        train_spools = list(cached["train"].spool_paths)
        validation_spools = list(cached["validation"].spool_paths)
        with timing.measure("preprocessing_fit", fold="train"):
            preprocessing = _fit_from_spool(train_spools, factors)
        with timing.measure("train_transform", fold="train") as payload:
            train_data = _materialize_fold(
                spool_paths=train_spools,
                factors=factors,
                preprocessing=preprocessing,
                output_dir=runtime_dir,
                name="train",
                keep_metadata=False,
            )
            payload["output_rows"] = train_data.row_count
            payload["train_rows"] = train_data.row_count
        with timing.measure("validation_transform", fold="validation") as payload:
            validation_data = _materialize_fold(
                spool_paths=validation_spools,
                factors=factors,
                preprocessing=preprocessing,
                output_dir=runtime_dir,
                name="validation",
                keep_metadata=True,
            )
            payload["output_rows"] = validation_data.row_count
            payload["validation_rows"] = validation_data.row_count
        if validation_data.metadata is None:
            raise AssertionError("fast validation metadata missing")
        dataset_params = {
            "feature_pre_filter": False,
            "data_random_seed": int(lightgbm_config["determinism"]["data_random_seed"]),
        }
        dataset_identity = canonical_hash(
            {
                "profile_id": FAST_PROFILE_ID,
                "split_id": split_id,
                "feature_order_sha256": canonical_hash(factors),
                "train_date_sha256": profile["date_scope"][split_id]["train"]["sha256"],
                "train_rows": train_data.row_count,
                "dataset_params": dataset_params,
                "dtype": "float64",
            }
        )
        with timing.measure(
            "lightgbm_dataset_build",
            train_rows=train_data.row_count,
            cache_hit=False,
            dataset_identity_sha256=dataset_identity,
        ):
            dataset = lgb.Dataset(
                train_data.features,
                label=train_data.target,
                weight=train_data.weights,
                feature_name=factors,
                free_raw_data=False,
                params=dataset_params,
            )
            dataset.construct()
        candidates = _fast_candidates(lightgbm_config, profile)
        candidate_hash = canonical_hash([row["candidate_sha256"] for row in candidates])
        metric_rows: list[dict[str, Any]] = []
        for structural_id in profile["candidate_subset"]["structural_row_ids"]:
            structural_candidates = [
                row for row in candidates if row["structural_row_id"] == structural_id
            ]
            max_round = max(int(row["num_boost_round"]) for row in structural_candidates)
            template = next(
                row
                for row in lightgbm_config["structural_rows"]
                if row["structural_row_id"] == structural_id
            )
            with timing.measure(
                "lightgbm_training",
                structural_row_id=structural_id,
                boosting_round=max_round,
                train_rows=train_data.row_count,
                dataset_identity_sha256=dataset_identity,
            ):
                booster = lgb.train(
                    _training_params(
                        lightgbm_config,
                        {**template, "num_boost_round": max_round},
                    ),
                    dataset,
                    num_boost_round=max_round,
                )
            for candidate in structural_candidates:
                checkpoint = int(candidate["num_boost_round"])
                with timing.measure(
                    "validation_prediction",
                    structural_row_id=structural_id,
                    candidate_sha256=candidate["candidate_sha256"],
                    boosting_round=checkpoint,
                    validation_rows=validation_data.row_count,
                ):
                    prediction = booster.predict(
                        validation_data.features, num_iteration=checkpoint
                    )
                with timing.measure(
                    "validation_metrics",
                    structural_row_id=structural_id,
                    candidate_sha256=candidate["candidate_sha256"],
                    boosting_round=checkpoint,
                    validation_rows=validation_data.row_count,
                ):
                    metrics = _validation_metrics(
                        validation_data.metadata, prediction
                    )
                passed = (
                    metrics["prediction_coverage"]
                    >= float(lightgbm_config["validation"]["minimum_prediction_coverage"])
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
                        "fast_candidate_table_sha256": candidate_hash,
                        "status": "pass" if passed else "blocked",
                        "execution_class": EXECUTION_CLASS,
                        "execution_profile": FAST_PROFILE_ID,
                        "authoritative_execution": False,
                        "selection_authorized": False,
                        "production_model_selected": False,
                        "strategy_v2_authorized": False,
                    }
                )
            del booster
        metrics = pd.DataFrame(metric_rows)
        selected = select_lightgbm_candidate(metrics)
        summary = {
            "outer_split_id": split_id,
            "policy_id": policy_id,
            "feature_count": len(factors),
            "train_rows": train_data.row_count,
            "validation_rows": validation_data.row_count,
            "selected_fast_candidate_sha256": str(selected["candidate_sha256"]),
            "selected_fast_structural_row_id": str(selected["structural_row_id"]),
            "selected_fast_num_boost_round": int(selected["num_boost_round"]),
            "mean_daily_rank_ic": float(selected["mean_daily_rank_ic"]),
            "daily_rank_ic_ir": float(selected["daily_rank_ic_ir"]),
            "prediction_coverage": float(selected["prediction_coverage"]),
            "wall_seconds": time.perf_counter() - started,
            "peak_rss_mib": sampler.peak_mb,
            "train_cache_hit": cached["train"].cache_hit,
            "validation_cache_hit": cached["validation"].cache_hit,
            "cache_disk_bytes": sum(value.disk_bytes for value in cached.values()),
            "train_date_scope_sha256": profile["date_scope"][split_id]["train"]["sha256"],
            "validation_date_scope_sha256": profile["date_scope"][split_id]["validation"]["sha256"],
            "preprocessing_fit_scope": "train_only",
            "test_feature_read_count": audit.feature_reads["test"],
            "test_label_read_count": audit.label_reads["test"],
        }
        del dataset, train_data, validation_data, preprocessing
        gc.collect()
    shutil.rmtree(runtime_dir)
    audit_frame = pd.DataFrame(
        [
            {"outer_split_id": split_id, "policy_id": policy_id, **row}
            for row in audit.rows()
        ]
    )
    return metrics, summary, audit_frame, timing.frame()


def _promotion_decision(deltas: pd.DataFrame, profile: dict[str, Any]) -> tuple[str, str]:
    gate = profile["promotion_gate"]
    values = deltas["mean_daily_rank_ic_delta"].to_numpy(dtype=float)
    mean_delta = float(values.mean())
    positive_fraction = float((values > 0).mean())
    nonpositive_fraction = float((values <= 0).mean())
    if (
        mean_delta >= float(gate["promote_minimum_mean_rank_ic_delta"])
        and positive_fraction >= float(gate["promote_minimum_positive_split_fraction"])
    ):
        return "promote_to_full", "pre_registered_fast_resource_gate_passed"
    if (
        mean_delta <= float(gate["reject_maximum_mean_rank_ic_delta"])
        and nonpositive_fraction >= float(gate["reject_minimum_nonpositive_split_fraction"])
    ):
        return "reject_before_full", "pre_registered_fast_resource_gate_failed"
    return "inconclusive", "mixed_or_small_development_only_delta"


def _concat_timing_frames(frames: list[pd.DataFrame]) -> pd.DataFrame:
    if not frames:
        return pd.DataFrame()
    records = [row for frame in frames for row in frame.to_dict("records")]
    return pd.DataFrame(records, columns=frames[0].columns)


def run_fast_research_pair(
    *,
    config_path: Path,
    baseline_id: str,
    proposal_id: str,
    output_dir: Path,
    cache_root: Path,
    runtime_root: Path,
    feature_manifest_path: Path | None = None,
    policy_manifest_path: Path | None = None,
    changed_dimension: str = "feature_pool_policy",
) -> dict[str, Any]:
    profile = load_fast_research_config(config_path)
    if baseline_id == proposal_id or not baseline_id.strip() or not proposal_id.strip():
        raise ValueError("fast research requires two distinct non-empty proposal ids")
    if not changed_dimension.strip():
        raise ValueError("fast research changed_dimension must be explicit")
    if output_dir.exists():
        raise FileExistsError("fast research outputs are immutable; refusing overwrite")
    _require_child_path(output_dir, profile["output_root"], "output")
    _require_child_path(runtime_root, profile["runtime_root"], "runtime")
    cache_allowed = (PROJECT_ROOT / "tmp" / "research_productivity_v1").resolve()
    if cache_root.resolve() != cache_allowed and cache_allowed not in cache_root.resolve().parents:
        raise ValueError("fast cache path escapes tmp/research_productivity_v1")
    policy_config_path = resolve(profile["parents"]["policy_config"])
    policy_config = load_policy_config(policy_config_path)
    lightgbm_config = load_lightgbm_config(
        resolve(policy_config["parents"]["lightgbm_config"])
    )
    frozen = profile["frozen_parent_contracts"]
    if canonical_hash(lightgbm_config) != frozen["lightgbm_config_sha256"]:
        raise ValueError("fast profile LightGBM parent changed; create a new profile")
    if int(lightgbm_config["determinism"]["num_threads"]) != int(profile["num_threads"]):
        raise ValueError("fast profile thread count differs from deterministic model config")
    if int(lightgbm_config["determinism"]["seed"]) != int(profile["seed"]):
        raise ValueError("fast profile seed differs from deterministic model config")
    if profile["execution_dtype"] != "float64":
        raise ValueError("fast research v1 execution dtype must remain float64")
    protocol_config = yaml.safe_load(
        resolve(lightgbm_config["protocol_config"]).read_text(encoding="utf-8")
    )
    if canonical_hash(protocol_config["preprocessing"]) != frozen[
        "preprocessing_config_sha256"
    ]:
        raise ValueError("fast profile preprocessing parent changed")
    metric_registry_sha256 = file_sha256(
        resolve("outputs/research_model_protocol_v1_1/current/metric_registry.json")
    )
    if metric_registry_sha256 != frozen["metric_registry_sha256"]:
        raise ValueError("fast profile metric registry changed")
    resolution = resolve_authoritative_parents(parent_paths(protocol_config))
    feature_manifest_path = feature_manifest_path or resolve(
        profile["parents"]["feature_manifest"]
    )
    policy_manifest_path = policy_manifest_path or resolve(
        profile["parents"]["policy_manifest"]
    )
    feature_manifest = pd.read_csv(feature_manifest_path)
    policies = pd.read_csv(policy_manifest_path)
    chosen = policies.loc[
        policies["policy_id"].isin([baseline_id, proposal_id])
        & policies["outer_split_id"].isin(profile["split_ids"])
    ]
    if len(chosen) != 2 * len(profile["split_ids"]):
        raise ValueError("fast research policy manifest scope is incomplete")
    if not chosen["decision_authority"].eq("diagnostic_only").all():
        raise ValueError("fast research inputs must remain diagnostic only")
    for authority_field in ("selection_authorized", "strategy_v2_authorized"):
        if not chosen[authority_field].astype(str).str.lower().eq("false").all():
            raise ValueError(f"fast research input {authority_field} must remain false")
    for row in chosen.itertuples(index=False):
        factors = _arm_factors(
            feature_manifest,
            split_id=str(row.outer_split_id),
            policy_id=str(row.policy_id),
        )
        if len(factors) != int(row.factor_count):
            raise ValueError("fast research feature/policy manifest count mismatch")
        if canonical_hash(factors) != str(row.feature_order_sha256):
            raise ValueError("fast research feature/policy manifest order mismatch")

    metric_frames = []
    summary_rows = []
    audit_frames = []
    timing_frames = []
    for split_id in profile["split_ids"]:
        for policy_id in (baseline_id, proposal_id):
            metrics, summary, audit, timing = _run_fast_arm(
                profile=profile,
                policy_config=policy_config,
                protocol_config=protocol_config,
                resolution=resolution,
                lightgbm_config=lightgbm_config,
                feature_manifest=feature_manifest,
                split_id=split_id,
                policy_id=policy_id,
                cache_root=cache_root,
                runtime_root=runtime_root,
            )
            metric_frames.append(metrics)
            summary_rows.append(summary)
            audit_frames.append(audit)
            timing_frames.append(timing)
    summaries = pd.DataFrame(summary_rows)
    baseline = summaries.loc[summaries["policy_id"].eq(baseline_id)].set_index(
        "outer_split_id"
    )
    proposal = summaries.loc[summaries["policy_id"].eq(proposal_id)].set_index(
        "outer_split_id"
    )
    if not baseline.index.equals(proposal.index):
        raise AssertionError("fast baseline/proposal split scopes differ")
    if not (
        baseline["train_date_scope_sha256"].equals(proposal["train_date_scope_sha256"])
        and baseline["validation_date_scope_sha256"].equals(
            proposal["validation_date_scope_sha256"]
        )
    ):
        raise AssertionError("fast baseline/proposal date scopes differ")
    delta_rows = []
    for split_id in baseline.index:
        delta_rows.append(
            {
                "outer_split_id": split_id,
                "baseline_id": baseline_id,
                "proposal_id": proposal_id,
                "baseline_mean_daily_rank_ic": baseline.at[split_id, "mean_daily_rank_ic"],
                "proposal_mean_daily_rank_ic": proposal.at[split_id, "mean_daily_rank_ic"],
                "mean_daily_rank_ic_delta": proposal.at[split_id, "mean_daily_rank_ic"]
                - baseline.at[split_id, "mean_daily_rank_ic"],
                "baseline_daily_rank_ic_ir": baseline.at[split_id, "daily_rank_ic_ir"],
                "proposal_daily_rank_ic_ir": proposal.at[split_id, "daily_rank_ic_ir"],
                "daily_rank_ic_ir_delta": proposal.at[split_id, "daily_rank_ic_ir"]
                - baseline.at[split_id, "daily_rank_ic_ir"],
            }
        )
    deltas = pd.DataFrame(delta_rows)
    promotion_status, promotion_reason = _promotion_decision(deltas, profile)
    audit = pd.concat(audit_frames, ignore_index=True)
    if int(audit.loc[audit["fold"].eq("test"), "read_count"].sum()) != 0:
        raise AssertionError("fast research accessed historical test")
    output_dir.mkdir(parents=True, exist_ok=False)
    outputs = {
        "arm_metrics.csv": pd.concat(metric_frames, ignore_index=True),
        "arm_summary.csv": summaries,
        "paired_deltas.csv": deltas,
        "access_audit.csv": audit,
        "runtime_timing.csv": _concat_timing_frames(timing_frames),
    }
    for name, frame in outputs.items():
        frame.to_csv(output_dir / name, index=False)
    proposal_manifest = {
        "proposal_id": proposal_id,
        "parent_baseline": baseline_id,
        "changed_dimension": changed_dimension,
        "config_hash": canonical_hash(profile),
        "feature_manifest_sha256": file_sha256(feature_manifest_path),
        "fast_execution_profile": FAST_PROFILE_ID,
    }
    (output_dir / "proposal_manifest.json").write_text(
        json.dumps(proposal_manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    receipt = {
        "schema_version": 1,
        "execution_class": EXECUTION_CLASS,
        "execution_profile": FAST_PROFILE_ID,
        "authoritative_execution": False,
        "selection_authorized": False,
        "production_model_selected": False,
        "strategy_v2_authorized": False,
        "promotion_is_scientific_winner": False,
        "promotion_status": promotion_status,
        "promotion_reason": promotion_reason,
        "baseline_id": baseline_id,
        "proposal_id": proposal_id,
        "split_ids": profile["split_ids"],
        "test_feature_read_count": 0,
        "test_label_read_count": 0,
        "historical_replay_count": 0,
        "portfolio_test_release_count": 0,
        "preprocessing_fit_scope": "train_only",
        "metric_registry_sha256": metric_registry_sha256,
        "profile_config_sha256": file_sha256(config_path),
        "output_sha256": {
            name: file_sha256(output_dir / name) for name in outputs
        },
    }
    receipt["receipt_sha256"] = canonical_hash(receipt)
    (output_dir / "fast_research_receipt.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return receipt
