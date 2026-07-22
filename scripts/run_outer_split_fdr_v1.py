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

from qlib_integration.contracts import contract_row  # noqa: E402
from research_validation.bootstrap import moving_block_mean_test  # noqa: E402
from research_validation.feature_matrix import file_sha256  # noqa: E402
from research_validation.lineage import capture_code_state, load_artifact_manifest, validate_manifest_outputs, write_stage_artifact_manifest  # noqa: E402
from research_validation.multiple_testing import apply_fdr  # noqa: E402
from research_validation.outer_fdr import compute_outer_split_fdr  # noqa: E402
from research_validation.stage_output import StageOutputPublisher  # noqa: E402

CONTROLLED = (
    "artifact_manifest.json", "factor_hypothesis_tests.csv", "test_family_summary.csv", "fdr_results.csv",
    "rejected_hypotheses.csv", "null_simulation_results.csv", "input_receipts.csv", "contract_status.csv",
    "multiple_testing_report.md", "resolved_config.json",
)


def resolve(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else (PROJECT_ROOT / path).resolve()


def main() -> int:
    parser = argparse.ArgumentParser(description="Run three outer-train-only FDR families.")
    parser.add_argument("--config", type=Path, default=Path("configs/factor_multiple_testing_full_research_669_v1.yaml"))
    args = parser.parse_args()
    config = yaml.safe_load(resolve(args.config).read_text(encoding="utf-8")) or {}
    if config.get("family_scope") != "outer_split" or config.get("included_folds") != ["train"]:
        raise ValueError("FDR family semantics must be outer_split with included_folds=[train]")
    manifest_paths = [resolve(path) for path in config["input_manifests"]]
    manifests = [load_artifact_manifest(path) for path in manifest_paths]
    issues = [issue for manifest, path in zip(manifests, manifest_paths) for issue in validate_manifest_outputs(manifest, path.parent)]
    if issues or any(manifest["artifact_status"] != "pass" for manifest in manifests):
        raise ValueError("FDR projection manifest is stale or blocked")
    projection_contract = pd.read_csv(manifest_paths[0].parent / "contract_status.csv")
    test_projection_check = projection_contract.loc[
        projection_contract["check_name"].eq("outer_test_date_in_projection_count")
    ]
    if len(test_projection_check) != 1 or test_projection_check.iloc[0]["status"] != "pass":
        raise ValueError("outer-train projection does not prove test-date exclusion")
    test_date_count = int(test_projection_check.iloc[0]["observed_value"])
    projection_path = resolve(config["input_projection"])
    inventory = pd.read_csv(resolve(config["projection_inventory"]))
    receipt_row = inventory.loc[inventory["projection"].eq("outer_train_daily_ic")]
    if len(receipt_row) != 1 or file_sha256(projection_path) != str(receipt_row.iloc[0]["sha256"]):
        raise ValueError("outer-train projection hash differs from compact receipt")
    projection = pd.read_parquet(projection_path)
    maximum_factors = config.get("maximum_factors")
    if maximum_factors is not None:
        factors = sorted(projection["factor"].astype(str).unique())[: int(maximum_factors)]
        projection = projection.loc[projection["factor"].astype(str).isin(factors)].copy()
    tests = compute_outer_split_fdr(
        projection,
        metric=str(config["metric"]),
        bootstrap_samples=int(config["bootstrap_samples"]),
        block_length=int(config["block_length"]),
        random_seed=int(config["random_seed"]),
        fdr_alpha=float(config["fdr_alpha"]),
        source_family=str(config["source_family"]),
        label_name=str(config["label_name"]),
        preprocessing_variant=str(config["preprocessing_variant"]),
    )
    rng = np.random.default_rng(int(config["random_seed"]))
    null_rows = []
    for index in range(int(config["null_simulation_factors"])):
        stats = moving_block_mean_test(pd.Series(rng.normal(0, 1, 500)), samples=500, block_length=int(config["block_length"]), seed=int(config["random_seed"]) + index)
        null_rows.append({"factor": f"null_{index:03d}", "test_family": "null_simulation", "metric": "daily_ic", **stats})
    null_results = apply_fdr(pd.DataFrame(null_rows), float(config["fdr_alpha"]))
    stable_stats = moving_block_mean_test(pd.Series(rng.normal(float(config["stable_signal_mean"]), 0.1, 500)), samples=1000, block_length=int(config["block_length"]), seed=int(config["random_seed"]))
    family_summary = tests.groupby(["outer_split_id", "test_family"], as_index=False).agg(hypotheses=("factor", "size"), unique_factors=("factor", "nunique"), bh_pass=("fdr_bh_pass", "sum"), by_pass=("fdr_by_pass", "sum"))
    duplicates = int(tests.duplicated(["outer_split_id", "factor"]).sum())
    expected_families = int(config["expected_family_count"])
    expected_hypotheses = int(config["expected_hypotheses_per_family"])
    false_discovery_rate = float(null_results["fdr_bh_pass"].mean())
    contracts = pd.DataFrame([
        contract_row("family_count", len(family_summary) == expected_families, len(family_summary), expected_families),
        contract_row("unique_factor_count_per_family", family_summary["unique_factors"].eq(expected_hypotheses).all(), family_summary["unique_factors"].tolist(), expected_hypotheses),
        contract_row("hypotheses_per_family", family_summary["hypotheses"].eq(expected_hypotheses).all(), family_summary["hypotheses"].tolist(), expected_hypotheses),
        contract_row("duplicate_outer_split_factor_count", duplicates == 0, duplicates, 0),
        contract_row("unexpected_fold_count", tests["included_folds"].ne("train").sum() == 0, int(tests["included_folds"].ne("train").sum()), 0),
        contract_row("test_date_in_fdr_input_count", test_date_count == 0, test_date_count, 0),
        contract_row("all_hypotheses_have_q_value", tests["fdr_bh_q_value"].notna().all(), int(tests["fdr_bh_q_value"].isna().sum()), 0),
        contract_row("projection_hash_bound", file_sha256(projection_path) == str(receipt_row.iloc[0]["sha256"]), file_sha256(projection_path), receipt_row.iloc[0]["sha256"]),
        contract_row("null_simulation_false_discovery_rate", false_discovery_rate <= float(config["fdr_alpha"]), false_discovery_rate, f"<={config['fdr_alpha']}"),
        contract_row("stable_signal_detected", stable_stats["raw_p_value"] <= float(config["fdr_alpha"]), stable_stats["raw_p_value"], f"<={config['fdr_alpha']}"),
    ])
    receipts = pd.DataFrame([{
        "input_name": "outer_train_daily_ic", "artifact_id": manifests[0]["artifact_id"], "path": projection_path.as_posix(),
        "sha256": file_sha256(projection_path), "join_keys": "outer_split_id,datetime,factor", "input_rows": int(receipt_row.iloc[0]["row_count"]),
        "consumed_rows": len(projection), "missing_rows": 0,
    }])
    ready = bool(contracts["status"].eq("pass").all())
    output_dir = resolve(config["output_dir"])
    with StageOutputPublisher(output_dir, CONTROLLED) as publisher:
        tests.to_csv(publisher.path("factor_hypothesis_tests.csv"), index=False, encoding="utf-8-sig")
        tests.to_csv(publisher.path("fdr_results.csv"), index=False, encoding="utf-8-sig")
        family_summary.to_csv(publisher.path("test_family_summary.csv"), index=False, encoding="utf-8-sig")
        tests.loc[tests["fdr_bh_pass"] | tests["fdr_by_pass"]].to_csv(publisher.path("rejected_hypotheses.csv"), index=False, encoding="utf-8-sig")
        null_results.to_csv(publisher.path("null_simulation_results.csv"), index=False, encoding="utf-8-sig")
        receipts.to_csv(publisher.path("input_receipts.csv"), index=False, encoding="utf-8-sig")
        contracts.to_csv(publisher.path("contract_status.csv"), index=False, encoding="utf-8-sig")
        publisher.path("resolved_config.json").write_text(json.dumps(config, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        publisher.path("multiple_testing_report.md").write_text(
            "# Outer-Split FDR Gate V1\n\n"
            + f"- Status: `{'pass' if ready else 'blocked'}`\n"
            + f"- Families / hypotheses per family: `{len(family_summary)}` / `{expected_hypotheses}`\n"
            + "- Input folds: `outer train only`; outer validation and test are absent.\n"
            + "- Inner-window semantics: full outer-train eligibility gate, not nested pseudo-OOS FDR replay.\n",
            encoding="utf-8",
        )
        files = [publisher.path(name) for name in CONTROLLED if name != "artifact_manifest.json"]
        write_stage_artifact_manifest(
            project_root=PROJECT_ROOT, stage_id="factor_multiple_testing_v1", config=config,
            output_dir=publisher.staging_dir, output_files=files, code_state=capture_code_state(PROJECT_ROOT),
            input_manifest_paths=manifest_paths, factor_frame_id=manifests[0]["factor_frame_id"],
            split_manifest_id=manifests[0]["split_manifest_id"], start_date=projection["datetime"].min(),
            end_date=projection["datetime"].max(), lineage_status="complete",
            artifact_status="pass" if ready else "blocked", blocked_reason="" if ready else "blocked_outer_split_fdr",
        )
        publisher.publish()
    print(contracts.to_string(index=False))
    return 0 if ready else 2


if __name__ == "__main__":
    raise SystemExit(main())
