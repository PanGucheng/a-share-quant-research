from __future__ import annotations

import argparse
import sys
from multiprocessing import freeze_support
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from universes.universe_audit import audit_universe  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Re-audit point-in-time universe outputs.")
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/point_in_time_universe_v1/local_smoke"))
    args = parser.parse_args()
    output = args.output_dir if args.output_dir.is_absolute() else PROJECT_ROOT / args.output_dir
    snapshots = pd.read_csv(output / "universe_membership_snapshots.csv", parse_dates=["selection_date", "effective_date", "max_source_date"])
    metrics = pd.read_csv(output / "universe_selection_metrics.csv", parse_dates=["selection_date", "effective_date", "max_source_date"])
    intervals = pd.read_csv(output / "universe_intervals.csv", parse_dates=["start_date", "end_date", "selection_date", "effective_date"])
    prior = pd.read_csv(output / "contract_status.csv")
    mutation_row = prior.loc[prior["check_name"] == "historical_membership_mutation_count", "observed_value"]
    mutation_count = int(float(mutation_row.iloc[0])) if not mutation_row.empty else -1
    contract = audit_universe(snapshots, metrics, intervals, output / "qlib_instruments.txt", mutation_count)
    contract.to_csv(output / "contract_status.csv", index=False, encoding="utf-8-sig")
    contract.to_csv(output / "point_in_time_audit.csv", index=False, encoding="utf-8-sig")
    print(contract.to_string(index=False))
    return 1 if (contract["status"] == "fail").any() else 0


if __name__ == "__main__":
    freeze_support()
    raise SystemExit(main())
