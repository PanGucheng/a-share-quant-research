from __future__ import annotations

import json
import os
import shutil
import uuid
from contextlib import nullcontext
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from qlib_baseline.cache import normalized_callable_ast_hash
from research_validation.feature_matrix import canonical_hash, file_sha256

from .inputs import InputAccessAudit, _project_features, _read_partition_dates
from .linear_models import _spool_fold
from .development_dry_run import _fit_from_spool
from .preprocessing import WeightedPreprocessingFit, daily_equal_weights, stable_weighted_median
from .targets import eligible_daily_cross_sectional_rank_centered


CACHE_SCHEMA_VERSION = 1
CACHE_IMPLEMENTATION = "development_projection_spool_cache_v1"
PREPROCESSING_CACHE_SCHEMA_VERSION = 1
PREPROCESSING_CACHE_IMPLEMENTATION = "weighted_preprocessing_fit_cache_v1"
ALLOWED_FOLDS = {"train", "validation"}


@dataclass(frozen=True)
class ProjectionSpoolCacheResult:
    spool_paths: tuple[Path, ...]
    eligibility_receipt: pd.DataFrame
    cache_key: str
    cache_hit: bool
    cache_status: str
    manifest_path: Path
    disk_bytes: int


@dataclass(frozen=True)
class PreprocessingFitCacheResult:
    preprocessing: WeightedPreprocessingFit
    cache_key: str
    cache_hit: bool
    cache_status: str
    manifest_path: Path
    disk_bytes: int


def _implementation_sha256() -> str:
    return normalized_callable_ast_hash(
        _read_partition_dates,
        _project_features,
        eligible_daily_cross_sectional_rank_centered,
        daily_equal_weights,
        _spool_fold,
    )


def _selected_partition_identity(matrix: Any, factors: list[str]) -> list[dict[str, Any]]:
    selected_paths = {matrix.factor_index[factor].resolve() for factor in factors}
    rows = []
    for receipt in matrix.partition_receipts:
        path = Path(str(receipt["partition_path"])).resolve()
        if path in selected_paths:
            rows.append(
                {
                    "partition_path": path.as_posix(),
                    "recorded_sha256": str(receipt["recorded_sha256"]),
                    "observed_sha256": str(receipt["observed_sha256"]),
                    "hash_verified": bool(receipt["hash_verified"]),
                }
            )
    if not rows or not all(row["hash_verified"] for row in rows):
        raise ValueError("projection cache requires verified selected matrix partitions")
    return sorted(rows, key=lambda row: row["partition_path"])


def build_projection_spool_identity(
    *,
    protocol_config: dict[str, Any],
    resolution: Any,
    matrix: Any,
    split_id: str,
    fold: str,
    dates: pd.DatetimeIndex,
    factors: list[str],
    labels_path: Path,
    dtype: str = "float64",
) -> dict[str, Any]:
    if fold not in ALLOWED_FOLDS:
        raise PermissionError("development projection cache forbids test scope")
    if not factors or len(factors) != len(set(factors)):
        raise ValueError("projection cache requires a non-empty unique feature order")
    normalized_dates = pd.DatetimeIndex(dates).normalize()
    if normalized_dates.empty or normalized_dates.duplicated().any():
        raise ValueError("projection cache requires non-empty unique dates")
    date_values = [value.date().isoformat() for value in normalized_dates]
    matrix_manifest = resolution.manifests["matrix"]
    label_manifest = resolution.manifests["labels"]
    identity = {
        "cache_schema_version": CACHE_SCHEMA_VERSION,
        "cache_implementation": CACHE_IMPLEMENTATION,
        "projection_implementation_sha256": _implementation_sha256(),
        "matrix_artifact_id": str(matrix_manifest["artifact_id"]),
        "matrix_manifest_sha256": canonical_hash(matrix_manifest),
        "matrix_partition_identity": _selected_partition_identity(matrix, factors),
        "factor_universe_version": str(matrix_manifest.get("factor_catalog_id", "")),
        "outer_split_id": split_id,
        "fold": fold,
        "feature_pool_sha256": canonical_hash(sorted(factors)),
        "feature_order_sha256": canonical_hash(factors),
        "feature_order": factors,
        "date_scope_sha256": canonical_hash(date_values),
        "date_count": len(date_values),
        "date_start": date_values[0],
        "date_end": date_values[-1],
        "label_artifact_id": str(label_manifest["artifact_id"]),
        "label_manifest_sha256": canonical_hash(label_manifest),
        "label_payload_sha256": file_sha256(labels_path),
        "target_config_sha256": canonical_hash(protocol_config["target"]),
        "date_batch_size": int(protocol_config["development_dry_run"]["date_batch_size"]),
        "dtype": str(dtype),
        "test_scope_materialized": False,
    }
    identity["cache_key"] = canonical_hash(identity)
    return identity


