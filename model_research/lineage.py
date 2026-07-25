from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

import pandas as pd
import pyarrow.parquet as pq

from research_validation.feature_matrix import file_sha256
from research_validation.lineage import (
    load_artifact_manifest,
    validate_manifest_outputs,
)


LEGACY_SPLIT_STAGE = "purged_walk_forward_v1"
EXPECTED_STAGES = {
    "date": "date_split_semantics_v1",
    "selection": "research_selection_lineage_closure_v1",
    "matrix": "full_research_feature_matrix_v4",
    "labels": "full_research_labels_v2",
    "universe": "point_in_time_universe_v2",
}


@dataclass(frozen=True)
class AuthoritativeParentPaths:
    date_manifest: Path
    selection_manifest: Path
    matrix_manifest: Path
    labels_manifest: Path
    universe_manifest: Path
    date_assignments: Path
    selection_date_assignments: Path

    @property
    def direct_model_parent_paths(self) -> tuple[Path, ...]:
        return (
            self.date_manifest,
            self.selection_manifest,
            self.matrix_manifest,
            self.labels_manifest,
            self.universe_manifest,
        )


@dataclass(frozen=True)
class AuthoritativeParentResolution:
    manifests: dict[str, dict[str, Any]]
    receipts: tuple[dict[str, object], ...]
    date_assignment_sha256: str


@dataclass(frozen=True)
class MatrixRuntimeAuthority:
    manifest: dict[str, Any]
    resolved_config: dict[str, Any]
    partition_status_path: Path
    runtime_dir: Path
    factor_index: dict[str, Path]
    partition_receipts: tuple[dict[str, object], ...]


def _require_manifest(
    name: str,
    path: Path,
    expected_stage: str,
) -> tuple[dict[str, Any], list[str]]:
    failures: list[str] = []
    if not path.is_file():
        return {}, [f"{name}_manifest_missing:{path}"]
    manifest = load_artifact_manifest(path)
    if manifest.get("stage_id") != expected_stage:
        failures.append(
            f"{name}_stage_mismatch:{manifest.get('stage_id')}!={expected_stage}"
        )
    if manifest.get("artifact_status") != "pass":
        failures.append(f"{name}_artifact_not_pass")
    if manifest.get("lineage_status") != "complete":
        failures.append(f"{name}_lineage_not_complete")
    failures.extend(
        f"{name}_{issue.check_name}:{issue.reason}"
        for issue in validate_manifest_outputs(manifest, path.parent)
    )
    return manifest, failures


def resolve_authoritative_parents(
    paths: AuthoritativeParentPaths,
) -> AuthoritativeParentResolution:
    manifests: dict[str, dict[str, Any]] = {}
    failures: list[str] = []
    for name, path in (
        ("date", paths.date_manifest),
        ("selection", paths.selection_manifest),
        ("matrix", paths.matrix_manifest),
        ("labels", paths.labels_manifest),
        ("universe", paths.universe_manifest),
    ):
        manifest, manifest_failures = _require_manifest(
            name, path, EXPECTED_STAGES[name]
        )
        manifests[name] = manifest
        failures.extend(manifest_failures)

    direct_stages = {str(item.get("stage_id")) for item in manifests.values()}
    if LEGACY_SPLIT_STAGE in direct_stages:
        failures.append("legacy_purged_split_is_direct_parent")

    for path in (paths.date_assignments, paths.selection_date_assignments):
        if not path.is_file():
            failures.append(f"date_assignments_missing:{path}")
    date_sha = ""
    selection_date_sha = ""
    if paths.date_assignments.is_file():
        date_sha = file_sha256(paths.date_assignments)
    if paths.selection_date_assignments.is_file():
        selection_date_sha = file_sha256(paths.selection_date_assignments)
    if date_sha != selection_date_sha:
        failures.append(
            f"date_assignment_payload_hash_mismatch:{date_sha}!={selection_date_sha}"
        )
    for name, manifest, observed in (
        ("date", manifests.get("date", {}), date_sha),
        ("selection", manifests.get("selection", {}), selection_date_sha),
    ):
        expected = manifest.get("output_file_hashes", {}).get("date_assignments.csv")
        if observed and expected != observed:
            failures.append(
                f"{name}_date_assignment_manifest_hash_mismatch:{observed}!={expected}"
            )

    date_artifact_id = manifests.get("date", {}).get("artifact_id")
    selection_inputs = set(manifests.get("selection", {}).get("input_artifact_ids", []))
    if date_artifact_id not in selection_inputs:
        failures.append("selection_does_not_consume_date_split_semantics")
    if manifests.get("matrix", {}).get("artifact_id") not in selection_inputs:
        failures.append("selection_does_not_consume_matrix_v4")
    if manifests.get("universe", {}).get("artifact_id") not in selection_inputs:
        failures.append("selection_does_not_consume_universe_v2")

    matrix = manifests.get("matrix", {})
    labels = manifests.get("labels", {})
    selection = manifests.get("selection", {})
    universe = manifests.get("universe", {})
    for field in ("universe_artifact_id", "factor_catalog_id", "factor_frame_id"):
        expected_values = {
            str(item.get(field))
            for item in (matrix, labels, selection)
            if item.get(field) is not None
        }
        if field == "universe_artifact_id" and universe.get(field) is not None:
            expected_values.add(str(universe[field]))
        if len(expected_values) != 1:
            failures.append(f"authoritative_{field}_inconsistent:{expected_values}")

    if failures:
        raise ValueError("authoritative parent resolution failed: " + " | ".join(failures))

    receipts = tuple(
        {
            "parent_role": name,
            "stage_id": manifest["stage_id"],
            "artifact_id": manifest["artifact_id"],
            "manifest_path": path.as_posix(),
            "artifact_status": manifest["artifact_status"],
            "lineage_status": manifest["lineage_status"],
            "direct_parent": True,
        }
        for name, path, manifest in (
            ("date_split_authority", paths.date_manifest, manifests["date"]),
            ("selection_authority", paths.selection_manifest, manifests["selection"]),
            ("feature_matrix", paths.matrix_manifest, manifests["matrix"]),
            ("labels", paths.labels_manifest, manifests["labels"]),
            ("universe", paths.universe_manifest, manifests["universe"]),
        )
    )
    return AuthoritativeParentResolution(
        manifests=manifests,
        receipts=receipts,
        date_assignment_sha256=date_sha,
    )


