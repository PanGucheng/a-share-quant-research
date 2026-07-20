from __future__ import annotations

import argparse
import re
import sys
from multiprocessing import freeze_support
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from research_validation.bootstrap import moving_block_mean_test  # noqa: E402
from research_validation.multiple_testing import apply_fdr  # noqa: E402
from research_validation.lineage import capture_code_state, content_reference_id, write_stage_artifact_manifest  # noqa: E402


def family(config: dict, horizon: str) -> str:
    return "|".join([config["source_family"], horizon, config["research_window"], config["preprocessing_variant"]])


def main() -> int:
    parser = argparse.ArgumentParser(description="Run block-bootstrap factor tests and FDR correction.")
    parser.add_argument("--config", type=Path, default=Path("configs/factor_multiple_testing_v1.yaml"))
    args = parser.parse_args()
    config_path = args.config if args.config.is_absolute() else PROJECT_ROOT / args.config
    config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    code_state = capture_code_state(PROJECT_ROOT)
    rows = []
    input_paths = (
        [PROJECT_ROOT / config["input_table"]]
        if config.get("input_table")
        else sorted(PROJECT_ROOT.glob(config["input_glob"]))
    )
    input_dates: list[pd.Timestamp] = []
    if config.get("input_table"):
        frame = pd.read_csv(input_paths[0])
        frame["datetime"] = pd.to_datetime(frame["datetime"])
        assignments = pd.read_csv(PROJECT_ROOT / config["date_assignments"])
        assignments["datetime"] = pd.to_datetime(assignments["datetime"])
        included_folds = set(config.get("included_folds", ["train"]))
        assignments = assignments.loc[assignments["fold"].isin(included_folds)]
        input_dates.extend(frame["datetime"].dropna().tolist())
        for split_id, dates in assignments.groupby("split_id", sort=True):
            selected_dates = set(dates["datetime"])
            selected = frame.loc[frame["datetime"].isin(selected_dates)]
            for factor, values in selected.groupby("factor", sort=True):
                stats = moving_block_mean_test(values[config["metric"]], samples=int(config["bootstrap_samples"]), block_length=int(config["block_length"]), seed=int(config["random_seed"]))
                test_family = "|".join([config["source_family"], config["label_name"], str(split_id), "+".join(sorted(included_folds)), config["preprocessing_variant"]])
                rows.append({"factor": factor, "test_family": test_family, "metric": config["metric"], **stats, "input_path": input_paths[0].relative_to(PROJECT_ROOT).as_posix(), "split_id": split_id, "included_folds": "+".join(sorted(included_folds))})
    else:
        for path in input_paths:
            factor = path.parent.name
            match = re.search(r"label_(\d+d_t\d+)_", path.name)
            horizon = match.group(1) if match else "unknown"
            frame = pd.read_csv(path)
            if "datetime" in frame:
                input_dates.extend(pd.to_datetime(frame["datetime"], errors="coerce").dropna().tolist())
            stats = moving_block_mean_test(frame[config["metric"]], samples=int(config["bootstrap_samples"]), block_length=int(config["block_length"]), seed=int(config["random_seed"]))
            rows.append({"factor": factor, "test_family": family(config, horizon), "metric": config["metric"], **stats, "input_path": path.relative_to(PROJECT_ROOT).as_posix()})
    tests = apply_fdr(pd.DataFrame(rows), float(config["fdr_alpha"]))

    rng = np.random.default_rng(int(config["random_seed"]))
    null_rows = []
    for index in range(int(config["null_simulation_factors"])):
        series = pd.Series(rng.normal(0, 1, 500))
        stats = moving_block_mean_test(series, samples=500, block_length=int(config["block_length"]), seed=int(config["random_seed"]) + index)
        null_rows.append({"factor": f"null_{index:03d}", "test_family": "null_simulation", "metric": "daily_ic", **stats})
    null_results = apply_fdr(pd.DataFrame(null_rows), float(config["fdr_alpha"]))
    stable = pd.Series(rng.normal(float(config["stable_signal_mean"]), 0.1, 500))
    stable_stats = moving_block_mean_test(stable, samples=1000, block_length=int(config["block_length"]), seed=int(config["random_seed"]))
    false_discovery_rate = float(null_results["fdr_bh_pass"].mean())
    checks = [
        ("all_selected_factors_have_q_value", bool(tests["fdr_bh_q_value"].notna().all()), True),
        ("missing_test_family_count", int(tests["test_family"].isna().sum()), 0),
        ("nan_p_value_promoted_count", int((tests["raw_p_value"].isna() & tests["fdr_bh_pass"]).sum()), 0),
        ("null_simulation_false_discovery_rate", false_discovery_rate, f"<={config['fdr_alpha']}"),
        ("stable_signal_detected", stable_stats["raw_p_value"] <= float(config["fdr_alpha"]), True),
    ]
    contract_rows = []
    for name, observed, required in checks:
        passed = observed <= float(config["fdr_alpha"]) if name == "null_simulation_false_discovery_rate" else observed == required
        contract_rows.append({"check_name": name, "status": "pass" if passed else "fail", "observed_value": observed, "required_value": required, "severity": "critical", "reason": "Multiple-testing control contract."})
    contract = pd.DataFrame(contract_rows)
    output = PROJECT_ROOT / config["output_dir"]
    output.mkdir(parents=True, exist_ok=True)
    tests.to_csv(output / "factor_hypothesis_tests.csv", index=False, encoding="utf-8-sig")
    tests.groupby("test_family").agg(hypotheses=("factor", "size"), bh_pass=("fdr_bh_pass", "sum"), by_pass=("fdr_by_pass", "sum")).reset_index().to_csv(output / "test_family_summary.csv", index=False, encoding="utf-8-sig")
    tests.to_csv(output / "fdr_results.csv", index=False, encoding="utf-8-sig")
    tests.loc[tests["fdr_bh_pass"] | tests["fdr_by_pass"]].to_csv(output / "rejected_hypotheses.csv", index=False, encoding="utf-8-sig")
    null_results.to_csv(output / "null_simulation_results.csv", index=False, encoding="utf-8-sig")
    contract.to_csv(output / "contract_status.csv", index=False, encoding="utf-8-sig")
    (output / "multiple_testing_report.md").write_text(f"# Factor Multiple Testing V1\n\n- Hypotheses: `{len(tests)}`\n- Null FDR: `{false_discovery_rate:.6f}`\n- Stable signal p-value: `{stable_stats['raw_p_value']:.6f}`\n", encoding="utf-8")
    compact_files = [
        output / "factor_hypothesis_tests.csv",
        output / "test_family_summary.csv",
        output / "fdr_results.csv",
        output / "rejected_hypotheses.csv",
        output / "null_simulation_results.csv",
        output / "contract_status.csv",
        output / "multiple_testing_report.md",
    ]
    input_manifest_paths = [PROJECT_ROOT / item for item in config.get("input_manifests", [])]
    write_stage_artifact_manifest(
        project_root=PROJECT_ROOT,
        stage_id="factor_multiple_testing_v1",
        config=config,
        output_dir=output,
        output_files=compact_files,
        code_state=code_state,
        input_manifest_paths=input_manifest_paths,
        factor_catalog_id=None if input_manifest_paths else content_reference_id("factor-catalog", input_paths),
        factor_frame_id=None if input_manifest_paths else content_reference_id("factor-series", input_paths),
        start_date=min(input_dates) if input_dates else None,
        end_date=max(input_dates) if input_dates else None,
        missing_lineage_fields=config.get("missing_lineage_fields", ["universe_artifact_id", "split_manifest_id", "legacy_liquid2000_input"]),
    )
    print(contract.to_string(index=False))
    return 1 if (contract["status"] == "fail").any() else 0


if __name__ == "__main__":
    freeze_support()
    raise SystemExit(main())
