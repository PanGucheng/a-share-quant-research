import argparse
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tradability.builder import choose_liquidity_source


REQUIRED_FILES = [
    "tradability_labels.csv",
    "summary.csv",
    "instrument_scores.csv",
    "date_coverage.csv",
    "reason_counts.csv",
    "tradability_report.md",
]

REQUIRED_COLUMNS = ["can_buy", "can_sell", "disabled_reason"]


def validate(output_dir: Path):
    missing = [name for name in REQUIRED_FILES if not (output_dir / name).exists()]
    if missing:
        raise FileNotFoundError(f"Missing tradability output files in {output_dir}: {missing}")
    labels = pd.read_csv(output_dir / "tradability_labels.csv")
    if labels.empty:
        raise ValueError(f"tradability_labels.csv is empty: {output_dir}")
    missing_columns = [column for column in REQUIRED_COLUMNS if column not in labels.columns]
    if missing_columns:
        raise ValueError(f"tradability_labels.csv missing required columns: {missing_columns}")
    summary = pd.read_csv(output_dir / "summary.csv")
    if summary.empty:
        raise ValueError("summary.csv is empty")
    validate_amount_fallback()
    print(f"Validated tradability outputs: {output_dir}")


def validate_amount_fallback():
    warnings = []
    frame = pd.DataFrame(
        {
            "instrument": ["SH600000"],
            "datetime": [pd.Timestamp("2021-01-04")],
            "close": [10.0],
            "volume": [1000.0],
        }
    )
    result, source = choose_liquidity_source(frame, warnings)
    if source != "close_volume":
        raise ValueError(f"Expected close_volume fallback when amount is absent, got {source}")
    if result.loc[0, "liquidity_value"] != 10000.0:
        raise ValueError("close*volume fallback produced an unexpected liquidity value")


def main():
    parser = argparse.ArgumentParser(description="Validate tradability label outputs.")
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    validate(Path(args.output_dir))


if __name__ == "__main__":
    main()
