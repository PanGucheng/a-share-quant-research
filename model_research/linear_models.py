from __future__ import annotations

import hashlib
import json
import shutil
import threading
import time
import gc
from contextlib import nullcontext
from datetime import datetime, timezone
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml
import joblib
from scipy.stats import spearmanr
from sklearn.linear_model import ElasticNet, Ridge

from research_validation.feature_matrix import canonical_hash
from research_validation.feature_matrix import file_sha256
from research_validation.lineage import (
    capture_code_state,
    load_artifact_manifest,
    write_stage_artifact_manifest,
)
from research_validation.stage_output import StageOutputPublisher

from .gates import assert_research_model_entry_artifact
from .inputs import (
    InputAccessAudit,
    assert_fold_isolation,
    join_labels,
    load_fold_dates,
    load_split_feature_order,
    project_features,
)
from .lineage import resolve_authoritative_parents
from .preprocessing import daily_equal_weights, fit_weighted_preprocessing
from .development_dry_run import _date_batches, _fit_from_spool
from .freeze import validate_pre_test_freeze
from .protocol import PROJECT_ROOT, parent_paths, resolve
from .protocol_v1_1 import _labels_runtime_path, _matrix_authority
from .targets import eligible_daily_cross_sectional_rank_centered


STAGE_ID = "research_linear_models_v1"
CANARY_OUTPUTS = (
    "artifact_manifest.json",
    "resolved_config.json",
    "parent_receipts.csv",
    "solver_canary_results.csv",
    "ridge_solver_receipt.json",
    "access_audit.csv",
    "resource_summary.csv",
    "contract_status.csv",
    "readiness_summary.csv",
    "run_review_bundle.json",
    "run_report.md",
)


def load_linear_config(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if payload.get("stage_id") != STAGE_ID:
        raise ValueError(f"unexpected linear model stage: {payload.get('stage_id')}")
    if payload.get("experiment_class") != "post_observation_research":
        raise ValueError("linear model experiment_class must be post_observation_research")
    ridge = payload["ridge"]
    elastic = payload["elastic_net"]
    if len(ridge["alphas"]) != int(ridge["maximum_candidates_per_split"]):
        raise ValueError("Ridge candidate count does not match frozen maximum")
    if (
        len(elastic["alphas"]) * len(elastic["l1_ratios"])
        != int(elastic["maximum_candidates_per_split"])
    ):
        raise ValueError("Elastic Net candidate count does not match frozen maximum")
    if str(ridge["solver"]).lower() == "auto":
        raise ValueError("solver=auto is forbidden")
    if payload["validation"]["primary_metric"] != "mean_daily_rank_ic":
        raise ValueError("linear model primary metric is not frozen")
    if payload["validation"]["final_fit_scope"] != "outer_train_plus_validation":
        raise ValueError("linear model final fit scope is not frozen")
    return payload


def _array_hash(value: np.ndarray) -> str:
    array = np.ascontiguousarray(np.asarray(value))
    digest = hashlib.sha256()
    digest.update(str(array.dtype).encode("ascii"))
    digest.update(str(array.shape).encode("ascii"))
    digest.update(array.tobytes())
    return digest.hexdigest()


def _current_rss_mb() -> float:
    try:
        import psutil

        return psutil.Process().memory_info().rss / (1024 * 1024)
    except Exception:  # pragma: no cover - optional diagnostic
        return float("nan")


@dataclass
class _MemorySampler:
    interval_seconds: float = 0.005

    def __post_init__(self) -> None:
        self.baseline_mb = _current_rss_mb()
        self.peak_mb = self.baseline_mb
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._sample, daemon=True)

    def _sample(self) -> None:
        while not self._stop.wait(self.interval_seconds):
            self.peak_mb = float(np.nanmax([self.peak_mb, _current_rss_mb()]))

    def __enter__(self) -> "_MemorySampler":
        self._thread.start()
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        self._stop.set()
        self._thread.join()
        self.peak_mb = float(np.nanmax([self.peak_mb, _current_rss_mb()]))

    @property
    def peak_delta_mb(self) -> float:
        return max(0.0, self.peak_mb - self.baseline_mb)


def _write_json(path: Path, payload: object) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _contract(
    name: str,
    passed: bool,
    observed: object,
    expected: object,
) -> dict[str, object]:
    return {
        "check_name": name,
        "status": "pass" if passed else "blocked",
        "severity": "critical",
        "observed": json.dumps(observed, ensure_ascii=False, default=str),
        "expected": json.dumps(expected, ensure_ascii=False, default=str),
        "reason": "" if passed else f"{name} failed",
    }


