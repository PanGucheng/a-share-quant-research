import argparse
import json
from pathlib import Path

import pandas as pd


FIELDS = ["$open", "$high", "$low", "$close", "$volume", "$amount", "$vwap", "$factor"]


def read_memberships(provider_uri: Path, instrument: str) -> dict[str, list[dict]]:
    instrument = instrument.upper()
    result: dict[str, list[dict]] = {}
    instruments_dir = provider_uri / "instruments"
    if not instruments_dir.exists():
        return result

    for path in sorted(instruments_dir.glob("*.txt")):
        rows = []
        with path.open("r", encoding="utf-8") as file:
            for line in file:
                parts = line.strip().split()
                if len(parts) >= 3 and parts[0].upper() == instrument:
                    rows.append({"start_time": parts[1], "end_time": parts[2]})
        if rows:
            result[path.stem] = rows
    return result


def inspect_instrument(
    provider_uri: Path,
    instrument: str,
    start_time: str,
    end_time: str,
) -> tuple[dict, pd.DataFrame]:
    import qlib
    from qlib.config import C, REG_CN
    from qlib.data import D

    qlib.init(provider_uri=str(provider_uri), region=REG_CN)
    C.kernels = 1
    C.joblib_backend = "sequential"

    data = D.features([instrument], FIELDS, start_time=start_time, end_time=end_time, freq="day").reset_index()
    data = data.sort_values("datetime")
    data["amount_per_volume_x10"] = data["$amount"] / data["$volume"] * 10
    data["vwap_diff"] = data["$vwap"] - data["amount_per_volume_x10"]
    data["daily_return"] = data["$close"].pct_change(fill_method=None)

    amount = data["$amount"].dropna()
    volume = data["$volume"].dropna()
    summary = {
        "provider_uri": str(provider_uri),
        "instrument": instrument,
        "start_time": start_time,
        "end_time": end_time,
        "rows": int(len(data)),
        "amount_non_null": int(amount.count()),
        "amount_min": float(amount.min()) if not amount.empty else None,
        "amount_median": float(amount.median()) if not amount.empty else None,
        "amount_mean": float(amount.mean()) if not amount.empty else None,
        "amount_max": float(amount.max()) if not amount.empty else None,
        "volume_median": float(volume.median()) if not volume.empty else None,
        "max_abs_daily_return": float(data["daily_return"].abs().max()) if not data.empty else None,
        "max_abs_vwap_diff": float(data["vwap_diff"].abs().max()) if not data.empty else None,
        "memberships": read_memberships(provider_uri, instrument),
    }
    return summary, data


def write_markdown(summary: dict, data: pd.DataFrame, output: Path):
    output.parent.mkdir(parents=True, exist_ok=True)
    top_amount = data.nlargest(20, "$amount")[
        ["datetime", "$open", "$high", "$low", "$close", "$volume", "$amount", "$vwap", "daily_return"]
    ].copy()
    if not top_amount.empty:
        top_amount["datetime"] = pd.to_datetime(top_amount["datetime"]).dt.strftime("%Y-%m-%d")

    lines = [
        "# Instrument History Inspection",
        "",
        f"- Provider URI: `{summary['provider_uri']}`",
        f"- Instrument: `{summary['instrument']}`",
        f"- Date range: `{summary['start_time']}` to `{summary['end_time']}`",
        f"- Rows: `{summary['rows']}`",
        f"- Amount non-null rows: `{summary['amount_non_null']}`",
        f"- Amount median: `{summary['amount_median']}`",
        f"- Amount mean: `{summary['amount_mean']}`",
        f"- Amount max: `{summary['amount_max']}`",
        f"- Volume median: `{summary['volume_median']}`",
        f"- Max absolute daily return: `{summary['max_abs_daily_return']}`",
        f"- Max absolute vwap diff: `{summary['max_abs_vwap_diff']}`",
        "",
        "## Memberships",
        "",
    ]
    if not summary["memberships"]:
        lines.append("No membership rows found.")
    else:
        lines.extend(["| market | start | end |", "| --- | --- | --- |"])
        for market, rows in summary["memberships"].items():
            for row in rows:
                lines.append(f"| {market} | {row['start_time']} | {row['end_time']} |")

    lines.extend(["", "## Top Amount Days", ""])
    if top_amount.empty:
        lines.append("No amount rows.")
    else:
        lines.extend(["| " + " | ".join(top_amount.columns) + " |", "| " + " | ".join(["---"] * len(top_amount.columns)) + " |"])
        for row in top_amount.values.tolist():
            lines.append("| " + " | ".join(str(value) for value in row) + " |")

    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Inspect one instrument's qlib history and memberships.")
    parser.add_argument("--provider-uri", required=True)
    parser.add_argument("--instrument", required=True)
    parser.add_argument("--start-time", required=True)
    parser.add_argument("--end-time", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--csv-output")
    parser.add_argument("--json-output")
    args = parser.parse_args()

    summary, data = inspect_instrument(Path(args.provider_uri), args.instrument.upper(), args.start_time, args.end_time)
    write_markdown(summary, data, Path(args.output))
    if args.csv_output:
        data.to_csv(args.csv_output, index=False, encoding="utf-8-sig")
    if args.json_output:
        json_path = Path(args.json_output)
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Wrote instrument inspection to {args.output}")


if __name__ == "__main__":
    main()
