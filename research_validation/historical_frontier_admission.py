from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

import numpy as np
import pandas as pd


def active_universe(stock_basic: pd.DataFrame, date: str | pd.Timestamp) -> pd.DataFrame:
    """Return the securities whose published listing interval contains ``date``.

    This is intentionally a *canary* universe.  Tushare's current stock_basic
    snapshot is not treated as a historical database vintage; callers must keep
    the limitation visible in their report.
    """
    if stock_basic.empty:
        return stock_basic.copy()
    result = stock_basic.copy()
    result["list_date"] = pd.to_datetime(result.get("list_date"), format="%Y%m%d", errors="coerce")
    result["delist_date"] = pd.to_datetime(result.get("delist_date"), format="%Y%m%d", errors="coerce")
    point = pd.Timestamp(date).normalize()
    mask = result["list_date"].le(point) & (
        result["delist_date"].isna() | result["delist_date"].ge(point)
    )
    return result.loc[mask].copy()


def stratified_stock_sample(
    stock_basic: pd.DataFrame,
    *,
    sample_per_stratum: int = 6,
    seed: int = 20260830,
) -> pd.DataFrame:
    """Build a reproducible market canary across listing cohorts and status.

    Both listed and delisted securities are retained.  Sampling is deliberately
    small enough for a bounded API audit while preventing a surviving-only sample.
    """
    if sample_per_stratum <= 0:
        raise ValueError("sample_per_stratum must be positive")
    if stock_basic.empty:
        return stock_basic.copy()
    frame = stock_basic.copy()
    frame["list_date"] = pd.to_datetime(frame["list_date"], format="%Y%m%d", errors="coerce")
    frame["delist_date"] = pd.to_datetime(frame.get("delist_date"), format="%Y%m%d", errors="coerce")
    frame["status_cohort"] = np.where(frame["list_status"].astype(str).eq("D"), "delisted", "listed")
    frame["listing_cohort"] = pd.cut(
        frame["list_date"].dt.year,
        bins=[-np.inf, 1999, 2004, 2009, 2014, 2017, 2020, np.inf],
        labels=["pre_2000", "2000_2004", "2005_2009", "2010_2014", "2015_2017", "2018_2020", "2021_plus"],
    ).astype("string")
    rng = np.random.default_rng(seed)
    sampled: list[pd.DataFrame] = []
    for (_, _), group in frame.groupby(["status_cohort", "listing_cohort"], dropna=False, sort=True):
        count = min(sample_per_stratum, len(group))
        indices = rng.choice(len(group), size=count, replace=False)
        sampled.append(group.iloc[np.sort(indices)])
    if not sampled:
        return frame.head(0)
    return pd.concat(sampled, ignore_index=True).sort_values(["status_cohort", "listing_cohort", "ts_code"]).reset_index(drop=True)


def audit_cross_sectional_coverage(
    stock_basic: pd.DataFrame,
    snapshots: Iterable[tuple[str, str, pd.DataFrame]],
) -> pd.DataFrame:
    """Measure market-wide layer coverage against the published active canary."""
    rows: list[dict[str, Any]] = []
    for date, layer, frame in snapshots:
        active = active_universe(stock_basic, date)
        observed = set(frame.get("ts_code", pd.Series(dtype=object)).astype(str).str.upper()) if not frame.empty else set()
        expected = set(active.get("ts_code", pd.Series(dtype=object)).astype(str).str.upper())
        rows.append(
            {
                "trade_date": pd.Timestamp(date).strftime("%Y-%m-%d"),
                "layer": layer,
                "active_canary_count": len(expected),
                "observed_count": len(observed),
                "aligned_count": len(expected & observed),
                "missing_count": len(expected - observed),
                "unexpected_count": len(observed - expected),
                "coverage_ratio": (len(expected & observed) / len(expected)) if expected else np.nan,
            }
        )
    return pd.DataFrame(rows)


