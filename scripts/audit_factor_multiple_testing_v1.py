from __future__ import annotations

import argparse
from multiprocessing import freeze_support
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit factor multiple-testing outputs.")
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/factor_multiple_testing_v1/local_reference"))
    args = parser.parse_args()
    output = args.output_dir if args.output_dir.is_absolute() else PROJECT_ROOT / args.output_dir
    results = pd.read_csv(output / "fdr_results.csv")
    nulls = pd.read_csv(output / "null_simulation_results.csv")
    checks = [
        ("all_selected_factors_have_q_value", bool(results["fdr_bh_q_value"].notna().all()), True),
        ("missing_test_family_count", int(results["test_family"].isna().sum()), 0),
        ("nan_p_value_promoted_count", int((results["raw_p_value"].isna() & results["fdr_bh_pass"]).sum()), 0),
        ("null_simulation_false_discovery_rate", float(nulls["fdr_bh_pass"].mean()), "<=0.05"),
    ]
    rows = []
    for name, observed, required in checks:
        passed = observed <= 0.05 if name == "null_simulation_false_discovery_rate" else observed == required
        rows.append({"check_name": name, "status": "pass" if passed else "fail", "observed_value": observed, "required_value": required, "severity": "critical", "reason": "Multiple-testing output audit."})
    contract = pd.DataFrame(rows)
    contract.to_csv(output / "contract_status.csv", index=False, encoding="utf-8-sig")
    print(contract.to_string(index=False))
    return 1 if (contract["status"] == "fail").any() else 0


if __name__ == "__main__":
    freeze_support()
    raise SystemExit(main())
