import argparse
import json
from pathlib import Path

import pandas as pd


FIELDS = ["$close", "$volume", "$amount"]


def read_instrument_ranges(path: Path) -> pd.DataFrame:
    rows = []
    if not path.exists():
        return pd.DataFrame(columns=["instrument", "start_time", "end_time"])
    with path.open("r", encoding="utf-8") as file:
        for line in file:
            parts = line.strip().split()
            if len(parts) < 3:
                continue
            rows.append({"instrument": parts[0].upper(), "start_time": parts[1], "end_time": parts[2]})
    frame = pd.DataFrame(rows)
    if frame.empty:
        return frame
    frame["start_time"] = pd.to_datetime(frame["start_time"])
    frame["end_time"] = pd.to_datetime(frame["end_time"])
    return frame


def select_sample_symbols(membership: pd.DataFrame, start_time: str, end_time: str, sample_size: int) -> list[str]:
    start = pd.Timestamp(start_time)
    end = pd.Timestamp(end_time)
    active = membership[(membership["start_time"] <= end) & (membership["end_time"] >= start)]
    return sorted(active["instrument"].unique())[:sample_size]


def validate_provider(provider_uri: Path, market: str, start_time: str, end_time: str, sample_size: int) -> tuple[dict, pd.DataFrame]:
    import qlib
    from qlib.config import C, REG_CN
    from qlib.data import D

    qlib.init(provider_uri=str(provider_uri), region=REG_CN)
    C.kernels = 1
    C.joblib_backend = "sequential"

    membership_path = provider_uri / "instruments" / f"{market}.txt"
    membership = read_instrument_ranges(membership_path)
    symbols = select_sample_symbols(membership, start_time, end_time, sample_size)
    features = D.features(symbols, FIELDS, start_time=start_time, end_time=end_time, freq="day") if symbols else pd.DataFrame()

    if isinstance(features.index, pd.MultiIndex):
        feature_rows = features.reset_index()
    else:
        feature_rows = features.copy()

    field_non_null = {field: int(features[field].notna().sum()) for field in FIELDS if field in features.columns}
    summary = {
        "provider_uri": str(provider_uri),
        "market": market,
        "membership_file": str(membership_path),
        "membership_rows": int(len(membership)),
        "membership_instruments": int(membership["instrument"].nunique()) if not membership.empty else 0,
        "start_time": start_time,
        "end_time": end_time,
        "sample_symbols": symbols,
        "feature_rows": int(len(features)),
        "field_non_null": field_non_null,
    }
    return summary, feature_rows.head(30)


def write_markdown(summary: dict, sample: pd.DataFrame, output: Path):
    output.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Provider Validation",
        "",
        f"- Provider URI: `{summary['provider_uri']}`",
        f"- Market: `{summary['market']}`",
        f"- Membership rows: `{summary['membership_rows']}`",
        f"- Membership instruments: `{summary['membership_instruments']}`",
        f"- Date range: `{summary['start_time']}` to `{summary['end_time']}`",
        f"- Sample symbols: `{', '.join(summary['sample_symbols'])}`",
        f"- Feature rows: `{summary['feature_rows']}`",
        "",
        "## Field Non-null Counts",
        "",
        "| field | non-null rows |",
        "| --- | ---: |",
    ]
    for field, count in summary["field_non_null"].items():
        lines.append(f"| {field} | {count} |")

    lines.extend(["", "## Sample Rows", ""])
    if sample.empty:
        lines.append("No sample rows.")
    else:
        display = sample.copy()
        for col in display.columns:
            if pd.api.types.is_datetime64_any_dtype(display[col]):
                display[col] = display[col].dt.strftime("%Y-%m-%d")
        lines.extend(["| " + " | ".join(map(str, display.columns)) + " |", "| " + " | ".join(["---"] * len(display.columns)) + " |"])
        for row in display.values.tolist():
            lines.append("| " + " | ".join(str(value) for value in row) + " |")

    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Validate a qlib provider and a named universe.")
    parser.add_argument("--provider-uri", required=True, help="Path to qlib provider.")
    parser.add_argument("--market", required=True, help="Instrument file name without .txt.")
    parser.add_argument("--start-time", required=True)
    parser.add_argument("--end-time", required=True)
    parser.add_argument("--output", required=True, help="Markdown validation report path.")
    parser.add_argument("--json-output", help="Optional JSON summary path.")
    parser.add_argument("--sample-size", type=int, default=5)
    args = parser.parse_args()

    summary, sample = validate_provider(
        Path(args.provider_uri),
        market=args.market,
        start_time=args.start_time,
        end_time=args.end_time,
        sample_size=args.sample_size,
    )
    write_markdown(summary, sample, Path(args.output))
    if args.json_output:
        json_path = Path(args.json_output)
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Wrote provider validation to {args.output}")


if __name__ == "__main__":
    main()
