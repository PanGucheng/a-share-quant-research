from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd
import yaml

from research_validation.feature_matrix import canonical_hash, file_sha256

from .inputs import KEY_COLUMNS, load_fold_dates, partition_factor_index


STAGE_ID = "ml_feature_eligibility_mvp_v1"
ALLOWED_THRESHOLD_AUTHORITIES = frozenset(
    {"feature_data_quality", "distribution_structure", "resource_feasibility"}
)
FORBIDDEN_THRESHOLD_BASES = frozenset(
    {
        "target_feature_count",
        "desired_feature_count",
        "retained_feature_count",
        "target_retention_ratio",
    }
)
THRESHOLD_FIELDS = (
    "maximum_missing_rate",
    "minimum_finite_dates",
    "minimum_finite_samples",
    "minimum_imputed_weighted_variance",
)


def load_eligibility_config(path: Path) -> dict[str, Any]:
    config = yaml.safe_load(path.read_text(encoding="utf-8"))
    if config.get("stage_id") != STAGE_ID:
        raise ValueError("unexpected eligibility stage")
    if config.get("audit_scope") != "feature_only":
        raise ValueError("eligibility audit must be feature_only")
    if config.get("decision_authority") != "diagnostic_only":
        raise ValueError("eligibility decision authority must be diagnostic_only")
    _reject_forbidden_threshold_bases(config)
    return config


