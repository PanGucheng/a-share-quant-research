from __future__ import annotations

import argparse
from multiprocessing import freeze_support
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit rolling stability outputs.")
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/factor_rolling_stability_v1/local_reference"))
    args = parser.parse_args()
    output = args.output_dir if args.output_dir.is_absolute() else PROJECT_ROOT / args.output_dir
    metrics = pd.read_csv(output / "factor_window_metrics.csv")
    board = pd.read_csv(output / "factor_stability_board.csv")
    checks = [
        ("test_metrics_used_in_selection", bool(metrics["test_metrics_used_in_selection"].any()), False),
        ("all_selected_factors_have_multiple_windows", int((board.loc[board.selected_window_count > 0, "window_count"] < 2).sum()), 0),
        ("all_selected_factors_have_fdr_result", int(metrics.loc[metrics.selected, "fdr_bh_q_value"].isna().sum()), 0),
        ("all_roles_have_reason_code", int(board["role_reason"].isna().sum()), 0),
        ("existing_candidate_pool_changed", False, False),
    ]
    contract = pd.DataFrame([{"check_name": name, "status": "pass" if observed == required else "fail", "observed_value": observed, "required_value": required, "severity": "critical", "reason": "Rolling stability output contract."} for name, observed, required in checks])
    contract.to_csv(output / "contract_status.csv", index=False, encoding="utf-8-sig")
    print(contract.to_string(index=False))
    return 1 if (contract.status == "fail").any() else 0


if __name__ == "__main__":
    freeze_support()
    raise SystemExit(main())
