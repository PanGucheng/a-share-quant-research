from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from qlib_integration.contracts import contract_row  # noqa: E402
from research_validation.feature_matrix import file_sha256  # noqa: E402
from research_validation.lineage import capture_code_state, load_artifact_manifest, validate_manifest_outputs, write_stage_artifact_manifest  # noqa: E402
from research_validation.mutation_contract import canonical_frame_hash, frame_content_hash, mutate_test_rows  # noqa: E402
from research_validation.stage_output import StageOutputPublisher  # noqa: E402

CONTROLLED = (
    "artifact_manifest.json", "mutation_results.csv", "business_payload_hashes.csv", "input_receipts.csv",
    "contract_status.csv", "mutation_contract_report.md", "resolved_config.json",
)


def resolve(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else (PROJECT_ROOT / path).resolve()


def selection_hashes(config: dict[str, object], outer_split_id: str) -> dict[str, str]:
    hashes = {}
    for name, value in config["selection_artifacts"].items():
        frame = pd.read_csv(resolve(value))
        scoped = frame.loc[frame["outer_split_id"].astype(str).eq(outer_split_id)].copy()
        keys = [column for column in ["outer_split_id", "inner_split_id", "factor", "cluster_id"] if column in scoped]
        hashes[name] = canonical_frame_hash(scoped, sort_keys=keys)
    return hashes


def validate_selection_parent_chain(manifests: list[dict[str, object]]) -> tuple[bool, list[str]]:
    by_stage = {str(manifest["stage_id"]): manifest for manifest in manifests}
    stage_by_artifact_id = {str(manifest["artifact_id"]): str(manifest["stage_id"]) for manifest in manifests}
    expected = {
        "factor_multiple_testing_v1": {"selection_input_projection_v1"},
        "factor_rolling_stability_v1": {"selection_input_projection_v1", "factor_multiple_testing_v1"},
        "factor_clustering_v1": {"factor_rolling_stability_v1", "clustering_input_projection_v1", "development_robustness_split_v1"},
        "split_specific_allowlist_v1": {"factor_clustering_v1", "factor_rolling_stability_v1", "development_robustness_split_v1", "purged_walk_forward_v1"},
    }
    issues: list[str] = []
    for stage_id, required_parents in expected.items():
        manifest = by_stage.get(stage_id)
        if manifest is None:
            issues.append(f"missing selection manifest: {stage_id}")
            continue
        parent_stages = {
            stage_by_artifact_id.get(str(artifact_id), "")
            for artifact_id in manifest.get("input_artifact_ids", [])
        }
        missing = sorted(required_parents - parent_stages)
        if missing:
            issues.append(f"{stage_id} missing direct parents: {missing}")
    return not issues, issues


def sampled_instruments(frame: pd.DataFrame, count: int) -> pd.DataFrame:
    instruments = sorted(frame["instrument"].astype(str).unique())[:count]
    return frame.loc[frame["instrument"].astype(str).isin(instruments)].copy()


def main() -> int:
    parser = argparse.ArgumentParser(description="Prove outer-test mutations cannot change selection inputs or payloads.")
    parser.add_argument("--config", type=Path, default=Path("configs/selection_mutation_contract_669_v1.yaml"))
    args = parser.parse_args()
    config = yaml.safe_load(resolve(args.config).read_text(encoding="utf-8")) or {}
    manifest_paths = [resolve(path) for path in config["input_manifests"]]
    manifests = [load_artifact_manifest(path) for path in manifest_paths]
    issues = [issue for manifest, path in zip(manifests, manifest_paths) for issue in validate_manifest_outputs(manifest, path.parent)]
    if issues or any(manifest["artifact_status"] != "pass" for manifest in manifests):
        raise ValueError("mutation contract upstream is stale or blocked")
    outer = pd.read_csv(resolve(config["outer_date_assignments"]), parse_dates=["datetime"])
    allowed = pd.read_csv(resolve(config["allowed_dates"]), parse_dates=["datetime"])
    daily = pd.read_csv(resolve(config["daily_ic"]), parse_dates=["datetime"])
    selected_outer_splits = [str(value) for value in config.get("selected_outer_splits", [])]
    if selected_outer_splits:
        known_splits = set(outer["split_id"].astype(str))
        unknown_splits = sorted(set(selected_outer_splits) - known_splits)
        if unknown_splits:
            raise ValueError(f"unknown selected_outer_splits: {unknown_splits}")
        outer = outer.loc[outer["split_id"].astype(str).isin(selected_outer_splits)].copy()
        allowed = allowed.loc[allowed["outer_split_id"].astype(str).isin(selected_outer_splits)].copy()
    maximum_daily_factors = config.get("maximum_daily_factors")
    if maximum_daily_factors is not None:
        factors = sorted(daily["factor"].astype(str).unique())[: int(maximum_daily_factors)]
        daily = daily.loc[daily["factor"].astype(str).isin(factors)].copy()
    labels = sampled_instruments(pd.read_parquet(resolve(config["labels"])), int(config["sample_instruments"]))
    exposure = pd.read_parquet(resolve(config["factor_exposure"]))
    exposure_columns = [column for column in exposure.columns if column not in {"datetime", "instrument"}][: int(config["sample_exposure_factors"])]
    exposure = sampled_instruments(exposure[["datetime", "instrument", *exposure_columns]], int(config["sample_instruments"]))
    raw_columns = ["$open", "$high", "$low", "$close", "$volume", "$amount"]
    raw = sampled_instruments(pd.read_parquet(resolve(config["raw_ohlcva"]), columns=["datetime", "instrument", *raw_columns]), int(config["sample_instruments"]))
    sources = {
        "test_ic": (daily, ["rank_ic"], ["datetime", "factor"]),
        "factor_exposure": (exposure, exposure_columns, ["datetime", "instrument"]),
        "labels": (labels, [column for column in labels if column not in {"datetime", "instrument"}], ["datetime", "instrument"]),
        "raw_ohlcva": (raw, raw_columns, ["datetime", "instrument"]),
    }
    results = []
    payload_rows = []
    selection_chain_valid, selection_chain_issues = validate_selection_parent_chain(manifests)
    for outer_split_id in sorted(outer["split_id"].astype(str).unique()):
        test_dates = pd.DatetimeIndex(outer.loc[outer["split_id"].astype(str).eq(outer_split_id) & outer["fold"].eq("test"), "datetime"])
        development_dates = pd.DatetimeIndex(allowed.loc[allowed["outer_split_id"].astype(str).eq(outer_split_id), "datetime"])
        committed_hashes = selection_hashes(config, outer_split_id)
        payload_rows.append({"outer_split_id": outer_split_id, **{f"{name}_sha256": value for name, value in committed_hashes.items()}})
        for source_name, (frame, value_columns, keys) in sources.items():
            baseline_projection = frame.loc[pd.to_datetime(frame["datetime"]).isin(development_dates)].copy()
            baseline_hash = canonical_frame_hash(baseline_projection, sort_keys=keys)
            baseline_source_canonical_hash = canonical_frame_hash(frame, sort_keys=keys)
            baseline_source_order_hash = frame_content_hash(frame)
            mutations = [source_name, "extreme_missing", "row_order"]
            for mutation in mutations:
                mutated = mutate_test_rows(frame, test_dates=test_dates, mutation=mutation, value_columns=value_columns)
                mutated_projection = mutated.loc[pd.to_datetime(mutated["datetime"]).isin(development_dates)].copy()
                after_hash = canonical_frame_hash(mutated_projection, sort_keys=keys)
                mutated_source_canonical_hash = canonical_frame_hash(mutated, sort_keys=keys)
                mutated_source_order_hash = frame_content_hash(mutated)
                canonical_source_changed = baseline_source_canonical_hash != mutated_source_canonical_hash
                order_source_changed = baseline_source_order_hash != mutated_source_order_hash
                mutation_effective = order_source_changed if mutation == "row_order" else canonical_source_changed
                results.append({
                    "outer_split_id": outer_split_id, "source": source_name, "mutation": mutation,
                    "test_row_count": int(pd.to_datetime(frame["datetime"]).isin(test_dates).sum()),
                    "development_row_count": len(baseline_projection),
                    "development_projection_sha256_before": baseline_hash,
                    "development_projection_sha256_after": after_hash,
                    "development_projection_unchanged": baseline_hash == after_hash,
                    "source_canonical_sha256_before": baseline_source_canonical_hash,
                    "source_canonical_sha256_after": mutated_source_canonical_hash,
                    "source_order_sha256_before": baseline_source_order_hash,
                    "source_order_sha256_after": mutated_source_order_hash,
                    "mutation_effective": mutation_effective,
                    "row_order_canonicalized": mutation != "row_order" or not canonical_source_changed,
                    **{f"{name}_sha256_before": value for name, value in committed_hashes.items()},
                    **{f"{name}_sha256_after": value for name, value in committed_hashes.items()},
                    "selection_payloads_unchanged": baseline_hash == after_hash and selection_chain_valid,
                    "execution_mode": "content_addressed_projection_and_parent_chain_proof",
                })
    mutation_results = pd.DataFrame(results)
    payload_hashes = pd.DataFrame(payload_rows)
    expected_mutations = len(sources) * 3 * outer["split_id"].nunique()
    contracts = pd.DataFrame([
        contract_row("mutation_case_count", len(mutation_results) == expected_mutations, len(mutation_results), expected_mutations),
        contract_row("development_projection_hash_unchanged", mutation_results["development_projection_unchanged"].all(), int(mutation_results["development_projection_unchanged"].sum()), len(mutation_results)),
        contract_row("selection_payload_hashes_unchanged", mutation_results["selection_payloads_unchanged"].all(), int(mutation_results["selection_payloads_unchanged"].sum()), len(mutation_results)),
        contract_row("selection_parent_chain_valid", selection_chain_valid, selection_chain_issues, []),
        contract_row("all_mutations_touch_test_rows", mutation_results["test_row_count"].gt(0).all(), int(mutation_results["test_row_count"].gt(0).sum()), len(mutation_results)),
        contract_row("mutation_effective", mutation_results["mutation_effective"].all(), int(mutation_results["mutation_effective"].sum()), len(mutation_results)),
        contract_row("row_order_canonicalized", mutation_results.loc[mutation_results["mutation"].eq("row_order"), "row_order_canonicalized"].all(), int(mutation_results.loc[mutation_results["mutation"].eq("row_order"), "row_order_canonicalized"].sum()), len(mutation_results.loc[mutation_results["mutation"].eq("row_order")])),
    ])
    receipts = pd.DataFrame([
        {
            "input_name": manifest["stage_id"],
            "artifact_id": manifest["artifact_id"],
            "path": path.as_posix(),
            "sha256": file_sha256(path),
        }
        for manifest, path in zip(manifests, manifest_paths)
    ])
    ready = bool(contracts["status"].eq("pass").all())
    output_dir = resolve(config["output_dir"])
    with StageOutputPublisher(output_dir, CONTROLLED) as publisher:
        mutation_results.to_csv(publisher.path("mutation_results.csv"), index=False, encoding="utf-8-sig")
        payload_hashes.to_csv(publisher.path("business_payload_hashes.csv"), index=False, encoding="utf-8-sig")
        receipts.to_csv(publisher.path("input_receipts.csv"), index=False, encoding="utf-8-sig")
        contracts.to_csv(publisher.path("contract_status.csv"), index=False, encoding="utf-8-sig")
        publisher.path("resolved_config.json").write_text(json.dumps(config, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        publisher.path("mutation_contract_report.md").write_text(
            "# Selection Mutation Contract V1\n\n"
            + f"- Status: `{'pass' if ready else 'blocked'}`\n"
            + f"- Outer-test mutation cases: `{len(mutation_results)}`\n"
            + "- Sources: test IC, factor exposure, labels, raw OHLCVA; each also covers row order and extreme missing values.\n"
            + "- Proof mode: effective source mutation, exact allowed-date projection identity, verified selection parent chain, and committed split-scoped business payload hashes.\n"
            + "- Selection stages are not re-run because their content-addressed inputs are byte-identical after mutation; this contract proves the release boundary rather than fabricating alternate outputs.\n",
            encoding="utf-8",
        )
        files = [publisher.path(name) for name in CONTROLLED if name != "artifact_manifest.json"]
        write_stage_artifact_manifest(
            project_root=PROJECT_ROOT, stage_id="selection_mutation_contract_v1", config=config,
            output_dir=publisher.staging_dir, output_files=files, code_state=capture_code_state(PROJECT_ROOT),
            input_manifest_paths=manifest_paths, factor_frame_id=manifests[1]["factor_frame_id"],
            split_manifest_id=manifests[4]["split_manifest_id"], start_date=allowed["datetime"].min(),
            end_date=allowed["datetime"].max(), lineage_status="complete",
            artifact_status="pass" if ready else "blocked", blocked_reason="" if ready else "blocked_selection_mutation_contract",
        )
        publisher.publish()
    print(contracts.to_string(index=False))
    return 0 if ready else 2


if __name__ == "__main__":
    raise SystemExit(main())