def _walk_keys(value: Any) -> Iterable[str]:
    if isinstance(value, dict):
        for key, child in value.items():
            yield str(key)
            yield from _walk_keys(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_keys(child)


def _reject_forbidden_threshold_bases(config: dict[str, Any]) -> None:
    found = FORBIDDEN_THRESHOLD_BASES.intersection(_walk_keys(config))
    if found:
        raise ValueError(
            "eligibility thresholds may not use target feature count: "
            + ", ".join(sorted(found))
        )


def validate_threshold_freeze(config: dict[str, Any]) -> dict[str, float | int]:
    _reject_forbidden_threshold_bases(config)
    thresholds = config.get("thresholds", {})
    missing = [name for name in THRESHOLD_FIELDS if thresholds.get(name) is None]
    if missing:
        raise ValueError("eligibility thresholds are not frozen: " + ", ".join(missing))
    reasons = config.get("threshold_selection", {}).get("reasons", [])
    by_threshold: dict[str, list[dict[str, Any]]] = {}
    for row in reasons:
        authority = str(row.get("authority", ""))
        if authority not in ALLOWED_THRESHOLD_AUTHORITIES:
            raise ValueError(f"forbidden threshold authority: {authority}")
        threshold = str(row.get("threshold", ""))
        if threshold not in THRESHOLD_FIELDS:
            raise ValueError(f"unknown threshold reason target: {threshold}")
        if not str(row.get("reason", "")).strip():
            raise ValueError(f"empty threshold reason: {threshold}")
        by_threshold.setdefault(threshold, []).append(row)
    unreasoned = [name for name in THRESHOLD_FIELDS if name not in by_threshold]
    if unreasoned:
        raise ValueError("threshold selection reasons missing: " + ", ".join(unreasoned))

    result: dict[str, float | int] = {
        "maximum_missing_rate": float(thresholds["maximum_missing_rate"]),
        "minimum_finite_dates": int(thresholds["minimum_finite_dates"]),
        "minimum_finite_samples": int(thresholds["minimum_finite_samples"]),
        "minimum_imputed_weighted_variance": float(
            thresholds["minimum_imputed_weighted_variance"]
        ),
    }
    if not 0 <= result["maximum_missing_rate"] <= 1:
        raise ValueError("maximum_missing_rate must be in [0, 1]")
    if result["minimum_finite_dates"] < 1 or result["minimum_finite_samples"] < 1:
        raise ValueError("finite date/sample thresholds must be positive")
    if result["minimum_imputed_weighted_variance"] < 0:
        raise ValueError("variance threshold must be non-negative")
    return result


def _content_hash(values: np.ndarray) -> str:
    normalized = np.asarray(values, dtype="<f8").copy()
    normalized[np.isnan(normalized)] = np.nan
    digest = hashlib.sha256()
    digest.update(str(normalized.shape).encode("ascii"))
    digest.update(normalized.tobytes())
    return digest.hexdigest()


def profile_feature_frame(
    frame: pd.DataFrame,
    *,
    factor_names: list[str],
    outer_split_id: str,
) -> pd.DataFrame:
    required = set(KEY_COLUMNS).union(factor_names)
    absent = sorted(required.difference(frame.columns))
    if absent:
        raise ValueError(f"feature profile columns missing: {absent}")
    if frame.duplicated(list(KEY_COLUMNS)).any():
        raise ValueError("duplicate feature profile keys")
    work = frame.sort_values(list(KEY_COLUMNS), kind="stable").reset_index(drop=True)
    work["datetime"] = pd.to_datetime(work["datetime"], errors="raise").dt.normalize()
    total_rows = len(work)
    total_dates = int(work["datetime"].nunique())
    date_counts = work.groupby("datetime", sort=False)["instrument"].transform("count")
    row_weights = np.divide(1.0, date_counts.to_numpy(dtype=float))
    rows: list[dict[str, Any]] = []
    for factor in factor_names:
        values = pd.to_numeric(work[factor], errors="coerce").to_numpy(dtype=float)
        finite = np.isfinite(values)
        finite_values = values[finite]
        finite_rows = int(finite.sum())
        finite_dates = int(work.loc[finite, "datetime"].nunique())
        if finite_rows:
            median = float(np.median(finite_values))
            imputed = np.where(finite, values, median)
            weighted_mean = float(np.average(imputed, weights=row_weights))
            imputed_variance = float(
                np.average((imputed - weighted_mean) ** 2, weights=row_weights)
            )
            quantiles = np.quantile(
                finite_values, [0.0, 0.01, 0.25, 0.5, 0.75, 0.99, 1.0]
            )
            raw_variance = float(np.var(finite_values))
        else:
            quantiles = np.full(7, np.nan)
            raw_variance = np.nan
            imputed_variance = np.nan
        rows.append(
            {
                "outer_split_id": outer_split_id,
                "factor": factor,
                "total_rows": total_rows,
                "finite_rows": finite_rows,
                "finite_sample_rate": finite_rows / total_rows if total_rows else 0.0,
                "missing_rate": 1.0 - finite_rows / total_rows if total_rows else 1.0,
                "total_dates": total_dates,
                "finite_dates": finite_dates,
                "minimum": quantiles[0],
                "q01": quantiles[1],
                "q25": quantiles[2],
                "median": quantiles[3],
                "q75": quantiles[4],
                "q99": quantiles[5],
                "maximum": quantiles[6],
                "raw_variance": raw_variance,
                "imputed_weighted_variance": imputed_variance,
                "feature_content_sha256": _content_hash(values),
            }
        )
    profile = pd.DataFrame(rows)
    profile["duplicate_canonical_factor"] = profile.groupby(
        ["outer_split_id", "feature_content_sha256"], sort=False
    )["factor"].transform("min")
    profile["is_duplicate_canonical"] = profile["factor"].eq(
        profile["duplicate_canonical_factor"]
    )
    return profile


def apply_eligibility_thresholds(
    profile: pd.DataFrame,
    *,
    inventory: pd.DataFrame,
    dependencies: pd.DataFrame,
    thresholds: dict[str, float | int],
) -> pd.DataFrame:
    inventory_columns = {"name", "source", "enabled", "runnable"}
    dependency_columns = {"factor", "source_family", "dependency_class", "review_status"}
    if not inventory_columns.issubset(inventory.columns):
        raise ValueError("factor inventory schema mismatch")
    if not dependency_columns.issubset(dependencies.columns):
        raise ValueError("dependency inventory schema mismatch")
    merged = profile.merge(
        inventory[list(inventory_columns)].rename(columns={"name": "factor"}),
        on="factor",
        how="left",
        validate="many_to_one",
    ).merge(
        dependencies[list(dependency_columns)],
        on="factor",
        how="left",
        validate="many_to_one",
        suffixes=("", "_dependency"),
    )
    boolean_true = {True, "True", "true", 1, "1"}
    checks = {
        "correctness_inventory_enabled": merged["enabled"].isin(boolean_true),
        "correctness_inventory_runnable": merged["runnable"].isin(boolean_true),
        "correctness_dependency_proven": merged["review_status"].eq("proven")
        & merged["dependency_class"].notna()
        & ~merged["dependency_class"].astype(str).str.lower().isin(["", "unknown"]),
        "correctness_matrix_present": merged["total_rows"].gt(0),
        "correctness_any_finite": merged["finite_rows"].gt(0),
        "quality_missing_rate_pass": merged["missing_rate"].le(
            float(thresholds["maximum_missing_rate"])
        ),
        "quality_finite_dates_pass": merged["finite_dates"].ge(
            int(thresholds["minimum_finite_dates"])
        ),
        "quality_finite_samples_pass": merged["finite_rows"].ge(
            int(thresholds["minimum_finite_samples"])
        ),
        "quality_variance_pass": merged["imputed_weighted_variance"].ge(
            float(thresholds["minimum_imputed_weighted_variance"])
        ),
        "quality_duplicate_pass": merged["is_duplicate_canonical"].astype(bool),
    }
    for name, values in checks.items():
        merged[name] = values.fillna(False)
    correctness = [name for name in checks if name.startswith("correctness_")]
    quality = [name for name in checks if name.startswith("quality_")]
    merged["correctness_pass"] = merged[correctness].all(axis=1)
    merged["data_qualified"] = merged[correctness + quality].all(axis=1)
    merged["eligibility_reason"] = merged.apply(
        lambda row: "pass"
        if row["data_qualified"]
        else ";".join(name for name in correctness + quality if not bool(row[name])),
        axis=1,
    )
    return merged.sort_values(["outer_split_id", "factor"], kind="stable").reset_index(
        drop=True
    )


def resource_estimate(profile: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for split_id, group in profile.groupby("outer_split_id", sort=True):
        total_rows = int(group["total_rows"].max())
        width = int(group["factor"].nunique())
        rows.append(
            {
                "outer_split_id": split_id,
                "inventory_feature_count": width,
                "development_row_count": total_rows,
                "float64_matrix_gib": total_rows * width * 8 / 1024**3,
                "basis": "full_inventory_width_resource_feasibility_only",
            }
        )
    return pd.DataFrame(rows)


def run_feature_only_profile(
    config: dict[str, Any], *, project_root: Path
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Profile Matrix v4 on development dates without accepting any label input."""
    parents = config["parents"]
    inventory_path = project_root / parents["factor_inventory"]
    dependency_path = project_root / parents["dependency_inventory"]
    status_path = project_root / parents["partition_status"]
    assignments_path = project_root / parents["date_assignments"]
    inventory = pd.read_csv(inventory_path)
    dependencies = pd.read_csv(dependency_path)
    factor_index = partition_factor_index(status_path)
    inventory_factors = inventory.loc[
        inventory["enabled"].astype(str).str.lower().eq("true")
        & inventory["runnable"].astype(str).str.lower().eq("true"),
        "name",
    ].astype(str).tolist()
    absent = sorted(set(inventory_factors).difference(factor_index))
    if absent:
        raise ValueError(f"enabled/runnable inventory factors missing from Matrix v4: {absent}")
    by_partition: dict[Path, list[str]] = {}
    for factor in inventory_factors:
        by_partition.setdefault(factor_index[factor], []).append(factor)

    profiles: list[pd.DataFrame] = []
    access_rows: list[dict[str, Any]] = []
    for split_id in config["split_ids"]:
        fold_dates = [
            load_fold_dates(
                assignments_path, outer_split_id=str(split_id), fold=str(fold)
            )
            for fold in config["folds"]
        ]
        dates = fold_dates[0].append(fold_dates[1:]).sort_values().unique()
        expected_key_hash: str | None = None
        for partition_path, factors in sorted(by_partition.items(), key=lambda item: str(item[0])):
            frame = pd.read_parquet(
                partition_path,
                columns=list(KEY_COLUMNS) + factors,
                filters=[
                    ("datetime", ">=", dates.min()),
                    ("datetime", "<=", dates.max()),
                ],
            )
            frame["datetime"] = pd.to_datetime(frame["datetime"], errors="raise").dt.normalize()
            frame["instrument"] = frame["instrument"].astype(str).str.upper()
            frame = frame.loc[frame["datetime"].isin(dates)].sort_values(
                list(KEY_COLUMNS), kind="stable"
            ).reset_index(drop=True)
            keys = (
                frame["datetime"].dt.strftime("%Y-%m-%d")
                + "|"
                + frame["instrument"]
            ).tolist()
            key_hash = canonical_hash(keys)
            if expected_key_hash is None:
                expected_key_hash = key_hash
            elif key_hash != expected_key_hash:
                raise ValueError(f"Matrix v4 partition key mismatch for {split_id}")
            profiles.append(
                profile_feature_frame(
                    frame, factor_names=factors, outer_split_id=str(split_id)
                )
            )
            access_rows.append(
                {
                    "outer_split_id": split_id,
                    "input_kind": "feature",
                    "scope": "train_plus_validation",
                    "path": str(partition_path),
                    "read_count": 1,
                    "row_count": len(frame),
                    "sha256": file_sha256(partition_path),
                }
            )
    profile = pd.concat(profiles, ignore_index=True)
    profile["duplicate_canonical_factor"] = profile.groupby(
        ["outer_split_id", "feature_content_sha256"], sort=False
    )["factor"].transform("min")
    profile["is_duplicate_canonical"] = profile["factor"].eq(
        profile["duplicate_canonical_factor"]
    )
    profile = profile.merge(
        inventory[["name", "source"]].rename(columns={"name": "factor"}),
        on="factor",
        how="left",
        validate="many_to_one",
    ).merge(
        dependencies[["factor", "source_family", "dependency_class", "review_status"]],
        on="factor",
        how="left",
        validate="many_to_one",
    )
    access = pd.DataFrame(access_rows)
    access = pd.concat(
        [
            access,
            pd.DataFrame(
                [
                    {
                        "outer_split_id": "all",
                        "input_kind": kind,
                        "scope": scope,
                        "path": "not_accessed",
                        "read_count": 0,
                        "row_count": 0,
                        "sha256": "not_applicable",
                    }
                    for kind, scope in (
                        ("label", "all"),
                        ("feature", "test"),
                        ("model_metric", "all"),
                        ("feature_role_or_cluster", "all"),
                    )
                ]
            ),
        ],
        ignore_index=True,
    )
    return profile, resource_estimate(profile), access


def write_feature_only_profile(
    *,
    output_dir: Path,
    config: dict[str, Any],
    profile: pd.DataFrame,
    resources: pd.DataFrame,
    access: pd.DataFrame,
    project_root: Path = Path("."),
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    targets = {
        "feature_quality_profile.csv": profile,
        "resource_feasibility.csv": resources,
        "access_audit.csv": access,
    }
    if any((output_dir / name).exists() for name in targets):
        raise FileExistsError("feature-only profile is immutable; refusing overwrite")
    for name, frame in targets.items():
        frame.to_csv(output_dir / name, index=False, encoding="utf-8-sig")
    receipt = {
        "schema_version": 1,
        "stage_id": STAGE_ID,
        "audit_scope": "feature_only",
        "decision_authority": "diagnostic_only",
        "thresholds_frozen": False,
        "threshold_basis_forbidden": sorted(FORBIDDEN_THRESHOLD_BASES),
        "profile_sha256": file_sha256(output_dir / "feature_quality_profile.csv"),
        "resource_sha256": file_sha256(output_dir / "resource_feasibility.csv"),
        "access_audit_sha256": file_sha256(output_dir / "access_audit.csv"),
        "source_receipts": {
            key: file_sha256(source_path)
            for key, value in config["parents"].items()
            if (source_path := project_root / value).is_file()
        },
    }
    (output_dir / "profile_receipt.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def write_freeze(
    *,
    output_dir: Path,
    config: dict[str, Any],
    profile_path: Path,
    decisions: pd.DataFrame,
) -> Path:
    thresholds = validate_threshold_freeze(config)
    output_dir.mkdir(parents=True, exist_ok=True)
    freeze_path = output_dir / "eligibility_freeze.json"
    decisions_path = output_dir / "feature_eligibility_decisions.csv"
    if freeze_path.exists() or decisions_path.exists():
        raise FileExistsError("eligibility freeze is immutable; refusing overwrite")
    decisions.to_csv(decisions_path, index=False, encoding="utf-8-sig")
    payload = {
        "schema_version": 1,
        "stage_id": STAGE_ID,
        "audit_scope": "feature_only",
        "decision_authority": "diagnostic_only",
        "selection_authorized": False,
        "strategy_v2_authorized": False,
        "thresholds": thresholds,
        "threshold_selection_reasons": config["threshold_selection"]["reasons"],
        "profile_sha256": file_sha256(profile_path),
        "decisions_sha256": file_sha256(decisions_path),
        "decision_row_count": len(decisions),
        "decision_content_sha256": canonical_hash(
            decisions.sort_values(["outer_split_id", "factor"]).to_dict("records")
        ),
    }
    freeze_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return freeze_path
