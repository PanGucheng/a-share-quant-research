from __future__ import annotations

import argparse
import sys
from multiprocessing import freeze_support
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from research_validation.purged_split import leakage_audit  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Re-audit purged walk-forward runtime assignments.")
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/purged_walk_forward_v1/local_reference"))
    args = parser.parse_args()
    output = args.output_dir if args.output_dir.is_absolute() else PROJECT_ROOT / args.output_dir
    assignments = pd.read_csv(output / "runtime/date_assignments.csv", parse_dates=["datetime"])
    labels = pd.read_csv(output / "runtime/label_intervals.csv", parse_dates=["feature_time", "label_start_time", "label_end_time"])
    embargo = pd.read_csv(output / "embargoed_dates.csv", parse_dates=["datetime"])
    contract = leakage_audit({"date_assignments": assignments, "label_intervals": labels, "embargoed_dates": embargo})
    contract.to_csv(output / "leakage_audit.csv", index=False, encoding="utf-8-sig")
    contract.to_csv(output / "contract_status.csv", index=False, encoding="utf-8-sig")
    print(contract.to_string(index=False))
    return 1 if (contract["status"] == "fail").any() else 0


if __name__ == "__main__":
    freeze_support()
    raise SystemExit(main())
