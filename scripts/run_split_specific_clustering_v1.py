from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from factor_research.factor_clustering import hierarchical_clusters  # noqa: E402
from factor_research.factor_similarity import combined_distance, daily_exposure_similarity, performance_similarity  # noqa: E402
from factor_research.representative_selection import select_representatives  # noqa: E402
from qlib_integration.contracts import contract_row  # noqa: E402
from research_validation.feature_matrix import canonical_hash, file_sha256  # noqa: E402
from research_validation.lineage import capture_code_state, load_artifact_manifest, validate_manifest_outputs, write_stage_artifact_manifest  # noqa: E402
from research_validation.stage_output import StageOutputPublisher  # noqa: E402

CONTROLLED = (
    "artifact_manifest.json", "exposure_similarity_by_split.csv", "performance_similarity_by_split.csv",
    "factor_distance_by_split.csv", "factor_clusters_by_split.csv", "representatives_by_split.csv",
    "excluded_redundant_factors_by_split.csv", "cluster_stability_by_split.csv", "selection_date_audit.csv",
    "input_receipts.csv", "contract_status.csv", "clustering_report.md", "resolved_config.json",
)


def resolve(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else (PROJECT_ROOT / path).resolve()


def matrix_to_long(matrix: pd.DataFrame, outer_split_id: str, value_name: str) -> pd.DataFrame:
    return matrix.rename_axis("left_factor").reset_index().melt(
        id_vars="left_factor", var_name="right_factor", value_name=value_name
    ).assign(outer_split_id=outer_split_id)[["outer_split_id", "left_factor", "right_factor", value_name]]


def main() -> int:
    parser = argparse.ArgumentParser(description="Cluster stable factors separately on exact development dates.")
    parser.add_argument("--config", type=Path, default=Path("configs/factor_clustering_full_research_669_v1.yaml"))
    args = parser.parse_args()
    config = yaml.safe_load(resolve(args.config).read_text(encoding="utf-8")) or {}
    manifest_paths = [resolve(path) for path in config["input_manifests"]]
    manifests = [load_artifact_manifest(path) for path in manifest_paths]
    issues = [issue for manifest, path in zip(manifests, manifest_paths) for issue in validate_manifest_outputs(manifest, path.parent)]
    if issues or any(manifest["artifact_status"] != "pass" for manifest in manifests):
        raise ValueError("split clustering upstream is stale or blocked")
    source_bindings = [
        (0, resolve(config["stability_board"])),
        (1, resolve(config["projection_inventory"])),
        (2, resolve(config["allowed_dates"])),
    ]
    for manifest_index, source_path in source_bindings:
        expected_hash = manifests[manifest_index]["output_file_hashes"].get(source_path.name)
        if not expected_hash or file_sha256(source_path) != expected_hash:
            raise ValueError(f"clustering source is not bound by manifest: {source_path}")
    canary_manifest_path = config.get("canary_manifest")
    canary_gate_observed = "not_required"
    if canary_manifest_path:
        canary_manifest_resolved = resolve(canary_manifest_path)
        canary_manifest = load_artifact_manifest(canary_manifest_resolved)
        canary_issues = validate_manifest_outputs(canary_manifest, canary_manifest_resolved.parent)
        canary_contract = pd.read_csv(resolve(config["canary_contract"]))
        if canary_issues or canary_manifest["artifact_status"] != "pass" or not canary_contract["status"].eq("pass").all():
            raise ValueError("corrected clustering canary is stale, blocked, or incomplete")
        canary_gate_observed = "pass"
    stability = pd.read_csv(resolve(config["stability_board"]))
    stability = stability.loc[stability["stability_role"].isin(config["eligible_roles"])].copy()
    inventory = pd.read_csv(resolve(config["projection_inventory"]))
    allowed_table = pd.read_csv(resolve(config["allowed_dates"]), parse_dates=["datetime"])
    exposure_rows, performance_rows, distance_rows = [], [], []
    cluster_rows, representative_rows, excluded_rows, cluster_summary_rows, audit_rows = [], [], [], [], []
    insufficient_pairs = 0
    for receipt in inventory.itertuples(index=False):
        outer_split_id = str(receipt.outer_split_id)
        split_stability = stability.loc[
            stability["outer_split_id"].astype(str).eq(outer_split_id)
            & stability["factor"].astype(str).isin(pd.read_parquet(resolve(receipt.performance_path), columns=["factor"])["factor"].astype(str).unique())
        ].copy()
        factors = sorted(split_stability["factor"].astype(str))
        if len(factors) != int(receipt.factor_count) or len(factors) < int(config["minimum_components"]):
            raise ValueError(f"clustering factor inventory mismatch for {outer_split_id}")
        exposure_path = resolve(receipt.exposure_path)
        performance_path = resolve(receipt.performance_path)
        if file_sha256(exposure_path) != str(receipt.exposure_sha256) or file_sha256(performance_path) != str(receipt.performance_sha256):
            raise ValueError(f"clustering runtime projection hash mismatch for {outer_split_id}")
        exposure_frame = pd.read_parquet(exposure_path)
        performance_frame = pd.read_parquet(performance_path)
        allowed_dates = pd.DatetimeIndex(allowed_table.loc[allowed_table["outer_split_id"].astype(str).eq(outer_split_id), "datetime"]).sort_values().unique()
        factor_map = {factor: factor for factor in factors}
        exposure = daily_exposure_similarity(
            exposure_frame, factor_map, allowed_dates=allowed_dates,
            minimum_pair_observations=int(config["minimum_exposure_pair_observations"]),
        )
        series_map = {
            str(factor): group.set_index("datetime")[str(config["daily_ic_column"])]
            for factor, group in performance_frame.groupby("factor", sort=True)
        }
        performance = performance_similarity(
            series_map, allowed_dates=allowed_dates,
            minimum_pair_dates=int(config["minimum_performance_pair_dates"]),
        )
        off_diagonal = ~np.eye(len(factors), dtype=bool)
        insufficient_pairs += int(exposure.to_numpy()[off_diagonal].astype(float).size - np.isfinite(exposure.to_numpy()[off_diagonal].astype(float)).sum())
        insufficient_pairs += int(performance.to_numpy()[off_diagonal].astype(float).size - np.isfinite(performance.to_numpy()[off_diagonal].astype(float)).sum())
        distance = combined_distance(exposure, performance, float(config["exposure_weight"]))
        clusters = hierarchical_clusters(distance, float(config["cluster_distance_threshold"]), str(config["linkage_method"]))
        representatives, excluded = select_representatives(clusters, split_stability.drop(columns=["outer_split_id"]))
        for frame in (clusters, representatives, excluded):
            frame.insert(0, "outer_split_id", outer_split_id)
        summary = clusters.groupby(["outer_split_id", "cluster_id"]).size().reset_index(name="member_count")
        exposure_rows.append(matrix_to_long(exposure, outer_split_id, "exposure_correlation"))
        performance_rows.append(matrix_to_long(performance, outer_split_id, "performance_correlation"))
        distance_rows.append(matrix_to_long(distance, outer_split_id, "distance"))
        cluster_rows.append(clusters)
        representative_rows.append(representatives)
        excluded_rows.append(excluded)
        cluster_summary_rows.append(summary)
        audit_rows.append({
            "outer_split_id": outer_split_id, "allowed_date_count": len(allowed_dates),
            "allowed_dates_sha256": receipt.allowed_dates_sha256,
            "allowed_dates_hash_match": canonical_hash([value.date().isoformat() for value in allowed_dates]) == str(receipt.allowed_dates_sha256),
            "exposure_date_min": pd.to_datetime(exposure_frame["datetime"]).min(), "exposure_date_max": pd.to_datetime(exposure_frame["datetime"]).max(),
            "performance_date_min": pd.to_datetime(performance_frame["datetime"]).min(), "performance_date_max": pd.to_datetime(performance_frame["datetime"]).max(),
            "exposure_outside_allowed_count": int((~pd.to_datetime(exposure_frame["datetime"]).isin(allowed_dates)).sum()),
            "performance_outside_allowed_count": int((~pd.to_datetime(performance_frame["datetime"]).isin(allowed_dates)).sum()),
        })
    exposure_long = pd.concat(exposure_rows, ignore_index=True)
    performance_long = pd.concat(performance_rows, ignore_index=True)
    distance_long = pd.concat(distance_rows, ignore_index=True)
    clusters_all = pd.concat(cluster_rows, ignore_index=True)
    representatives_all = pd.concat(representative_rows, ignore_index=True)
    excluded_all = pd.concat(excluded_rows, ignore_index=True)
    cluster_summary = pd.concat(cluster_summary_rows, ignore_index=True)
    audit = pd.DataFrame(audit_rows)
    expected_splits = int(config["expected_outer_splits"])
    expected_factor_counts = inventory.set_index("outer_split_id")["factor_count"].astype(int)
    actual_factor_counts = clusters_all.groupby("outer_split_id")["factor"].nunique()
    contracts = pd.DataFrame([
        contract_row("canary_gate_passed", canary_gate_observed in {"not_required", "pass"}, canary_gate_observed, "pass_or_not_required"),
        contract_row("outer_split_count", clusters_all["outer_split_id"].nunique() == expected_splits, clusters_all["outer_split_id"].nunique(), expected_splits),
        contract_row("every_selected_factor_has_cluster", actual_factor_counts.eq(expected_factor_counts).all(), actual_factor_counts.tolist(), expected_factor_counts.tolist()),
        contract_row("every_cluster_has_representative", representatives_all.groupby("outer_split_id")["cluster_id"].nunique().eq(clusters_all.groupby("outer_split_id")["cluster_id"].nunique()).all(), representatives_all.groupby("outer_split_id")["cluster_id"].nunique().tolist(), clusters_all.groupby("outer_split_id")["cluster_id"].nunique().tolist()),
        contract_row("duplicate_cluster_votes", not representatives_all.duplicated(["outer_split_id", "cluster_id"]).any(), int(representatives_all.duplicated(["outer_split_id", "cluster_id"]).sum()), 0),
        contract_row("minimum_components", representatives_all.groupby("outer_split_id")["factor"].nunique().ge(int(config["minimum_components"])).all(), representatives_all.groupby("outer_split_id")["factor"].nunique().tolist(), f">={config['minimum_components']}"),
        contract_row("insufficient_pair_overlap_count", insufficient_pairs == 0, insufficient_pairs, 0),
        contract_row("exposure_dates_exactly_allowed", audit["exposure_outside_allowed_count"].sum() == 0, int(audit["exposure_outside_allowed_count"].sum()), 0),
        contract_row("performance_dates_exactly_allowed", audit["performance_outside_allowed_count"].sum() == 0, int(audit["performance_outside_allowed_count"].sum()), 0),
        contract_row("allowed_dates_hash_match", audit["allowed_dates_hash_match"].all(), int(audit["allowed_dates_hash_match"].sum()), len(audit)),
        contract_row("source_manifests_hash_bound", True, len(source_bindings), len(source_bindings)),
    ])
    receipts = pd.DataFrame([
        {"input_name": "stability", "artifact_id": manifests[0]["artifact_id"], "path": resolve(config["stability_board"]).as_posix(), "sha256": file_sha256(resolve(config["stability_board"])), "join_keys": "outer_split_id,factor", "input_rows": len(stability), "consumed_rows": len(clusters_all), "missing_rows": 0},
        {"input_name": "clustering_projection", "artifact_id": manifests[1]["artifact_id"], "path": resolve(config["projection_inventory"]).as_posix(), "sha256": file_sha256(resolve(config["projection_inventory"])), "join_keys": "outer_split_id", "input_rows": len(inventory), "consumed_rows": len(inventory), "missing_rows": 0},
        {"input_name": "allowed_dates", "artifact_id": manifests[2]["artifact_id"], "path": resolve(config["allowed_dates"]).as_posix(), "sha256": file_sha256(resolve(config["allowed_dates"])), "join_keys": "outer_split_id,datetime", "input_rows": len(allowed_table), "consumed_rows": int(audit["allowed_date_count"].sum()), "missing_rows": 0},
    ])
    ready = bool(contracts["status"].eq("pass").all())
    output_dir = resolve(config["output_dir"])
    with StageOutputPublisher(output_dir, CONTROLLED) as publisher:
        for name, frame in (
            ("exposure_similarity_by_split.csv", exposure_long), ("performance_similarity_by_split.csv", performance_long),
            ("factor_distance_by_split.csv", distance_long), ("factor_clusters_by_split.csv", clusters_all),
            ("representatives_by_split.csv", representatives_all), ("excluded_redundant_factors_by_split.csv", excluded_all),
            ("cluster_stability_by_split.csv", cluster_summary), ("selection_date_audit.csv", audit),
            ("input_receipts.csv", receipts), ("contract_status.csv", contracts),
        ):
            frame.to_csv(publisher.path(name), index=False, encoding="utf-8-sig")
        publisher.path("resolved_config.json").write_text(json.dumps(config, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        publisher.path("clustering_report.md").write_text(
            "# Corrected Split-Specific Factor Clustering\n\n"
            + f"- Status: `{'pass' if ready else 'blocked'}`\n"
            + f"- Outer splits / stable factors / representatives: `{expected_splits}` / `{len(clusters_all)}` / `{len(representatives_all)}`\n"
            + "- Exposure and performance similarities use exact development allowed dates only.\n",
            encoding="utf-8",
        )
        files = [publisher.path(name) for name in CONTROLLED if name != "artifact_manifest.json"]
        write_stage_artifact_manifest(
            project_root=PROJECT_ROOT, stage_id=str(config.get("stage_id", "factor_clustering_v1")), config=config,
            output_dir=publisher.staging_dir, output_files=files, code_state=capture_code_state(PROJECT_ROOT),
            input_manifest_paths=manifest_paths, factor_frame_id=manifests[0]["factor_frame_id"],
            split_manifest_id=manifests[0]["split_manifest_id"], start_date=allowed_table["datetime"].min(),
            end_date=allowed_table["datetime"].max(), lineage_status="complete",
            artifact_status="pass" if ready else "blocked", blocked_reason="" if ready else "blocked_split_clustering",
        )
        publisher.publish()
    print(contracts.to_string(index=False))
    return 0 if ready else 2


if __name__ == "__main__":
    raise SystemExit(main())