def _resolve_project_path(project_root: Path, value: object) -> Path:
    path = Path(str(value))
    return path.resolve() if path.is_absolute() else (project_root / path).resolve()


def resolve_matrix_runtime_authority(
    *,
    project_root: Path,
    matrix_manifest_path: Path,
    selected_factors: list[str] | None = None,
    verify_selected_partition_hashes: bool = True,
) -> MatrixRuntimeAuthority:
    manifest, failures = _require_manifest(
        "matrix",
        matrix_manifest_path,
        EXPECTED_STAGES["matrix"],
    )
    output_hashes = dict(manifest.get("output_file_hashes", {}))
    for filename in ("resolved_config.json", "partition_status.csv"):
        if filename not in output_hashes:
            failures.append(f"matrix_manifest_does_not_control:{filename}")
    resolved_config_path = matrix_manifest_path.parent / "resolved_config.json"
    partition_status_path = matrix_manifest_path.parent / "partition_status.csv"
    if not resolved_config_path.is_file():
        failures.append("matrix_resolved_config_missing")
        resolved_config: dict[str, Any] = {}
    else:
        resolved_config = json.loads(
            resolved_config_path.read_text(encoding="utf-8")
        )
    configured_output = _resolve_project_path(
        project_root,
        resolved_config.get("output_dir", matrix_manifest_path.parent),
    )
    if configured_output != matrix_manifest_path.parent.resolve():
        failures.append(
            f"matrix_output_dir_mismatch:{configured_output}!="
            f"{matrix_manifest_path.parent.resolve()}"
        )
    runtime_dir = _resolve_project_path(
        project_root, resolved_config.get("runtime_dir", "")
    )
    if not runtime_dir.is_dir():
        failures.append(f"matrix_runtime_dir_missing:{runtime_dir}")
    if not partition_status_path.is_file():
        failures.append("matrix_partition_status_missing")
        status = pd.DataFrame()
    else:
        status = pd.read_csv(partition_status_path)
    required_columns = {
        "batch_id",
        "status",
        "output_path",
        "output_sha256",
    }
    if not required_columns.issubset(status.columns):
        failures.append(
            "matrix_partition_status_columns_missing:"
            + ",".join(sorted(required_columns - set(status.columns)))
        )

    factor_index: dict[str, Path] = {}
    partition_factors: dict[Path, list[str]] = {}
    receipts: list[dict[str, object]] = []
    if not failures:
        for row in status.loc[status["status"].astype(str).eq("pass")].itertuples(
            index=False
        ):
            path = _resolve_project_path(project_root, row.output_path)
            if runtime_dir != path.parent and runtime_dir not in path.parents:
                failures.append(f"matrix_partition_escapes_runtime:{path}")
                continue
            if not path.is_file():
                failures.append(f"matrix_partition_missing:{path}")
                continue
            factors = [
                name
                for name in pq.read_schema(path).names
                if name not in {"datetime", "instrument"}
            ]
            partition_factors[path] = factors
            for factor in factors:
                if factor in factor_index:
                    failures.append(
                        f"matrix_factor_in_multiple_partitions:{factor}"
                    )
                factor_index[factor] = path
            receipts.append(
                {
                    "batch_id": str(row.batch_id),
                    "partition_path": path.as_posix(),
                    "recorded_sha256": str(row.output_sha256),
                    "observed_sha256": "",
                    "hash_verified": False,
                    "factor_count": len(factors),
                    "runtime_dir": runtime_dir.as_posix(),
                }
            )
    selected = list(selected_factors or [])
    missing_selected = sorted(set(selected) - set(factor_index))
    if missing_selected:
        failures.append(f"matrix_selected_factors_missing:{missing_selected}")
    selected_paths = {factor_index[name] for name in selected if name in factor_index}
    if verify_selected_partition_hashes:
        for receipt in receipts:
            path = Path(str(receipt["partition_path"]))
            if path not in selected_paths:
                continue
            observed = file_sha256(path)
            receipt["observed_sha256"] = observed
            receipt["hash_verified"] = observed == receipt["recorded_sha256"]
            if not receipt["hash_verified"]:
                failures.append(f"matrix_partition_hash_mismatch:{path}")
    if failures:
        raise ValueError(
            "matrix runtime authority resolution failed: "
            + " | ".join(failures)
        )
    return MatrixRuntimeAuthority(
        manifest=manifest,
        resolved_config=resolved_config,
        partition_status_path=partition_status_path,
        runtime_dir=runtime_dir,
        factor_index=factor_index,
        partition_receipts=tuple(receipts),
    )
