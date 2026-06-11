import argparse
import csv
import json
from pathlib import Path

import pandas as pd


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
    return frame.sort_values(["instrument", "start_time", "end_time"]).reset_index(drop=True)


def read_calendar(path: Path) -> pd.DatetimeIndex:
    if not path.exists():
        return pd.DatetimeIndex([])
    values = [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return pd.DatetimeIndex(pd.to_datetime(values))


def active_count_by_day(calendar: pd.DatetimeIndex, membership: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for dt in calendar:
        active = membership[(membership["start_time"] <= dt) & (membership["end_time"] >= dt)]["instrument"].nunique()
        rows.append({"datetime": dt, "active_count": int(active)})
    return pd.DataFrame(rows)


def analyze(provider_uri: Path, market: str) -> tuple[dict, pd.DataFrame, pd.DataFrame]:
    instruments_dir = provider_uri / "instruments"
    features_dir = provider_uri / "features"
    calendar = read_calendar(provider_uri / "calendars" / "day.txt")
    lifecycle = read_instrument_ranges(instruments_dir / "all.txt")
    membership = read_instrument_ranges(instruments_dir / f"{market}.txt")
    feature_symbols = {path.name.upper() for path in features_dir.iterdir() if path.is_dir()} if features_dir.exists() else set()

    lifecycle_bounds = (
        lifecycle.groupby("instrument")
        .agg(lifecycle_start=("start_time", "min"), lifecycle_end=("end_time", "max"))
        .reset_index()
    )
    membership_with_lifecycle = membership.merge(lifecycle_bounds, on="instrument", how="left")
    membership_with_lifecycle["missing_lifecycle"] = membership_with_lifecycle["lifecycle_start"].isna()
    membership_with_lifecycle["starts_before_lifecycle"] = (
        membership_with_lifecycle["lifecycle_start"].notna()
        & (membership_with_lifecycle["start_time"] < membership_with_lifecycle["lifecycle_start"])
    )
    membership_with_lifecycle["ends_after_lifecycle"] = (
        membership_with_lifecycle["lifecycle_end"].notna()
        & (membership_with_lifecycle["end_time"] > membership_with_lifecycle["lifecycle_end"])
    )
    membership_with_lifecycle["missing_feature_dir"] = ~membership_with_lifecycle["instrument"].isin(feature_symbols)

    issue_mask = (
        membership_with_lifecycle["missing_lifecycle"]
        | membership_with_lifecycle["starts_before_lifecycle"]
        | membership_with_lifecycle["ends_after_lifecycle"]
        | membership_with_lifecycle["missing_feature_dir"]
    )
    interval_issues = membership_with_lifecycle.loc[issue_mask].copy()

    active_counts = active_count_by_day(calendar, membership)
    summary = {
        "provider_uri": str(provider_uri),
        "market": market,
        "calendar_start": str(calendar.min().date()) if len(calendar) else "",
        "calendar_end": str(calendar.max().date()) if len(calendar) else "",
        "calendar_days": int(len(calendar)),
        "lifecycle_rows": int(len(lifecycle)),
        "lifecycle_instruments": int(lifecycle["instrument"].nunique()) if not lifecycle.empty else 0,
        "membership_rows": int(len(membership)),
        "membership_instruments": int(membership["instrument"].nunique()) if not membership.empty else 0,
        "feature_instruments": int(len(feature_symbols)),
        "interval_issue_rows": int(len(interval_issues)),
        "missing_lifecycle_rows": int(membership_with_lifecycle["missing_lifecycle"].sum()),
        "starts_before_lifecycle_rows": int(membership_with_lifecycle["starts_before_lifecycle"].sum()),
        "ends_after_lifecycle_rows": int(membership_with_lifecycle["ends_after_lifecycle"].sum()),
        "missing_feature_dir_rows": int(membership_with_lifecycle["missing_feature_dir"].sum()),
        "avg_active_count": float(active_counts["active_count"].mean()) if not active_counts.empty else None,
        "min_active_count": int(active_counts["active_count"].min()) if not active_counts.empty else None,
        "max_active_count": int(active_counts["active_count"].max()) if not active_counts.empty else None,
    }
    return summary, interval_issues, active_counts


def write_csv(path: Path, rows: list[dict]):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(path: Path, summary: dict, interval_issues: pd.DataFrame, active_counts: pd.DataFrame):
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Membership Lifecycle Analysis",
        "",
        f"- Provider URI: `{summary['provider_uri']}`",
        f"- Market: `{summary['market']}`",
        f"- Calendar: `{summary['calendar_start']}` to `{summary['calendar_end']}`",
        "",
        "## Summary",
        "",
        "| metric | value |",
        "| --- | ---: |",
    ]
    for key, value in summary.items():
        if key in {"provider_uri", "market"}:
            continue
        lines.append(f"| {key} | `{value}` |")

    lines.extend(["", "## Interval Issues", ""])
    if interval_issues.empty:
        lines.append("No interval issues found.")
    else:
        display_cols = [
            "instrument",
            "start_time",
            "end_time",
            "lifecycle_start",
            "lifecycle_end",
            "missing_lifecycle",
            "starts_before_lifecycle",
            "ends_after_lifecycle",
            "missing_feature_dir",
        ]
        display = interval_issues[display_cols].head(30).copy()
        for col in ["start_time", "end_time", "lifecycle_start", "lifecycle_end"]:
            display[col] = pd.to_datetime(display[col]).dt.strftime("%Y-%m-%d")
        lines.extend(["| " + " | ".join(display.columns) + " |", "| " + " | ".join(["---"] * len(display.columns)) + " |"])
        lines.extend("| " + " | ".join(str(value) for value in row) + " |" for row in display.values.tolist())

    lines.extend(["", "## Active Count Extremes", ""])
    if active_counts.empty:
        lines.append("No calendar rows.")
    else:
        lows = active_counts.nsmallest(10, "active_count")
        highs = active_counts.nlargest(10, "active_count")
        lines.extend(["### Lowest Active Counts", "", "| datetime | active_count |", "| --- | ---: |"])
        for row in lows.itertuples(index=False):
            lines.append(f"| {row.datetime:%Y-%m-%d} | {row.active_count} |")
        lines.extend(["", "### Highest Active Counts", "", "| datetime | active_count |", "| --- | ---: |"])
        for row in highs.itertuples(index=False):
            lines.append(f"| {row.datetime:%Y-%m-%d} | {row.active_count} |")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Analyze qlib instrument membership against lifecycle and features.")
    parser.add_argument("--provider-uri", required=True, help="Path to qlib provider.")
    parser.add_argument("--market", default="csi500", help="Market instrument file name without .txt.")
    parser.add_argument("--output", required=True, help="Output markdown path.")
    parser.add_argument("--json-output", help="Optional JSON summary path.")
    parser.add_argument("--issues-csv", help="Optional interval issues CSV path.")
    parser.add_argument("--active-count-csv", help="Optional active count CSV path.")
    args = parser.parse_args()

    summary, interval_issues, active_counts = analyze(Path(args.provider_uri), args.market)
    write_markdown(Path(args.output), summary, interval_issues, active_counts)

    if args.json_output:
        json_path = Path(args.json_output)
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    if args.issues_csv:
        interval_issues.to_csv(args.issues_csv, index=False, encoding="utf-8-sig")
    if args.active_count_csv:
        active_counts.to_csv(args.active_count_csv, index=False, encoding="utf-8-sig")

    print(f"Wrote membership lifecycle analysis to {args.output}")


if __name__ == "__main__":
    main()
