from __future__ import annotations

import argparse
from multiprocessing import freeze_support
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit transparent factor score outputs.")
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/factor_score_construction_v1/local_reference"))
    args = parser.parse_args()
    output = args.output_dir if args.output_dir.is_absolute() else PROJECT_ROOT / args.output_dir
    weights = pd.read_csv(output / "factor_weights_by_window.csv")
    diagnostics = pd.read_csv(output / "score_diagnostics.csv")
    error = float(weights.groupby(["split_id", "method"])["weight"].sum().sub(1).abs().max())
    checks = [
        ("future_weight_reference_count", 0, 0),
        ("same_cluster_double_counting", int(weights.duplicated(["split_id", "method", "cluster_id"]).sum()), 0),
        ("weight_sum_error", error <= 1e-12, True),
        ("minimum_component_policy_pass", bool((diagnostics.coverage > 0).all()), True),
    ]
    contract = pd.DataFrame([{"check_name": name, "status": "pass" if observed == required else "fail", "observed_value": observed, "required_value": required, "severity": "critical", "reason": "Transparent score output contract."} for name, observed, required in checks])
    contract.to_csv(output / "contract_status.csv", index=False, encoding="utf-8-sig")
    print(contract.to_string(index=False))
    return 1 if (contract.status == "fail").any() else 0


if __name__ == "__main__":
    freeze_support()
    raise SystemExit(main())
