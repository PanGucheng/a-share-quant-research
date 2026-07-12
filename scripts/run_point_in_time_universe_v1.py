from __future__ import annotations

import argparse
import json
import sys
from multiprocessing import freeze_support
from pathlib import Path

import pandas as pd
import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from factor_research.context.universe import load_instrument_intervals  # noqa: E402
from universes.interval_writer import snapshots_to_intervals, write_qlib_instruments  # noqa: E402
from universes.point_in_time_universe import build_point_in_time_universe, monthly_selection_dates  # noqa: E402
from universes.universe_audit import audit_universe  # noqa: E402


def resolve(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else PROJECT_ROOT / path


def markdown_table(frame: pd.DataFrame) -> str:
    rendered = frame.fillna("").astype(str)
    columns = list(rendered.columns)
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join("---" for _ in columns) + " |"]
    for row in rendered.itertuples(index=False, name=None):
        lines.append("| " + " | ".join(str(value).replace("|", "\\|") for value in row) + " |")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a point-in-time rolling liquidity universe.")
    parser.add_argument("--config", type=Path, default=Path("configs/point_in_time_universe_smoke_v1.yaml"))
    args = parser.parse_args()
    config = yaml.safe_load(resolve(args.config).read_text(encoding="utf-8")) or {}
    output = resolve(config["output_dir"])
    output.mkdir(parents=True, exist_ok=True)

    import qlib
    from qlib.config import C, REG_CN
    from qlib.data import D

    qlib.init(provider_uri=str(resolve(config["provider_uri"])), region=REG_CN)
    C.kernels = 1
    C.joblib_backend = "sequential"
    calendar_end = (pd.Timestamp(config["end_date"]) + pd.Timedelta(days=10)).strftime("%Y-%m-%d")
    full_calendar = pd.DatetimeIndex(D.calendar(start_time="2000-01-01", end_time=calendar_end, freq="day"))
    selections = monthly_selection_dates(full_calendar, config["start_date"], config["end_date"])
    end_date = pd.Timestamp(config["end_date"])
    selections = pd.DatetimeIndex(
        [date for date in selections if len(full_calendar[(full_calendar > date) & (full_calendar <= end_date)]) > 0]
    )
    if selections.empty:
        raise ValueError("no selection date has an effective trading date inside the configured range")
    first_position = full_calendar.searchsorted(selections[0])
    fetch_start = full_calendar[max(0, first_position - int(config["lookback_trading_days"]) + 1)]
    source = load_instrument_intervals(resolve(config["source_intervals"])).rename(columns={"start": "start", "end": "end"})
    symbols = sorted(source.loc[(source["start"] <= selections[-1]) & (source["end"] >= fetch_start), "instrument"].unique())
    raw = D.features(symbols, ["$amount"], start_time=str(fetch_start.date()), end_time=str(selections[-1].date()), freq="day").reset_index()
    amount = raw.rename(columns={"$amount": "amount"})
    snapshots, metrics, changes = build_point_in_time_universe(
        amount, source, full_calendar, selections,
        lookback_days=int(config["lookback_trading_days"]),
        min_valid_days=int(config["minimum_valid_days"]),
        min_listing_days=int(config["minimum_listing_trading_days"]),
        top_n=int(config["top_n"]),
    )
    first_snapshot, _, _ = build_point_in_time_universe(
        amount.loc[amount["datetime"] <= selections[0]], source, full_calendar, selections[:1],
        lookback_days=int(config["lookback_trading_days"]),
        min_valid_days=int(config["minimum_valid_days"]),
        min_listing_days=int(config["minimum_listing_trading_days"]),
        top_n=int(config["top_n"]),
    )
    expected_first = set(snapshots.loc[snapshots["selection_date"] == selections[0], "instrument"])
    truncated_first = set(first_snapshot["instrument"])
    historical_mutation_count = len(expected_first.symmetric_difference(truncated_first))
    final_trading_date = full_calendar[full_calendar <= pd.Timestamp(config["end_date"])][-1]
    intervals = snapshots_to_intervals(snapshots, full_calendar, final_trading_date)
    qlib_file = output / "qlib_instruments.txt"
    write_qlib_instruments(intervals, qlib_file)
    contract = audit_universe(snapshots, metrics, intervals, qlib_file, historical_mutation_count)

    snapshots.to_csv(output / "universe_membership_snapshots.csv", index=False, encoding="utf-8-sig")
    metrics.to_csv(output / "universe_selection_metrics.csv", index=False, encoding="utf-8-sig")
    intervals.to_csv(output / "universe_intervals.csv", index=False, encoding="utf-8-sig")
    changes.to_csv(output / "universe_change_log.csv", index=False, encoding="utf-8-sig")
    contract.to_csv(output / "point_in_time_audit.csv", index=False, encoding="utf-8-sig")
    contract.to_csv(output / "contract_status.csv", index=False, encoding="utf-8-sig")
    (output / "resolved_config.json").write_text(json.dumps(config, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    report = ["# Point-In-Time Universe V1", "", f"- Profile: `{config['profile']}`", f"- Selection months: `{len(selections)}`", f"- Snapshot rows: `{len(snapshots)}`", f"- Interval rows: `{len(intervals)}`", "", markdown_table(contract), ""]
    (output / "universe_report.md").write_text("\n".join(report), encoding="utf-8")
    print(contract.to_string(index=False))
    return 1 if (contract["status"] == "fail").any() else 0


if __name__ == "__main__":
    freeze_support()
    raise SystemExit(main())
