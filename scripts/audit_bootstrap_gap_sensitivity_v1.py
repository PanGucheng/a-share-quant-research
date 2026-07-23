from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import pandas as pd
import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from research_validation.bootstrap import (  # noqa: E402
    gap_aware_moving_block_mean_test,
    moving_block_mean_test,
)
from research_validation.feature_matrix import file_sha256  # noqa: E402
from research_validation.lineage import (  # noqa: E402
    capture_code_state,
    load_artifact_manifest,
    validate_manifest_outputs,
    write_stage_artifact_manifest,
)
from research_validation.multiple_testing import apply_fdr  # noqa: E402
from research_validation.stage_output import StageOutputPublisher  # noqa: E402


CONTROLLED = [
    "artifact_manifest.json",
    "bootstrap_gap_report.md",
    "contract_status.csv",
    "factor_method_comparison.csv",
    "fdr_method_comparison.csv",
    "frozen_bootstrap_policy.json",
    "gap_injection_results.csv",
    "resolved_config.json",
    "sensitivity_summary.csv",
]


def resolve(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else (PROJECT_ROOT / path).resolve()


def factor_seed(base: int, split: str, factor: str) -> int:
    digest = hashlib.sha256(f"{base}|{split}|{factor}".encode("utf-8")).digest()
    return int.from_bytes(digest[:4], "big")


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit contiguous versus gap-aware block bootstrap.")
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/bootstrap_gap_sensitivity_v1.yaml"),
    )
    args = parser.parse_args()
    config_path = resolve(args.config)
    config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    manifest_path = resolve(config["projection_manifest"])
    manifest = load_artifact_manifest(manifest_path)
    if (
        validate_manifest_outputs(manifest, manifest_path.parent)
        or manifest["artifact_status"] != "pass"
        or manifest["lineage_status"] != "complete"
        or bool(manifest["code_dirty"])
    ):
        raise ValueError("selection projection v2 is stale, blocked, or non-authoritative")
    inventory = pd.read_csv(resolve(config["projection_inventory"]))
    receipt = inventory.loc[inventory["projection"].eq("outer_train_daily_ic")]
    projection_path = resolve(config["outer_train_projection"])
    if len(receipt) != 1 or file_sha256(projection_path) != receipt.iloc[0]["sha256"]:
        raise ValueError("outer-train projection hash mismatch")
    projection = pd.read_parquet(projection_path)
    projection["datetime"] = pd.to_datetime(projection["datetime"])
    maximum = config.get("maximum_factors")
    if maximum is not None:
        selected = sorted(projection["factor"].astype(str).unique())[: int(maximum)]
        projection = projection.loc[projection["factor"].isin(selected)].copy()
    metric = str(config["metric"])
    rows = []
    for (split, factor), group in projection.groupby(
        ["outer_split_id", "factor"], sort=True
    ):
        ordered = group.sort_values("datetime", kind="stable")
        series = pd.Series(
            pd.to_numeric(ordered[metric], errors="coerce").to_numpy(),
            index=ordered["datetime"],
        )
        seed = factor_seed(int(config["random_seed"]), str(split), str(factor))
        legacy = moving_block_mean_test(
            series,
            samples=int(config["bootstrap_samples"]),
            block_length=int(config["block_length"]),
            seed=seed,
        )
        gap = gap_aware_moving_block_mean_test(
            series,
            samples=int(config["bootstrap_samples"]),
            block_length=int(config["block_length"]),
            seed=seed,
        )
        rows.append(
            {
                "outer_split_id": split,
                "factor": factor,
                "test_family": f"gap_audit|{split}",
                "metric": metric,
                "observation_count": legacy["observation_count"],
                "contiguous_segment_count": gap["contiguous_segment_count"],
                "eligible_block_count": gap["eligible_block_count"],
                "legacy_p_value": legacy["raw_p_value"],
                "gap_aware_p_value": gap["raw_p_value"],
                "p_value_absolute_difference": abs(
                    legacy["raw_p_value"] - gap["raw_p_value"]
                ),
                "legacy_ci_lower": legacy["mean_ci_lower"],
                "legacy_ci_upper": legacy["mean_ci_upper"],
                "gap_aware_ci_lower": gap["mean_ci_lower"],
                "gap_aware_ci_upper": gap["mean_ci_upper"],
                "ci_endpoint_max_absolute_difference": max(
                    abs(legacy["mean_ci_lower"] - gap["mean_ci_lower"]),
                    abs(legacy["mean_ci_upper"] - gap["mean_ci_upper"]),
                ),
            }
        )
    comparison = pd.DataFrame(rows)
    legacy_fdr = apply_fdr(
        comparison.rename(columns={"legacy_p_value": "raw_p_value"})[
            ["outer_split_id", "factor", "test_family", "metric", "raw_p_value"]
        ],
        float(config["fdr_alpha"]),
    )
    gap_fdr = apply_fdr(
        comparison.rename(columns={"gap_aware_p_value": "raw_p_value"})[
            ["outer_split_id", "factor", "test_family", "metric", "raw_p_value"]
        ],
        float(config["fdr_alpha"]),
    )
    fdr = legacy_fdr.merge(
        gap_fdr,
        on=["outer_split_id", "factor", "test_family", "metric"],
        suffixes=("_legacy", "_gap_aware"),
        validate="one_to_one",
    )
    fdr["bh_pass_changed"] = (
        fdr["fdr_bh_pass_legacy"] != fdr["fdr_bh_pass_gap_aware"]
    )
    fdr["by_pass_changed"] = (
        fdr["fdr_by_pass_legacy"] != fdr["fdr_by_pass_gap_aware"]
    )
    injection_rows = []
    injection_factors = sorted(projection["factor"].unique())[
        : int(config["gap_injection_factor_count"])
    ]
    for (split, factor), group in projection.loc[
        projection["factor"].isin(injection_factors)
    ].groupby(["outer_split_id", "factor"], sort=True):
        ordered = group.sort_values("datetime", kind="stable")
        baseline = pd.Series(
            pd.to_numeric(ordered[metric], errors="coerce").to_numpy(),
            index=ordered["datetime"],
        )
        injected = baseline.copy()
        injected.iloc[
            int(config["gap_injection_stride"]) - 1 :: int(
                config["gap_injection_stride"]
            )
        ] = pd.NA
        seed = factor_seed(int(config["random_seed"]) + 1, str(split), str(factor))
        before = gap_aware_moving_block_mean_test(
            baseline,
            samples=int(config["bootstrap_samples"]),
            block_length=int(config["block_length"]),
            seed=seed,
        )
        after = gap_aware_moving_block_mean_test(
            injected,
            samples=int(config["bootstrap_samples"]),
            block_length=int(config["block_length"]),
            seed=seed,
        )
        injection_rows.append(
            {
                "outer_split_id": split,
                "factor": factor,
                "injected_gap_count": int(injected.isna().sum() - baseline.isna().sum()),
                "baseline_p_value": before["raw_p_value"],
                "injected_p_value": after["raw_p_value"],
                "p_value_absolute_change": abs(
                    before["raw_p_value"] - after["raw_p_value"]
                ),
                "baseline_segment_count": before["contiguous_segment_count"],
                "injected_segment_count": after["contiguous_segment_count"],
            }
        )
    injection = pd.DataFrame(injection_rows)
    thresholds = config["thresholds"]
    observed = {
        "maximum_p_value_absolute_difference": float(
            comparison["p_value_absolute_difference"].max()
        ),
        "maximum_ci_endpoint_absolute_difference": float(
            comparison["ci_endpoint_max_absolute_difference"].max()
        ),
        "maximum_bh_pass_changes": int(fdr["bh_pass_changed"].sum()),
        "maximum_by_pass_changes": int(fdr["by_pass_changed"].sum()),
        "maximum_injected_p_value_change": float(
            injection["p_value_absolute_change"].max()
        ),
    }
    threshold_breaches = {
        key: observed[key] > float(thresholds[key]) for key in thresholds
    }
    frozen_method = (
        "gap_aware_moving_block"
        if any(threshold_breaches.values())
        else "legacy_dropna_moving_block"
    )
    policy = {
        "schema_version": 1,
        "status": "frozen",
        "selected_method": frozen_method,
        "decision_rule": "select gap-aware if any pre-frozen sensitivity threshold is exceeded",
        "thresholds": thresholds,
        "observed": observed,
        "threshold_breaches": threshold_breaches,
        "selection_data_scope": "outer_train_only",
        "outer_test_used": False,
        "bootstrap_samples_for_audit": int(config["bootstrap_samples"]),
        "block_length": int(config["block_length"]),
        "random_seed": int(config["random_seed"]),
    }
    summary = pd.DataFrame(
        [
            {
                "selected_method": frozen_method,
                "comparison_rows": len(comparison),
                "outer_split_count": comparison["outer_split_id"].nunique(),
                "factor_count": comparison["factor"].nunique(),
                **observed,
                "threshold_breach_count": sum(threshold_breaches.values()),
            }
        ]
    )
    checks = [
        ("outer_split_count", comparison["outer_split_id"].nunique() == int(config["expected_outer_splits"]), comparison["outer_split_id"].nunique()),
        ("factor_count", comparison["factor"].nunique() == int(config["expected_factor_count"]), comparison["factor"].nunique()),
        ("outer_train_only", set(projection["fold"]) == {"train"}, sorted(projection["fold"].unique())),
        ("method_rows_unique", not comparison.duplicated(["outer_split_id", "factor"]).any(), int(comparison.duplicated(["outer_split_id", "factor"]).sum())),
        ("gap_blocks_available", comparison["eligible_block_count"].gt(0).all(), int(comparison["eligible_block_count"].min())),
        ("injection_increases_segments", injection["injected_segment_count"].ge(injection["baseline_segment_count"]).all(), int(injection["injected_segment_count"].min())),
        ("policy_frozen_before_fdr", policy["status"] == "frozen", frozen_method),
        ("outer_test_not_used", not policy["outer_test_used"], policy["selection_data_scope"]),
    ]
    contracts = pd.DataFrame(
        [
            {
                "check": name,
                "status": "pass" if passed else "fail",
                "severity": "critical",
                "detail": detail,
            }
            for name, passed, detail in checks
        ]
    )
    ready = contracts["status"].eq("pass").all()
    resolved = {
        **config,
        "config_file_sha256": file_sha256(config_path),
        "projection_sha256": file_sha256(projection_path),
    }
    output = resolve(config["output_dir"])
    with StageOutputPublisher(output, CONTROLLED) as publisher:
        comparison.to_csv(
            publisher.path("factor_method_comparison.csv"),
            index=False,
            encoding="utf-8-sig",
        )
        fdr.to_csv(
            publisher.path("fdr_method_comparison.csv"),
            index=False,
            encoding="utf-8-sig",
        )
        injection.to_csv(
            publisher.path("gap_injection_results.csv"),
            index=False,
            encoding="utf-8-sig",
        )
        summary.to_csv(
            publisher.path("sensitivity_summary.csv"),
            index=False,
            encoding="utf-8-sig",
        )
        contracts.to_csv(
            publisher.path("contract_status.csv"), index=False, encoding="utf-8-sig"
        )
        publisher.path("frozen_bootstrap_policy.json").write_text(
            json.dumps(policy, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        publisher.path("resolved_config.json").write_text(
            json.dumps(resolved, ensure_ascii=False, indent=2, default=str) + "\n",
            encoding="utf-8",
        )
        publisher.path("bootstrap_gap_report.md").write_text(
            "\n".join(
                [
                    "# Bootstrap Gap Sensitivity Audit V1",
                    "",
                    f"- Status: `{'pass' if ready else 'blocked'}`",
                    f"- Outer splits / factors: `{comparison['outer_split_id'].nunique()}` / `{comparison['factor'].nunique()}`",
                    f"- Frozen method: `{frozen_method}`",
                    f"- Threshold breaches: `{sum(threshold_breaches.values())}`",
                    f"- BH / BY pass changes: `{observed['maximum_bh_pass_changes']}` / `{observed['maximum_by_pass_changes']}`",
                    "- Method selection uses outer-train data only and occurs before corrected FDR.",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        files = [publisher.path(name) for name in CONTROLLED if name != "artifact_manifest.json"]
        write_stage_artifact_manifest(
            project_root=PROJECT_ROOT,
            stage_id="bootstrap_gap_sensitivity_v1",
            config=resolved,
            output_dir=publisher.staging_dir,
            output_files=files,
            code_state=capture_code_state(PROJECT_ROOT),
            input_manifest_paths=[manifest_path],
            universe_artifact_id=manifest["universe_artifact_id"],
            factor_catalog_id=manifest["factor_catalog_id"],
            factor_frame_id=manifest["factor_frame_id"],
            split_manifest_id=manifest["split_manifest_id"],
            start_date=projection["datetime"].min(),
            end_date=projection["datetime"].max(),
            artifact_status="pass" if ready else "blocked",
            blocked_reason="" if ready else "blocked_bootstrap_gap_audit",
        )
        publisher.publish()
    print(contracts.to_string(index=False))
    print(json.dumps(policy, indent=2))
    return 0 if ready else 2


if __name__ == "__main__":
    raise SystemExit(main())
