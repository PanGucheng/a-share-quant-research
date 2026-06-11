import argparse
import json
from pathlib import Path

import pandas as pd


def read_instrument_ranges(path: Path) -> pd.DataFrame:
    rows = []
    with path.open("r", encoding="utf-8") as file:
        for line in file:
            parts = line.strip().split()
            if len(parts) < 3:
                continue
            rows.append({"instrument": parts[0].upper(), "start_time": parts[1], "end_time": parts[2], "line": line.strip()})
    frame = pd.DataFrame(rows)
    if frame.empty:
        return frame
    frame["start_time"] = pd.to_datetime(frame["start_time"])
    frame["end_time"] = pd.to_datetime(frame["end_time"])
    return frame


def active_symbols(membership: pd.DataFrame, start_time: str, end_time: str) -> list[str]:
    start = pd.Timestamp(start_time)
    end = pd.Timestamp(end_time)
    active = membership[(membership["start_time"] <= end) & (membership["end_time"] >= start)]
    return sorted(active["instrument"].unique())


def create_liquidity_universe(
    provider_uri: Path,
    source_market: str,
    start_time: str,
    end_time: str,
    top_n: int,
    min_valid_days: int,
    output: Path,
) -> tuple[dict, pd.DataFrame]:
    import qlib
    from qlib.config import C, REG_CN
    from qlib.data import D

    qlib.init(provider_uri=str(provider_uri), region=REG_CN)
    C.kernels = 1
    C.joblib_backend = "sequential"

    source_path = provider_uri / "instruments" / f"{source_market}.txt"
    membership = read_instrument_ranges(source_path)
    symbols = active_symbols(membership, start_time, end_time)
    amount = D.features(symbols, ["$amount"], start_time=start_time, end_time=end_time, freq="day")

    amount_frame = amount.reset_index()
    ranking = (
        amount_frame.groupby("instrument")["$amount"]
        .agg(median_amount="median", mean_amount="mean", valid_days="count")
        .reset_index()
    )
    ranking = ranking[ranking["valid_days"] >= min_valid_days].sort_values(
        ["median_amount", "mean_amount", "instrument"], ascending=[False, False, True]
    )
    selected = set(ranking.head(top_n)["instrument"])

    output_lines = membership[membership["instrument"].isin(selected)]["line"].tolist()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(output_lines) + ("\n" if output_lines else ""), encoding="utf-8")

    selected_ranking = ranking[ranking["instrument"].isin(selected)].copy()
    summary = {
        "provider_uri": str(provider_uri),
        "source_market": source_market,
        "source_path": str(source_path),
        "start_time": start_time,
        "end_time": end_time,
        "candidate_instruments": int(len(symbols)),
        "min_valid_days": min_valid_days,
        "top_n": top_n,
        "selected_instruments": int(len(selected)),
        "output": str(output),
        "min_selected_median_amount": float(selected_ranking["median_amount"].min()) if not selected_ranking.empty else None,
        "max_selected_median_amount": float(selected_ranking["median_amount"].max()) if not selected_ranking.empty else None,
    }
    return summary, ranking


def write_markdown(summary: dict, ranking: pd.DataFrame, output: Path):
    output.parent.mkdir(parents=True, exist_ok=True)
    top = ranking.head(20).copy()
    lines = [
        "# Liquidity Universe Summary",
        "",
        f"- Provider URI: `{summary['provider_uri']}`",
        f"- Source market: `{summary['source_market']}`",
        f"- Date range: `{summary['start_time']}` to `{summary['end_time']}`",
        f"- Candidate instruments: `{summary['candidate_instruments']}`",
        f"- Minimum valid days: `{summary['min_valid_days']}`",
        f"- Top N: `{summary['top_n']}`",
        f"- Selected instruments: `{summary['selected_instruments']}`",
        f"- Output: `{summary['output']}`",
        f"- Selected median amount range: `{summary['min_selected_median_amount']}` to `{summary['max_selected_median_amount']}`",
        "",
        "## Top Ranked Instruments",
        "",
    ]
    if top.empty:
        lines.append("No ranked instruments.")
    else:
        lines.extend(["| instrument | median_amount | mean_amount | valid_days |", "| --- | ---: | ---: | ---: |"])
        for row in top.itertuples(index=False):
            lines.append(f"| {row.instrument} | {row.median_amount:.6f} | {row.mean_amount:.6f} | {row.valid_days} |")
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Create a liquidity-filtered qlib universe from a source universe.")
    parser.add_argument("--provider-uri", required=True)
    parser.add_argument("--source-market", required=True)
    parser.add_argument("--start-time", required=True)
    parser.add_argument("--end-time", required=True)
    parser.add_argument("--top-n", type=int, default=2000)
    parser.add_argument("--min-valid-days", type=int, default=180)
    parser.add_argument("--output", required=True)
    parser.add_argument("--summary-output", required=True)
    parser.add_argument("--ranking-output")
    parser.add_argument("--json-output")
    args = parser.parse_args()

    summary, ranking = create_liquidity_universe(
        provider_uri=Path(args.provider_uri),
        source_market=args.source_market,
        start_time=args.start_time,
        end_time=args.end_time,
        top_n=args.top_n,
        min_valid_days=args.min_valid_days,
        output=Path(args.output),
    )
    write_markdown(summary, ranking, Path(args.summary_output))
    if args.ranking_output:
        ranking.to_csv(args.ranking_output, index=False, encoding="utf-8-sig")
    if args.json_output:
        json_path = Path(args.json_output)
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Wrote liquidity universe to {args.output}")


if __name__ == "__main__":
    main()
