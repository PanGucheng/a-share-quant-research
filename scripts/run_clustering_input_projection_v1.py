from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from qlib_integration.contracts import contract_row  # noqa: E402
from research_validation.feature_matrix import atomic_parquet, canonical_hash, file_sha256  # noqa: E402
from research_validation.lineage import capture_code_state, load_artifact_manifest, validate_manifest_outputs, write_stage_artifact_manifest  # noqa: E402
from research_validation.stage_output import StageOutputPublisher  # noqa: E402

CONTROLLED = (
    "artifact_manifest.json", "projection_inventory.csv", "selection_date_audit.csv", "input_receipts.csv",
    "contract_status.csv", "clustering_input_projection_report.md", "resolved_config.json",
)


def resolve(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else (PROJECT_ROOT / path).resolve()


def sampled_dates(allowed: pd.DatetimeIndex, maximum: int) -> pd.DatetimeIndex:
    dates = pd.DatetimeIndex(allowed).sort_values().unique()
    if len(dates) <= maximum:
        return dates
    positions = np.linspace(0, len(dates) - 1, maximum, dtype=int)
    return pd.DatetimeIndex([dates[position] for position in positions]).unique()


def main() -> int:
    parser = argparse.ArgumentParser(description="Project stable factors onto exact development dates for clustering.")
    parser.add_argument("--config", type=Path, default=Path("configs/clustering_input_projection_669_v1.yaml"))
    args = parser.parse_args()
    config = yaml.safe_load(resolve(args.config).read_text(encoding="utf-8")) or {}
    manifest_paths = [resolve(path) for path in config["input_manifests"]]
    manifests = [load_artifact_manifest(path) for path in manifest_paths]
    issues = [issue for manifest, path in zip(manifests, manifest_paths) for issue in validate_manifest_outputs(manifest, path.parent)]
    if issues or any(manifest["artifact_status"] != "pass" for manifest in manifests):
        raise ValueError("clustering projection upstream is stale or blocked")
    stability = pd.read_csv(resolve(config["stability_board"]))
    stability = stability.loc[stability["stability_role"].isin(config["eligible_roles"])].copy()
    allowed = pd.read_csv(resolve(config["allowed_dates"]), parse_dates=["datetime"])
    outer = pd.read_csv(resolve(config["outer_date_assignments"]), parse_dates=["datetime"])
    selected_outer = {str(value) for value in config.get("selected_outer_splits", [])}
    if selected_outer:
        stability = stability.loc[stability["outer_split_id"].astype(str).isin(selected_outer)]
        allowed = allowed.loc[allowed["outer_split_id"].astype(str).isin(selected_outer)]
    batches = pd.read_csv(resolve(config["factor_batch_manifest"]))
    daily = pd.read_csv(resolve(config["daily_ic_table"]), parse_dates=["datetime"])
    runtime = resolve(config["runtime_dir"])
    runtime.mkdir(parents=True, exist_ok=True)
    inventory_rows = []
    audit_rows = []
    for outer_split_id, split_stability in stability.groupby("outer_split_id", sort=True):
        split_stability = split_stability.sort_values(["selection_frequency", "factor"], ascending=[False, True])
        if config.get("maximum_factors_per_split") is not None:
            split_stability = split_stability.head(int(config["maximum_factors_per_split"]))
        factors = sorted(split_stability["factor"].astype(str))
        if len(factors) < int(config["minimum_components"]):
            raise ValueError(f"{outer_split_id} has fewer than minimum_components stable factors")
        allowed_dates = pd.DatetimeIndex(allowed.loc[allowed["outer_split_id"].astype(str).eq(str(outer_split_id)), "datetime"]).sort_values().unique()
        exposure_dates = sampled_dates(allowed_dates, int(config["max_exposure_dates"]))
        frame: pd.DataFrame | None = None
        needed = set(factors)
        for batch in batches.itertuples(index=False):
            batch_path = resolve(str(batch.output_path))
            columns = pq.ParquetFile(batch_path).schema.names
            selected_columns = sorted(needed & set(columns))
            if not selected_columns:
                continue
            available = pd.read_parquet(batch_path, columns=["datetime", "instrument", *selected_columns])
            available["datetime"] = pd.to_datetime(available["datetime"])
            available = available.loc[available["datetime"].isin(exposure_dates)].reset_index(drop=True)
            if frame is None:
                frame = available
            else:
                if not frame[["datetime", "instrument"]].equals(available[["datetime", "instrument"]]):
                    raise ValueError(f"clustering projection key mismatch: {outer_split_id}/{batch.batch_id}")
                for column in selected_columns:
                    frame[column] = available[column].to_numpy()
        if frame is None or not needed.issubset(frame.columns):
            raise ValueError(f"missing clustering factors for {outer_split_id}: {sorted(needed - set(frame.columns if frame is not None else []))}")
        performance = daily.loc[daily["factor"].astype(str).isin(factors) & daily["datetime"].isin(allowed_dates)].copy()
        performance["outer_split_id"] = outer_split_id
        exposure_path = runtime / f"{outer_split_id}_exposure.parquet"
        performance_path = runtime / f"{outer_split_id}_performance.parquet"
        atomic_parquet(frame, exposure_path)
        atomic_parquet(performance.sort_values(["datetime", "factor"], kind="stable"), performance_path)
        test_dates = set(outer.loc[outer["split_id"].astype(str).eq(str(outer_split_id)) & outer["fold"].eq("test"), "datetime"])
        exposure_outside = int((~frame["datetime"].isin(allowed_dates)).sum())
        performance_outside = int((~performance["datetime"].isin(allowed_dates)).sum())
        audit_rows.append({
            "outer_split_id": outer_split_id, "allowed_date_count": len(allowed_dates), "exposure_date_count": frame["datetime"].nunique(),
            "performance_date_count": performance["datetime"].nunique(), "exposure_outside_allowed_count": exposure_outside,
            "performance_outside_allowed_count": performance_outside,
            "outer_test_in_exposure_count": int(frame["datetime"].isin(test_dates).sum()),
            "outer_test_in_performance_count": int(performance["datetime"].isin(test_dates).sum()),
        })
        inventory_rows.append({
            "outer_split_id": outer_split_id, "factor_count": len(factors),
            "allowed_dates_sha256": canonical_hash([value.date().isoformat() for value in allowed_dates]),
            "exposure_dates_sha256": canonical_hash([value.date().isoformat() for value in exposure_dates]),
            "exposure_path": exposure_path.as_posix(), "exposure_sha256": file_sha256(exposure_path), "exposure_rows": len(frame),
            "performance_path": performance_path.as_posix(), "performance_sha256": file_sha256(performance_path), "performance_rows": len(performance),
            "factor_list_sha256": canonical_hash(factors),
        })
    inventory = pd.DataFrame(inventory_rows)
    audit = pd.DataFrame(audit_rows)
    receipts = pd.DataFrame([
        {"input_name": name, "artifact_id": manifest["artifact_id"], "path": path.as_posix(), "sha256": file_sha256(path), "join_keys": join_keys}
        for name, manifest, path, join_keys in (
            ("stability", manifests[0], resolve(config["stability_board"]), "outer_split_id,factor"),
            ("matrix_batches", manifests[1], resolve(config["factor_batch_manifest"]), "datetime,instrument,factor"),
            ("daily_ic", manifests[2], resolve(config["daily_ic_table"]), "datetime,factor"),
            ("allowed_dates", manifests[3], resolve(config["allowed_dates"]), "outer_split_id,datetime"),
            ("outer_assignments", manifests[4], resolve(config["outer_date_assignments"]), "outer_split_id,datetime,fold"),
        )
    ])
    contracts = pd.DataFrame([
        contract_row("outer_split_count", len(inventory) == int(config["expected_outer_splits"]), len(inventory), config["expected_outer_splits"]),
        contract_row("minimum_components", inventory["factor_count"].ge(int(config["minimum_components"])).all(), inventory["factor_count"].tolist(), f">={config['minimum_components']}"),
        contract_row("exposure_outside_allowed_dates", audit["exposure_outside_allowed_count"].sum() == 0, int(audit["exposure_outside_allowed_count"].sum()), 0),
        contract_row("performance_outside_allowed_dates", audit["performance_outside_allowed_count"].sum() == 0, int(audit["performance_outside_allowed_count"].sum()), 0),
        contract_row("outer_test_in_exposure", audit["outer_test_in_exposure_count"].sum() == 0, int(audit["outer_test_in_exposure_count"].sum()), 0),
        contract_row("outer_test_in_performance", audit["outer_test_in_performance_count"].sum() == 0, int(audit["outer_test_in_performance_count"].sum()), 0),
        contract_row("projection_hashes_present", inventory[["exposure_sha256", "performance_sha256"]].apply(lambda column: column.str.len().eq(64)).all().all(), int(inventory[["exposure_sha256", "performance_sha256"]].apply(lambda column: column.str.len().eq(64)).sum().sum()), len(inventory) * 2),
    ])
    ready = bool(contracts["status"].eq("pass").all())
    output_dir = resolve(config["output_dir"])
    with StageOutputPublisher(output_dir, CONTROLLED) as publisher:
        inventory.to_csv(publisher.path("projection_inventory.csv"), index=False, encoding="utf-8-sig")
        audit.to_csv(publisher.path("selection_date_audit.csv"), index=False, encoding="utf-8-sig")
        receipts.to_csv(publisher.path("input_receipts.csv"), index=False, encoding="utf-8-sig")
        contracts.to_csv(publisher.path("contract_status.csv"), index=False, encoding="utf-8-sig")
        publisher.path("resolved_config.json").write_text(json.dumps(config, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        publisher.path("clustering_input_projection_report.md").write_text(
            "# Clustering Input Projection V1\n\n"
            + f"- Status: `{'pass' if ready else 'blocked'}`\n"
            + f"- Outer splits: `{len(inventory)}`\n"
            + "- Exposure and performance inputs are restricted to exact allowed development dates.\n"
            + "- Outer-test rows: `0`\n",
            encoding="utf-8",
        )
        files = [publisher.path(name) for name in CONTROLLED if name != "artifact_manifest.json"]
        write_stage_artifact_manifest(
            project_root=PROJECT_ROOT, stage_id="clustering_input_projection_v1", config=config,
            output_dir=publisher.staging_dir, output_files=files, code_state=capture_code_state(PROJECT_ROOT),
            input_manifest_paths=manifest_paths, factor_frame_id=manifests[1]["factor_frame_id"],
            split_manifest_id=manifests[4]["split_manifest_id"], start_date=allowed["datetime"].min(),
            end_date=allowed["datetime"].max(), lineage_status="complete",
            artifact_status="pass" if ready else "blocked", blocked_reason="" if ready else "blocked_clustering_projection",
        )
        publisher.publish()
    print(contracts.to_string(index=False))
    return 0 if ready else 2


if __name__ == "__main__":
    raise SystemExit(main())
