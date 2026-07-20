from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description="Rebuild compact PIT exposure coverage from collected snapshots.")
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/external_exposure_data_v1/current"))
    args = parser.parse_args(); output = args.output_dir if args.output_dir.is_absolute() else PROJECT_ROOT / args.output_dir
    fields = pd.read_parquet(output / "point_in_time_field_table.parquet")
    coverage = fields.groupby("field_name").agg(rows=("instrument", "size"), instruments=("instrument", "nunique")).reset_index() if not fields.empty else pd.DataFrame(columns=["field_name", "rows", "instruments"])
    coverage.to_csv(output / "field_coverage.csv", index=False, encoding="utf-8-sig")
    print(f"Wrote {len(coverage)} field coverage rows."); return 0


if __name__ == "__main__": raise SystemExit(main())
