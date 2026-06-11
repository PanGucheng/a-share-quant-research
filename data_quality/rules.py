from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np
import pandas as pd


FIELDS = ["open", "high", "low", "close", "volume", "amount"]
PRICE_FIELDS = ["open", "high", "low", "close"]


@dataclass(frozen=True)
class Thresholds:
    max_abs_daily_return: float = 0.25
    max_abs_close_jump: float = 0.35
    suspicious_adjusted_return: float = 0.50
    long_zero_run_days: int = 20
    long_gap_days: int = 20
    long_missing_ratio: float = 0.50


def normalize_feature_frame(raw: pd.DataFrame) -> pd.DataFrame:
    """Normalize Qlib fields like $close into close."""
    frame = raw.copy()
    frame.columns = [str(col).lstrip("$") for col in frame.columns]
    frame = frame.reset_index()
    if "datetime" not in frame.columns or "instrument" not in frame.columns:
        raise ValueError("Expected Qlib feature frame indexed by instrument and datetime.")
    frame["datetime"] = pd.to_datetime(frame["datetime"])
    return frame.sort_values(["instrument", "datetime"]).reset_index(drop=True)


def consecutive_true_runs(mask: pd.Series) -> tuple[int, int]:
    """Return max run length and number of runs for a boolean mask."""
    max_run = 0
    run_count = 0
    current = 0
    for value in mask.fillna(False).astype(bool):
        if value:
            current += 1
            if current == 1:
                run_count += 1
            max_run = max(max_run, current)
        else:
            current = 0
    return max_run, run_count


def field_missing_rate(frame: pd.DataFrame) -> pd.DataFrame:
    rows = []
    total = len(frame)
    for field in FIELDS:
        missing = int(frame[field].isna().sum())
        rows.append(
            {
                "field": field,
                "missing_count": missing,
                "total_count": total,
                "missing_rate": missing / total if total else np.nan,
            }
        )
    return pd.DataFrame(rows)


def normalize_membership_frame(membership: pd.DataFrame | None) -> pd.DataFrame | None:
    if membership is None or membership.empty:
        return None
    required = {"instrument", "start_time", "end_time"}
    missing = required - set(membership.columns)
    if missing:
        raise ValueError(f"Membership frame is missing columns: {sorted(missing)}")
    result = membership.copy()
    result["instrument"] = result["instrument"].astype(str).str.upper()
    result["start_time"] = pd.to_datetime(result["start_time"])
    result["end_time"] = pd.to_datetime(result["end_time"])
    return result.sort_values(["instrument", "start_time", "end_time"]).reset_index(drop=True)


def expected_calendar_for_instrument(
    instrument: str,
    calendar: pd.DatetimeIndex,
    membership: pd.DataFrame | None,
) -> pd.DatetimeIndex:
    if membership is None or membership.empty:
        return pd.DatetimeIndex(calendar)
    instrument_membership = membership.loc[membership["instrument"] == str(instrument).upper()]
    if instrument_membership.empty:
        return pd.DatetimeIndex(calendar)
    masks = []
    for row in instrument_membership.itertuples(index=False):
        masks.append((calendar >= row.start_time) & (calendar <= row.end_time))
    if not masks:
        return pd.DatetimeIndex([])
    expected = masks[0]
    for mask in masks[1:]:
        expected = expected | mask
    return pd.DatetimeIndex(calendar[expected])


def dynamic_membership_coverage(
    calendar: pd.DatetimeIndex,
    membership: pd.DataFrame | None,
) -> pd.DataFrame:
    calendar = pd.DatetimeIndex(calendar)
    if membership is None or membership.empty:
        return pd.DataFrame({"datetime": calendar, "expected_instrument_count": np.nan})
    rows = []
    for dt in calendar:
        active = membership[(membership["start_time"] <= dt) & (membership["end_time"] >= dt)]["instrument"].nunique()
        rows.append({"datetime": dt, "expected_instrument_count": int(active)})
    return pd.DataFrame(rows)


