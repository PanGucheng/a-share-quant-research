from __future__ import annotations

from pathlib import Path

import pandas as pd


def write_csv_outputs(output_dir: Path, tables: dict[str, pd.DataFrame]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for name, frame in tables.items():
        frame.to_csv(output_dir / f"{name}.csv", index=False, encoding="utf-8-sig")


def _metric_value(metrics: pd.DataFrame, name: str, default: str = "n/a") -> str:
    row = metrics.loc[metrics["metric"] == name]
    if row.empty:
        return default
    value = row.iloc[0]["value"]
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


def _markdown_table(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "No rows."
    display = frame.copy()
    for col in display.columns:
        if pd.api.types.is_datetime64_any_dtype(display[col]):
            display[col] = display[col].dt.strftime("%Y-%m-%d")
    display = display.astype(object).where(pd.notna(display), "")
    headers = [str(col) for col in display.columns]
    rows = display.astype(str).values.tolist()
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    lines.extend("| " + " | ".join(row) + " |" for row in rows)
    return "\n".join(lines)


def build_markdown_report(
    output_dir: Path,
    config: dict,
    metrics: pd.DataFrame,
    tables: dict[str, pd.DataFrame],
) -> str:
    abnormal_instruments = tables["abnormal_instruments"]
    abnormal_dates = tables["abnormal_dates"]
    rule_counts = tables["rule_counts"]
    missing = tables["field_missing_rate"]
    availability = tables["instrument_availability"]
    coverage = tables["date_coverage"]

    lowest_scores = availability.nsmallest(10, "availability_score")[
        ["instrument", "availability_score", "missing_ratio", "max_internal_gap_days"]
    ]
    lowest_coverage = coverage.nsmallest(10, "coverage_rate")[
        ["datetime", "covered_instrument_count", "expected_instrument_count", "coverage_rate"]
    ]
    top_rules = rule_counts.head(15)

    lines = [
        "# A-share Qlib Data Quality Report",
        "",
        "## Scope",
        "",
        f"- Market: `{config['diagnosis']['market']}`",
        f"- Start time: `{config['diagnosis']['start_time']}`",
        f"- End time: `{config['diagnosis']['end_time']}`",
        f"- Provider URI: `{config['qlib']['provider_uri']}`",
        f"- Output directory: `{output_dir.as_posix()}`",
        "",
        "## Overview",
        "",
        f"- Instrument count: `{_metric_value(metrics, 'instrument_count')}`",
        f"- Membership rows: `{_metric_value(metrics, 'membership_rows')}`",
        f"- Dynamic membership enabled: `{_metric_value(metrics, 'dynamic_membership_enabled')}`",
        f"- Calendar trading days: `{_metric_value(metrics, 'calendar_trade_days')}`",
        f"- Raw data rows: `{_metric_value(metrics, 'raw_rows')}`",
        f"- Total issue rows: `{_metric_value(metrics, 'total_issue_rows')}`",
        f"- Average expected instruments per day: `{_metric_value(metrics, 'avg_expected_instruments_per_day')}`",
        f"- Minimum expected instruments per day: `{_metric_value(metrics, 'min_expected_instruments_per_day')}`",
        f"- Maximum expected instruments per day: `{_metric_value(metrics, 'max_expected_instruments_per_day')}`",
        f"- Abnormal instruments: `{len(abnormal_instruments)}`",
        f"- Abnormal dates: `{len(abnormal_dates)}`",
        f"- Average instrument availability score: `{_metric_value(metrics, 'avg_availability_score')}`",
        f"- Average date coverage rate: `{_metric_value(metrics, 'avg_coverage_rate')}`",
        "",
        "## Field Missing Rate",
        "",
        _markdown_table(missing),
        "",
        "## Top Rule Counts",
        "",
        _markdown_table(top_rules) if not top_rules.empty else "No row-level rule issues found.",
        "",
        "## Lowest Instrument Availability Scores",
        "",
        _markdown_table(lowest_scores) if not lowest_scores.empty else "No instrument availability rows.",
        "",
        "## Lowest Date Coverage",
        "",
        _markdown_table(lowest_coverage) if not lowest_coverage.empty else "No date coverage rows.",
        "",
        "## CSV Outputs",
        "",
        "- `overview.csv`: total counts and top-level indicators.",
        "- `field_missing_rate.csv`: missing rate by OHLCVA field.",
        "- `rule_counts.csv`: issue counts by rule.",
        "- `row_issues.csv`: row-level issue detail.",
        "- `price_anomalies.csv`: price issue detail.",
        "- `volume_amount_anomalies.csv`: volume and amount issue detail.",
        "- `return_anomalies.csv`: return and close-jump issue detail.",
        "- `instrument_availability.csv`: per-instrument availability and score.",
        "- `date_coverage.csv`: per-date coverage statistics.",
        "- `abnormal_instruments.csv`: instruments with row-level or structural issues.",
        "- `abnormal_dates.csv`: dates with row-level issues or incomplete coverage.",
        "- `long_gaps.csv`: instruments with long internal missing gaps.",
        "",
        "## Notes",
        "",
        "This module only reads Qlib data and writes diagnostic outputs. It does not repair data, train models, run backtests, or calculate factor IC.",
    ]
    return "\n".join(lines) + "\n"


def write_markdown_report(output_dir: Path, report: str) -> Path:
    path = output_dir / "data_quality_report.md"
    path.write_text(report, encoding="utf-8")
    return path
