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
from research_validation.rolling_evaluation import DEVELOPMENT_SELECTION_COLUMNS, development_stability_board, select_development_factor_window  # noqa: E402
from research_validation.stage_output import StageOutputPublisher  # noqa: E402

CONTROLLED = (
    "artifact_manifest.json", "factor_window_metrics.csv", "factor_selection_history.csv",
    "factor_direction_history.csv", "factor_stability_board.csv", "stability_role_summary.csv",
    "input_receipts.csv", "contract_status.csv", "stability_report.md", "resolved_config.json",
)


def resolve(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else (PROJECT_ROOT / path).resolve()


def main() -> int:
    parser = argparse.ArgumentParser(description="Build holdout-clean stability from inner development windows and upstream FDR.")
    parser.add_argument("--config", type=Path, default=Path("configs/factor_rolling_stability_full_research_669_v1.yaml"))
    args = parser.parse_args()
    config = yaml.safe_load(resolve(args.config).read_text(encoding="utf-8")) or {}
    manifest_paths = [resolve(path) for path in config["input_manifests"]]
    manifests = [load_artifact_manifest(path) for path in manifest_paths]
    issues = [issue for manifest, path in zip(manifests, manifest_paths) for issue in validate_manifest_outputs(manifest, path.parent)]
    if issues or any(manifest["artifact_status"] != "pass" for manifest in manifests):
        raise ValueError("stability upstream is stale or blocked")
    projection_contract = pd.read_csv(manifest_paths[0].parent / "contract_status.csv")
    inner_test_check = projection_contract.loc[
        projection_contract["check_name"].eq("inner_test_date_in_projection_count")
    ]
    if len(inner_test_check) != 1 or inner_test_check.iloc[0]["status"] != "pass":
        raise ValueError("inner development projection does not prove test-date exclusion")
    inner_test_count = int(inner_test_check.iloc[0]["observed_value"])
    canary_manifest_path = config.get("canary_manifest")
    canary_gate_observed = "not_required"
    if canary_manifest_path:
        canary_manifest_resolved = resolve(canary_manifest_path)
        canary_manifest = load_artifact_manifest(canary_manifest_resolved)
        canary_issues = validate_manifest_outputs(canary_manifest, canary_manifest_resolved.parent)
        canary_contract = pd.read_csv(resolve(config["canary_contract"]))
        if canary_issues or canary_manifest["artifact_status"] != "pass" or not canary_contract["status"].eq("pass").all():
            raise ValueError("corrected stability canary is stale, blocked, or incomplete")
        canary_gate_observed = "pass"
    projection_path = resolve(config["input_projection"])
    inventory = pd.read_csv(resolve(config["projection_inventory"]))
    projection_receipt = inventory.loc[inventory["projection"].eq("inner_development_daily_ic")]
    if len(projection_receipt) != 1 or file_sha256(projection_path) != str(projection_receipt.iloc[0]["sha256"]):
        raise ValueError("inner development projection hash differs from compact receipt")
    projection = pd.read_parquet(projection_path)
    fdr_path = resolve(config["fdr_results"])
    expected_fdr_hash = manifests[1]["output_file_hashes"].get(fdr_path.name)
    if not expected_fdr_hash or file_sha256(fdr_path) != expected_fdr_hash:
        raise ValueError("FDR result hash differs from its manifest")
    fdr = pd.read_csv(fdr_path)
    expected_bootstrap_method = str(config["expected_bootstrap_method"])
    if "bootstrap_method" not in fdr or not fdr["bootstrap_method"].eq(expected_bootstrap_method).all():
        raise ValueError("FDR rows do not use the frozen bootstrap method")
    maximum_factors = config.get("maximum_factors")
    if maximum_factors is not None:
        factors = sorted(fdr["factor"].astype(str).unique())[: int(maximum_factors)]
        projection = projection.loc[projection["factor"].astype(str).isin(factors)].copy()
        fdr = fdr.loc[fdr["factor"].astype(str).isin(factors)].copy()
    if fdr.duplicated(["outer_split_id", "factor"]).any():
        raise ValueError("upstream FDR has duplicate outer_split_id/factor keys")
    grouped = projection.groupby(["outer_split_id", "inner_split_id", "factor", "fold"], sort=True)[str(config["metric_column"])]
    stats = grouped.agg(valid_count="count", total_count="size", mean_ic="mean").reset_index()
    wide = stats.pivot(index=["outer_split_id", "inner_split_id", "factor"], columns="fold", values=["valid_count", "total_count", "mean_ic"]).reset_index()
    wide.columns = ["_".join(str(part) for part in column if str(part)) if isinstance(column, tuple) else str(column) for column in wide.columns]
    wide = wide.rename(columns={
        "mean_ic_train": "train_mean_ic", "mean_ic_validation": "validation_mean_ic",
        "valid_count_train": "train_count", "valid_count_validation": "validation_count",
        "total_count_train": "train_total", "total_count_validation": "validation_total",
    })
    wide["train_coverage"] = wide["train_count"] / wide["train_total"]
    wide["validation_coverage"] = wide["validation_count"] / wide["validation_total"]
    wide["selection_eligible"] = (
        wide["train_count"].ge(int(config["minimum_train_valid_ic_count"]))
        & wide["validation_count"].ge(int(config["minimum_validation_valid_ic_count"]))
        & wide["train_coverage"].ge(float(config["minimum_train_coverage"]))
        & wide["validation_coverage"].ge(float(config["minimum_validation_coverage"]))
    )
    fdr_columns = ["outer_split_id", "factor", "fdr_bh_pass", "fdr_bh_q_value"]
    merged = wide.merge(fdr[fdr_columns], on=["outer_split_id", "factor"], how="left", validate="many_to_one", indicator=True)
    missing_count = int(merged["_merge"].ne("both").sum())
    metric_keys = set(map(tuple, wide[["outer_split_id", "factor"]].drop_duplicates().to_numpy()))
    fdr_keys = set(map(tuple, fdr[["outer_split_id", "factor"]].drop_duplicates().to_numpy()))
    extra_count = len(fdr_keys - metric_keys)
    merged = merged.drop(columns="_merge")
    decision_rows = []
    for row in merged.to_dict("records"):
        decision_input = pd.Series({column: row[column] for column in DEVELOPMENT_SELECTION_COLUMNS})
        decision = select_development_factor_window(decision_input, min_abs_validation_ic=float(config["min_abs_validation_ic"]), min_dates=int(config["minimum_dates_per_fold"]))
        decision_rows.append({**row, **decision, "eligible": bool(row["selection_eligible"]), "internally_recomputed_fdr": False})
    metrics = pd.DataFrame(decision_rows)
    board = development_stability_board(metrics, config)
    expected_outer = int(config["expected_outer_splits"])
    expected_inner = int(config["expected_inner_splits_per_outer"])
    expected_factors = int(config["expected_factor_count"])
    fdr_source = fdr.set_index(["outer_split_id", "factor"])["fdr_bh_q_value"]
    joined_q = metrics.set_index(["outer_split_id", "factor"])["fdr_bh_q_value"]
    mismatch = int((joined_q - joined_q.index.map(fdr_source)).abs().gt(0).sum())
    contracts = pd.DataFrame([
        contract_row("canary_gate_passed", canary_gate_observed in {"not_required", "pass"}, canary_gate_observed, "pass_or_not_required"),
        contract_row("outer_split_count", board["outer_split_id"].nunique() == expected_outer, board["outer_split_id"].nunique(), expected_outer),
        contract_row("factor_count_per_outer", board.groupby("outer_split_id")["factor"].nunique().eq(expected_factors).all(), board.groupby("outer_split_id")["factor"].nunique().tolist(), expected_factors),
        contract_row("inner_window_count_per_outer", metrics.groupby("outer_split_id")["inner_split_id"].nunique().eq(expected_inner).all(), metrics.groupby("outer_split_id")["inner_split_id"].nunique().tolist(), expected_inner),
        contract_row("fdr_join_missing", missing_count == 0, missing_count, 0),
        contract_row("fdr_join_extra", extra_count == 0, extra_count, 0),
        contract_row("fdr_q_value_mismatch", mismatch == 0, mismatch, 0),
        contract_row("fdr_output_hash_bound", file_sha256(fdr_path) == expected_fdr_hash, file_sha256(fdr_path), expected_fdr_hash),
        contract_row("fdr_bootstrap_method_frozen", fdr["bootstrap_method"].eq(expected_bootstrap_method).all(), expected_bootstrap_method, expected_bootstrap_method),
        contract_row("internally_recomputed_fdr", not metrics["internally_recomputed_fdr"].any(), bool(metrics["internally_recomputed_fdr"].any()), False),
        contract_row("inner_test_date_in_projection_count", inner_test_count == 0, inner_test_count, 0),
        contract_row("test_metrics_used_in_selection", not any(str(column).startswith("test_") or "oos" in str(column).lower() for column in metrics.columns), False, False),
        contract_row("selection_schema_has_no_test_fields", not any(str(column).startswith("test_") or "oos" in str(column).lower() for column in metrics.columns), [column for column in metrics.columns if str(column).startswith("test_") or "oos" in str(column).lower()], []),
        contract_row("all_selected_factors_have_fdr_result", metrics.loc[metrics["selected"], "fdr_bh_q_value"].notna().all(), int(metrics.loc[metrics["selected"], "fdr_bh_q_value"].isna().sum()), 0),
    ])
    receipts = pd.DataFrame([
        {"input_name": "inner_development_daily_ic", "artifact_id": manifests[0]["artifact_id"], "path": projection_path.as_posix(), "sha256": file_sha256(projection_path), "join_keys": "outer_split_id,inner_split_id,fold,datetime,factor", "input_rows": int(projection_receipt.iloc[0]["row_count"]), "consumed_rows": len(projection), "missing_rows": 0},
        {"input_name": "outer_split_fdr", "artifact_id": manifests[1]["artifact_id"], "path": fdr_path.as_posix(), "sha256": file_sha256(fdr_path), "join_keys": "outer_split_id,factor", "input_rows": len(fdr), "consumed_rows": len(metrics), "missing_rows": missing_count},
    ])
    ready = bool(contracts["status"].eq("pass").all())
    output_dir = resolve(config["output_dir"])
    with StageOutputPublisher(output_dir, CONTROLLED) as publisher:
        metrics.to_csv(publisher.path("factor_window_metrics.csv"), index=False, encoding="utf-8-sig")
        metrics[["outer_split_id", "inner_split_id", "factor", "selected", "selection_eligible", "selection_reason", "frozen_direction", "fdr_bh_q_value"]].to_csv(publisher.path("factor_selection_history.csv"), index=False, encoding="utf-8-sig")
        metrics[["outer_split_id", "inner_split_id", "factor", "frozen_direction"]].to_csv(publisher.path("factor_direction_history.csv"), index=False, encoding="utf-8-sig")
        board.to_csv(publisher.path("factor_stability_board.csv"), index=False, encoding="utf-8-sig")
        board.groupby(["outer_split_id", "stability_role"]).size().reset_index(name="factor_count").to_csv(publisher.path("stability_role_summary.csv"), index=False, encoding="utf-8-sig")
        receipts.to_csv(publisher.path("input_receipts.csv"), index=False, encoding="utf-8-sig")
        contracts.to_csv(publisher.path("contract_status.csv"), index=False, encoding="utf-8-sig")
        publisher.path("resolved_config.json").write_text(json.dumps(config, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        publisher.path("stability_report.md").write_text(
            "# Corrected Holdout-Clean Stability\n\n"
            + f"- Status: `{'pass' if ready else 'blocked'}`\n"
            + f"- Outer splits / factor rows: `{board['outer_split_id'].nunique()}` / `{len(board)}`\n"
            + f"- Stable-core rows: `{int(board['stability_role'].eq('stable_core').sum())}`\n"
            + "- FDR is consumed from the upstream artifact; it is never recomputed here.\n"
            + "- Outer-test fields and rows are absent from the selection API and artifacts.\n",
            encoding="utf-8",
        )
        files = [publisher.path(name) for name in CONTROLLED if name != "artifact_manifest.json"]
        write_stage_artifact_manifest(
            project_root=PROJECT_ROOT, stage_id=str(config.get("stage_id", "factor_rolling_stability_v1")), config=config,
            output_dir=publisher.staging_dir, output_files=files, code_state=capture_code_state(PROJECT_ROOT),
            input_manifest_paths=manifest_paths, factor_frame_id=manifests[0]["factor_frame_id"],
            split_manifest_id=manifests[0]["split_manifest_id"], start_date=projection["datetime"].min(),
            end_date=projection["datetime"].max(), lineage_status="complete",
            artifact_status="pass" if ready else "blocked", blocked_reason="" if ready else "blocked_holdout_clean_stability",
        )
        publisher.publish()
    print(contracts.to_string(index=False))
    return 0 if ready else 2


if __name__ == "__main__":
    raise SystemExit(main())
