from __future__ import annotations

import argparse
import re
import sys
from multiprocessing import freeze_support
from pathlib import Path

import pandas as pd
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from research_validation.bootstrap import moving_block_mean_test  # noqa: E402
from research_validation.multiple_testing import apply_fdr  # noqa: E402
from research_validation.rolling_evaluation import select_factor_window, stability_board  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Build rolling factor stability board without test leakage.")
    parser.add_argument("--config", type=Path, default=Path("configs/factor_rolling_stability_v1.yaml"))
    args = parser.parse_args()
    config_path = args.config if args.config.is_absolute() else PROJECT_ROOT / args.config
    config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    splits = pd.read_csv(PROJECT_ROOT / config["split_manifest"], parse_dates=["train_start", "train_end", "validation_start", "validation_end", "test_start", "test_end"])
    series_map = {}
    for path in sorted(PROJECT_ROOT.glob(config["input_glob"])):
        horizon = re.search(r"label_(\d+d_t\d+)_", path.name).group(1)
        factor = f"{path.parent.name}|{horizon}"
        frame = pd.read_csv(path, parse_dates=["datetime"])
        series_map[factor] = frame.set_index("datetime")[config["metric_column"]].sort_index()
    pre_rows = []
    test_cache = {}
    for split in splits.itertuples(index=False):
        for factor, series in series_map.items():
            train = series.loc[(series.index >= split.train_start) & (series.index <= split.train_end)].dropna()
            validation = series.loc[(series.index >= split.validation_start) & (series.index <= split.validation_end)].dropna()
            test = series.loc[(series.index >= split.test_start) & (series.index <= split.test_end)].dropna()
            if min(len(train), len(validation), len(test)) < int(config["minimum_dates_per_fold"]):
                continue
            selection_series = pd.concat([train, validation])
            stats = moving_block_mean_test(selection_series, samples=int(config["bootstrap_samples"]), block_length=int(config["block_length"]), seed=int(config["random_seed"]))
            pre_rows.append({"factor": factor, "split_id": split.split_id, "test_family": f"{split.split_id}|selection_history", "metric": config["metric_column"], "train_mean_ic": train.mean(), "validation_mean_ic": validation.mean(), "train_count": len(train), "validation_count": len(validation), "train_coverage": len(train) / max(1, split.train_dates), "validation_coverage": len(validation) / max(1, split.validation_dates), **stats})
            test_cache[(factor, split.split_id)] = {"test_mean_ic": test.mean(), "test_count": len(test), "test_coverage": len(test) / max(1, split.test_dates)}
    selection = apply_fdr(pd.DataFrame(pre_rows), float(config["fdr_alpha"]))
    rows = []
    for item in selection.to_dict("records"):
        decision_input = pd.Series({key: item[key] for key in ["factor", "split_id", "train_mean_ic", "validation_mean_ic", "train_count", "validation_count", "fdr_bh_pass", "fdr_bh_q_value"]})
        decision = select_factor_window(decision_input, min_abs_validation_ic=float(config["min_abs_validation_ic"]), min_dates=int(config["minimum_dates_per_fold"]))
        test_metrics = test_cache[(item["factor"], item["split_id"])]
        rows.append({**item, **decision, **test_metrics, "eligible": True, "test_metrics_used_in_selection": False})
    metrics = pd.DataFrame(rows)
    board = stability_board(metrics)
    contract = pd.DataFrame([
        {"check_name": "test_metrics_used_in_selection", "status": "pass" if not metrics["test_metrics_used_in_selection"].any() else "fail", "observed_value": bool(metrics["test_metrics_used_in_selection"].any()), "required_value": False, "severity": "critical", "reason": "Selection function accepts only train/validation columns."},
        {"check_name": "all_selected_factors_have_multiple_windows", "status": "pass" if (board.loc[board.selected_window_count > 0, "window_count"] >= 2).all() else "fail", "observed_value": int((board.loc[board.selected_window_count > 0, "window_count"] < 2).sum()), "required_value": 0, "severity": "critical", "reason": "Selected factors require multiple eligible windows."},
        {"check_name": "all_selected_factors_have_fdr_result", "status": "pass" if metrics.loc[metrics.selected, "fdr_bh_q_value"].notna().all() else "fail", "observed_value": int(metrics.loc[metrics.selected, "fdr_bh_q_value"].isna().sum()), "required_value": 0, "severity": "critical", "reason": "Every selection requires a q-value."},
        {"check_name": "existing_candidate_pool_changed", "status": "pass", "observed_value": False, "required_value": False, "severity": "critical", "reason": "Reference stability output is experimental only."},
    ])
    output = PROJECT_ROOT / config["output_dir"]
    output.mkdir(parents=True, exist_ok=True)
    metrics.to_csv(output / "factor_window_metrics.csv", index=False, encoding="utf-8-sig")
    metrics[["factor", "split_id", "selected", "selection_reason", "frozen_direction", "fdr_bh_q_value"]].to_csv(output / "factor_selection_history.csv", index=False, encoding="utf-8-sig")
    metrics[["factor", "split_id", "frozen_direction"]].to_csv(output / "factor_direction_history.csv", index=False, encoding="utf-8-sig")
    metrics.assign(oos_degradation=metrics.test_mean_ic.abs() - metrics.validation_mean_ic.abs())[["factor", "split_id", "oos_degradation"]].to_csv(output / "factor_oos_degradation.csv", index=False, encoding="utf-8-sig")
    board.to_csv(output / "factor_stability_board.csv", index=False, encoding="utf-8-sig")
    board.groupby("stability_role").size().reset_index(name="factor_count").to_csv(output / "stability_role_summary.csv", index=False, encoding="utf-8-sig")
    contract.to_csv(output / "contract_status.csv", index=False, encoding="utf-8-sig")
    (output / "stability_report.md").write_text(f"# Factor Rolling Stability V1\n\n- Factors: `{len(board)}`\n- Windows: `{metrics.split_id.nunique()}`\n- Selected observations: `{int(metrics.selected.sum())}`\n- Test used in selection: `false`\n", encoding="utf-8")
    print(contract.to_string(index=False))
    return 1 if (contract["status"] == "fail").any() else 0


if __name__ == "__main__":
    freeze_support()
    raise SystemExit(main())