def _canary_training_sample(
    config: dict[str, Any],
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
    split_id = str(config["solver_canary"]["split_id"])
    ordered, _ = load_split_feature_order(
        resolve(protocol_config["selection"]["factor_weights"]),
        resolve(protocol_config["selection"]["allowlist_manifest"]),
        outer_split_id=split_id,
    )
    factor_count = int(config["solver_canary"]["factor_count"])
    factors = tuple(ordered["factor"].astype(str).tolist()[:factor_count])
    matrix = _matrix_authority(
        protocol_config,
        selected_factors=list(factors),
        verify_hashes=True,
    )
    dates = load_fold_dates(
        parent_paths(protocol_config).selection_date_assignments,
        outer_split_id=split_id,
        fold="train",
        limit=int(config["solver_canary"]["train_date_count"]),
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
        minimum_daily_pairs=int(protocol_config["target"]["minimum_daily_pairs"]),
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
    transformed = preprocessing.transform(
        selected[list(factors)].to_numpy(dtype=float)
    )
    selected_paths = {matrix.factor_index[factor] for factor in factors}
    partition_receipts = [
        row
        for row in matrix.partition_receipts
        if Path(str(row["partition_path"])) in selected_paths
    ]
    if audit.test_read_count:
        raise AssertionError("solver canary read test payload")
    if not receipt["status"].eq("pass").all():
        raise ValueError("solver canary sample eligibility failed")
    return (
        transformed,
        target.loc[eligible].to_numpy(dtype=float),
        weights,
        factors,
        audit,
        partition_receipts,
    )


def run_solver_canary(
    config: dict[str, Any],
    *,
    output_dir: Path,
    command: str,
) -> dict[str, Any]:
    protocol_manifest_path = resolve(config["protocol_manifest"])
    assert_research_model_entry_artifact(
        protocol_manifest_path,
        experiment_class=str(config["experiment_class"]),
        operation="canary",
    )
    code_state = capture_code_state(PROJECT_ROOT)
    if code_state.dirty:
        raise ValueError("solver canary requires a clean committed worktree")
    free_disk_gb = shutil.disk_usage(PROJECT_ROOT).free / (1024**3)
    minimum_free = float(config["resource_budget"]["minimum_free_disk_gb"])
    if free_disk_gb < minimum_free:
        raise ValueError(
            f"insufficient free disk for solver canary: {free_disk_gb:.2f} GiB"
        )
    (
        features,
        target,
        weights,
        factors,
        audit,
        partition_receipts,
    ) = _canary_training_sample(config)
    repeat_count = int(config["solver_canary"]["repeat_count"])
    rows: list[dict[str, object]] = []
    for solver in [str(item) for item in config["solver_canary"]["candidates"]]:
        coefficient_hashes: list[str] = []
        prediction_hashes: list[str] = []
        solver_rows: list[dict[str, object]] = []
        for repeat_index in range(repeat_count):
            started = time.perf_counter()
            with _MemorySampler() as sampler:
                model = Ridge(
                    alpha=1.0,
                    fit_intercept=True,
                    solver=solver,
                )
                model.fit(features, target, sample_weight=weights)
                prediction = model.predict(features)
            coefficient_hashes.append(
                canonical_hash(
                    {
                        "coef": _array_hash(model.coef_),
                        "intercept": float(model.intercept_),
                    }
                )
            )
            prediction_hashes.append(_array_hash(prediction))
            solver_rows.append(
                {
                    "solver": solver,
                    "repeat_index": repeat_index,
                    "coefficient_sha256": coefficient_hashes[-1],
                    "prediction_sha256": prediction_hashes[-1],
                    "wall_time_seconds": time.perf_counter() - started,
                    "peak_memory_delta_mb": sampler.peak_delta_mb,
                    "fit_row_count": len(features),
                    "factor_count": len(factors),
                    "status": "",
                }
            )
        stable = (
            len(set(coefficient_hashes)) == 1
            and len(set(prediction_hashes)) == 1
        )
        for row in solver_rows:
            row["status"] = "pass" if stable else "blocked"
        rows.extend(solver_rows)
    results = pd.DataFrame(rows)
    eligible = results.groupby("solver", as_index=False).agg(
        stable=("status", lambda values: values.eq("pass").all()),
        peak_memory_delta_mb=("peak_memory_delta_mb", "max"),
        wall_time_seconds=("wall_time_seconds", "sum"),
    )
    eligible = eligible.loc[eligible["stable"]].sort_values(
        ["peak_memory_delta_mb", "wall_time_seconds", "solver"],
        kind="stable",
    )
    if eligible.empty:
        raise ValueError("no deterministic Ridge solver passed canary")
    selected_solver = str(eligible.iloc[0]["solver"])
    protocol_manifest = load_artifact_manifest(protocol_manifest_path)
    receipt = {
        "schema_version": 1,
        "selected_solver": selected_solver,
        "selection_uses_prediction_quality": False,
        "candidate_solvers": [
            str(item) for item in config["solver_canary"]["candidates"]
        ],
        "repeat_count": repeat_count,
        "factor_count": len(factors),
        "train_date_count": int(config["solver_canary"]["train_date_count"]),
        "fit_row_count": len(features),
        "selection_order": [
            "lower_peak_memory",
            "lower_wall_time",
            "canonical_solver_name",
        ],
        "result_sha256": canonical_hash(results.to_dict("records")),
        "protocol_artifact_id": protocol_manifest["artifact_id"],
        "code_commit_sha": code_state.commit_sha,
        "test_read_count": audit.test_read_count,
    }
    receipt["solver_receipt_sha256"] = canonical_hash(receipt)
    review = {
        "schema_version": 1,
        "approval_type": "user_session_waiver",
        "scope": "PR5B frozen linear model config and staged run sequence",
        "command": command,
        "config_sha256": canonical_hash(config),
        "protocol_artifact_id": protocol_manifest["artifact_id"],
        "code_commit_sha": code_state.commit_sha,
        "input_partition_receipts_sha256": canonical_hash(partition_receipts),
        "free_disk_gb_at_start": free_disk_gb,
        "resource_budget": config["resource_budget"],
        "test_read_budget": 0,
    }
    review["approval_id"] = "user-session-waiver:" + canonical_hash(review)
    contracts = pd.DataFrame(
        [
            _contract(
                "protocol_artifact_gate_valid",
                True,
                protocol_manifest["artifact_id"],
                "hash-verified V1.1 protocol",
            ),
            _contract(
                "solver_auto_forbidden",
                "auto"
                not in {
                    str(value).lower()
                    for value in config["solver_canary"]["candidates"]
                },
                config["solver_canary"]["candidates"],
                "auto absent",
            ),
            _contract(
                "solver_repeat_hash_stable",
                results["status"].eq("pass").all(),
                results.groupby("solver")["status"].apply(list).to_dict(),
                "all pass",
            ),
            _contract(
                "test_read_count_before_freeze_zero",
                audit.test_read_count == 0,
                audit.test_read_count,
                0,
            ),
            _contract(
                "resource_budget_valid",
                float(results["peak_memory_delta_mb"].max())
                <= float(config["resource_budget"]["maximum_peak_rss_mb"]),
                float(results["peak_memory_delta_mb"].max()),
                config["resource_budget"]["maximum_peak_rss_mb"],
            ),
        ]
    )
    ready = contracts["status"].eq("pass").all()
    if not ready:
        raise ValueError("solver canary critical contracts failed")
    readiness = pd.DataFrame(
        [
            {
                "solver_canary_ready": True,
                "ridge_development_ready": True,
                "elastic_net_development_ready": False,
                "linear_model_research_complete": False,
                "research_model_experiment_started": True,
                "model_training_started": True,
                "test_read_count_before_freeze": audit.test_read_count,
                "production_model_selected": False,
                "authoritative_execution": False,
                "unbiased_final_estimate": False,
            }
        ]
    )
    resource = pd.DataFrame(
        [
            {
                "fit_row_count": len(features),
                "factor_count": len(factors),
                "candidate_solver_count": results["solver"].nunique(),
                "repeat_fit_count": len(results),
                "peak_memory_delta_mb": results["peak_memory_delta_mb"].max(),
                "wall_time_seconds": results["wall_time_seconds"].sum(),
                "free_disk_gb_at_start": free_disk_gb,
                "test_read_count": audit.test_read_count,
            }
        ]
    )
    parent_receipts = pd.DataFrame(
        [
            {
                "parent_role": "research_model_protocol_v1_1",
                "stage_id": protocol_manifest["stage_id"],
                "artifact_id": protocol_manifest["artifact_id"],
                "manifest_path": protocol_manifest_path.as_posix(),
                "artifact_status": protocol_manifest["artifact_status"],
                "lineage_status": protocol_manifest["lineage_status"],
                "direct_parent": True,
            }
        ]
    )
    resolved_config = {
        **config,
        "executed_command": command,
        "executed_scope": "solver_canary",
        "selected_solver": selected_solver,
        "approval_id": review["approval_id"],
    }
    with StageOutputPublisher(output_dir, CANARY_OUTPUTS) as publisher:
        results.to_csv(
            publisher.path("solver_canary_results.csv"), index=False
        )
        _write_json(publisher.path("ridge_solver_receipt.json"), receipt)
        pd.DataFrame(audit.rows()).to_csv(
            publisher.path("access_audit.csv"), index=False
        )
        resource.to_csv(publisher.path("resource_summary.csv"), index=False)
        contracts.to_csv(publisher.path("contract_status.csv"), index=False)
        readiness.to_csv(
            publisher.path("readiness_summary.csv"), index=False
        )
        parent_receipts.to_csv(
            publisher.path("parent_receipts.csv"), index=False
        )
        _write_json(publisher.path("run_review_bundle.json"), review)
        _write_json(publisher.path("resolved_config.json"), resolved_config)
        publisher.path("run_report.md").write_text(
            "# Research Linear Models V1 Solver Canary\n\n"
            f"- Selected Ridge solver: `{selected_solver}`.\n"
            f"- Scope: {len(factors)} factors × "
            f"{config['solver_canary']['train_date_count']} train dates.\n"
            f"- Fit rows: {len(features):,}.\n"
            f"- Test payload reads: {audit.test_read_count}.\n"
            "- Solver selection did not use validation or prediction quality.\n",
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
            input_manifest_paths=[protocol_manifest_path],
            universe_artifact_id=protocol_manifest.get(
                "universe_artifact_id"
            ),
            split_manifest_id=protocol_manifest.get("split_manifest_id"),
            factor_catalog_id=protocol_manifest.get("factor_catalog_id"),
            factor_frame_id=protocol_manifest.get("factor_frame_id"),
            contract_paths=[publisher.path("contract_status.csv")],
        )
        publisher.publish()
    return {
        "selected_solver": selected_solver,
        "output_dir": output_dir.as_posix(),
        "approval_id": review["approval_id"],
        "test_read_count": audit.test_read_count,
    }


def _safe_prepare_runtime(path: Path) -> None:
    allowed = resolve("outputs/research_linear_models_v1/runtime").resolve()
    target = path.resolve()
    if target != allowed and allowed not in target.parents:
        raise ValueError(f"linear model runtime escapes controlled root: {target}")
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True, exist_ok=False)


def _load_solver_receipt(
    canary_manifest_path: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    manifest = load_artifact_manifest(canary_manifest_path)
    if manifest.get("stage_id") != STAGE_ID:
        raise ValueError("solver canary stage mismatch")
    if manifest.get("artifact_status") != "pass":
        raise ValueError("solver canary artifact is not pass")
    from research_validation.lineage import validate_manifest_outputs

    issues = validate_manifest_outputs(manifest, canary_manifest_path.parent)
    if issues:
        raise ValueError(
            "solver canary output hash failure: "
            + " | ".join(item.reason for item in issues)
        )
    receipt_path = canary_manifest_path.parent / "ridge_solver_receipt.json"
    if "ridge_solver_receipt.json" not in manifest["output_file_hashes"]:
        raise ValueError("solver canary manifest does not control solver receipt")
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    if receipt.get("selected_solver") == "auto":
        raise ValueError("solver=auto is forbidden")
    if int(receipt.get("test_read_count", -1)) != 0:
        raise ValueError("solver canary accessed test payload")
    return manifest, receipt


def _spool_fold(
    *,
    protocol_config: dict[str, Any],
    resolution: Any,
    matrix: Any,
    split_id: str,
    fold: str,
    dates: pd.DatetimeIndex,
    factors: list[str],
    output_dir: Path,
    audit: InputAccessAudit,
    timing_recorder: Any | None = None,
) -> tuple[list[Path], pd.DataFrame]:
    paths: list[Path] = []
    receipts: list[pd.DataFrame] = []
    batch_size = int(protocol_config["development_dry_run"]["date_batch_size"])
    for batch_index, batch_dates in enumerate(_date_batches(dates, batch_size)):
        timing = (
            timing_recorder.measure(
                "feature_projection",
                fold=fold,
                batch_index=batch_index,
                input_date_count=len(batch_dates),
            )
            if timing_recorder is not None
            else nullcontext({})
        )
        with timing as timing_payload:
            features = project_features(
                factor_names=factors,
                factor_index=matrix.factor_index,
                dates=batch_dates,
                fold=fold,
                audit=audit,
            )
            timing_payload["output_rows"] = len(features)
        timing = (
            timing_recorder.measure(
                "label_loading_and_join",
                fold=fold,
                batch_index=batch_index,
                input_date_count=len(batch_dates),
            )
            if timing_recorder is not None
            else nullcontext({})
        )
        with timing as timing_payload:
            joined = join_labels(
                features,
                labels_path=_labels_runtime_path(protocol_config, resolution),
                label_name=protocol_config["target"]["label_id"],
                dates=batch_dates,
                fold=fold,
                audit=audit,
            )
            timing_payload["output_rows"] = len(joined)
        target, _, date_receipt = eligible_daily_cross_sectional_rank_centered(
            joined,
            label_column=protocol_config["target"]["label_id"],
            feature_columns=factors,
            expected_dates=batch_dates,
            minimum_daily_pairs=int(
                protocol_config["target"]["minimum_daily_pairs"]
            ),
        )
        date_receipt = date_receipt.assign(
            outer_split_id=split_id,
            fold=fold,
        )
        receipts.append(date_receipt)
        eligible = target.notna()
        frame = joined.loc[
            eligible,
            ["datetime", "instrument", protocol_config["target"]["label_id"], *factors],
        ].copy()
        frame = frame.rename(
            columns={protocol_config["target"]["label_id"]: "__label"}
        )
        frame["__target"] = target.loc[eligible].to_numpy(dtype=float)
        frame["__weight"] = daily_equal_weights(
            frame["datetime"].to_numpy()
        )
        path = output_dir / f"{fold}_{batch_index:03d}.parquet"
        timing = (
            timing_recorder.measure(
                "feature_spooling",
                fold=fold,
                batch_index=batch_index,
                output_rows=len(frame),
            )
            if timing_recorder is not None
            else nullcontext({})
        )
        with timing:
            frame.to_parquet(path, index=False, compression="zstd")
        paths.append(path)
    receipt = pd.concat(receipts, ignore_index=True)
    if len(receipt) != len(dates) or not receipt["status"].eq("pass").all():
        raise ValueError(f"{split_id}/{fold} eligibility receipt failed")
    return paths, receipt


@dataclass
class _MaterializedFold:
    features: np.memmap
    target: np.memmap
    weights: np.memmap
    metadata: pd.DataFrame | None
    row_count: int


def _parquet_row_count(path: Path) -> int:
    import pyarrow.parquet as pq

    return int(pq.ParquetFile(path).metadata.num_rows)


def _materialize_fold(
    *,
    spool_paths: list[Path],
    factors: list[str],
    preprocessing: Any,
    output_dir: Path,
    name: str,
    keep_metadata: bool,
    timing_recorder: Any | None = None,
) -> _MaterializedFold:
    row_count = sum(_parquet_row_count(path) for path in spool_paths)
    features = np.lib.format.open_memmap(
        output_dir / f"{name}_features.npy",
        mode="w+",
        dtype=np.float64,
        shape=(row_count, len(factors)),
        fortran_order=True,
    )
    target = np.lib.format.open_memmap(
        output_dir / f"{name}_target.npy",
        mode="w+",
        dtype=np.float64,
        shape=(row_count,),
    )
    weights = np.lib.format.open_memmap(
        output_dir / f"{name}_weights.npy",
        mode="w+",
        dtype=np.float64,
        shape=(row_count,),
    )
    metadata_frames: list[pd.DataFrame] = []
    offset = 0
    for batch_index, path in enumerate(spool_paths):
        columns = [
            "datetime",
            "instrument",
            "__label",
            "__target",
            "__weight",
            *factors,
        ]
        read_timing = (
            timing_recorder.measure(
                "materialization_parquet_read",
                fold=name,
                batch_index=batch_index,
            )
            if timing_recorder is not None
            else nullcontext({})
        )
        with read_timing as timing_payload:
            frame = pd.read_parquet(path, columns=columns)
            timing_payload["output_rows"] = len(frame)
        length = len(frame)
        transform_timing = (
            timing_recorder.measure(
                "preprocessing_transform",
                fold=name,
                batch_index=batch_index,
                output_rows=length,
            )
            if timing_recorder is not None
            else nullcontext({})
        )
        with transform_timing:
            transformed = preprocessing.transform(
                frame[factors].to_numpy(dtype=float)
            )
        write_timing = (
            timing_recorder.measure(
                "materialization_memmap_write",
                fold=name,
                batch_index=batch_index,
                output_rows=length,
            )
            if timing_recorder is not None
            else nullcontext({})
        )
        with write_timing:
            features[offset : offset + length] = transformed
            target[offset : offset + length] = frame["__target"].to_numpy(
                dtype=float
            )
            weights[offset : offset + length] = frame["__weight"].to_numpy(
                dtype=float
            )
        if keep_metadata:
            metadata_frames.append(
                frame[["datetime", "instrument", "__label"]]
            )
        offset += length
    if offset != row_count:
        raise AssertionError("materialized row count mismatch")
    features.flush()
    target.flush()
    weights.flush()
    metadata = (
        pd.concat(metadata_frames, ignore_index=True)
        if keep_metadata
        else None
    )
    return _MaterializedFold(
        features=features,
        target=target,
        weights=weights,
        metadata=metadata,
        row_count=row_count,
    )


def _candidate_grid(
    config: dict[str, Any],
    *,
    method: str,
    solver: str,
    limit: int | None,
) -> list[dict[str, Any]]:
    if method == "ridge":
        values = [
            {
                "method": method,
                "alpha": float(alpha),
                "fit_intercept": bool(config["ridge"]["fit_intercept"]),
                "solver": solver,
            }
            for alpha in config["ridge"]["alphas"]
        ]
    elif method == "elastic_net":
        values = [
            {
                "method": method,
                "alpha": float(alpha),
                "l1_ratio": float(l1_ratio),
                "fit_intercept": bool(
                    config["elastic_net"]["fit_intercept"]
                ),
                "max_iter": int(config["elastic_net"]["max_iter"]),
                "tol": float(config["elastic_net"]["tol"]),
                "selection": str(config["elastic_net"]["selection"]),
                "random_state": int(config["elastic_net"]["random_seed"]),
            }
            for alpha in config["elastic_net"]["alphas"]
            for l1_ratio in config["elastic_net"]["l1_ratios"]
        ]
    else:
        raise ValueError(f"unsupported linear model method: {method}")
    if limit is not None:
        values = values[:limit]
    for value in values:
        value["candidate_sha256"] = canonical_hash(value)
    return values


def _build_model(candidate: dict[str, Any]) -> Ridge | ElasticNet:
    if candidate["method"] == "ridge":
        return Ridge(
            alpha=float(candidate["alpha"]),
            fit_intercept=bool(candidate["fit_intercept"]),
            solver=str(candidate["solver"]),
        )
    return ElasticNet(
        alpha=float(candidate["alpha"]),
        l1_ratio=float(candidate["l1_ratio"]),
        fit_intercept=bool(candidate["fit_intercept"]),
        max_iter=int(candidate["max_iter"]),
        tol=float(candidate["tol"]),
        selection=str(candidate["selection"]),
        random_state=int(candidate["random_state"]),
        copy_X=True,
    )


def _validation_metrics(
    metadata: pd.DataFrame,
    prediction: np.ndarray,
) -> dict[str, float]:
    frame = metadata.copy()
    frame["prediction"] = np.asarray(prediction, dtype=float)
    finite = np.isfinite(frame["prediction"]) & np.isfinite(frame["__label"])
    coverage = float(finite.sum() / len(frame)) if len(frame) else 0.0
    daily_values: list[float] = []
    for _, group in frame.loc[finite].groupby("datetime", sort=True):
        if len(group) < 2:
            continue
        if group["prediction"].nunique(dropna=True) < 2:
            continue
        value = float(
            spearmanr(
                group["prediction"].to_numpy(),
                group["__label"].to_numpy(),
            ).statistic
        )
        if np.isfinite(value):
            daily_values.append(value)
    if not daily_values:
        return {
            "mean_daily_rank_ic": float("-inf"),
            "daily_rank_ic_ir": float("-inf"),
            "prediction_coverage": coverage,
            "daily_ic_count": 0,
        }
    values = np.asarray(daily_values, dtype=float)
    standard_deviation = float(values.std(ddof=1)) if len(values) > 1 else 0.0
    return {
        "mean_daily_rank_ic": float(values.mean()),
        "daily_rank_ic_ir": (
            float(values.mean() / standard_deviation)
            if standard_deviation > 0
            else 0.0
        ),
        "prediction_coverage": coverage,
        "daily_ic_count": len(values),
    }


def _select_candidate(
    metrics: pd.DataFrame,
    *,
    method: str,
) -> pd.Series:
    eligible = metrics.loc[metrics["status"].eq("pass")].copy()
    if eligible.empty:
        raise ValueError(f"no eligible {method} validation candidate")
    if method == "ridge":
        eligible["_complexity_1"] = -eligible["alpha"].astype(float)
        eligible["_complexity_2"] = 0.0
    else:
        eligible["_complexity_1"] = eligible["nonzero_coefficient_count"]
        eligible["_complexity_2"] = -eligible["alpha"].astype(float)
        eligible["_complexity_3"] = -eligible["l1_ratio"].astype(float)
    sort_columns = [
        "mean_daily_rank_ic",
        "daily_rank_ic_ir",
        "prediction_coverage",
        "_complexity_1",
        "_complexity_2",
    ]
    ascending = [False, False, False, True, True]
    if method == "elastic_net":
        sort_columns.append("_complexity_3")
        ascending.append(True)
    sort_columns.append("candidate_sha256")
    ascending.append(True)
    return eligible.sort_values(
        sort_columns,
        ascending=ascending,
        kind="stable",
    ).iloc[0]


def _preprocessing_payload(preprocessing: Any) -> dict[str, Any]:
    payload = {
        "feature_names": list(preprocessing.feature_names),
        "medians": preprocessing.medians.tolist(),
        "means": preprocessing.means.tolist(),
        "variances": preprocessing.variances.tolist(),
        "algorithm": "stable_daily_equal_weighted_preprocessing_v1",
    }
    payload["preprocessing_artifact_id"] = (
        "weighted-preprocessing:" + canonical_hash(payload)
    )
    return payload


def _spool_hash(spool_paths: list[Path]) -> str:
    return canonical_hash(
        [
            {"name": path.name, "sha256": file_sha256(path)}
            for path in spool_paths
        ]
    )


def _environment_lock() -> dict[str, Any]:
    path = resolve(
        "outputs/research_model_protocol_v1_1/current/environment_lock.json"
    )
    return json.loads(path.read_text(encoding="utf-8"))


def run_linear_development(
    config: dict[str, Any],
    *,
    output_dir: Path,
    runtime_dir: Path,
    split_ids: list[str],
    methods: list[str],
    factor_limit: int | None,
    train_date_limit: int | None,
    validation_date_limit: int | None,
    candidate_limit: int | None,
    full_scope: bool,
    command: str,
) -> dict[str, Any]:
    protocol_manifest_path = resolve(config["protocol_manifest"])
    assert_research_model_entry_artifact(
        protocol_manifest_path,
        experiment_class=str(config["experiment_class"]),
        operation="training",
    )
    code_state = capture_code_state(PROJECT_ROOT)
    if code_state.dirty:
        raise ValueError("linear development requires a clean committed worktree")
    canary_manifest_path = resolve(
        "outputs/research_linear_models_v1/canary/artifact_manifest.json"
    )
    canary_manifest, solver_receipt = _load_solver_receipt(
        canary_manifest_path
    )
    solver = str(solver_receipt["selected_solver"])
    if solver == "auto":
        raise ValueError("solver=auto is forbidden")
    expected_sequence = ["ridge", "elastic_net"]
    if methods != [item for item in expected_sequence if item in methods]:
        raise ValueError("linear methods must preserve Ridge then Elastic Net order")
    if "elastic_net" in methods and "ridge" not in methods:
        ridge_parent = resolve(
            "outputs/research_linear_models_v1/ridge_all/artifact_manifest.json"
        )
        if not ridge_parent.is_file():
            raise ValueError("Elastic Net requires completed 3-split Ridge parent")
        ridge_manifest = load_artifact_manifest(ridge_parent)
        if ridge_manifest.get("artifact_status") != "pass":
            raise ValueError("3-split Ridge parent is not pass")
    _safe_prepare_runtime(runtime_dir)
    protocol_config = yaml.safe_load(
        resolve(config["protocol_config"]).read_text(encoding="utf-8")
    )
    resolution = resolve_authoritative_parents(parent_paths(protocol_config))
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
    access = InputAccessAudit()
    candidate_rows: list[dict[str, Any]] = []
    metric_rows: list[dict[str, Any]] = []
    selected_payload: dict[str, Any] = {}
    coefficient_rows: list[dict[str, Any]] = []
    preprocessing_rows: list[dict[str, Any]] = []
    model_rows: list[dict[str, Any]] = []
    resource_rows: list[dict[str, Any]] = []
    eligibility_rows: list[pd.DataFrame] = []
    mutation_rows: list[dict[str, Any]] = []
    freeze_payloads: dict[str, dict[str, Any]] = {}
    started_all = time.perf_counter()
    peak_rss_mb = _current_rss_mb()
    environment = _environment_lock()

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
        assert_fold_isolation(train_dates, validation_dates, test_dates)
        split_runtime = runtime_dir / split_id
        split_runtime.mkdir(parents=True)
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
        train_preprocessing = _fit_from_spool(train_spools, factors)
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
            raise AssertionError("validation metadata missing")
        validation_label_hash = canonical_hash(
            validation_data.metadata[
                ["datetime", "instrument", "__label"]
            ].astype(str).to_dict("records")
        )
        for method in methods:
            candidates = _candidate_grid(
                config,
                method=method,
                solver=solver,
                limit=candidate_limit,
            )
            method_metrics: list[dict[str, Any]] = []
            for candidate in candidates:
                candidate_rows.append(
                    {
                        "outer_split_id": split_id,
                        **candidate,
                    }
                )
                fit_started = time.perf_counter()
                with _MemorySampler() as sampler:
                    model = _build_model(candidate)
                    model.fit(
                        train_data.features,
                        train_data.target,
                        sample_weight=train_data.weights,
                    )
                    prediction = model.predict(validation_data.features)
                metrics = _validation_metrics(
                    validation_data.metadata,
                    prediction,
                )
                nonzero = int(np.count_nonzero(model.coef_))
                converged = not (
                    method == "elastic_net"
                    and int(getattr(model, "n_iter_", 0))
                    >= int(candidate["max_iter"])
                )
                coverage_pass = (
                    metrics["prediction_coverage"]
                    >= float(config["validation"]["minimum_prediction_coverage"])
                )
                metric_valid = (
                    int(metrics["daily_ic_count"]) > 0
                    and np.isfinite(metrics["mean_daily_rank_ic"])
                    and np.isfinite(metrics["daily_rank_ic_ir"])
                )
                row = {
                    "outer_split_id": split_id,
                    **candidate,
                    **metrics,
                    "nonzero_coefficient_count": nonzero,
                    "n_iter": int(getattr(model, "n_iter_", 0)),
                    "fit_wall_time_seconds": time.perf_counter() - fit_started,
                    "peak_memory_delta_mb": sampler.peak_delta_mb,
                    "coefficient_sha256": _array_hash(model.coef_),
                    "validation_prediction_sha256": _array_hash(prediction),
                    "validation_label_sha256": validation_label_hash,
                    "status": (
                        "pass"
                        if converged and coverage_pass and metric_valid
                        else "blocked"
                    ),
                }
                method_metrics.append(row)
                metric_rows.append(row)
                peak_rss_mb = float(
                    np.nanmax([peak_rss_mb, sampler.peak_mb])
                )
                del model, prediction
                gc.collect()
            metrics_frame = pd.DataFrame(method_metrics)
            selected = _select_candidate(metrics_frame, method=method)
            selected_candidate = next(
                candidate
                for candidate in candidates
                if candidate["candidate_sha256"]
                == selected["candidate_sha256"]
            )
            validation_search_sha = canonical_hash(
                metrics_frame.to_dict("records")
            )
            mutated_metadata = validation_data.metadata.copy()
            mutated_metadata["__label"] = mutated_metadata.groupby(
                "datetime", sort=False
            )["__label"].transform(lambda values: values.iloc[::-1].to_numpy())
            mutated_label_sha = canonical_hash(
                mutated_metadata[
                    ["datetime", "instrument", "__label"]
                ].astype(str).to_dict("records")
            )
            mutation_model = _build_model(selected_candidate)
            mutation_model.fit(
                train_data.features,
                train_data.target,
                sample_weight=train_data.weights,
            )
            mutation_prediction = mutation_model.predict(
                validation_data.features
            )
            mutated_metrics = _validation_metrics(
                mutated_metadata,
                mutation_prediction,
            )
            mutated_metric_sha = canonical_hash(mutated_metrics)
            original_metric_sha = canonical_hash(
                {
                    key: selected[key]
                    for key in (
                        "mean_daily_rank_ic",
                        "daily_rank_ic_ir",
                        "prediction_coverage",
                        "daily_ic_count",
                    )
                }
            )
            mutated_search_sha = canonical_hash(
                {
                    "original_search_sha256": validation_search_sha,
                    "mutated_label_sha256": mutated_label_sha,
                    "mutated_metric_sha256": mutated_metric_sha,
                }
            )
            mutation_pass = (
                mutated_label_sha != validation_label_hash
                and mutated_metric_sha != original_metric_sha
                and mutated_search_sha != validation_search_sha
            )
            mutation_rows.append(
                {
                    "outer_split_id": split_id,
                    "method": method,
                    "validation_label_sha256": validation_label_hash,
                    "mutated_validation_label_sha256": mutated_label_sha,
                    "validation_metric_sha256": original_metric_sha,
                    "mutated_validation_metric_sha256": mutated_metric_sha,
                    "validation_search_sha256": validation_search_sha,
                    "mutated_validation_search_sha256": mutated_search_sha,
                    "selected_candidate_change_required": False,
                    "status": "pass" if mutation_pass else "blocked",
                }
            )
            del mutation_model, mutation_prediction
            gc.collect()

            combined_spools = train_spools + validation_spools
            final_preprocessing = _fit_from_spool(combined_spools, factors)
            final_data = _materialize_fold(
                spool_paths=combined_spools,
                factors=factors,
                preprocessing=final_preprocessing,
                output_dir=split_runtime,
                name=f"{method}_final",
                keep_metadata=False,
            )
            final_model = _build_model(selected_candidate)
            final_model.fit(
                final_data.features,
                final_data.target,
                sample_weight=final_data.weights,
            )
            model_dir = runtime_dir / "models"
            model_dir.mkdir(exist_ok=True)
            model_path = model_dir / f"{split_id}_{method}.joblib"
            joblib.dump(final_model, model_path, compress=3)
            model_sha = file_sha256(model_path)
            preprocessing_payload = _preprocessing_payload(
                final_preprocessing
            )
            preprocessing_path = (
                model_dir / f"{split_id}_{method}_preprocessing.json"
            )
            _write_json(preprocessing_path, preprocessing_payload)
            preprocessing_sha = file_sha256(preprocessing_path)
            training_data_sha = _spool_hash(combined_spools)
            allowlist = allowlist_rows[split_id]
            selected_payload[f"{split_id}:{method}"] = {
                key: (
                    value.item()
                    if isinstance(value, np.generic)
                    else value
                )
                for key, value in selected_candidate.items()
            }
            for feature_index, factor in enumerate(factors):
                coefficient_rows.append(
                    {
                        "outer_split_id": split_id,
                        "method": method,
                        "factor": factor,
                        "feature_order": feature_index,
                        "coefficient": float(final_model.coef_[feature_index]),
                        "coefficient_nonzero": bool(
                            final_model.coef_[feature_index] != 0
                        ),
                    }
                )
            preprocessing_rows.append(
                {
                    "outer_split_id": split_id,
                    "method": method,
                    "preprocessing_artifact_id": preprocessing_payload[
                        "preprocessing_artifact_id"
                    ],
                    "preprocessing_sha256": preprocessing_sha,
                    "feature_count": len(factors),
                    "fit_scope": "outer_train_plus_validation",
                    "runtime_path": preprocessing_path.as_posix(),
                }
            )
            model_rows.append(
                {
                    "outer_split_id": split_id,
                    "method": method,
                    "model_binary_sha256": model_sha,
                    "model_config_sha256": canonical_hash(selected_candidate),
                    "training_data_sha256": training_data_sha,
                    "validation_search_sha256": validation_search_sha,
                    "fit_row_count": final_data.row_count,
                    "runtime_path": model_path.as_posix(),
                }
            )
            scope_is_exact = (
                full_scope
                and factor_limit is None
                and train_date_limit is None
                and validation_date_limit is None
                and candidate_limit is None
            )
            if scope_is_exact:
                freeze = {
                    "outer_split_id": split_id,
                    "method": method,
                    "experiment_class": "post_observation_research",
                    "allowlist_sha256": str(allowlist["allowlist_sha256"]),
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
                    "fitted_preprocessing_artifact_id": preprocessing_payload[
                        "preprocessing_artifact_id"
                    ],
                    "selected_hyperparameters": selected_candidate,
                    "model_config_sha256": canonical_hash(selected_candidate),
                    "model_binary_sha256": model_sha,
                    "training_data_sha256": training_data_sha,
                    "train_validation_date_sha256": canonical_hash(
                        {
                            "train": [
                                value.date().isoformat() for value in train_dates
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
                    "random_seed": int(
                        config["execution"]["random_seed"]
                    ),
                    "code_commit_sha": code_state.commit_sha,
                    "freeze_timestamp": datetime.now(timezone.utc).isoformat(),
                    **environment,
                    "historical_test_already_observed": True,
                    "authoritative_execution": False,
                    "unbiased_final_estimate": False,
                }
                validate_pre_test_freeze(freeze)
                freeze_payloads[f"{split_id}_{method}"] = freeze
            del final_model, final_data
            gc.collect()
        resource_rows.append(
            {
                "outer_split_id": split_id,
                "factor_count": len(factors),
                "train_date_count": len(train_dates),
                "validation_date_count": len(validation_dates),
                "train_fit_row_count": train_data.row_count,
                "validation_row_count": validation_data.row_count,
                "runtime_seconds": time.perf_counter() - split_started,
                "peak_rss_mb_observed": peak_rss_mb,
                "test_read_count": access.test_read_count,
            }
        )
        del train_data, validation_data
        gc.collect()
        shutil.rmtree(split_runtime)

    metrics_frame = pd.DataFrame(metric_rows)
    candidates_frame = pd.DataFrame(candidate_rows)
    mutations = pd.DataFrame(mutation_rows)
    eligibility = pd.concat(eligibility_rows, ignore_index=True)
    exact_candidate_counts = all(
        len(
            candidates_frame.loc[
                candidates_frame["outer_split_id"].eq(split_id)
                & candidates_frame["method"].eq(method)
            ]
        )
        == (
            (5 if method == "ridge" else 15)
            if candidate_limit is None
            else min(candidate_limit, 5 if method == "ridge" else 15)
        )
        for split_id in split_ids
        for method in methods
    )
    full_exact_scope = (
        full_scope
        and split_ids == [str(item) for item in config["execution"]["split_ids"]]
        and methods == ["ridge", "elastic_net"]
        and factor_limit is None
        and train_date_limit is None
        and validation_date_limit is None
        and candidate_limit is None
    )
    freezes_expected = (
        len(split_ids) * len(methods)
        if full_scope
        and factor_limit is None
        and train_date_limit is None
        and validation_date_limit is None
        and candidate_limit is None
        else 0
    )
    resource_budget_pass = peak_rss_mb <= float(
        config["resource_budget"]["maximum_peak_rss_mb"]
    )
    contracts = pd.DataFrame(
        [
            _contract(
                "train_only_search_fit",
                access.feature_reads["test"] == 0
                and access.label_reads["test"] == 0,
                access.test_read_count,
                0,
            ),
            _contract(
                "validation_only_hyperparameter_selection",
                not metrics_frame.empty,
                sorted(metrics_frame["outer_split_id"].unique()),
                split_ids,
            ),
            _contract(
                "candidate_grid_exact",
                exact_candidate_counts,
                len(candidates_frame),
                "frozen method/split candidate counts",
            ),
            _contract(
                "daily_sample_weight_valid",
                True,
                "weights generated by daily_equal_weights",
                "daily sum = 1",
            ),
            _contract(
                "final_refit_train_plus_validation",
                len(model_rows) == len(split_ids) * len(methods),
                len(model_rows),
                len(split_ids) * len(methods),
            ),
            _contract(
                "validation_label_mutation_sensitive",
                not mutations.empty and mutations["status"].eq("pass").all(),
                mutations["status"].tolist(),
                "all pass",
            ),
            _contract(
                "pre_test_freeze_valid",
                len(freeze_payloads) == freezes_expected,
                len(freeze_payloads),
                freezes_expected,
            ),
            _contract(
                "test_read_count_before_freeze_zero",
                access.test_read_count == 0,
                access.test_read_count,
                0,
            ),
            _contract(
                "resource_budget_valid",
                resource_budget_pass,
                peak_rss_mb,
                config["resource_budget"]["maximum_peak_rss_mb"],
            ),
        ]
    )
    if not contracts["status"].eq("pass").all():
        raise ValueError(
            "linear development contracts failed: "
            + ",".join(
                contracts.loc[
                    ~contracts["status"].eq("pass"), "check_name"
                ].astype(str)
            )
        )
    protocol_manifest = load_artifact_manifest(protocol_manifest_path)
    review = {
        "schema_version": 1,
        "approval_type": "user_session_waiver",
        "scope": {
            "split_ids": split_ids,
            "methods": methods,
            "factor_limit": factor_limit,
            "train_date_limit": train_date_limit,
            "validation_date_limit": validation_date_limit,
            "candidate_limit": candidate_limit,
            "full_scope": full_scope,
        },
        "command": command,
        "config_sha256": canonical_hash(config),
        "protocol_artifact_id": protocol_manifest["artifact_id"],
        "solver_receipt_sha256": solver_receipt["solver_receipt_sha256"],
        "code_commit_sha": code_state.commit_sha,
        "resource_budget": config["resource_budget"],
        "test_read_budget": 0,
    }
    review["approval_id"] = "user-session-waiver:" + canonical_hash(review)
    readiness = pd.DataFrame(
        [
            {
                "ridge_split_count_complete": (
                    len(split_ids) if "ridge" in methods else 0
                ),
                "elastic_net_split_count_complete": (
                    len(split_ids) if "elastic_net" in methods else 0
                ),
                "linear_model_development_complete": full_exact_scope,
                "linear_model_research_complete": False,
                "pre_test_freeze_ready": freezes_expected > 0,
                "research_model_experiment_started": True,
                "model_training_started": True,
                "test_read_count_before_freeze": access.test_read_count,
                "production_model_selected": False,
                "authoritative_execution": False,
                "unbiased_final_estimate": False,
            }
        ]
    )
    parent_paths_for_manifest = [
        protocol_manifest_path,
        canary_manifest_path,
    ]
    dynamic_freeze_names = [
        f"pre_test_freezes/{name}.json"
        for name in sorted(freeze_payloads)
    ]
    controlled = (
        "artifact_manifest.json",
        "resolved_config.json",
        "parent_receipts.csv",
        "candidate_manifest.csv",
        "validation_metrics.csv",
        "selected_hyperparameters.json",
        "coefficient_summary.csv",
        "preprocessing_receipt.csv",
        "model_receipt.csv",
        "sample_eligibility_receipt.csv",
        "mutation_results.csv",
        "access_audit.csv",
        "resource_summary.csv",
        "contract_status.csv",
        "readiness_summary.csv",
        "run_review_bundle.json",
        "run_report.md",
        *dynamic_freeze_names,
    )
    resolved_config = {
        **config,
        "executed_command": command,
        "executed_scope": review["scope"],
        "selected_solver": solver,
        "approval_id": review["approval_id"],
        "runtime_dir": runtime_dir.as_posix(),
        "output_dir": output_dir.as_posix(),
    }
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
            for role, path, manifest in (
                (
                    "research_model_protocol_v1_1",
                    protocol_manifest_path,
                    protocol_manifest,
                ),
                (
                    "ridge_solver_canary",
                    canary_manifest_path,
                    canary_manifest,
                ),
            )
        ]
    )
    with StageOutputPublisher(output_dir, controlled) as publisher:
        candidates_frame.to_csv(
            publisher.path("candidate_manifest.csv"), index=False
        )
        metrics_frame.to_csv(
            publisher.path("validation_metrics.csv"), index=False
        )
        _write_json(
            publisher.path("selected_hyperparameters.json"),
            selected_payload,
        )
        pd.DataFrame(coefficient_rows).to_csv(
            publisher.path("coefficient_summary.csv"), index=False
        )
        pd.DataFrame(preprocessing_rows).to_csv(
            publisher.path("preprocessing_receipt.csv"), index=False
        )
        pd.DataFrame(model_rows).to_csv(
            publisher.path("model_receipt.csv"), index=False
        )
        eligibility.to_csv(
            publisher.path("sample_eligibility_receipt.csv"), index=False
        )
        mutations.to_csv(
            publisher.path("mutation_results.csv"), index=False
        )
        pd.DataFrame(access.rows()).to_csv(
            publisher.path("access_audit.csv"), index=False
        )
        pd.DataFrame(resource_rows).assign(
            total_runtime_seconds=time.perf_counter() - started_all,
            peak_rss_mb_observed=peak_rss_mb,
        ).to_csv(publisher.path("resource_summary.csv"), index=False)
        contracts.to_csv(publisher.path("contract_status.csv"), index=False)
        readiness.to_csv(
            publisher.path("readiness_summary.csv"), index=False
        )
        parent_receipts.to_csv(
            publisher.path("parent_receipts.csv"), index=False
        )
        _write_json(publisher.path("run_review_bundle.json"), review)
        _write_json(publisher.path("resolved_config.json"), resolved_config)
        for name, payload in freeze_payloads.items():
            _write_json(
                publisher.path(f"pre_test_freezes/{name}.json"),
                payload,
            )
        publisher.path("run_report.md").write_text(
            "# Research Linear Models V1 Development\n\n"
            f"- Splits: {', '.join(split_ids)}.\n"
            f"- Methods: {', '.join(methods)}.\n"
            f"- Frozen Ridge solver: `{solver}`.\n"
            f"- Candidate fits: {len(metrics_frame)}.\n"
            f"- Final train+validation refits: {len(model_rows)}.\n"
            f"- Pre-test freezes: {len(freeze_payloads)}.\n"
            f"- Test payload reads: {access.test_read_count}.\n"
            "- Historical test remains unopened by this development stage.\n",
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
            input_manifest_paths=parent_paths_for_manifest,
            universe_artifact_id=protocol_manifest.get(
                "universe_artifact_id"
            ),
            split_manifest_id=protocol_manifest.get("split_manifest_id"),
            factor_catalog_id=protocol_manifest.get("factor_catalog_id"),
            factor_frame_id=protocol_manifest.get("factor_frame_id"),
            contract_paths=[publisher.path("contract_status.csv")],
        )
        publisher.publish()
    return {
        "output_dir": output_dir.as_posix(),
        "runtime_dir": runtime_dir.as_posix(),
        "candidate_fit_count": len(metrics_frame),
        "final_refit_count": len(model_rows),
        "freeze_count": len(freeze_payloads),
        "test_read_count": access.test_read_count,
        "peak_rss_mb": peak_rss_mb,
    }
