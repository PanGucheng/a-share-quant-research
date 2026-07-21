from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from qlib_integration.contracts import contract_row  # noqa: E402
from research_validation.bulk_run_gate import approval_id, build_bulk_run_binding  # noqa: E402
from research_validation.lineage import (  # noqa: E402
    capture_code_state,
    load_artifact_manifest,
    write_stage_artifact_manifest,
)
from research_validation.stage_output import StageOutputPublisher  # noqa: E402
from scripts.run_full_research_feature_matrix_v1 import (  # noqa: E402
    matrix_exact_command,
    matrix_input_inventory,
    matrix_run_scope,
)


CONTROLLED = (
    "artifact_manifest.json",
    "bulk_run_review.md",
    "canary_contract_status.csv",
    "canary_summary.csv",
    "exact_command.txt",
    "factor_and_family_inventory.csv",
    "input_inventory.csv",
    "resolved_config.json",
    "resource_estimate.json",
    "split_and_date_inventory.csv",
    "user_approval.json",
)


def resolve(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else (PROJECT_ROOT / path).resolve()


def batch_specs(matrix_config: dict[str, object]) -> tuple[list[tuple[str, str, list[str]]], pd.DataFrame]:
    plan = pd.read_csv(resolve(matrix_config["batch_plan"]))
    inventory = pd.read_csv(resolve(matrix_config["factor_inventory"]))
    specs = []
    for row in plan.itertuples(index=False):
        names = sorted(inventory.loc[inventory["batch_id"].eq(row.batch_id), "name"].astype(str))
        specs.append((str(row.batch_id), str(row.source), names))
    return specs, inventory


def compare_canary(config: dict[str, object]) -> pd.DataFrame:
    new = pd.read_parquet(resolve(config["canary_partition"]))
    factors = [column for column in new.columns if column not in {"datetime", "instrument"}]
    old = pd.read_parquet(resolve(config["legacy_partition"]), columns=["datetime", "instrument", *factors])
    old["datetime"] = pd.to_datetime(old["datetime"])
    new["datetime"] = pd.to_datetime(new["datetime"])
    old = old.loc[old["datetime"].between(new["datetime"].min(), new["datetime"].max())]
    merged = old.merge(new, on=["datetime", "instrument"], how="outer", suffixes=("_legacy", "_v3"), indicator=True, validate="one_to_one")
    rows = []
    for factor in factors:
        legacy = pd.to_numeric(merged[f"{factor}_legacy"], errors="coerce")
        current = pd.to_numeric(merged[f"{factor}_v3"], errors="coerce")
        valid = legacy.notna() & current.notna()
        difference = (legacy.loc[valid] - current.loc[valid]).abs()
        rows.append(
            {
                "factor": factor,
                "legacy_rows": len(old),
                "v3_rows": len(new),
                "left_only_keys": int(merged["_merge"].eq("left_only").sum()),
                "right_only_keys": int(merged["_merge"].eq("right_only").sum()),
                "nan_mismatch_count": int(legacy.isna().ne(current.isna()).sum()),
                "nonzero_difference_count": int(difference.gt(0).sum()),
                "max_absolute_difference": float(difference.max()) if len(difference) else 0.0,
            }
        )
    return pd.DataFrame(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare an exact self-reviewed waiver bundle for the matrix v3 bulk run.")
    parser.add_argument("--config", type=Path, default=Path("configs/full_research_feature_matrix_669_bulk_review_v1.yaml"))
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--run-purpose", choices=("materialize", "cache_verify"), required=True)
    args = parser.parse_args()
    review_config = yaml.safe_load(resolve(args.config).read_text(encoding="utf-8")) or {}
    matrix_config_path = resolve(review_config["matrix_config"])
    matrix_config = yaml.safe_load(matrix_config_path.read_text(encoding="utf-8")) or {}
    specs, factor_inventory = batch_specs(matrix_config)
    code_state = capture_code_state(PROJECT_ROOT)
    if code_state.dirty:
        raise ValueError("bulk-run review bundle must be generated from a clean project worktree")

    catalog_manifest = load_artifact_manifest(resolve(matrix_config["factor_catalog_manifest"]))
    universe_manifest = load_artifact_manifest(resolve(matrix_config["universe_manifest"]))
    raw_manifest = load_artifact_manifest(resolve(matrix_config["raw_market_data_snapshot_manifest"]))
    source_manifest = load_artifact_manifest(resolve(matrix_config["factor_source_provenance_manifest"]))
    canary_manifest_path = resolve(review_config["canary_output_dir"]) / "artifact_manifest.json"
    canary_manifest = load_artifact_manifest(canary_manifest_path)
    raw_detail = json.loads(resolve(matrix_config["raw_market_data_detail_manifest"]).read_text(encoding="utf-8"))
    source_detail = json.loads(resolve(matrix_config["factor_source_detail_manifest"]).read_text(encoding="utf-8"))
    inventory_rows = matrix_input_inventory(
        matrix_config,
        [catalog_manifest, universe_manifest, raw_manifest, source_manifest],
        raw_detail,
        source_detail,
    )
    scope = matrix_run_scope(matrix_config, specs, args.run_purpose)
    output_dir = resolve(review_config["output_root"]) / args.run_id
    approval_path = output_dir / "user_approval.json"
    exact_command = matrix_exact_command(matrix_config_path, approval_path, args.run_purpose)
    binding = build_bulk_run_binding(
        run_id=args.run_id,
        commit_sha=code_state.commit_sha,
        config=matrix_config,
        input_inventory=inventory_rows,
        exact_command=exact_command,
        scope=scope,
    )

    canary_contract = pd.read_csv(resolve(review_config["canary_output_dir"]) / "contract_status.csv")
    canary_batch = pd.read_csv(resolve(review_config["canary_output_dir"]) / "batch_manifest.csv")
    comparison = compare_canary(review_config)
    legacy_batch = pd.read_csv(resolve(review_config["legacy_batch_manifest"]))
    estimated_compute_seconds = float(pd.to_numeric(legacy_batch["runtime_seconds"], errors="coerce").fillna(0).sum())
    estimated_write_bytes = int(pd.to_numeric(legacy_batch["output_size_bytes"], errors="coerce").fillna(0).sum())
    estimated_read_bytes = estimated_write_bytes + int(raw_detail["raw_parquet"]["size_bytes"])
    free_disk = shutil.disk_usage(resolve(matrix_config["runtime_dir"]).parent).free
    required_disk = int(estimated_write_bytes * float(review_config["minimum_free_disk_multiplier"]))
    preflight = pd.DataFrame(
        [
            contract_row("canary_contracts_pass", bool(canary_contract["status"].eq("pass").all()), int(canary_contract["status"].ne("pass").sum()), 0),
            contract_row("canary_cache_hit_verified", bool(canary_batch["cache_hit"].astype(bool).all()), int(canary_batch["cache_hit"].astype(bool).sum()), len(canary_batch)),
            contract_row("canary_key_schema_v3", bool(canary_batch["key_schema_version"].eq(3).all()), canary_batch["key_schema_version"].tolist(), 3),
            contract_row("canary_legacy_reindex_zero", not canary_batch["reindexed_from_cache"].astype(bool).any(), int(canary_batch["reindexed_from_cache"].astype(bool).sum()), 0),
            contract_row("canary_key_grid_exact", int(comparison[["left_only_keys", "right_only_keys"]].to_numpy().sum()) == 0, int(comparison[["left_only_keys", "right_only_keys"]].to_numpy().sum()), 0),
            contract_row("canary_nan_pattern_exact", int(comparison["nan_mismatch_count"].sum()) == 0, int(comparison["nan_mismatch_count"].sum()), 0),
            contract_row("canary_values_exact", int(comparison["nonzero_difference_count"].sum()) == 0, int(comparison["nonzero_difference_count"].sum()), 0),
            contract_row("free_disk_sufficient", free_disk >= required_disk, free_disk, f">={required_disk}"),
            contract_row("full_scope_factors", int(scope["factor_count"]) == 669, scope["factor_count"], 669),
            contract_row("full_scope_batches", int(scope["batch_count"]) == 30, scope["batch_count"], 30),
        ]
    )
    ready = bool(preflight["status"].eq("pass").all() and canary_manifest["artifact_status"] == "pass")
    approval = {
        **binding,
        "bulk_run_approval_id": approval_id(binding),
        "status": "approved" if ready else "pending_review",
        "approval_mode": str(review_config["approval_mode"]),
        "approved_by": str(review_config["approved_by"]),
        "approval_source": str(review_config["approval_source"]),
        "approval_timestamp": datetime.now(timezone.utc).isoformat(),
        "single_use": True,
    }
    resource_estimate = {
        "estimated_compute_seconds_from_pr4": estimated_compute_seconds,
        "estimated_read_bytes": estimated_read_bytes,
        "estimated_write_bytes": 0 if args.run_purpose == "cache_verify" else estimated_write_bytes,
        "estimated_peak_memory_bytes": int(review_config["estimated_peak_memory_bytes"]),
        "free_disk_bytes": free_disk,
        "required_free_disk_bytes": required_disk,
        "resume_policy": "per-batch v3 input/output hash; failed batch blocks publication",
        "cache_policy": "v2 and legacy hashes are never accepted as v3 hits",
        "failure_policy": "stop, retain valid v3 partitions, repair, regenerate review binding if code/config/input/scope changes",
    }
    split_dates = pd.DataFrame(
        [
            {
                "run_id": args.run_id,
                "operation": args.run_purpose,
                "warmup_start_date": matrix_config["warmup_start_date"],
                "start_date": matrix_config["start_date"],
                "end_date": matrix_config["end_date"],
                "outer_test_read": False,
                "pre_test_freeze_required": False,
                "selection_semantics": "feature_materialization_only",
            }
        ]
    )
    with StageOutputPublisher(output_dir, CONTROLLED) as publisher:
        pd.DataFrame(inventory_rows).to_csv(publisher.path("input_inventory.csv"), index=False, encoding="utf-8-sig")
        factor_inventory.to_csv(publisher.path("factor_and_family_inventory.csv"), index=False, encoding="utf-8-sig")
        split_dates.to_csv(publisher.path("split_and_date_inventory.csv"), index=False, encoding="utf-8-sig")
        preflight.to_csv(publisher.path("canary_contract_status.csv"), index=False, encoding="utf-8-sig")
        comparison.to_csv(publisher.path("canary_summary.csv"), index=False, encoding="utf-8-sig")
        publisher.path("resolved_config.json").write_text(json.dumps(matrix_config, ensure_ascii=False, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
        publisher.path("resource_estimate.json").write_text(json.dumps(resource_estimate, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        publisher.path("exact_command.txt").write_text(exact_command + "\n", encoding="utf-8")
        publisher.path("user_approval.json").write_text(json.dumps(approval, ensure_ascii=False, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
        publisher.path("bulk_run_review.md").write_text(
            "# Matrix V3 Bulk-Run Review\n\n"
            + f"- Run ID / purpose: `{args.run_id}` / `{args.run_purpose}`\n"
            + f"- Status: `{'approved_by_session_waiver' if ready else 'blocked'}`\n"
            + f"- Clean commit: `{code_state.commit_sha}`\n"
            + f"- Scope: `{scope['batch_count']}` batches / `{scope['factor_count']}` factors / `{scope['start_date']}` to `{scope['end_date']}`\n"
            + f"- Canary: 1 batch / 5 factors / `{len(comparison)}` exact legacy comparisons; nonzero differences `{int(comparison['nonzero_difference_count'].sum())}`\n"
            + f"- Estimated PR #4 compute time: `{estimated_compute_seconds / 3600:.2f}` hours\n"
            + f"- Estimated read/write: `{estimated_read_bytes / 1e9:.2f}` GB / `{resource_estimate['estimated_write_bytes'] / 1e9:.2f}` GB\n"
            + f"- Free disk: `{free_disk / 1e9:.2f}` GB\n"
            + f"- Approval: `{approval['bulk_run_approval_id']}` (`{approval['approval_mode']}`)\n"
            + "- Outer test is not read; this run only materializes PIT factor features.\n"
            + "- Any code/config/input/command/scope change invalidates this approval binding.\n",
            encoding="utf-8",
        )
        files = [publisher.path(item) for item in CONTROLLED if item != "artifact_manifest.json"]
        write_stage_artifact_manifest(
            project_root=PROJECT_ROOT,
            stage_id="bulk_run_review_v1",
            config={**review_config, "run_id": args.run_id, "run_purpose": args.run_purpose, "matrix_config": matrix_config},
            output_dir=publisher.staging_dir,
            output_files=files,
            code_state=code_state,
            input_manifest_paths=[
                resolve(matrix_config["factor_catalog_manifest"]),
                resolve(matrix_config["universe_manifest"]),
                resolve(matrix_config["raw_market_data_snapshot_manifest"]),
                resolve(matrix_config["factor_source_provenance_manifest"]),
                canary_manifest_path,
            ],
            universe_artifact_id=universe_manifest["universe_artifact_id"],
            factor_catalog_id=catalog_manifest["factor_catalog_id"],
            factor_frame_id=canary_manifest["factor_frame_id"],
            start_date=matrix_config["start_date"],
            end_date=matrix_config["end_date"],
            lineage_status="complete",
            artifact_status="pass" if ready else "blocked",
            blocked_reason="" if ready else "blocked_bulk_run_preflight",
        )
        publisher.publish()
    print(preflight.to_string(index=False))
    print(exact_command)
    return 0 if ready else 2


if __name__ == "__main__":
    raise SystemExit(main())
