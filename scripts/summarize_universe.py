import argparse
import json
from collections import Counter
from pathlib import Path

import pandas as pd


def read_instrument_ranges(path: Path) -> pd.DataFrame:
    rows = []
    if not path.exists():
        return pd.DataFrame(columns=["instrument", "start_time", "end_time"])

    with path.open("r", encoding="utf-8") as file:
        for line in file:
            parts = line.strip().split()
            if len(parts) < 1:
                continue
            instrument = parts[0].upper()
            start_time = parts[1] if len(parts) >= 2 else None
            end_time = parts[2] if len(parts) >= 3 else None
            rows.append({"instrument": instrument, "start_time": start_time, "end_time": end_time})

    frame = pd.DataFrame(rows)
    if frame.empty:
        return frame
    frame["start_time"] = pd.to_datetime(frame["start_time"], errors="coerce")
    frame["end_time"] = pd.to_datetime(frame["end_time"], errors="coerce")
    return frame.sort_values(["instrument", "start_time", "end_time"]).reset_index(drop=True)


def prefix_for(instrument: str) -> str:
    for prefix in ("SH", "SZ", "BJ"):
        if instrument.startswith(prefix):
            return prefix
    return "OTHER"


def summarize_file(path: Path, feature_symbols: set[str]) -> dict:
    frame = read_instrument_ranges(path)
    if frame.empty:
        return {
            "file": path.name,
            "rows": 0,
            "unique_instruments": 0,
            "prefix_counts": {},
            "feature_missing_instruments": 0,
            "start_time": "",
            "end_time": "",
        }

    symbols = sorted(frame["instrument"].unique())
    prefix_counts = Counter(prefix_for(symbol) for symbol in symbols)
    missing_features = [symbol for symbol in symbols if symbol not in feature_symbols]

    start_time = frame["start_time"].min()
    end_time = frame["end_time"].max()
    return {
        "file": path.name,
        "rows": int(len(frame)),
        "unique_instruments": int(len(symbols)),
        "prefix_counts": dict(sorted(prefix_counts.items())),
        "feature_missing_instruments": int(len(missing_features)),
        "start_time": start_time.strftime("%Y-%m-%d") if pd.notna(start_time) else "",
        "end_time": end_time.strftime("%Y-%m-%d") if pd.notna(end_time) else "",
    }


def collect_summary(provider_uri: Path) -> dict:
    instruments_dir = provider_uri / "instruments"
    features_dir = provider_uri / "features"
    feature_symbols = {path.name.upper() for path in features_dir.iterdir() if path.is_dir()} if features_dir.exists() else set()
    instrument_files = sorted(instruments_dir.glob("*.txt")) if instruments_dir.exists() else []

    files = [summarize_file(path, feature_symbols) for path in instrument_files]
    feature_prefix_counts = Counter(prefix_for(symbol) for symbol in feature_symbols)
    return {
        "provider_uri": str(provider_uri),
        "feature_instruments": int(len(feature_symbols)),
        "feature_prefix_counts": dict(sorted(feature_prefix_counts.items())),
        "instrument_files": files,
    }


def format_prefix_counts(counts: dict) -> str:
    if not counts:
        return ""
    return ", ".join(f"{key}: {value}" for key, value in counts.items())


def write_markdown(summary: dict, output: Path):
    output.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Universe Summary",
        "",
        f"- Provider URI: `{summary['provider_uri']}`",
        f"- Feature instruments: `{summary['feature_instruments']}`",
        f"- Feature prefix counts: `{format_prefix_counts(summary['feature_prefix_counts'])}`",
        "",
        "## Instrument Files",
        "",
        "| file | rows | unique instruments | prefixes | missing feature dirs | start | end |",
        "| --- | ---: | ---: | --- | ---: | --- | --- |",
    ]
    for item in summary["instrument_files"]:
        lines.append(
            "| {file} | {rows} | {unique_instruments} | {prefixes} | {missing} | {start} | {end} |".format(
                file=item["file"],
                rows=item["rows"],
                unique_instruments=item["unique_instruments"],
                prefixes=format_prefix_counts(item["prefix_counts"]),
                missing=item["feature_missing_instruments"],
                start=item["start_time"],
                end=item["end_time"],
            )
        )

    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Summarize qlib universe and market instrument files.")
    parser.add_argument("--provider-uri", required=True, help="Path to qlib data provider directory.")
    parser.add_argument("--output", required=True, help="Output markdown report path.")
    parser.add_argument("--json-output", help="Optional output JSON path.")
    args = parser.parse_args()

    summary = collect_summary(Path(args.provider_uri))
    write_markdown(summary, Path(args.output))
    if args.json_output:
        json_path = Path(args.json_output)
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Wrote universe summary to {args.output}")


if __name__ == "__main__":
    main()