def audit_statement_panel(
    frames: Iterable[tuple[str, str, pd.DataFrame]],
    *,
    years: Iterable[int] = range(2010, 2018),
    list_dates: Mapping[str, Any] | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Audit issuer statement histories for PIT completeness and revision risk."""
    expected = {f"{year}{month:02d}{day:02d}" for year in years for month, day in ((3, 31), (6, 30), (9, 30), (12, 31))}
    detail: list[dict[str, Any]] = []
    for ts_code, api, raw in frames:
        frame = raw.copy()
        if frame.empty:
            detail.append({"ts_code": ts_code, "api": api, "rows": 0, "report_periods": 0, "period_coverage_ratio": 0.0, "duplicate_key_rows": 0, "revision_rows": 0, "row_cap_reached": False, "report_type_count": 0, "median_announcement_delay_days": np.nan, "p95_announcement_delay_days": np.nan})
            continue
        for column in ("end_date", "ann_date", "f_ann_date"):
            if column in frame:
                frame[column] = pd.to_datetime(frame[column], format="%Y%m%d", errors="coerce")
        periods = set(frame.get("end_date", pd.Series(dtype="datetime64[ns]")).dropna().dt.strftime("%Y%m%d"))
        eligible_expected = expected
        if list_dates and ts_code in list_dates:
            listing = pd.Timestamp(list_dates[ts_code])
            eligible_expected = {period for period in expected if pd.Timestamp(period) >= listing}
        target_periods = periods & eligible_expected
        key_columns = [column for column in ("ts_code", "end_date", "report_type") if column in frame]
        duplicate_rows = int(frame.duplicated(key_columns, keep=False).sum()) if key_columns else 0
        available = frame.get("f_ann_date", frame.get("ann_date", pd.Series(dtype="datetime64[ns]")))
        report_end = frame.get("end_date", pd.Series(dtype="datetime64[ns]"))
        delay = (available - report_end).dt.days.dropna()
        detail.append(
            {
                "ts_code": ts_code,
                "api": api,
                "rows": len(frame),
                "report_periods": len(periods),
                "target_periods": len(target_periods),
                "period_coverage_ratio": len(target_periods) / len(eligible_expected) if eligible_expected else np.nan,
                "duplicate_key_rows": duplicate_rows,
                "revision_rows": int(frame.get("update_flag", pd.Series(dtype=object)).astype(str).eq("1").sum()),
                "row_cap_reached": len(frame) >= 100,
                "report_type_count": int(frame.get("report_type", pd.Series(dtype=object)).nunique(dropna=True)),
                "median_announcement_delay_days": float(delay.median()) if not delay.empty else np.nan,
                "p95_announcement_delay_days": float(delay.quantile(0.95)) if not delay.empty else np.nan,
            }
        )
    detail_frame = pd.DataFrame(detail)
    if detail_frame.empty:
        return detail_frame, detail_frame
    summary = (
        detail_frame.groupby("api", as_index=False)
        .agg(
            issuers=("ts_code", "nunique"),
            median_period_coverage=("period_coverage_ratio", "median"),
            p10_period_coverage=("period_coverage_ratio", lambda value: value.quantile(0.10)),
            row_cap_issuer_count=("row_cap_reached", "sum"),
            duplicate_key_issuer_count=("duplicate_key_rows", lambda value: int((value > 0).sum())),
            revision_issuer_count=("revision_rows", lambda value: int((value > 0).sum())),
            median_announcement_delay_days=("median_announcement_delay_days", "median"),
            p95_announcement_delay_days=("p95_announcement_delay_days", "median"),
        )
    )
    return detail_frame, summary


def audit_lifecycle_alignment(
    stock_basic: pd.DataFrame,
    qlib_intervals: pd.DataFrame,
    dates: Iterable[str | pd.Timestamp],
) -> pd.DataFrame:
    """Compare Qlib interval membership with the current stock_basic canary."""
    intervals = qlib_intervals.copy()
    if intervals.empty:
        intervals = pd.DataFrame(columns=["instrument", "start_date", "end_date"])
    intervals["start_date"] = pd.to_datetime(intervals["start_date"], errors="coerce")
    intervals["end_date"] = pd.to_datetime(intervals["end_date"], errors="coerce")
    rows: list[dict[str, Any]] = []
    for value in dates:
        date = pd.Timestamp(value).normalize()
        qlib_active = set(intervals.loc[(intervals["start_date"] <= date) & (intervals["end_date"] >= date), "instrument"].astype(str).str.upper())
        ts_active = set(
            active_universe(stock_basic, date)
            .get("ts_code", pd.Series(dtype=object))
            .astype(str)
            .str.upper()
            .map(lambda item: (item.rsplit(".", 1)[1] + item.rsplit(".", 1)[0]) if "." in item else item)
        )
        rows.append(
            {
                "date": date.strftime("%Y-%m-%d"),
                "qlib_active_count": len(qlib_active),
                "stock_basic_active_count": len(ts_active),
                "intersection_count": len(qlib_active & ts_active),
                "qlib_only_count": len(qlib_active - ts_active),
                "stock_basic_only_count": len(ts_active - qlib_active),
                "intersection_ratio_qlib": len(qlib_active & ts_active) / len(qlib_active) if qlib_active else np.nan,
                "intersection_ratio_stock_basic": len(qlib_active & ts_active) / len(ts_active) if ts_active else np.nan,
            }
        )
    return pd.DataFrame(rows)


def audit_adjustment_continuity(frame: pd.DataFrame) -> pd.DataFrame:
    """Check daily/adjustment overlap and factor-change event continuity."""
    if frame.empty:
        return pd.DataFrame()
    source = frame.copy()
    if "date" not in source and "trade_date" in source:
        source = source.rename(columns={"trade_date": "date"})
    if "adj_factor" not in source:
        source["adj_factor"] = np.nan
    source["date"] = pd.to_datetime(source["date"], errors="coerce")
    source["adj_factor"] = pd.to_numeric(source["adj_factor"], errors="coerce")
    source = source.dropna(subset=["instrument", "date"]).sort_values(["instrument", "date"])
    rows: list[dict[str, Any]] = []
    for instrument, group in source.groupby("instrument", sort=True):
        factor = group["adj_factor"]
        changes = factor.ne(factor.shift()) & factor.notna() & factor.shift().notna()
        rows.append(
            {
                "instrument": instrument,
                "rows": len(group),
                "date_start": group["date"].min().date().isoformat(),
                "date_end": group["date"].max().date().isoformat(),
                "positive_factor_ratio": float(factor.gt(0).mean()),
                "factor_nonnull_ratio": float(factor.notna().mean()),
                "factor_change_events": int(changes.sum()),
                "duplicate_date_rows": int(group.duplicated(["date"]).sum()),
                "daily_adj_overlap_ratio": float(group["daily_present"].mean()) if "daily_present" in group else np.nan,
            }
        )
    return pd.DataFrame(rows)


def continuous_frontier(
    coverage: pd.DataFrame,
    *,
    layer: str,
    minimum_coverage: float = 0.90,
    consecutive_periods: int = 4,
) -> dict[str, Any]:
    """Find the first date starting a stable run, not an isolated passing date."""
    subset = coverage.loc[coverage["layer"].eq(layer)].copy()
    if subset.empty:
        return {"layer": layer, "frontier": "", "stable": False, "passing_periods": 0}
    subset = subset.sort_values("trade_date").reset_index(drop=True)
    passed = subset["coverage_ratio"].ge(minimum_coverage).fillna(False).to_numpy()
    failing = np.flatnonzero(~passed)
    start = int(failing[-1] + 1) if len(failing) else 0
    run = len(passed) - start
    if run >= consecutive_periods:
        return {"layer": layer, "frontier": str(subset.loc[len(subset) - run, "trade_date"]), "stable": True, "passing_periods": int(passed.sum())}
    return {"layer": layer, "frontier": "", "stable": False, "passing_periods": int(passed.sum())}
