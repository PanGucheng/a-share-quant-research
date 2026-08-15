from __future__ import annotations

import json
import os
import shutil
import uuid
from contextlib import nullcontext
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd
import pyarrow.parquet as pq

from qlib_baseline.cache import normalized_callable_ast_hash
from research_validation.feature_matrix import canonical_hash, file_sha256

from .inputs import InputAccessAudit, _project_features, _read_partition_dates
from .linear_models import _spool_fold
from .preprocessing import daily_equal_weights
from .targets import eligible_daily_cross_sectional_rank_centered


CACHE_SCHEMA_VERSION = 1
CACHE_IMPLEMENTATION = "development_projection_spool_cache_v1"
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
