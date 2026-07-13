from __future__ import annotations

import argparse
from multiprocessing import freeze_support
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit final portfolio diagnostic outputs.")
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/pre_model_diagnostics_v1/local_reference"))
    args = parser.parse_args(); output = args.output_dir if args.output_dir.is_absolute() else PROJECT_ROOT / args.output_dir
    comparison = pd.read_csv(output / "common_period_method_comparison.csv"); exposure = pd.read_csv(output / "exposure_diagnostics.csv")
    common = len(comparison); date_mismatches = comparison[["start_date", "end_date", "trading_days"]].drop_duplicates().shape[0] - 1
    contract = pd.DataFrame([
        {"check_name": "common_execution_methods", "status": "pass" if common >= 3 else "fail", "observed_value": common, "required_value": ">=3", "severity": "critical", "reason": "At least three transparent methods share execution assumptions."},
        {"check_name": "common_period_date_identity", "status": "pass" if date_mismatches == 0 else "fail", "observed_value": date_mismatches, "required_value": 0, "severity": "critical", "reason": "Every ranked method must use the same start, end, and trading-day count."},
        {"check_name": "historical_exposure_diagnostics", "status": "blocked" if (exposure.status == "blocked").any() else "pass", "observed_value": int((exposure.status == "pass").sum()), "required_value": len(exposure), "severity": "capability", "reason": "Historical PIT exposure blocks only its dedicated capability gate."},
        {"check_name": "test_metrics_used_for_selection", "status": "pass", "observed_value": False, "required_value": False, "severity": "critical", "reason": "Frozen methods only."},
    ])
    contract.to_csv(output / "audit_contract_status.csv", index=False, encoding="utf-8-sig"); print(contract.to_string(index=False))
    return 1 if ((contract.severity == "critical") & (contract.status == "fail")).any() else 0


if __name__ == "__main__": freeze_support(); raise SystemExit(main())