def row_issue_frame(frame: pd.DataFrame, thresholds: Thresholds) -> pd.DataFrame:
    checks: list[tuple[str, str, pd.Series]] = []

    for field in FIELDS:
        checks.append(("missing", f"{field}_missing", frame[field].isna()))

    for field in PRICE_FIELDS:
        checks.append(("price", f"{field}_le_zero", frame[field].le(0) & frame[field].notna()))

    checks.extend(
        [
            ("price", "high_lt_low", frame["high"].lt(frame["low"]) & frame["high"].notna() & frame["low"].notna()),
            (
                "price",
                "open_outside_high_low",
                (frame["open"].lt(frame["low"]) | frame["open"].gt(frame["high"]))
                & frame[["open", "high", "low"]].notna().all(axis=1),
            ),
            (
                "price",
                "close_outside_high_low",
                (frame["close"].lt(frame["low"]) | frame["close"].gt(frame["high"]))
                & frame[["close", "high", "low"]].notna().all(axis=1),
            ),
            ("volume_amount", "volume_lt_zero", frame["volume"].lt(0) & frame["volume"].notna()),
            ("volume_amount", "amount_lt_zero", frame["amount"].lt(0) & frame["amount"].notna()),
        ]
    )

    ordered = frame.sort_values(["instrument", "datetime"]).copy()
    ordered["daily_return"] = ordered.groupby("instrument")["close"].pct_change(fill_method=None)
    ordered["abs_daily_return"] = ordered["daily_return"].abs()
    ordered["close_jump"] = ordered.groupby("instrument")["close"].diff().abs() / ordered.groupby("instrument")[
        "close"
    ].shift(1).abs()

    checks.extend(
        [
            (
                "return",
                "abs_daily_return_too_large",
                ordered["abs_daily_return"].gt(thresholds.max_abs_daily_return),
            ),
            ("return", "close_jump_too_large", ordered["close_jump"].gt(thresholds.max_abs_close_jump)),
            (
                "return",
                "suspected_adjustment_error",
                ordered["abs_daily_return"].gt(thresholds.suspicious_adjusted_return),
            ),
        ]
    )

    base_cols = ["instrument", "datetime", *FIELDS]
    issues = []
    for category, rule, mask in checks:
        if mask.index is not frame.index:
            source = ordered.loc[mask.fillna(False), base_cols + ["daily_return", "close_jump"]]
        else:
            source = frame.loc[mask.fillna(False), base_cols].copy()
            source["daily_return"] = np.nan
            source["close_jump"] = np.nan
        if not source.empty:
            source.insert(2, "category", category)
            source.insert(3, "rule", rule)
            issues.append(source)

    if not issues:
        return pd.DataFrame(columns=["instrument", "datetime", "category", "rule", *FIELDS, "daily_return", "close_jump"])
    return pd.concat(issues, ignore_index=True).sort_values(["datetime", "instrument", "category", "rule"])


