from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import pandas as pd
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from portfolio.score_construction import construct_daily_scores  # noqa: E402
from qlib_integration.contracts import contract_row  # noqa: E402
from research_validation.feature_matrix import canonical_hash, file_sha256  # noqa: E402
from research_validation.lineage import capture_code_state, load_artifact_manifest, validate_manifest_outputs, write_stage_artifact_manifest  # noqa: E402
from research_validation.stage_output import StageOutputPublisher  # noqa: E402
from scripts.run_split_transparent_score_v1 import load_test_factor_frame, selected_partition_inventory  # noqa: E402

CONTROLLED = (
    "artifact_manifest.json", "score_artifact.csv", "score_sample.csv", "score_diagnostics.csv",
    "daily_factor_component_count.csv", "factor_partition_inventory.csv", "input_receipts.csv",
    "contract_status.csv", "score_report.md", "resolved_config.json",
)


def resolve(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else (PROJECT_ROOT / path).resolve()


def main() -> int:
    parser = argparse.ArgumentParser(description="Materialize corrected transparent scores without reading outcomes.")
    parser.add_argument("--config", type=Path, default=Path("configs/split_transparent_score_corrected_v2.yaml"))
    args = parser.parse_args()
    config = yaml.safe_load(resolve(args.config).read_text(encoding="utf-8")) or {}
    manifest_paths = [resolve(path) for path in config["input_manifests"]]
    manifests = [load_artifact_manifest(path) for path in manifest_paths]
    issues = [issue for manifest, path in zip(manifests, manifest_paths) for issue in validate_manifest_outputs(manifest, path.parent)]
    if issues or any(manifest["artifact_status"] != "pass" for manifest in manifests):
        raise ValueError("corrected score upstream is stale or blocked")
    by_stage = {manifest["stage_id"]: manifest for manifest in manifests}
    weights_manifest = by_stage["split_transparent_weights_v2"]
    matrix_manifest = by_stage["full_research_feature_matrix_v4"]
    split_manifest = by_stage["purged_walk_forward_v1"]
    policy_manifest = by_stage["transparent_score_policy_v1"]
    mutation_manifest = by_stage["selection_mutation_contract_v2"]
    source_paths = {
        "weights": resolve(config["factor_weights"]),
        "weight_manifest": resolve(config["weight_manifest"]),
        "partitions": resolve(config["factor_partition_status"]),
        "assignments": resolve(config["outer_date_assignments"]),
        "policy": resolve(config["score_policy"]),
        "mutation_contract": resolve(config["mutation_contract"]),
    }
    source_manifests = {
        "weights": weights_manifest, "weight_manifest": weights_manifest,
        "partitions": matrix_manifest, "assignments": split_manifest,
        "policy": policy_manifest, "mutation_contract": mutation_manifest,
    }
    for name, path in source_paths.items():
        expected = source_manifests[name]["output_file_hashes"].get(path.name)
        if not expected or file_sha256(path) != expected:
            raise ValueError(f"corrected score source is not manifest-bound: {name}")
    canary_manifest_path = config.get("canary_manifest")
    canary_gate = "not_required"
    if canary_manifest_path:
        canary_path = resolve(canary_manifest_path)
        canary = load_artifact_manifest(canary_path)
        if validate_manifest_outputs(canary, canary_path.parent) or canary["artifact_status"] != "pass":
            raise ValueError("corrected score canary is stale or blocked")
        if not pd.read_csv(resolve(config["canary_contract"]))["status"].eq("pass").all():
            raise ValueError("corrected score canary contract is incomplete")
        canary_gate = "pass"
    policy = json.loads(source_paths["policy"].read_text(encoding="utf-8"))
    if (
        policy["status"] != "frozen"
        or policy["outer_test_used"] is not False
        or policy["below_threshold_action"] != "reject_score"
        or not policy["same_policy_for_all_methods"]
    ):
        raise ValueError("transparent score policy is not frozen with fail-closed semantics")
    mutation_contract = pd.read_csv(source_paths["mutation_contract"])
    if not mutation_contract["status"].eq("pass").all():
        raise ValueError("selection mutation contract is incomplete")
    weights = pd.read_csv(source_paths["weights"])
    weight_index = pd.read_csv(source_paths["weight_manifest"])
    partitions = pd.read_csv(source_paths["partitions"])
    assignments = pd.read_csv(source_paths["assignments"], parse_dates=["datetime"])
    selected = [str(value) for value in config.get("selected_outer_splits", [])]
    if selected:
        weights = weights.loc[weights["outer_split_id"].astype(str).isin(selected)].copy()
        weight_index = weight_index.loc[weight_index["outer_split_id"].astype(str).isin(selected)].copy()
        assignments = assignments.loc[assignments["split_id"].astype(str).isin(selected)].copy()
    score_rows, diagnostic_rows, audit_rows = [], [], []
    hash_cache: dict[str, str] = {}
    for split_id in sorted(weights["outer_split_id"].astype(str).unique()):
        split_weights = weights.loc[weights["outer_split_id"].astype(str).eq(split_id)].copy()
        factors = split_weights.sort_values("feature_order")["factor_column"].drop_duplicates().tolist()
        inventory, _ = selected_partition_inventory(partitions, set(factors))
        test_dates = pd.DatetimeIndex(
            assignments.loc[
                assignments["split_id"].astype(str).eq(split_id) & assignments["fold"].eq("test"),
                "datetime",
            ]
        ).sort_values().unique()
        maximum_dates = config.get("maximum_test_dates")
        if maximum_dates is not None:
            test_dates = test_dates[: int(maximum_dates)]
        frame, audited = load_test_factor_frame(inventory, factors, test_dates, hash_cache)
        maximum_instruments = config.get("maximum_instruments")
        if maximum_instruments is not None:
            instruments = sorted(frame["instrument"].astype(str).unique())[: int(maximum_instruments)]
            frame = frame.loc[frame["instrument"].astype(str).isin(instruments)].reset_index(drop=True)
        audited.insert(0, "outer_split_id", split_id)
        audit_rows.append(audited)
        expected_components = len(factors)
        threshold = max(
            int(policy["minimum_component_count"]),
            math.ceil(expected_components * float(policy["minimum_component_fraction"])),
        )
        for method in sorted(split_weights["method"].astype(str).unique()):
            method_weights = split_weights.loc[split_weights["method"].eq(method)].sort_values("feature_order")
            scores, diagnostics = construct_daily_scores(
                frame, method_weights, method=method, min_components=threshold, clip=float(config["clip"]),
            )
            scores["outer_split_id"] = split_id
            scores["expected_component_count"] = expected_components
            scores["component_fraction"] = scores["component_count"] / expected_components
            scores["component_policy_pass"] = scores["component_count"].ge(threshold)
            scores["renormalization_applied"] = scores["component_policy_pass"] & scores["component_count"].lt(expected_components)
            score_rows.append(scores)
            diagnostics["outer_split_id"] = split_id
            diagnostics["expected_component_count"] = expected_components
            diagnostics["required_component_count"] = threshold
            diagnostic_rows.append(diagnostics)
    scores = pd.concat(score_rows, ignore_index=True)
    diagnostics = pd.concat(diagnostic_rows, ignore_index=True)
    audits = pd.concat(audit_rows, ignore_index=True)
    output_dir = resolve(config["output_dir"])
    expected_splits = int(config["expected_outer_splits"])
    expected_methods = len(config["methods"])
    date_counts = scores.groupby("outer_split_id")["datetime"].nunique()
    expected_dates = (
        assignments.loc[assignments["fold"].eq("test")]
        .groupby("split_id")["datetime"].nunique()
        .reindex(date_counts.index)
    )
    if config.get("maximum_test_dates") is not None:
        expected_dates[:] = int(config["maximum_test_dates"])
    contracts = pd.DataFrame([
        contract_row("canary_gate_passed", canary_gate in {"not_required", "pass"}, canary_gate, "pass_or_not_required"),
        contract_row("outer_split_count", scores["outer_split_id"].nunique() == expected_splits, scores["outer_split_id"].nunique(), expected_splits),
        contract_row("method_count_per_split", scores.groupby("outer_split_id")["method"].nunique().eq(expected_methods).all(), scores.groupby("outer_split_id")["method"].nunique().tolist(), expected_methods),
        contract_row("score_test_dates_complete", date_counts.eq(expected_dates).all(), date_counts.tolist(), expected_dates.tolist()),
        contract_row("factor_partition_hashes_valid", audits["runtime_hash_match"].all(), int(audits["runtime_hash_match"].sum()), len(audits)),
        contract_row("score_policy_hash_valid", file_sha256(source_paths["policy"]) == policy_manifest["output_file_hashes"][source_paths["policy"].name], file_sha256(source_paths["policy"]), policy_manifest["output_file_hashes"][source_paths["policy"].name]),
        contract_row("mutation_contract_pass", mutation_contract["status"].eq("pass").all(), int(mutation_contract["status"].eq("pass").sum()), len(mutation_contract)),
        contract_row("component_policy_applied", scores.loc[~scores["component_policy_pass"], "composite_score"].isna().all(), int(scores.loc[~scores["component_policy_pass"], "composite_score"].notna().sum()), 0),
        contract_row("score_has_no_outcome_fields", not any(token in column.lower() for column in scores for token in ("label", "return", "nav", "sharpe", "drawdown", "ic")), list(scores.columns), "prediction-only"),
        contract_row("score_non_null", scores["composite_score"].notna().any(), int(scores["composite_score"].notna().sum()), ">0"),
    ])
    ready = contracts["status"].eq("pass").all()
    with StageOutputPublisher(output_dir, CONTROLLED) as publisher:
        runtime = publisher.path("runtime/composite_scores.parquet")
        runtime.parent.mkdir(parents=True, exist_ok=True)
        scores.to_parquet(runtime, index=False)
        runtime_hash = file_sha256(runtime)
        pd.DataFrame([{"path": (output_dir / "runtime/composite_scores.parquet").as_posix(), "rows": len(scores), "sha256": runtime_hash}]).to_csv(publisher.path("score_artifact.csv"), index=False, encoding="utf-8-sig")
        scores.sort_values(["outer_split_id", "method", "datetime", "instrument"]).groupby(["outer_split_id", "method"]).head(3).to_csv(publisher.path("score_sample.csv"), index=False, encoding="utf-8-sig")
        scores.groupby(["outer_split_id", "method"]).agg(
            rows=("composite_score", "size"), score_row_presence_coverage=("composite_score", lambda x: x.notna().mean()),
            component_completeness_coverage=("component_policy_pass", "mean"), minimum_components=("component_count", "min"),
            median_component_fraction=("component_fraction", "median"), renormalization_rate=("renormalization_applied", "mean"),
        ).reset_index().to_csv(publisher.path("score_diagnostics.csv"), index=False, encoding="utf-8-sig")
        diagnostics.to_csv(publisher.path("daily_factor_component_count.csv"), index=False, encoding="utf-8-sig")
        audits.to_csv(publisher.path("factor_partition_inventory.csv"), index=False, encoding="utf-8-sig")
        pd.DataFrame([
            {"input_name": name, "artifact_id": source_manifests[name]["artifact_id"], "path": path.as_posix(), "sha256": file_sha256(path)}
            for name, path in source_paths.items()
        ]).to_csv(publisher.path("input_receipts.csv"), index=False, encoding="utf-8-sig")
        contracts.to_csv(publisher.path("contract_status.csv"), index=False, encoding="utf-8-sig")
        publisher.path("resolved_config.json").write_text(json.dumps(config, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        publisher.path("score_report.md").write_text(
            "# Corrected Transparent Score V2\n\n"
            f"- Status: `{'pass' if ready else 'blocked'}`\n"
            f"- Splits / methods / rows: `{scores['outer_split_id'].nunique()}` / `{expected_methods}` / `{len(scores)}`\n"
            "- Deterministically consumes PR6 weights and score policy; no labels, returns, execution, or NAV are read.\n",
            encoding="utf-8",
        )
        files = [publisher.path(name) for name in CONTROLLED if name != "artifact_manifest.json"]
        write_stage_artifact_manifest(
            project_root=PROJECT_ROOT, stage_id="split_transparent_score_v2", config=config,
            output_dir=publisher.staging_dir, output_files=files, code_state=capture_code_state(PROJECT_ROOT),
            input_manifest_paths=manifest_paths, factor_frame_id=matrix_manifest["factor_frame_id"],
            split_manifest_id=split_manifest["split_manifest_id"], start_date=scores["datetime"].min(),
            end_date=scores["datetime"].max(), lineage_status="complete",
            artifact_status="pass" if ready else "blocked", blocked_reason="" if ready else "blocked_corrected_score",
        )
        publisher.publish()
    print(contracts.to_string(index=False))
    return 0 if ready else 2


if __name__ == "__main__":
    raise SystemExit(main())