def _row_key_sha256(path: Path) -> str:
    keys = pd.read_parquet(path, columns=["datetime", "instrument"])
    keys["datetime"] = pd.to_datetime(keys["datetime"]).dt.strftime("%Y-%m-%d")
    keys["instrument"] = keys["instrument"].astype(str)
    return canonical_hash(keys.to_dict("records"))


def _spool_receipts(paths: list[Path]) -> list[dict[str, Any]]:
    rows = []
    for path in paths:
        schema = pq.read_schema(path)
        rows.append(
            {
                "filename": path.name,
                "sha256": file_sha256(path),
                "size_bytes": path.stat().st_size,
                "row_count": int(pq.ParquetFile(path).metadata.num_rows),
                "columns": schema.names,
                "row_key_sha256": _row_key_sha256(path),
            }
        )
    return rows


def _validate_entry(entry: Path, identity: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    manifest_path = entry / "cache_manifest.json"
    if not manifest_path.is_file():
        return False, {}
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("identity") != identity:
            return False, manifest
        receipt_path = entry / "sample_eligibility_receipt.csv"
        if not receipt_path.is_file() or file_sha256(receipt_path) != manifest.get(
            "eligibility_receipt_sha256"
        ):
            return False, manifest
        expected_columns = [
            "datetime",
            "instrument",
            "__label",
            *identity["feature_order"],
            "__target",
            "__weight",
        ]
        for spool in manifest.get("spools", []):
            filename = Path(str(spool["filename"]))
            if filename.is_absolute() or len(filename.parts) != 1:
                return False, manifest
            path = entry / filename
            if (
                not path.is_file()
                or path.stat().st_size != int(spool["size_bytes"])
                or file_sha256(path) != spool["sha256"]
                or pq.read_schema(path).names != expected_columns
                or int(pq.ParquetFile(path).metadata.num_rows) != int(spool["row_count"])
                or _row_key_sha256(path) != spool["row_key_sha256"]
            ):
                return False, manifest
        if not manifest.get("spools"):
            return False, manifest
        return True, manifest
    except (KeyError, TypeError, ValueError, OSError, json.JSONDecodeError):
        return False, {}


def get_or_build_projection_spools(
    *,
    cache_root: Path,
    protocol_config: dict[str, Any],
    resolution: Any,
    matrix: Any,
    split_id: str,
    fold: str,
    dates: pd.DatetimeIndex,
    factors: list[str],
    labels_path: Path,
    audit: InputAccessAudit,
    timing_recorder: Any | None = None,
    dtype: str = "float64",
) -> ProjectionSpoolCacheResult:
    identity = build_projection_spool_identity(
        protocol_config=protocol_config,
        resolution=resolution,
        matrix=matrix,
        split_id=split_id,
        fold=fold,
        dates=dates,
        factors=factors,
        labels_path=labels_path,
        dtype=dtype,
    )
    cache_root = cache_root.resolve()
    cache_root.mkdir(parents=True, exist_ok=True)
    entry = cache_root / str(identity["cache_key"])
    validation_timing = (
        timing_recorder.measure(
            "projection_spool_cache_validation",
            fold=fold,
            cache_key=identity["cache_key"],
        )
        if timing_recorder is not None
        else nullcontext({})
    )
    with validation_timing as validation_payload:
        valid, manifest = _validate_entry(entry, identity)
        validation_payload["cache_hit"] = valid
    if valid:
        if timing_recorder is not None:
            with timing_recorder.measure(
                "projection_spool_cache_hit",
                fold=fold,
                cache_hit=True,
                cache_key=identity["cache_key"],
                output_rows=sum(int(row["row_count"]) for row in manifest["spools"]),
            ):
                pass
        receipt = pd.read_csv(entry / "sample_eligibility_receipt.csv")
        return ProjectionSpoolCacheResult(
            spool_paths=tuple(entry / row["filename"] for row in manifest["spools"]),
            eligibility_receipt=receipt,
            cache_key=str(identity["cache_key"]),
            cache_hit=True,
            cache_status="hit",
            manifest_path=entry / "cache_manifest.json",
            disk_bytes=sum(int(row["size_bytes"]) for row in manifest["spools"]),
        )

    cache_status = "miss"
    if entry.exists():
        if entry.resolve().parent != cache_root:
            raise ValueError("cache corruption target escaped cache root")
        shutil.rmtree(entry)
        cache_status = "corrupt_rebuilt"
    staging = cache_root / f".build-{identity['cache_key']}-{uuid.uuid4().hex}"
    staging.mkdir(parents=False, exist_ok=False)
    try:
        spools, receipt = _spool_fold(
            protocol_config=protocol_config,
            resolution=resolution,
            matrix=matrix,
            split_id=split_id,
            fold=fold,
            dates=dates,
            factors=factors,
            output_dir=staging,
            audit=audit,
            timing_recorder=timing_recorder,
        )
        receipt_path = staging / "sample_eligibility_receipt.csv"
        receipt.to_csv(receipt_path, index=False)
        spool_rows = _spool_receipts(spools)
        manifest = {
            "schema_version": CACHE_SCHEMA_VERSION,
            "identity": identity,
            "spools": spool_rows,
            "row_key_grid_sha256": canonical_hash(
                [row["row_key_sha256"] for row in spool_rows]
            ),
            "eligibility_receipt_sha256": file_sha256(receipt_path),
            "cache_provenance": {
                "immutable": True,
                "content_addressed": True,
                "test_scope_materialized": False,
            },
        }
        (staging / "cache_manifest.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        os.replace(staging, entry)
    finally:
        if staging.exists():
            shutil.rmtree(staging)
    if timing_recorder is not None:
        with timing_recorder.measure(
            "projection_spool_cache_publish",
            fold=fold,
            cache_hit=False,
            cache_key=identity["cache_key"],
            cache_status=cache_status,
            output_rows=sum(int(row["row_count"]) for row in manifest["spools"]),
        ):
            pass
    return ProjectionSpoolCacheResult(
        spool_paths=tuple(entry / row["filename"] for row in manifest["spools"]),
        eligibility_receipt=receipt,
        cache_key=str(identity["cache_key"]),
        cache_hit=False,
        cache_status=cache_status,
        manifest_path=entry / "cache_manifest.json",
        disk_bytes=sum(int(row["size_bytes"]) for row in manifest["spools"]),
    )


def _array_sha256(value: np.ndarray) -> str:
    array = np.ascontiguousarray(np.asarray(value))
    import hashlib

    digest = hashlib.sha256()
    digest.update(str(array.dtype).encode("ascii"))
    digest.update(str(array.shape).encode("ascii"))
    digest.update(array.tobytes())
    return digest.hexdigest()


def build_preprocessing_fit_identity(
    *,
    spool_paths: list[Path],
    factors: list[str],
    fit_scope: str,
    preprocessing_config: dict[str, Any],
    factor_batch_size: int,
    median_workers: int = 1,
    dtype: str = "float64",
) -> dict[str, Any]:
    if not spool_paths:
        raise ValueError("preprocessing cache requires at least one spool")
    if not factors or len(factors) != len(set(factors)):
        raise ValueError("preprocessing cache requires a non-empty unique feature order")
    if fit_scope not in {"train", "train_plus_validation"}:
        raise ValueError("preprocessing cache fit scope is invalid")
    if factor_batch_size < 1:
        raise ValueError("preprocessing cache factor batch size must be positive")
    spools = _spool_receipts(spool_paths)
    identity = {
        "cache_schema_version": PREPROCESSING_CACHE_SCHEMA_VERSION,
        "cache_implementation": PREPROCESSING_CACHE_IMPLEMENTATION,
        "preprocessing_implementation_sha256": normalized_callable_ast_hash(
            _fit_from_spool, stable_weighted_median
        ),
        "fit_scope": fit_scope,
        "feature_order": factors,
        "feature_order_sha256": canonical_hash(factors),
        "spools": spools,
        "spool_grid_sha256": canonical_hash(spools),
        "row_key_grid_sha256": canonical_hash(
            [row["row_key_sha256"] for row in spools]
        ),
        "weight_and_target_identity": [row["sha256"] for row in spools],
        "preprocessing_config_sha256": canonical_hash(preprocessing_config),
        "factor_batch_size": int(factor_batch_size),
        "median_workers": int(median_workers),
        "weighted_median_algorithm": "stable_weighted_median_v1",
        "dtype": str(dtype),
    }
    identity["cache_key"] = canonical_hash(identity)
    return identity


def _load_preprocessing_entry(
    entry: Path, identity: dict[str, Any]
) -> tuple[bool, dict[str, Any], WeightedPreprocessingFit | None]:
    manifest_path = entry / "cache_manifest.json"
    payload_path = entry / "preprocessing.npz"
    if not manifest_path.is_file() or not payload_path.is_file():
        return False, {}, None
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("identity") != identity:
            return False, manifest, None
        if file_sha256(payload_path) != manifest.get("payload_file_sha256"):
            return False, manifest, None
        with np.load(payload_path, allow_pickle=False) as payload:
            medians = np.asarray(payload["medians"], dtype=np.float64)
            means = np.asarray(payload["means"], dtype=np.float64)
            variances = np.asarray(payload["variances"], dtype=np.float64)
        expected = manifest.get("array_sha256", {})
        if {
            "medians": _array_sha256(medians),
            "means": _array_sha256(means),
            "variances": _array_sha256(variances),
        } != expected:
            return False, manifest, None
        if any(len(value) != len(identity["feature_order"]) for value in (medians, means, variances)):
            return False, manifest, None
        preprocessing = WeightedPreprocessingFit(
            feature_names=tuple(identity["feature_order"]),
            medians=medians,
            means=means,
            variances=variances,
        )
        return True, manifest, preprocessing
    except (KeyError, TypeError, ValueError, OSError, json.JSONDecodeError):
        return False, {}, None


def get_or_build_preprocessing_fit(
    *,
    cache_root: Path,
    spool_paths: list[Path],
    factors: list[str],
    fit_scope: str,
    preprocessing_config: dict[str, Any],
    factor_batch_size: int = 16,
    median_workers: int = 1,
    timing_recorder: Any | None = None,
    dtype: str = "float64",
) -> PreprocessingFitCacheResult:
    identity = build_preprocessing_fit_identity(
        spool_paths=spool_paths,
        factors=factors,
        fit_scope=fit_scope,
        preprocessing_config=preprocessing_config,
        factor_batch_size=factor_batch_size,
        median_workers=median_workers,
        dtype=dtype,
    )
    cache_root = cache_root.resolve()
    cache_root.mkdir(parents=True, exist_ok=True)
    entry = cache_root / str(identity["cache_key"])
    validation = (
        timing_recorder.measure(
            "preprocessing_fit_cache_validation",
            fold=fit_scope,
            cache_key=identity["cache_key"],
        )
        if timing_recorder is not None
        else nullcontext({})
    )
    with validation as timing_payload:
        valid, manifest, preprocessing = _load_preprocessing_entry(entry, identity)
        timing_payload["cache_hit"] = valid
    if valid and preprocessing is not None:
        return PreprocessingFitCacheResult(
            preprocessing=preprocessing,
            cache_key=str(identity["cache_key"]),
            cache_hit=True,
            cache_status="hit",
            manifest_path=entry / "cache_manifest.json",
            disk_bytes=int(manifest["payload_size_bytes"]),
        )
    cache_status = "miss"
    if entry.exists():
        if entry.resolve().parent != cache_root:
            raise ValueError("preprocessing cache corruption target escaped cache root")
        shutil.rmtree(entry)
        cache_status = "corrupt_rebuilt"
    staging = cache_root / f".build-{identity['cache_key']}-{uuid.uuid4().hex}"
    staging.mkdir(parents=False, exist_ok=False)
    try:
        fit_timing = (
            timing_recorder.measure(
                "preprocessing_fit",
                fold=fit_scope,
                cache_hit=False,
                factor_batch_size=factor_batch_size,
                median_workers=median_workers,
            )
            if timing_recorder is not None
            else nullcontext({})
        )
        with fit_timing:
            preprocessing = _fit_from_spool(
                spool_paths,
                factors,
                factor_batch_size=factor_batch_size,
                median_workers=median_workers,
            )
        payload_path = staging / "preprocessing.npz"
        np.savez(
            payload_path,
            medians=preprocessing.medians,
            means=preprocessing.means,
            variances=preprocessing.variances,
        )
        manifest = {
            "schema_version": PREPROCESSING_CACHE_SCHEMA_VERSION,
            "identity": identity,
            "payload_file_sha256": file_sha256(payload_path),
            "payload_size_bytes": payload_path.stat().st_size,
            "array_sha256": {
                "medians": _array_sha256(preprocessing.medians),
                "means": _array_sha256(preprocessing.means),
                "variances": _array_sha256(preprocessing.variances),
            },
            "cache_provenance": {"immutable": True, "content_addressed": True},
        }
        (staging / "cache_manifest.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        os.replace(staging, entry)
    finally:
        if staging.exists():
            shutil.rmtree(staging)
    return PreprocessingFitCacheResult(
        preprocessing=preprocessing,
        cache_key=str(identity["cache_key"]),
        cache_hit=False,
        cache_status=cache_status,
        manifest_path=entry / "cache_manifest.json",
        disk_bytes=int(manifest["payload_size_bytes"]),
    )