def instrument_availability(
    frame: pd.DataFrame,
    calendar: pd.DatetimeIndex,
    thresholds: Thresholds,
    membership: pd.DataFrame | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    calendar = pd.DatetimeIndex(calendar)
    membership = normalize_membership_frame(membership)
    rows = []
    gap_rows = []

    for instrument, group in frame.groupby("instrument", sort=True):
        expected_calendar = expected_calendar_for_instrument(instrument, calendar, membership)
        expected_days = len(expected_calendar)
        group = group.sort_values("datetime")
        valid_mask = group[FIELDS].notna().any(axis=1)
        close_valid = group["close"].notna()
        valid_dates = pd.DatetimeIndex(group.loc[valid_mask, "datetime"])
        valid_dates_in_scope = valid_dates.intersection(expected_calendar)
        valid_days = int(valid_mask.sum())
        valid_days_in_scope = len(valid_dates_in_scope)
        missing_days = max(expected_days - valid_days_in_scope, 0)
        missing_ratio = missing_days / expected_days if expected_days else np.nan
        start = valid_dates_in_scope.min() if len(valid_dates_in_scope) else pd.NaT
        end = valid_dates_in_scope.max() if len(valid_dates_in_scope) else pd.NaT

        zero_volume_max, zero_volume_runs = consecutive_true_runs(group["volume"].fillna(np.nan).eq(0))
        zero_amount_max, zero_amount_runs = consecutive_true_runs(group["amount"].fillna(np.nan).eq(0))

        internal_missing = []
        if pd.notna(start) and pd.notna(end):
            expected_between = expected_calendar[(expected_calendar >= start) & (expected_calendar <= end)]
            observed = set(valid_dates_in_scope)
            internal_missing = [dt for dt in expected_between if dt not in observed]

        internal_missing_mask = pd.Series(expected_calendar.isin(internal_missing), index=expected_calendar)
        max_gap, gap_count = consecutive_true_runs(internal_missing_mask)
        if max_gap >= thresholds.long_gap_days:
            gap_rows.append(
                {
                    "instrument": instrument,
                    "max_internal_gap_days": max_gap,
                    "internal_gap_count": gap_count,
                    "start_time": start,
                    "end_time": end,
                }
            )

        issue_penalty = min(missing_ratio, 1.0) * 60
        if zero_volume_max >= thresholds.long_zero_run_days:
            issue_penalty += 15
        if zero_amount_max >= thresholds.long_zero_run_days:
            issue_penalty += 15
        if max_gap >= thresholds.long_gap_days:
            issue_penalty += 10
        availability_score = max(0.0, 100.0 - issue_penalty)

        rows.append(
            {
                "instrument": instrument,
                "expected_trade_days": expected_days,
                "valid_trade_days": valid_days_in_scope,
                "raw_valid_trade_days": valid_days,
                "missing_trade_days": missing_days,
                "missing_ratio": missing_ratio,
                "start_time": start,
                "end_time": end,
                "close_valid_days": int(close_valid.sum()),
                "max_zero_volume_run_days": zero_volume_max,
                "zero_volume_run_count": zero_volume_runs,
                "max_zero_amount_run_days": zero_amount_max,
                "zero_amount_run_count": zero_amount_runs,
                "max_internal_gap_days": max_gap,
                "internal_gap_count": gap_count,
                "long_missing": bool(missing_ratio >= thresholds.long_missing_ratio),
                "long_zero_volume": bool(zero_volume_max >= thresholds.long_zero_run_days),
                "long_zero_amount": bool(zero_amount_max >= thresholds.long_zero_run_days),
                "long_internal_gap": bool(max_gap >= thresholds.long_gap_days),
                "availability_score": round(availability_score, 2),
            }
        )

    return pd.DataFrame(rows).sort_values("availability_score"), pd.DataFrame(gap_rows)


def date_coverage(
    frame: pd.DataFrame,
    calendar: pd.DatetimeIndex,
    instrument_count: int,
    membership: pd.DataFrame | None = None,
) -> pd.DataFrame:
    valid = frame.assign(has_data=frame[FIELDS].notna().any(axis=1))
    coverage = valid.groupby("datetime")["has_data"].sum().reindex(pd.DatetimeIndex(calendar), fill_value=0)
    result = coverage.rename("covered_instrument_count").reset_index().rename(columns={"index": "datetime"})
    membership = normalize_membership_frame(membership)
    if membership is None:
        result["expected_instrument_count"] = instrument_count
    else:
        dynamic_expected = dynamic_membership_coverage(pd.DatetimeIndex(calendar), membership)
        result = result.merge(dynamic_expected, on="datetime", how="left")
        result["expected_instrument_count"] = result["expected_instrument_count"].fillna(0).astype(int)
    result["coverage_rate"] = np.where(
        result["expected_instrument_count"].gt(0),
        result["covered_instrument_count"] / result["expected_instrument_count"],
        np.nan,
    )
    return result


def aggregate_rule_counts(issues: pd.DataFrame) -> pd.DataFrame:
    if issues.empty:
        return pd.DataFrame(columns=["category", "rule", "issue_count", "instrument_count", "date_count"])
    return (
        issues.groupby(["category", "rule"])
        .agg(
            issue_count=("rule", "size"),
            instrument_count=("instrument", "nunique"),
            date_count=("datetime", "nunique"),
        )
        .reset_index()
        .sort_values(["category", "issue_count"], ascending=[True, False])
    )


def abnormal_instruments(issues: pd.DataFrame, availability: pd.DataFrame) -> pd.DataFrame:
    if issues.empty:
        issue_counts = pd.DataFrame(columns=["instrument", "issue_count", "issue_rule_count"])
    else:
        issue_counts = (
            issues.groupby("instrument")
            .agg(issue_count=("rule", "size"), issue_rule_count=("rule", "nunique"))
            .reset_index()
        )
    result = availability.merge(issue_counts, on="instrument", how="left")
    result[["issue_count", "issue_rule_count"]] = result[["issue_count", "issue_rule_count"]].fillna(0).astype(int)
    flags = ["long_missing", "long_zero_volume", "long_zero_amount", "long_internal_gap"]
    result["has_structural_issue"] = result[flags].any(axis=1)
    return result[(result["issue_count"] > 0) | result["has_structural_issue"]].sort_values(
        ["availability_score", "issue_count"], ascending=[True, False]
    )


def abnormal_dates(issues: pd.DataFrame, coverage: pd.DataFrame) -> pd.DataFrame:
    if issues.empty:
        issue_counts = pd.DataFrame(columns=["datetime", "issue_count", "issue_instrument_count", "issue_rule_count"])
    else:
        issue_counts = (
            issues.groupby("datetime")
            .agg(
                issue_count=("rule", "size"),
                issue_instrument_count=("instrument", "nunique"),
                issue_rule_count=("rule", "nunique"),
            )
            .reset_index()
        )
    result = coverage.merge(issue_counts, on="datetime", how="left")
    result[["issue_count", "issue_instrument_count", "issue_rule_count"]] = result[
        ["issue_count", "issue_instrument_count", "issue_rule_count"]
    ].fillna(0).astype(int)
    return result[(result["issue_count"] > 0) | (result["coverage_rate"] < 1.0)].sort_values(
        ["coverage_rate", "issue_count"], ascending=[True, False]
    )


def select_category(issues: pd.DataFrame, categories: Iterable[str]) -> pd.DataFrame:
    if issues.empty:
        return issues.copy()
    return issues[issues["category"].isin(categories)].copy()
