from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from portfolio.score_construction import construct_daily_scores  # noqa: E402
from qlib_integration.contracts import contract_row  # noqa: E402
from research_validation.feature_matrix import canonical_hash, file_sha256  # noqa: E402
from research_validation.lineage import capture_code_state, config_sha256, load_artifact_manifest, sha256_file, validate_manifest_outputs, write_stage_artifact_manifest  # noqa: E402
from research_validation.pretest_freeze import finalize_test_release, load_freeze_with_file_hash, reserve_test_release, validate_pretest_freeze  # noqa: E402
from research_validation.stage_output import StageOutputPublisher  # noqa: E402


BASE_OUTPUTS = (
    "artifact_manifest.json",
    "factor_partition_inventory.csv",
    "score_artifact.csv",
    "score_sample.csv",
    "score_diagnostics.csv",
    "daily_factor_component_count.csv",
    "test_release_index.csv",
    "input_receipts.csv",
    "contract_status.csv",
    "score_report.md",
    "resolved_config.json",
    "runtime/composite_scores.parquet",
)


def resolve(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else (PROJECT_ROOT / path).resolve()


def selected_partition_inventory(batch_manifest: pd.DataFrame, factor_columns: set[str]) -> tuple[pd.DataFrame, dict[str, str]]:
    rows: list[dict[str, object]] = []
    factor_to_batch: dict[str, str] = {}
    remaining = set(factor_columns)
    for batch in batch_manifest.itertuples(index=False):
        path = resolve(batch.output_path)
        schema_columns = set(pq.ParquetFile(path).schema.names)
        selected = sorted(remaining & schema_columns)
        if not selected:
            continue
        for factor in selected:
            factor_to_batch[factor] = str(batch.batch_id)
        rows.append(
            {
                "batch_id": batch.batch_id,
                "path": path.as_posix(),
                "declared_sha256": batch.output_sha256,
                "factor_count": len(selected),
                "factors": "|".join(selected),
                "runtime_sha256": "not_checked_preflight",
                "runtime_hash_match": False,
            }
        )
        remaining.difference_update(selected)
    if remaining:
        raise ValueError(f"score factors are missing from batch runtime: {sorted(remaining)}")
    return pd.DataFrame(rows), factor_to_batch


def load_test_factor_frame(
    inventory: pd.DataFrame,
    factors: list[str],
    test_dates: pd.DatetimeIndex,
    hash_cache: dict[str, str],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    frame: pd.DataFrame | None = None
    audited = inventory.copy()
    for index, row in audited.iterrows():
        path = Path(str(row["path"]))
        cache_key = path.as_posix()
        if cache_key not in hash_cache:
            hash_cache[cache_key] = file_sha256(path)
        actual_hash = hash_cache[cache_key]
        audited.loc[index, "runtime_sha256"] = actual_hash
        audited.loc[index, "runtime_hash_match"] = actual_hash == str(row["declared_sha256"])
        if actual_hash != str(row["declared_sha256"]):
            raise ValueError(f"factor partition hash mismatch: {row['batch_id']}")
        columns = [factor for factor in str(row["factors"]).split("|") if factor in factors]
        if not columns:
            continue
        part = pd.read_parquet(
            path,
            columns=["datetime", "instrument", *columns],
            filters=[("datetime", ">=", test_dates.min()), ("datetime", "<=", test_dates.max())],
        )
        part["datetime"] = pd.to_datetime(part["datetime"])
        part = part.loc[part["datetime"].isin(test_dates)].sort_values(["datetime", "instrument"], kind="stable").reset_index(drop=True)
        if frame is None:
            frame = part
        else:
            if not frame[["datetime", "instrument"]].equals(part[["datetime", "instrument"]]):
                raise ValueError(f"score factor key mismatch: {row['batch_id']}")
            frame = pd.concat([frame, part[columns]], axis=1)
    if frame is None:
        raise ValueError("no test factor frame was loaded")
    missing = set(factors) - set(frame.columns)
    if missing:
        raise ValueError(f"loaded score frame misses factors: {sorted(missing)}")
    return frame, audited


def main() -> int:
    parser = argparse.ArgumentParser(description="Construct frozen split-specific transparent outer-test scores.")
    parser.add_argument("--config", type=Path, default=Path("configs/split_transparent_score_669_v1.yaml"))
    args = parser.parse_args()
    config_path = resolve(args.config)
    config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    code_state = capture_code_state(PROJECT_ROOT)
    if code_state.dirty:
        raise ValueError("transparent score release requires a clean committed worktree")
    manifest_paths = [resolve(path) for path in config["input_manifests"]]
    manifests = [load_artifact_manifest(path) for path in manifest_paths]
    issues = [issue for manifest, path in zip(manifests, manifest_paths) for issue in validate_manifest_outputs(manifest, path.parent)]
    if issues or any(manifest["artifact_status"] != "pass" for manifest in manifests):
        raise ValueError(f"transparent score upstream is stale or blocked: {issues}")
    manifest_by_stage = {manifest["stage_id"]: manifest for manifest in manifests}
    freeze_artifact = manifest_by_stage["pre_test_freeze_v1"]
    matrix_artifact = manifest_by_stage["full_research_feature_matrix_v1"]
    split_artifact = manifest_by_stage["purged_walk_forward_v1"]
    weights = pd.read_csv(resolve(config["factor_weights"]))
    weight_manifest = pd.read_csv(resolve(config["weight_manifest"]))
    allowlist_manifest = pd.read_csv(resolve(config["allowlist_manifest"]))
    assignments = pd.read_csv(resolve(config["outer_date_assignments"]), parse_dates=["datetime"])
    batch_manifest = pd.read_csv(resolve(config["factor_batch_manifest"]))
    freeze_index = pd.read_csv(resolve(config["pre_test_freeze_index"]))
    selected_outer_splits = [str(value) for value in config.get("selected_outer_splits", [])]
    if selected_outer_splits:
        weights = weights.loc[weights["outer_split_id"].astype(str).isin(selected_outer_splits)].copy()
        weight_manifest = weight_manifest.loc[weight_manifest["outer_split_id"].astype(str).isin(selected_outer_splits)].copy()
        allowlist_manifest = allowlist_manifest.loc[allowlist_manifest["outer_split_id"].astype(str).isin(selected_outer_splits)].copy()
        freeze_index = freeze_index.loc[freeze_index["outer_split_id"].astype(str).isin(selected_outer_splits)].copy()
    split_ids = sorted(weight_manifest["outer_split_id"].astype(str).unique())
    factor_columns = set(weights["factor_column"].astype(str))
    partition_inventory, factor_to_batch = selected_partition_inventory(batch_manifest, factor_columns)
    preflight_only = bool(config.get("preflight_only", False))
    output_dir = resolve(config["output_dir"])
    release_outputs = tuple(f"test_release_receipts/{split_id}.json" for split_id in split_ids)
    controlled = BASE_OUTPUTS + release_outputs
    score_rows: list[pd.DataFrame] = []
    diagnostic_rows: list[pd.DataFrame] = []
    release_receipts: dict[str, dict[str, object]] = {}
    partition_audits: list[pd.DataFrame] = []
    freeze_issue_rows: list[dict[str, str]] = []
    partition_hash_cache: dict[str, str] = {}
    qlib_config_hash = file_sha256(resolve(config["qlib_exchange_config"]))
    preprocessing_hash = config_sha256(config["preprocessing"])
    score_config_hash = file_sha256(config_path)
    for split_id in split_ids:
        split_weights = weights.loc[weights["outer_split_id"].astype(str).eq(split_id)].copy()
        split_weight_manifest = weight_manifest.loc[weight_manifest["outer_split_id"].astype(str).eq(split_id)]
        split_allowlist = allowlist_manifest.loc[allowlist_manifest["outer_split_id"].astype(str).eq(split_id)]
        test_dates = pd.DatetimeIndex(
            assignments.loc[assignments["split_id"].astype(str).eq(split_id) & assignments["fold"].eq("test"), "datetime"]
        ).sort_values().unique()
        freeze_row = freeze_index.loc[freeze_index["outer_split_id"].astype(str).eq(split_id)]
        if len(freeze_row) != 1 or len(split_allowlist) != 1:
            raise ValueError(f"freeze or allowlist index mismatch: {split_id}")
        freeze_path = resolve(config["pre_test_freeze_dir"]) / str(freeze_row.iloc[0]["freeze_path"])
        freeze, freeze_sha = load_freeze_with_file_hash(freeze_path)
        if freeze_sha != str(freeze_row.iloc[0]["freeze_sha256"]):
            raise ValueError(f"freeze file hash mismatch: {split_id}")
        weights_by_method = dict(zip(split_weight_manifest["method"], split_weight_manifest["weights_sha256"]))
        freeze_issues = validate_pretest_freeze(
            freeze,
            expected_outer_split_id=split_id,
            expected_code_commit_sha=code_state.commit_sha,
            expected_allowlist_sha256=str(split_allowlist.iloc[0]["allowlist_sha256"]),
            expected_feature_order_sha256=str(split_allowlist.iloc[0]["feature_order_sha256"]),
            expected_weights_by_method=weights_by_method,
            expected_preprocessing_config_sha256=preprocessing_hash,
            expected_model_config_sha256=score_config_hash,
            expected_qlib_exchange_config_sha256=qlib_config_hash,
            expected_test_dates_sha256=canonical_hash([date.date().isoformat() for date in test_dates]),
        )
        freeze_issue_rows.extend({"outer_split_id": split_id, "issue": issue} for issue in freeze_issues)
        if freeze_issues:
            raise ValueError(f"invalid pre-test freeze for {split_id}: {freeze_issues}")
        split_factors = split_weights.sort_values("feature_order")["factor_column"].drop_duplicates().tolist()
        split_batches = sorted({factor_to_batch[factor] for factor in split_factors})
        release_core = {
            "schema_version": 1,
            "outer_split_id": split_id,
            "freeze_id": freeze["freeze_id"],
            "freeze_artifact_id": freeze_artifact["artifact_id"],
            "freeze_sha256": freeze_sha,
            "factor_matrix_artifact_id": matrix_artifact["artifact_id"],
            "split_artifact_id": split_artifact["artifact_id"],
            "test_dates_sha256": freeze["test_dates_sha256"],
            "test_feature_partition_ids": split_batches,
            "test_feature_partition_hashes": {
                row.batch_id: row.output_sha256
                for row in batch_manifest.loc[batch_manifest["batch_id"].astype(str).isin(split_batches)].itertuples(index=False)
            },
            "score_methods": sorted(split_weights["method"].unique()),
            "execution_commit_sha": code_state.commit_sha,
        }
        if preflight_only:
            continue
        reservation_path = output_dir / f"test_release_receipts/{split_id}.json"
        receipt = reserve_test_release(reservation_path, release_core)
        frame, audited = load_test_factor_frame(
            partition_inventory.loc[partition_inventory["batch_id"].astype(str).isin(split_batches)].copy(),
            split_factors,
            test_dates,
            partition_hash_cache,
        )
        audited.insert(0, "outer_split_id", split_id)
        partition_audits.append(audited)
        for method in sorted(split_weights["method"].unique()):
            method_weights = split_weights.loc[split_weights["method"].eq(method)].sort_values("feature_order").copy()
            scores, diagnostics = construct_daily_scores(
                frame,
                method_weights,
                method=method,
                min_components=int(config["preprocessing"]["minimum_components"]),
                clip=float(config["preprocessing"]["clip"]),
            )
            scores["outer_split_id"] = split_id
            diagnostics["outer_split_id"] = split_id
            score_rows.append(scores)
            diagnostic_rows.append(diagnostics)
        release_receipts[split_id] = receipt

    if preflight_only:
        contracts = pd.DataFrame(
            [
                contract_row("pre_test_freeze_valid", not freeze_issue_rows, len(freeze_issue_rows), 0),
                contract_row("factor_partition_schema_complete", len(factor_to_batch) == len(factor_columns), len(factor_to_batch), len(factor_columns)),
                contract_row("test_data_read_count", True, 0, 0),
                contract_row("test_release_count", True, 0, 0),
            ]
        )
        scores = pd.DataFrame(columns=["datetime", "instrument", "method", "composite_score", "component_count", "outer_split_id"])
        diagnostics = pd.DataFrame()
        audited_inventory = partition_inventory
    else:
        scores = pd.concat(score_rows, ignore_index=True)
        diagnostics = pd.concat(diagnostic_rows, ignore_index=True)
        audited_inventory = pd.concat(partition_audits, ignore_index=True)
        score_dates = scores.groupby("outer_split_id")["datetime"].nunique()
        expected_dates = assignments.loc[assignments["fold"].eq("test")].groupby("split_id")["datetime"].nunique().reindex(score_dates.index)
        contracts = pd.DataFrame(
            [
                contract_row("pre_test_freeze_valid", not freeze_issue_rows, len(freeze_issue_rows), 0),
                contract_row("test_release_count", len(release_receipts) == len(split_ids), len(release_receipts), len(split_ids)),
                contract_row("factor_partition_hashes_valid", audited_inventory["runtime_hash_match"].all(), int(audited_inventory["runtime_hash_match"].sum()), len(audited_inventory)),
                contract_row("score_test_dates_complete", score_dates.eq(expected_dates).all(), score_dates.tolist(), expected_dates.tolist()),
                contract_row("score_methods_complete", scores.groupby("outer_split_id")["method"].nunique().eq(len(config["methods"])).all(), scores.groupby("outer_split_id")["method"].nunique().tolist(), len(config["methods"])),
                contract_row("score_has_no_labels_or_test_metrics", not any("label" in column.lower() or "return" in column.lower() or "ic" in column.lower() for column in scores.columns), list(scores.columns), "prediction-only schema"),
                contract_row("score_non_null", scores["composite_score"].notna().any(), int(scores["composite_score"].notna().sum()), ">0"),
            ]
        )
    ready = bool(contracts["status"].eq("pass").all())
    with StageOutputPublisher(output_dir, controlled) as publisher:
        audited_inventory.to_csv(publisher.path("factor_partition_inventory.csv"), index=False, encoding="utf-8-sig")
        if not preflight_only:
            runtime = publisher.path("runtime/composite_scores.parquet")
            scores.to_parquet(runtime, index=False)
            runtime_hash = sha256_file(runtime)
            for split_id, receipt in release_receipts.items():
                finalized = finalize_test_release(receipt, score_artifact_sha256=runtime_hash)
                path = publisher.path(f"test_release_receipts/{split_id}.json")
                path.write_text(json.dumps(finalized, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            pd.DataFrame(
                [{"path": (output_dir / "runtime/composite_scores.parquet").as_posix(), "rows": len(scores), "sha256": runtime_hash}]
            ).to_csv(publisher.path("score_artifact.csv"), index=False, encoding="utf-8-sig")
        else:
            pd.DataFrame(columns=["path", "rows", "sha256"]).to_csv(publisher.path("score_artifact.csv"), index=False, encoding="utf-8-sig")
        scores.sort_values(["outer_split_id", "method", "datetime", "instrument"]).groupby(["outer_split_id", "method"], sort=True).head(3).to_csv(publisher.path("score_sample.csv"), index=False, encoding="utf-8-sig")
        if preflight_only:
            pd.DataFrame(columns=["outer_split_id", "method", "rows", "coverage", "score_std"]).to_csv(publisher.path("score_diagnostics.csv"), index=False, encoding="utf-8-sig")
            pd.DataFrame(columns=["outer_split_id", "method", "datetime", "rows", "minimum_components", "median_components"]).to_csv(publisher.path("daily_factor_component_count.csv"), index=False, encoding="utf-8-sig")
        else:
            scores.groupby(["outer_split_id", "method"]).agg(rows=("composite_score", "size"), coverage=("composite_score", lambda values: values.notna().mean()), score_std=("composite_score", "std")).reset_index().to_csv(publisher.path("score_diagnostics.csv"), index=False, encoding="utf-8-sig")
            diagnostics.to_csv(publisher.path("daily_factor_component_count.csv"), index=False, encoding="utf-8-sig")
        release_index_rows = []
        for split_id in split_ids:
            path = publisher.staging_dir / f"test_release_receipts/{split_id}.json"
            if path.is_file():
                receipt = json.loads(path.read_text(encoding="utf-8"))
                release_index_rows.append({"outer_split_id": split_id, "receipt_id": receipt["receipt_id"], "status": receipt["status"], "receipt_path": f"test_release_receipts/{split_id}.json", "receipt_sha256": file_sha256(path)})
        pd.DataFrame(release_index_rows, columns=["outer_split_id", "receipt_id", "status", "receipt_path", "receipt_sha256"]).to_csv(publisher.path("test_release_index.csv"), index=False, encoding="utf-8-sig")
        pd.DataFrame(
            [{"input_name": manifest["stage_id"], "artifact_id": manifest["artifact_id"], "path": path.as_posix(), "sha256": file_sha256(path)} for manifest, path in zip(manifests, manifest_paths)]
        ).to_csv(publisher.path("input_receipts.csv"), index=False, encoding="utf-8-sig")
        contracts.to_csv(publisher.path("contract_status.csv"), index=False, encoding="utf-8-sig")
        publisher.path("resolved_config.json").write_text(json.dumps(config, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        publisher.path("score_report.md").write_text(
            "# Split-Specific Transparent Score V1\n\n"
            + f"- Status: `{'pass' if ready else 'blocked'}`\n"
            + f"- Mode: `{'preflight_no_test_read' if preflight_only else 'frozen_outer_test_score_release'}`\n"
            + f"- Splits / methods / score rows: `{len(split_ids)}` / `{len(config['methods'])}` / `{len(scores)}`\n"
            + "- Scores contain predictions only; labels, returns, IC, and execution performance are not read or emitted.\n",
            encoding="utf-8",
        )
        files = [publisher.path(name) for name in controlled if name != "artifact_manifest.json" and not name.startswith("runtime/") and (publisher.staging_dir / name).is_file()]
        write_stage_artifact_manifest(
            project_root=PROJECT_ROOT,
            stage_id="split_transparent_score_preflight_v1" if preflight_only else "split_transparent_score_v1",
            config=config,
            output_dir=publisher.staging_dir,
            output_files=files,
            code_state=code_state,
            input_manifest_paths=manifest_paths,
            factor_frame_id=matrix_artifact["factor_frame_id"],
            split_manifest_id=split_artifact["split_manifest_id"],
            start_date=None if preflight_only else scores["datetime"].min(),
            end_date=None if preflight_only else scores["datetime"].max(),
            lineage_status="complete",
            artifact_status="pass" if ready else "blocked",
            blocked_reason="" if ready else "blocked_split_transparent_score",
        )
        publisher.publish()
    print(contracts.to_string(index=False))
    return 0 if ready else 2


if __name__ == "__main__":
    raise SystemExit(main())
