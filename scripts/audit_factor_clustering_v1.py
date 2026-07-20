from __future__ import annotations

import argparse
from multiprocessing import freeze_support
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit factor clustering outputs.")
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/factor_clustering_v1/local_reference"))
    args = parser.parse_args()
    output = args.output_dir if args.output_dir.is_absolute() else PROJECT_ROOT / args.output_dir
    clusters = pd.read_csv(output / "factor_clusters.csv")
    representatives = pd.read_csv(output / "cluster_representatives.csv")
    checks = [
        ("every_selected_factor_has_cluster", int(clusters.cluster_id.isna().sum()), 0),
        ("every_cluster_has_representative", representatives.cluster_id.nunique(), clusters.cluster_id.nunique()),
        ("default_combination_duplicate_cluster_votes", int(representatives.cluster_id.duplicated().sum()), 0),
    ]
    contract = pd.DataFrame([{"check_name": name, "status": "pass" if observed == required else "fail", "observed_value": observed, "required_value": required, "severity": "critical", "reason": "Factor clustering output contract."} for name, observed, required in checks])
    contract.to_csv(output / "contract_status.csv", index=False, encoding="utf-8-sig")
    print(contract.to_string(index=False))
    return 1 if (contract.status == "fail").any() else 0


if __name__ == "__main__":
    freeze_support()
    raise SystemExit(main())
