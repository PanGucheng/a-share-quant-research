from __future__ import annotations

import gc
import json
import shutil
import time
from datetime import datetime, timezone
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

from .development_dry_run import _fit_from_spool
from .forward_protocol import load_forward_config, resolve
from .inputs import InputAccessAudit, load_split_feature_order, project_features
from .lightgbm_models import _training_params, load_lightgbm_config
from .lineage import resolve_authoritative_parents
from .linear_models import (
    _MemorySampler,
    _materialize_fold,
    _preprocessing_payload,
    _spool_fold,
    _spool_hash,
)
from .preprocessing import daily_equal_weights, fit_weighted_preprocessing
from .protocol import parent_paths
from .protocol_v1_1 import _labels_runtime_path, _matrix_authority
from .targets import eligible_daily_cross_sectional_rank_centered


PROJECT_ROOT = Path(__file__).resolve().parents[1]
STAGE_ID = "prospective_forward_candidate_v1"
CANARY_OUTPUTS = (
    "access_audit.csv",
    "artifact_manifest.json",
    "canary_results.csv",
    "contract_status.csv",
    "parent_receipts.csv",
    "readiness_summary.csv",
    "resolved_config.json",
    "resource_summary.csv",
    "run_report.md",
    "run_review_bundle.json",
)
REFIT_OUTPUTS = (
    "access_audit.csv",
    "artifact_manifest.json",
    "candidate_model_receipt.csv",
    "contract_status.csv",
    "feature_importance.csv",
    "forward_candidate_freeze.json",
    "parent_receipts.csv",
    "readiness_summary.csv",
    "resolved_config.json",
    "resource_summary.csv",
    "run_report.md",
    "sample_eligibility_receipt.csv",
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


def _array_hash(array: np.ndarray) -> str:
    value = np.ascontiguousarray(np.asarray(array))
    return canonical_hash(
        {
            "dtype": str(value.dtype),
            "shape": list(value.shape),
            "bytes_sha256": __import__("hashlib").sha256(
                value.tobytes()
            ).hexdigest(),
        }
    )


def _parent(
    path: Path, *, expected_stage: str
) -> dict[str, Any]:
    manifest = load_artifact_manifest(path)
    if (
        manifest["stage_id"] != expected_stage
        or manifest["artifact_status"] != "pass"
        or manifest["lineage_status"] != "complete"
        or bool(manifest["code_dirty"])
    ):
        raise ValueError(f"invalid parent artifact: {path}")
    issues = validate_manifest_outputs(manifest, path.parent)
    if issues:
        raise ValueError(
            f"stale parent artifact {path}: "
            + "|".join(issue.reason for issue in issues)
        )
    return manifest


def _protocol_inputs(
    config: dict[str, Any],
    *,
    factor_limit: int | None,
) -> tuple[
    dict[str, Any],
    Any,
    list[str],
    pd.Series,
    Any,
]:
    protocol_config = __import__("yaml").safe_load(
        resolve(config["parents"]["protocol_config"]).read_text(
            encoding="utf-8"
        )
    )
    resolution = resolve_authoritative_parents(parent_paths(protocol_config))
    ordered, allowlist = load_split_feature_order(
        resolve(config["parents"]["factor_weights"]),
        resolve(config["parents"]["split_allowlist_manifest"]),
        outer_split_id="split_003",
    )
    factors = ordered["factor"].astype(str).tolist()
    if factor_limit is not None:
        factors = factors[:factor_limit]
    matrix = _matrix_authority(
        protocol_config,
        selected_factors=factors,
        verify_hashes=True,
    )
    return protocol_config, resolution, factors, allowlist, matrix


def _selected_candidate(config: dict[str, Any]) -> dict[str, Any]:
    selected = json.loads(
        resolve(config["parents"]["selected_hyperparameters"]).read_text(
            encoding="utf-8"
        )
    )["split_003"]
    candidate = config["candidate"]
    if (
        selected["structural_row_id"] != candidate["structural_row_id"]
        or int(selected["num_boost_round"])
        != int(candidate["num_boost_round"])
    ):
        raise ValueError("forward candidate differs from frozen split_003 spec")
    return selected


def _training_dates(
    config: dict[str, Any],
    *,
    limit: int | None = None,
) -> pd.DatetimeIndex:
    label_name = config["training"]["label_name"]
    labels = pd.read_parquet(
        resolve(config["parents"]["labels_runtime"]),
        columns=["datetime", label_name],
    )
    labels["datetime"] = pd.to_datetime(labels["datetime"]).dt.normalize()
    counts = labels.groupby("datetime")[label_name].count()
    dates = pd.DatetimeIndex(
        counts.loc[
            counts.ge(int(config["training"]["minimum_daily_pairs"]))
        ].index
    )
    dates = dates[
        (dates >= pd.Timestamp(config["training"]["start_date"]))
        & (dates <= pd.Timestamp(config["training"]["end_date"]))
    ].sort_values()
    if limit is not None:
        dates = dates[:limit]
    if dates.empty:
        raise ValueError("no candidate training dates")
    return dates


def _quarantine_dates(
    config: dict[str, Any], *, limit: int
) -> pd.DatetimeIndex:
    label_name = config["training"]["label_name"]
    labels = pd.read_parquet(
        resolve(config["parents"]["labels_runtime"]),
        columns=["datetime", label_name],
    )
    dates = pd.DatetimeIndex(
        pd.to_datetime(labels["datetime"]).dt.normalize().drop_duplicates()
    ).sort_values()
    start = pd.Timestamp(
        config["temporal_boundary"]["retrospective_extension_start"]
    )
    end = pd.Timestamp(config["temporal_boundary"]["current_snapshot_end"])
    selected = dates[(dates >= start) & (dates <= end)][:limit]
    if len(selected) != limit:
        raise ValueError("insufficient quarantine canary dates")
    return selected


def _candidate_parents(
    config: dict[str, Any],
    *,
    include_canary: bool,
) -> list[tuple[str, Path, dict[str, Any]]]:
    specs = [
        (
            "forward_protocol",
            resolve(
                "outputs/prospective_forward_protocol_v1/current/"
                "artifact_manifest.json"
            ),
            "prospective_forward_protocol_v1",
        ),
        (
            "historical_comparison",
            resolve(config["parents"]["historical_comparison_manifest"]),
            "historical_model_comparison_v1",
        ),
        (
            "selection",
            resolve(config["parents"]["selection_manifest"]),
            "research_selection_lineage_closure_v1",
        ),
        (
            "matrix",
            resolve(config["parents"]["matrix_manifest"]),
            "full_research_feature_matrix_v4",
        ),
        (
            "labels",
            resolve(config["parents"]["labels_manifest"]),
            "full_research_labels_v2",
        ),
    ]
    if include_canary:
        specs.append(
            (
                "candidate_canary",
                resolve(
                    "outputs/prospective_forward_candidate_v1/canary/"
                    "artifact_manifest.json"
                ),
                "prospective_forward_candidate_canary_v1",
            )
        )
    return [
        (role, path, _parent(path, expected_stage=stage))
        for role, path, stage in specs
    ]


def run_candidate_canary(
    config_path: str | Path,
    *,
    command: str,
) -> dict[str, object]:
    import lightgbm as lgb

    config_file = resolve(config_path)
    config = load_forward_config(config_file)
    parents = _candidate_parents(config, include_canary=False)
    code_state = capture_code_state(PROJECT_ROOT)
    if code_state.dirty:
        raise ValueError("forward candidate canary requires clean committed code")
    free_disk = shutil.disk_usage(PROJECT_ROOT).free / (1024**3)
    if free_disk < float(config["canary"]["minimum_free_disk_gib"]):
        raise ValueError("insufficient disk for forward candidate canary")
    (
        protocol_config,
        resolution,
        factors,
        allowlist,
        matrix,
    ) = _protocol_inputs(
        config, factor_limit=int(config["canary"]["factor_count"])
    )
    train_dates = _training_dates(
        config, limit=int(config["canary"]["train_date_count"])
    )
    quarantine_dates = _quarantine_dates(
        config, limit=int(config["canary"]["quarantine_date_count"])
    )
    audit = InputAccessAudit()
    joined = __import__(
        "model_research.inputs", fromlist=["join_labels"]
    ).join_labels(
        project_features(
            factor_names=factors,
            factor_index=matrix.factor_index,
            dates=train_dates,
            fold="train",
            audit=audit,
        ),
        labels_path=_labels_runtime_path(protocol_config, resolution),
        label_name=config["training"]["label_name"],
        dates=train_dates,
        fold="train",
        audit=audit,
    )
    target, _, receipt = eligible_daily_cross_sectional_rank_centered(
        joined,
        label_column=config["training"]["label_name"],
        feature_columns=factors,
        expected_dates=train_dates,
        minimum_daily_pairs=int(config["training"]["minimum_daily_pairs"]),
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
        selected[factors].to_numpy(dtype=float),
        weights,
        feature_names=tuple(factors),
        canonical_row_keys=keys,
    )
    train_features = preprocessing.transform(
        selected[factors].to_numpy(dtype=float)
    )
    quarantine = project_features(
        factor_names=factors,
        factor_index=matrix.factor_index,
        dates=quarantine_dates,
        fold="validation",
        audit=audit,
    )
    quarantine_features = preprocessing.transform(
        quarantine[factors].to_numpy(dtype=float)
    )
    lightgbm_config = load_lightgbm_config(
        resolve(config["parents"]["lightgbm_config"])
    )
    candidate = _selected_candidate(config)
    result_rows = []
    with _MemorySampler() as sampler:
        for repeat in range(int(config["canary"]["repeat_count"])):
            started = time.perf_counter()
            dataset = lgb.Dataset(
                train_features,
                label=target.loc[eligible].to_numpy(dtype=float),
                weight=weights,
                feature_name=factors,
                free_raw_data=False,
            )
            model = lgb.train(
                _training_params(lightgbm_config, candidate),
                dataset,
                num_boost_round=int(candidate["num_boost_round"]),
            )
            prediction = model.predict(
                quarantine_features,
                num_iteration=int(candidate["num_boost_round"]),
            )
            result_rows.append(
                {
                    "repeat_index": repeat,
                    "model_sha256": canonical_hash(model.model_to_string()),
                    "prediction_sha256": _array_hash(prediction),
                    "prediction_row_count": len(prediction),
                    "prediction_finite_count": int(np.isfinite(prediction).sum()),
                    "wall_time_seconds": time.perf_counter() - started,
                }
            )
            del model, dataset, prediction
            gc.collect()
    results = pd.DataFrame(result_rows)
    stable = (
        results["model_sha256"].nunique() == 1
        and results["prediction_sha256"].nunique() == 1
    )
    quarantine_label_reads = 0
    contracts = pd.DataFrame(
        [
            _contract("candidate_spec_exact", True, candidate, "split_003 frozen"),
            _contract(
                "canary_repeat_hash_stable", stable, stable, True
            ),
            _contract(
                "quarantine_label_read_count_zero",
                quarantine_label_reads == 0,
                quarantine_label_reads,
                0,
            ),
            _contract(
                "quarantine_prediction_finite",
                results["prediction_finite_count"].eq(
                    results["prediction_row_count"]
                ).all(),
                results["prediction_finite_count"].tolist(),
                results["prediction_row_count"].tolist(),
            ),
            _contract(
                "canary_memory_budget",
                sampler.peak_mb
                <= float(config["canary"]["maximum_peak_rss_mib"]),
                sampler.peak_mb,
                config["canary"]["maximum_peak_rss_mib"],
            ),
            _contract(
                "retrospective_extension_not_evaluated",
                True,
                "prediction_only",
                "no label evaluation",
            ),
        ]
    )
    if not receipt["status"].eq("pass").all() or not contracts[
        "status"
    ].eq("pass").all():
        raise ValueError("forward candidate canary failed")
    review = {
        "schema_version": 1,
        "approval_type": "user_session_waiver",
        "scope": "single fixed LightGBM forward candidate refit",
        "command": (
            "python scripts/refit_prospective_forward_candidate_v1.py "
            f"--config {config_path}"
        ),
        "config_sha256": file_sha256(config_file),
        "code_commit_sha": code_state.commit_sha,
        "factor_count": int(config["candidate"]["factor_count"]),
        "training_start": config["training"]["start_date"],
        "training_end": config["training"]["end_date"],
        "candidate": candidate,
        "hyperparameter_search_allowed": False,
        "resource_budget": config["refit"],
        "quarantine_label_read_budget": 0,
    }
    review["review_bundle_id"] = "forward-refit-review:" + canonical_hash(review)
    readiness = pd.DataFrame(
        [
            {
                "forward_candidate_canary_ready": True,
                "forward_candidate_refit_ready": True,
                "forward_candidate_refit_complete": False,
                "forward_data_waiting": True,
                "production_model_selected": False,
                "live_trading_ready": False,
            }
        ]
    )
    resource = pd.DataFrame(
        [
            {
                "train_row_count": len(selected),
                "quarantine_prediction_row_count": len(quarantine),
                "factor_count": len(factors),
                "train_date_count": len(train_dates),
                "quarantine_date_count": len(quarantine_dates),
                "repeat_count": len(results),
                "peak_rss_mib": sampler.peak_mb,
                "free_disk_gib_at_start": free_disk,
                "quarantine_label_read_count": quarantine_label_reads,
            }
        ]
    )
    parent_receipts = _parent_receipts(parents)
    resolved = {
        **config,
        "executed_command": command,
        "executed_scope": "fixed_candidate_train_and_quarantine_prediction_canary",
        "output_dir": resolve(config["canary"]["output_dir"]).as_posix(),
    }
    output_dir = resolve(config["canary"]["output_dir"])
    with StageOutputPublisher(output_dir, CANARY_OUTPUTS) as publisher:
        results.to_csv(publisher.path("canary_results.csv"), index=False)
        pd.DataFrame(audit.rows()).to_csv(
            publisher.path("access_audit.csv"), index=False
        )
        contracts.to_csv(publisher.path("contract_status.csv"), index=False)
        readiness.to_csv(publisher.path("readiness_summary.csv"), index=False)
        resource.to_csv(publisher.path("resource_summary.csv"), index=False)
        parent_receipts.to_csv(
            publisher.path("parent_receipts.csv"), index=False
        )
        _write_json(publisher.path("run_review_bundle.json"), review)
        _write_json(publisher.path("resolved_config.json"), resolved)
        publisher.path("run_report.md").write_text(
            "# Prospective Forward Candidate Canary V1\n\n"
            f"- Train: {len(train_dates)} dates × {len(factors)} factors.\n"
            f"- Quarantine projection: {len(quarantine_dates)} dates, "
            f"{len(quarantine):,} predictions.\n"
            "- Quarantine label reads: 0.\n"
            f"- Repeat hashes stable: {stable}.\n",
            encoding="utf-8",
        )
        output_files = [
            publisher.path(name)
            for name in CANARY_OUTPUTS
            if name != "artifact_manifest.json"
        ]
        write_stage_artifact_manifest(
            project_root=PROJECT_ROOT,
            stage_id="prospective_forward_candidate_canary_v1",
            config=resolved,
            output_dir=publisher.staging_dir,
            output_files=output_files,
            code_state=code_state,
            input_manifest_paths=[path for _, path, _ in parents],
            universe_artifact_id=parents[2][2].get("universe_artifact_id"),
            split_manifest_id=parents[2][2].get("split_manifest_id"),
            factor_catalog_id=parents[2][2].get("factor_catalog_id"),
            factor_frame_id=parents[2][2].get("factor_frame_id"),
            contract_paths=[publisher.path("contract_status.csv")],
        )
        publisher.publish()
    return {
        "output_dir": output_dir.as_posix(),
        "review_bundle_id": review["review_bundle_id"],
        "prediction_rows": len(quarantine),
        "quarantine_label_read_count": 0,
        "repeat_hash_stable": stable,
    }


def _parent_receipts(
    parents: list[tuple[str, Path, dict[str, Any]]]
) -> pd.DataFrame:
    return pd.DataFrame(
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


def _write_json(path: Path, payload: object) -> None:
    path.write_text(
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


def _prepare_runtime(path: Path) -> None:
    allowed = resolve("outputs/prospective_forward_candidate_v1/runtime").resolve()
    target = path.resolve()
    if target != allowed and allowed not in target.parents:
        raise ValueError("forward candidate runtime escapes controlled root")
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True, exist_ok=False)


def refit_forward_candidate(
    config_path: str | Path,
    *,
    command: str,
) -> dict[str, object]:
    import lightgbm as lgb

    started = time.perf_counter()
    config_file = resolve(config_path)
    config = load_forward_config(config_file)
    parents = _candidate_parents(config, include_canary=True)
    code_state = capture_code_state(PROJECT_ROOT)
    if code_state.dirty:
        raise ValueError("forward candidate refit requires clean committed code")
    free_disk = shutil.disk_usage(PROJECT_ROOT).free / (1024**3)
    if free_disk < float(config["refit"]["minimum_free_disk_gib"]):
        raise ValueError("insufficient disk for forward candidate refit")
    (
        protocol_config,
        resolution,
        factors,
        allowlist,
        matrix,
    ) = _protocol_inputs(config, factor_limit=None)
    if (
        len(factors) != int(config["candidate"]["factor_count"])
        or str(allowlist["feature_order_sha256"])
        != config["candidate"]["feature_order_sha256"]
    ):
        raise ValueError("forward candidate feature order changed")
    dates = _training_dates(config)
    if dates.max() != pd.Timestamp(config["training"]["end_date"]):
        raise ValueError("candidate training endpoint changed")
    runtime_dir = resolve(config["refit"]["runtime_dir"])
    _prepare_runtime(runtime_dir)
    spool_dir = runtime_dir / "spool"
    materialized_dir = runtime_dir / "materialized"
    model_dir = runtime_dir / "model"
    for path in (spool_dir, materialized_dir, model_dir):
        path.mkdir(parents=True, exist_ok=False)
    audit = InputAccessAudit()
    spool_paths, eligibility = _spool_fold(
        protocol_config=protocol_config,
        resolution=resolution,
        matrix=matrix,
        split_id="forward_candidate_v1",
        fold="train",
        dates=dates,
        factors=factors,
        output_dir=spool_dir,
        audit=audit,
    )
    preprocessing = _fit_from_spool(spool_paths, factors)
    materialized = _materialize_fold(
        spool_paths=spool_paths,
        factors=factors,
        preprocessing=preprocessing,
        output_dir=materialized_dir,
        name="forward_candidate",
        keep_metadata=False,
    )
    candidate = _selected_candidate(config)
    lightgbm_config = load_lightgbm_config(
        resolve(config["parents"]["lightgbm_config"])
    )
    dataset = lgb.Dataset(
        materialized.features,
        label=materialized.target,
        weight=materialized.weights,
        feature_name=factors,
        free_raw_data=False,
        params={"feature_pre_filter": False},
    )
    with _MemorySampler() as sampler:
        model = lgb.train(
            _training_params(lightgbm_config, candidate),
            dataset,
            num_boost_round=int(candidate["num_boost_round"]),
        )
    model_path = model_dir / "forward_candidate_lightgbm.txt"
    model.save_model(
        model_path, num_iteration=int(candidate["num_boost_round"])
    )
    preprocessing_payload = _preprocessing_payload(preprocessing)
    preprocessing_path = model_dir / "forward_candidate_preprocessing.json"
    _write_json(preprocessing_path, preprocessing_payload)
    model_sha = file_sha256(model_path)
    preprocessing_sha = file_sha256(preprocessing_path)
    training_data_sha = _spool_hash(spool_paths)
    importance_rows = []
    for kind in ("gain", "split"):
        for order, (factor, value) in enumerate(
            zip(factors, model.feature_importance(importance_type=kind))
        ):
            importance_rows.append(
                {
                    "importance_type": kind,
                    "factor": factor,
                    "feature_order": order,
                    "importance": float(value),
                    "selection_authority": "diagnostic_only",
                }
            )
    protocol_freeze = json.loads(
        resolve(
            "outputs/prospective_forward_protocol_v1/current/"
            "forward_protocol_freeze.json"
        ).read_text(encoding="utf-8")
    )
    candidate_freeze = {
        "schema_version": 1,
        "status": "frozen_waiting_for_new_data",
        "candidate_status": "provisional_research_only",
        "forward_protocol_freeze_id": protocol_freeze[
            "forward_protocol_freeze_id"
        ],
        "method": "lightgbm",
        "selected_hyperparameters": candidate,
        "factor_count": len(factors),
        "allowlist_sha256": str(allowlist["allowlist_sha256"]),
        "feature_order_sha256": str(allowlist["feature_order_sha256"]),
        "training_start_date": dates.min().date().isoformat(),
        "training_end_date": dates.max().date().isoformat(),
        "training_date_sha256": canonical_hash(
            [value.date().isoformat() for value in dates]
        ),
        "training_data_sha256": training_data_sha,
        "model_binary_sha256": model_sha,
        "preprocessing_sha256": preprocessing_sha,
        "preprocessing_artifact_id": preprocessing_payload[
            "preprocessing_artifact_id"
        ],
        "model_runtime_path": model_path.as_posix(),
        "preprocessing_runtime_path": preprocessing_path.as_posix(),
        "official_forward_decision_date_rule": (
            config["temporal_boundary"]["official_forward_rule"]
        ),
        "current_snapshot_end": config["temporal_boundary"][
            "current_snapshot_end"
        ],
        "minimum_label_mature_dates_for_primary_confirmation": int(
            config["temporal_boundary"][
                "minimum_label_mature_dates_for_primary_confirmation"
            ]
        ),
        "freeze_timestamp": datetime.now(timezone.utc).isoformat(),
        "code_commit_sha": code_state.commit_sha,
        "forward_data_waiting": True,
        "production_model_selected": False,
        "live_trading_ready": False,
        "unbiased_historical_estimate": False,
    }
    candidate_freeze["forward_candidate_freeze_id"] = (
        "forward-candidate-freeze:" + canonical_hash(candidate_freeze)
    )
    contracts = pd.DataFrame(
        [
            _contract(
                "candidate_feature_order_exact",
                len(factors) == 52
                and canonical_hash(factors)
                == config["candidate"]["feature_order_sha256"],
                canonical_hash(factors),
                config["candidate"]["feature_order_sha256"],
            ),
            _contract(
                "hyperparameter_search_absent",
                not bool(config["candidate"]["hyperparameter_search_allowed"]),
                config["candidate"]["hyperparameter_search_allowed"],
                False,
            ),
            _contract(
                "training_endpoint_exact",
                dates.max() == pd.Timestamp("2026-05-11"),
                dates.max().date().isoformat(),
                "2026-05-11",
            ),
            _contract(
                "training_label_window_precedes_forward_boundary",
                dates.max()
                < pd.Timestamp(
                    config["temporal_boundary"]["current_snapshot_end"]
                ),
                dates.max().date().isoformat(),
                "<2026-06-09",
            ),
            _contract(
                "model_binary_hash_valid",
                file_sha256(model_path) == model_sha,
                file_sha256(model_path),
                model_sha,
            ),
            _contract(
                "preprocessing_hash_valid",
                file_sha256(preprocessing_path) == preprocessing_sha,
                file_sha256(preprocessing_path),
                preprocessing_sha,
            ),
            _contract(
                "memory_budget_valid",
                sampler.peak_mb
                <= float(config["refit"]["maximum_peak_rss_mib"]),
                sampler.peak_mb,
                config["refit"]["maximum_peak_rss_mib"],
            ),
            _contract(
                "no_forward_evaluation_performed",
                True,
                "refit_only",
                "no forward label evaluation",
            ),
            _contract(
                "forward_waiting_fail_closed",
                candidate_freeze["forward_data_waiting"] is True,
                candidate_freeze["forward_data_waiting"],
                True,
            ),
        ]
    )
    if not contracts["status"].eq("pass").all():
        raise ValueError("forward candidate refit contracts failed")
    model_receipt = pd.DataFrame(
        [
            {
                "method": "lightgbm",
                "factor_count": len(factors),
                "fit_row_count": materialized.row_count,
                "training_date_count": len(dates),
                "model_binary_sha256": model_sha,
                "preprocessing_sha256": preprocessing_sha,
                "training_data_sha256": training_data_sha,
                "runtime_model_path": model_path.as_posix(),
                "runtime_preprocessing_path": preprocessing_path.as_posix(),
            }
        ]
    )
    readiness = pd.DataFrame(
        [
            {
                "forward_protocol_ready": True,
                "forward_candidate_canary_ready": True,
                "forward_candidate_refit_complete": True,
                "forward_candidate_freeze_ready": True,
                "forward_data_waiting": True,
                "forward_prediction_confirmation_complete": False,
                "provisional_candidate_confirmed": False,
                "production_model_selected": False,
                "live_trading_ready": False,
            }
        ]
    )
    resource = pd.DataFrame(
        [
            {
                "fit_row_count": materialized.row_count,
                "training_date_count": len(dates),
                "factor_count": len(factors),
                "spool_file_count": len(spool_paths),
                "spool_bytes": sum(path.stat().st_size for path in spool_paths),
                "peak_rss_mib": sampler.peak_mb,
                "free_disk_gib_at_start": free_disk,
                "runtime_seconds": time.perf_counter() - started,
                "forward_feature_read_count": 0,
                "forward_label_read_count": 0,
            }
        ]
    )
    resolved = {
        **config,
        "executed_command": command,
        "executed_scope": "single_fixed_candidate_refit_no_search",
        "output_dir": resolve(config["refit"]["output_dir"]).as_posix(),
        "runtime_dir": runtime_dir.as_posix(),
    }
    output_dir = resolve(config["refit"]["output_dir"])
    with StageOutputPublisher(output_dir, REFIT_OUTPUTS) as publisher:
        model_receipt.to_csv(
            publisher.path("candidate_model_receipt.csv"), index=False
        )
        pd.DataFrame(importance_rows).to_csv(
            publisher.path("feature_importance.csv"), index=False
        )
        eligibility.to_csv(
            publisher.path("sample_eligibility_receipt.csv"), index=False
        )
        pd.DataFrame(audit.rows()).to_csv(
            publisher.path("access_audit.csv"), index=False
        )
        contracts.to_csv(publisher.path("contract_status.csv"), index=False)
        readiness.to_csv(publisher.path("readiness_summary.csv"), index=False)
        resource.to_csv(publisher.path("resource_summary.csv"), index=False)
        _parent_receipts(parents).to_csv(
            publisher.path("parent_receipts.csv"), index=False
        )
        _write_json(
            publisher.path("forward_candidate_freeze.json"),
            candidate_freeze,
        )
        _write_json(publisher.path("resolved_config.json"), resolved)
        publisher.path("run_report.md").write_text(
            "# Prospective Forward Candidate V1 Refit\n\n"
            f"- Fit rows: {materialized.row_count:,}.\n"
            f"- Dates: {dates.min().date()}—{dates.max().date()}.\n"
            f"- Factors: {len(factors)}.\n"
            "- Hyperparameter search: none.\n"
            "- Official forward evaluation: not started.\n"
            "- Forward data waiting: true.\n"
            "- Production model selected: false.\n",
            encoding="utf-8",
        )
        output_files = [
            publisher.path(name)
            for name in REFIT_OUTPUTS
            if name != "artifact_manifest.json"
        ]
        write_stage_artifact_manifest(
            project_root=PROJECT_ROOT,
            stage_id=STAGE_ID,
            config=resolved,
            output_dir=publisher.staging_dir,
            output_files=output_files,
            code_state=code_state,
            input_manifest_paths=[path for _, path, _ in parents],
            universe_artifact_id=parents[2][2].get("universe_artifact_id"),
            split_manifest_id=parents[2][2].get("split_manifest_id"),
            factor_catalog_id=parents[2][2].get("factor_catalog_id"),
            factor_frame_id=parents[2][2].get("factor_frame_id"),
            start_date=dates.min(),
            end_date=dates.max(),
            contract_paths=[publisher.path("contract_status.csv")],
        )
        publisher.publish()
    del model, dataset, materialized
    gc.collect()
    return {
        "output_dir": output_dir.as_posix(),
        "forward_candidate_freeze_id": candidate_freeze[
            "forward_candidate_freeze_id"
        ],
        "fit_row_count": int(model_receipt.iloc[0]["fit_row_count"]),
        "training_date_count": len(dates),
        "peak_rss_mib": sampler.peak_mb,
        "runtime_seconds": float(resource.iloc[0]["runtime_seconds"]),
        "forward_data_waiting": True,
    }
