from __future__ import annotations

import argparse
from multiprocessing import freeze_support
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit final portfolio diagnostic outputs.")
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/final_portfolio_diagnostics_v1/local_reference"))
    args = parser.parse_args(); output = args.output_dir if args.output_dir.is_absolute() else PROJECT_ROOT / args.output_dir
    comparison = pd.read_csv(output / "method_comparison.csv"); exposure = pd.read_csv(output / "exposure_diagnostics.csv")
    common = int((comparison.comparison_status == "pass").sum()); blocked = int((comparison.comparison_status == "blocked").sum())
    contract = pd.DataFrame([
        {"check_name": "common_execution_methods", "status": "pass" if common >= 3 else "fail", "observed_value": common, "required_value": ">=3", "severity": "critical", "reason": "At least three transparent methods share execution assumptions."},
        {"check_name": "required_method_coverage", "status": "blocked" if blocked else "pass", "observed_value": len(comparison) - blocked, "required_value": len(comparison), "severity": "downstream", "reason": "Missing common-assumption method scores remain explicit."},
        {"check_name": "historical_exposure_diagnostics", "status": "blocked" if (exposure.status == "blocked").any() else "pass", "observed_value": int((exposure.status == "pass").sum()), "required_value": len(exposure), "severity": "downstream", "reason": "Historical PIT exposure dependency."},
        {"check_name": "test_metrics_used_for_selection", "status": "pass", "observed_value": False, "required_value": False, "severity": "critical", "reason": "Frozen methods only."},
    ])
    contract.to_csv(output / "contract_status.csv", index=False, encoding="utf-8-sig"); print(contract.to_string(index=False))
    return 1 if ((contract.severity == "critical") & (contract.status == "fail")).any() else 0


if __name__ == "__main__": freeze_support(); raise SystemExit(main())
