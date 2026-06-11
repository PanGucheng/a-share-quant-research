from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

import qlib
from qlib.config import C
from qlib.data import D

from data_quality.report import build_markdown_report, write_csv_outputs, write_markdown_report
from data_quality.rules import (
    FIELDS,
    Thresholds,
    abnormal_dates,
    abnormal_instruments,
    aggregate_rule_counts,
    date_coverage,
    field_missing_rate,
    instrument_availability,
    normalize_feature_frame,
    row_issue_frame,
    select_category,
)


def load_config(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        config = yaml.safe_load(file)
    if not isinstance(config, dict):
        raise ValueError(f"Invalid config file: {path}")
    return config


def apply_overrides(config: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    diagnosis = config.setdefault("diagnosis", {})
    qlib_conf = config.setdefault("qlib", {})
    thresholds = config.setdefault("thresholds", {})

    for key in ["market", "start_time", "end_time", "output_dir"]:
        value = getattr(args, key)
        if value is not None:
            diagnosis[key] = value
    if args.provider_uri is not None:
        qlib_conf["provider_uri"] = args.provider_uri
    if args.region is not None:
        qlib_conf["region"] = args.region
    if args.long_zero_run_days is not None:
        thresholds["long_zero_run_days"] = args.long_zero_run_days
    if args.long_gap_days is not None:
        thresholds["long_gap_days"] = args.long_gap_days
    return config


def threshold_from_config(config: dict[str, Any]) -> Thresholds:
    values = config.get("thresholds", {})
    return Thresholds(
        max_abs_daily_return=float(values.get("max_abs_daily_return", Thresholds.max_abs_daily_return)),
        max_abs_close_jump=float(values.get("max_abs_close_jump", Thresholds.max_abs_close_jump)),
        suspicious_adjusted_return=float(
            values.get("suspicious_adjusted_return", Thresholds.suspicious_adjusted_return)
        ),
        long_zero_run_days=int(values.get("long_zero_run_days", Thresholds.long_zero_run_days)),
        long_gap_days=int(values.get("long_gap_days", Thresholds.long_gap_days)),
        long_missing_ratio=float(values.get("long_missing_ratio", Thresholds.long_missing_ratio)),
    )


def init_qlib(config: dict[str, Any]) -> None:
    qlib_conf = config["qlib"]
    qlib.init(provider_uri=qlib_conf["provider_uri"], region=qlib_conf.get("region", "cn"))
    C.kernels = 1
    C.joblib_backend = "sequential"


def read_instrument_ranges(path: Path) -> pd.DataFrame:
    rows = []
    if not path.exists():
        return pd.DataFrame(columns=["instrument", "start_time", "end_time"])
    rows = []
    with path.open("r", encoding="utf-8") as file:
        for line in file:
            parts = line.strip().split()
            if len(parts) < 3:
                continue
            rows.append({"instrument": parts[0], "start_time": parts[1], "end_time": parts[2]})
    frame = pd.DataFrame(rows)
    if frame.empty:
        return pd.DataFrame(columns=["instrument", "start_time", "end_time"])
    frame["instrument"] = frame["instrument"].astype(str).str.upper()
    frame["start_time"] = pd.to_datetime(frame["start_time"])
    frame["end_time"] = pd.to_datetime(frame["end_time"])
    return frame


def load_membership(config: dict[str, Any]) -> pd.DataFrame | None:
    qlib_conf = config["qlib"]
    diagnosis = config["diagnosis"]
    market = diagnosis["market"]
    provider_uri = Path(qlib_conf["provider_uri"])
    membership = read_instrument_ranges(provider_uri / "instruments" / f"{market}.txt")
    if membership.empty:
        config["_membership_diagnostics"] = {"membership_rows": 0, "membership_clipped_rows": 0}
        return None

    lifecycle = read_instrument_ranges(provider_uri / "instruments" / "all.txt")
    clipped_rows = 0
    if not lifecycle.empty:
        bounds = (
            lifecycle.groupby("instrument")
            .agg(lifecycle_start=("start_time", "min"), lifecycle_end=("end_time", "max"))
            .reset_index()
        )
        membership = membership.merge(bounds, on="instrument", how="left")
        has_lifecycle = membership["lifecycle_start"].notna()
        clipped_start = membership["start_time"].copy()
        clipped_end = membership["end_time"].copy()
        clipped_start.loc[has_lifecycle] = clipped_start.loc[has_lifecycle].combine(
            membership.loc[has_lifecycle, "lifecycle_start"], max
        )
        clipped_end.loc[has_lifecycle] = clipped_end.loc[has_lifecycle].combine(
            membership.loc[has_lifecycle, "lifecycle_end"], min
        )
        clipped_rows = int(
            (has_lifecycle & ((clipped_start != membership["start_time"]) | (clipped_end != membership["end_time"]))).sum()
        )
        membership["start_time"] = clipped_start
        membership["end_time"] = clipped_end
        membership = membership.loc[membership["start_time"] <= membership["end_time"], ["instrument", "start_time", "end_time"]]

    config["_membership_diagnostics"] = {"membership_rows": len(membership), "membership_clipped_rows": clipped_rows}
    return membership


def load_qlib_features(config: dict[str, Any]) -> tuple[pd.DataFrame, pd.DatetimeIndex, int]:
    diagnosis = config["diagnosis"]
    freq = config.get("qlib", {}).get("freq", "day")
    market = diagnosis["market"]
    start_time = diagnosis["start_time"]
    end_time = diagnosis["end_time"]
    fields = [f"${field}" for field in FIELDS]

    instruments = D.instruments(market)
    calendar = pd.DatetimeIndex(D.calendar(start_time=start_time, end_time=end_time, freq=freq))
    raw = D.features(instruments, fields, start_time=start_time, end_time=end_time, freq=freq)
    frame = normalize_feature_frame(raw)
    instrument_count = frame["instrument"].nunique()
    return frame, calendar, instrument_count


def build_overview(
    config: dict[str, Any],
    frame: pd.DataFrame,
    calendar: pd.DatetimeIndex,
    instrument_count: int,
    membership: pd.DataFrame | None,
    issues: pd.DataFrame,
    availability: pd.DataFrame,
    coverage: pd.DataFrame,
) -> pd.DataFrame:
    active_counts = coverage["expected_instrument_count"].dropna()
    membership_diagnostics = config.get("_membership_diagnostics", {})
    metrics = [
        ("market", config["diagnosis"]["market"]),
        ("start_time", config["diagnosis"]["start_time"]),
        ("end_time", config["diagnosis"]["end_time"]),
        ("provider_uri", config["qlib"]["provider_uri"]),
        ("instrument_count", instrument_count),
        ("membership_rows", 0 if membership is None else len(membership)),
        ("membership_clipped_rows", membership_diagnostics.get("membership_clipped_rows", 0)),
        ("dynamic_membership_enabled", membership is not None),
        ("calendar_trade_days", len(calendar)),
        ("raw_rows", len(frame)),
        ("total_issue_rows", len(issues)),
        ("avg_availability_score", availability["availability_score"].mean()),
        ("min_availability_score", availability["availability_score"].min()),
        ("avg_expected_instruments_per_day", active_counts.mean() if not active_counts.empty else instrument_count),
        ("min_expected_instruments_per_day", active_counts.min() if not active_counts.empty else instrument_count),
        ("max_expected_instruments_per_day", active_counts.max() if not active_counts.empty else instrument_count),
        ("avg_coverage_rate", coverage["coverage_rate"].mean()),
        ("min_coverage_rate", coverage["coverage_rate"].min()),
        ("generated_at", datetime.now().isoformat(timespec="seconds")),
    ]
    return pd.DataFrame(metrics, columns=["metric", "value"])


def run_diagnosis(config: dict[str, Any]) -> Path:
    thresholds = threshold_from_config(config)
    init_qlib(config)
    membership = load_membership(config)
    frame, calendar, instrument_count = load_qlib_features(config)

    issues = row_issue_frame(frame, thresholds)
    availability, gaps = instrument_availability(frame, calendar, thresholds, membership)
    coverage = date_coverage(frame, calendar, instrument_count, membership)
    overview = build_overview(config, frame, calendar, instrument_count, membership, issues, availability, coverage)
    rule_counts = aggregate_rule_counts(issues)

    tables = {
        "overview": overview,
        "field_missing_rate": field_missing_rate(frame),
        "rule_counts": rule_counts,
        "row_issues": issues,
        "price_anomalies": select_category(issues, ["price"]),
        "volume_amount_anomalies": select_category(issues, ["volume_amount"]),
        "return_anomalies": select_category(issues, ["return"]),
        "instrument_availability": availability,
        "date_coverage": coverage,
        "abnormal_instruments": abnormal_instruments(issues, availability),
        "abnormal_dates": abnormal_dates(issues, coverage),
        "long_gaps": gaps,
    }

    base_output = Path(config["diagnosis"]["output_dir"])
    run_name = f"{config['diagnosis']['market']}_{config['diagnosis']['start_time']}_{config['diagnosis']['end_time']}"
    run_name = run_name.replace(":", "").replace("/", "-")
    output_dir = base_output / run_name
    write_csv_outputs(output_dir, tables)
    markdown = build_markdown_report(output_dir, config, overview, tables)
    write_markdown_report(output_dir, markdown)
    return output_dir


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Qlib A-share data quality diagnostics.")
    parser.add_argument("--config", default="data_quality/config.yaml", help="Path to diagnosis config YAML.")
    parser.add_argument("--market", help="Qlib instrument pool, e.g. csi300 or csi500.")
    parser.add_argument("--start-time", dest="start_time", help="Diagnosis start date.")
    parser.add_argument("--end-time", dest="end_time", help="Diagnosis end date.")
    parser.add_argument("--provider-uri", dest="provider_uri", help="Qlib provider URI.")
    parser.add_argument("--region", help="Qlib region, default cn.")
    parser.add_argument("--output-dir", dest="output_dir", help="Output directory for CSV and report files.")
    parser.add_argument("--long-zero-run-days", dest="long_zero_run_days", type=int)
    parser.add_argument("--long-gap-days", dest="long_gap_days", type=int)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = apply_overrides(load_config(Path(args.config)), args)
    output_dir = run_diagnosis(config)
    print(f"Data quality diagnosis completed: {output_dir}")


if __name__ == "__main__":
    main()
