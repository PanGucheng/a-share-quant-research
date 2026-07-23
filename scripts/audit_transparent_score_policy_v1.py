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
    "artifact_manifest.json", "transparent_score_policy.json", "component_completeness_summary.csv",
    "daily_component_summary.csv", "missing_component_frequency.csv", "component_audit_inventory.csv",
    "input_receipts.csv", "contract_status.csv", "score_policy_report.md", "resolved_config.json",
)


def resolve(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else (PROJECT_ROOT / path).resolve()


def sampled_dates(values: pd.DatetimeIndex, maximum: int | None) -> pd.DatetimeIndex:
    dates = pd.DatetimeIndex(values).sort_values().unique()
    if maximum is None or len(dates) <= maximum:
        return dates
    positions = np.linspace(0, len(dates) - 1, maximum, dtype=int)
    return pd.DatetimeIndex([dates[position] for position in positions]).unique()


def main() -> int:
    parser = argparse.ArgumentParser(description="Freeze a development-only transparent score completeness policy.")
    parser.add_argument("--config", type=Path, default=Path("configs/transparent_score_policy_corrected_v1.yaml"))
    args = parser.parse_args()
    config = yaml.safe_load(resolve(args.config).read_text(encoding="utf-8")) or {}
    manifest_paths = [resolve(path) for path in config["input_manifests"]]
    manifests = [load_artifact_manifest(path) for path in manifest_paths]
    issues = [issue for manifest, path in zip(manifests, manifest_paths) for issue in validate_manifest_outputs(manifest, path.parent)]
    if issues or any(manifest["artifact_status"] != "pass" for manifest in manifests):
        raise ValueError("score policy upstream is stale or blocked")
    source_paths = [
        resolve(config["factor_weights"]), resolve(config["weight_manifest"]),
        resolve(config["factor_partition_status"]), resolve(config["allowed_dates"]),
        resolve(config["outer_date_assignments"]),
    ]
    source_manifest_indexes = [0, 0, 1, 2, 3]
    for path, index in zip(source_paths, source_manifest_indexes):
        expected = manifests[index]["output_file_hashes"].get(path.name)
        if not expected or file_sha256(path) != expected:
            raise ValueError(f"score policy source is not manifest-bound: {path}")
    canary_manifest_path = config.get("canary_manifest")
    canary_gate = "not_required"
    if canary_manifest_path:
        canary_path = resolve(canary_manifest_path)
        canary = load_artifact_manifest(canary_path)
        if validate_manifest_outputs(canary, canary_path.parent) or canary["artifact_status"] != "pass":
            raise ValueError("score policy canary is stale or blocked")
        if not pd.read_csv(resolve(config["canary_contract"]))["status"].eq("pass").all():
            raise ValueError("score policy canary contract is incomplete")
        canary_gate = "pass"
    weights = pd.read_csv(source_paths[0])
    weight_manifest = pd.read_csv(source_paths[1])
    partitions = pd.read_csv(source_paths[2])
    allowed = pd.read_csv(source_paths[3], parse_dates=["datetime"])
    outer = pd.read_csv(source_paths[4], parse_dates=["datetime"])
    selected = [str(value) for value in config.get("selected_outer_splits", [])]
    if selected:
        weights = weights.loc[weights["outer_split_id"].astype(str).isin(selected)].copy()
        weight_manifest = weight_manifest.loc[weight_manifest["outer_split_id"].astype(str).isin(selected)].copy()
        allowed = allowed.loc[allowed["outer_split_id"].astype(str).isin(selected)].copy()
        outer = outer.loc[outer["split_id"].astype(str).isin(selected)].copy()
    split_factors = {
        split_id: sorted(group["factor_column"].astype(str).unique())
        for split_id, group in weights.groupby("outer_split_id", sort=True)
    }
    max_dates = config.get("maximum_development_dates")
    split_dates = {
        split_id: sampled_dates(
            pd.DatetimeIndex(allowed.loc[allowed["outer_split_id"].astype(str).eq(split_id), "datetime"]),
            None if max_dates is None else int(max_dates),
        )
        for split_id in split_factors
    }
    union_dates = pd.DatetimeIndex(sorted(set().union(*(set(values) for values in split_dates.values()))))
    union_factors = set().union(*(set(values) for values in split_factors.values()))
    base: pd.DataFrame | None = None
    counts: dict[str, np.ndarray] = {}
    missing_rows: list[dict[str, object]] = []
    remaining = set(union_factors)
    for batch in partitions.itertuples(index=False):
        path = resolve(str(batch.output_path))
        if file_sha256(path) != str(batch.output_sha256):
            raise ValueError(f"Matrix v4 partition hash mismatch: {batch.batch_id}")
        columns = set(pq.ParquetFile(path).schema.names)
        selected_columns = sorted(remaining & columns)
        if not selected_columns:
            continue
        part = pd.read_parquet(path, columns=["datetime", "instrument", *selected_columns])
        part["datetime"] = pd.to_datetime(part["datetime"])
        part = part.loc[part["datetime"].isin(union_dates)].sort_values(["datetime", "instrument"], kind="stable").reset_index(drop=True)
        max_instruments = config.get("maximum_instruments")
        if max_instruments is not None:
            instruments = sorted(part["instrument"].astype(str).unique())[: int(max_instruments)]
            part = part.loc[part["instrument"].astype(str).isin(instruments)].reset_index(drop=True)
        if base is None:
            base = part[["datetime", "instrument"]].copy()
            counts = {split_id: np.zeros(len(base), dtype=np.int16) for split_id in split_factors}
        elif not base.equals(part[["datetime", "instrument"]]):
            raise ValueError(f"score policy Matrix v4 key mismatch: {batch.batch_id}")
        for split_id, factors in split_factors.items():
            current = sorted(set(factors) & set(selected_columns))
            if not current:
                continue
            date_mask = base["datetime"].isin(split_dates[split_id]).to_numpy()
            counts[split_id][date_mask] += part.loc[date_mask, current].notna().sum(axis=1).to_numpy(dtype=np.int16)
            for factor in current:
                missing_rows.append({
                    "outer_split_id": split_id, "factor": factor,
                    "development_missing_count": int(part.loc[date_mask, factor].isna().sum()),
                    "development_row_count": int(date_mask.sum()),
                })
        remaining.difference_update(selected_columns)
    if base is None or remaining:
        raise ValueError(f"score policy factors missing from Matrix v4: {sorted(remaining)}")
    minimum_count = int(config["policy"]["minimum_component_count"])
    minimum_fraction = float(config["policy"]["minimum_component_fraction"])
    audit_rows, summary_rows, daily_rows = [], [], []
    for split_id, factors in split_factors.items():
        mask = base["datetime"].isin(split_dates[split_id]).to_numpy()
        scoped = base.loc[mask].copy()
        scoped["outer_split_id"] = split_id
        scoped["expected_component_count"] = len(factors)
        scoped["available_component_count"] = counts[split_id][mask]
        scoped["component_fraction"] = scoped["available_component_count"] / len(factors)
        scoped["score_row_present"] = scoped["available_component_count"].gt(0)
        scoped["component_complete"] = (
            scoped["available_component_count"].ge(minimum_count)
            & scoped["component_fraction"].ge(minimum_fraction)
        )
        scoped["renormalization_applied"] = scoped["component_complete"] & scoped["available_component_count"].lt(len(factors))
        audit_rows.append(scoped)
        for method in sorted(weight_manifest.loc[weight_manifest["outer_split_id"].astype(str).eq(split_id), "method"].astype(str)):
            summary_rows.append({
                "outer_split_id": split_id, "method": method, "expected_component_count": len(factors),
                "rows": len(scoped), "score_row_presence_coverage": float(scoped["score_row_present"].mean()),
                "component_completeness_coverage": float(scoped["component_complete"].mean()),
                "minimum_available_components": int(scoped["available_component_count"].min()),
                "median_component_fraction": float(scoped["component_fraction"].median()),
                "renormalization_rate": float(scoped["renormalization_applied"].mean()),
            })
        daily = scoped.groupby("datetime", as_index=False).agg(
            rows=("instrument", "size"), score_row_presence_coverage=("score_row_present", "mean"),
            component_completeness_coverage=("component_complete", "mean"),
            minimum_available_components=("available_component_count", "min"),
            median_component_fraction=("component_fraction", "median"),
        )
        daily.insert(0, "outer_split_id", split_id)
        daily_rows.append(daily)
    audit = pd.concat(audit_rows, ignore_index=True)
    summary = pd.DataFrame(summary_rows)
    daily_summary = pd.concat(daily_rows, ignore_index=True)
    runtime_path = resolve(config["runtime_audit"])
    atomic_parquet(audit, runtime_path)
    test_count = 0
    for split_id, group in audit.groupby("outer_split_id", sort=True):
        test_dates = set(
            outer.loc[
                outer["split_id"].astype(str).eq(str(split_id)) & outer["fold"].eq("test"),
                "datetime",
            ]
        )
        test_count += int(group["datetime"].isin(test_dates).sum())
    policy = {
        "schema_version": 1, "status": "frozen", "selection_data_scope": "outer_train_validation_only",
        "outer_test_used": False, "minimum_component_count": minimum_count,
        "minimum_component_fraction": minimum_fraction,
        "below_threshold_action": str(config["policy"]["below_threshold_action"]),
        "above_threshold_missing_action": str(config["policy"]["above_threshold_missing_action"]),
        "method_scope": sorted(config["methods"]), "same_policy_for_all_methods": True,
        "policy_sha256": canonical_hash(config["policy"]),
    }
    contracts = pd.DataFrame([
        contract_row("canary_gate_passed", canary_gate in {"not_required", "pass"}, canary_gate, "pass_or_not_required"),
        contract_row("outer_test_row_count", test_count == 0, test_count, 0),
        contract_row("split_count", summary["outer_split_id"].nunique() == int(config["expected_outer_splits"]), summary["outer_split_id"].nunique(), config["expected_outer_splits"]),
        contract_row("method_count_per_split", summary.groupby("outer_split_id")["method"].nunique().eq(len(config["methods"])).all(), summary.groupby("outer_split_id")["method"].nunique().tolist(), len(config["methods"])),
        contract_row("policy_frozen", policy["status"] == "frozen", policy["status"], "frozen"),
        contract_row("same_policy_for_all_methods", policy["same_policy_for_all_methods"], True, True),
        contract_row("presence_and_completeness_distinct", (summary["score_row_presence_coverage"] >= summary["component_completeness_coverage"]).all(), True, True),
        contract_row("runtime_audit_hash_present", len(file_sha256(runtime_path)) == 64, len(file_sha256(runtime_path)), 64),
    ])
    inventory = pd.DataFrame([{"path": runtime_path.as_posix(), "rows": len(audit), "sha256": file_sha256(runtime_path)}])
    receipts = pd.DataFrame([
        {"input_name": path.name, "artifact_id": manifests[index]["artifact_id"], "path": path.as_posix(), "sha256": file_sha256(path)}
        for path, index in zip(source_paths, source_manifest_indexes)
    ])
    ready = contracts["status"].eq("pass").all()
    with StageOutputPublisher(resolve(config["output_dir"]), CONTROLLED) as publisher:
        publisher.path("transparent_score_policy.json").write_text(json.dumps(policy, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        summary.to_csv(publisher.path("component_completeness_summary.csv"), index=False, encoding="utf-8-sig")
        daily_summary.to_csv(publisher.path("daily_component_summary.csv"), index=False, encoding="utf-8-sig")
        pd.DataFrame(missing_rows).to_csv(publisher.path("missing_component_frequency.csv"), index=False, encoding="utf-8-sig")
        inventory.to_csv(publisher.path("component_audit_inventory.csv"), index=False, encoding="utf-8-sig")
        receipts.to_csv(publisher.path("input_receipts.csv"), index=False, encoding="utf-8-sig")
        contracts.to_csv(publisher.path("contract_status.csv"), index=False, encoding="utf-8-sig")
        publisher.path("resolved_config.json").write_text(json.dumps(config, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        publisher.path("score_policy_report.md").write_text(
            "# Development-Only Transparent Score Policy\n\n"
            f"- Status: `{'pass' if ready else 'blocked'}`\n"
            f"- Policy: at least `{minimum_count}` components and fraction `{minimum_fraction:.2f}`.\n"
            "- Below threshold: reject score; otherwise missing components may be renormalized and flagged.\n"
            "- Outer-test rows used: `0`; no return, execution, or NAV is read.\n",
            encoding="utf-8",
        )
        files = [publisher.path(name) for name in CONTROLLED if name != "artifact_manifest.json"]
        write_stage_artifact_manifest(
            project_root=PROJECT_ROOT, stage_id="transparent_score_policy_v1", config=config,
            output_dir=publisher.staging_dir, output_files=files, code_state=capture_code_state(PROJECT_ROOT),
            input_manifest_paths=manifest_paths, factor_frame_id=manifests[1]["factor_frame_id"],
            split_manifest_id=manifests[2]["split_manifest_id"], start_date=audit["datetime"].min(),
            end_date=audit["datetime"].max(), lineage_status="complete",
            artifact_status="pass" if ready else "blocked", blocked_reason="" if ready else "blocked_score_policy",
        )
        publisher.publish()
    print(contracts.to_string(index=False))
    print(summary.to_string(index=False))
    return 0 if ready else 2


if __name__ == "__main__":
    raise SystemExit(main())
