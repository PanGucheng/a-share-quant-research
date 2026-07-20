from __future__ import annotations

import pandas as pd


def monthly_selection_dates(calendar: pd.DatetimeIndex, start: str, end: str) -> pd.DatetimeIndex:
    dates = pd.DatetimeIndex(calendar).sort_values().unique()
    dates = dates[(dates >= pd.Timestamp(start)) & (dates <= pd.Timestamp(end))]
    if dates.empty:
        raise ValueError("no trading dates in requested selection range")
    return pd.DatetimeIndex(pd.Series(dates, index=dates).groupby(dates.to_period("M")).last().to_list())


def _next_trading_date(calendar: pd.DatetimeIndex, date: pd.Timestamp) -> pd.Timestamp:
    later = calendar[calendar > date]
    if later.empty:
        raise ValueError(f"no effective trading date after {date.date()}")
    return pd.Timestamp(later[0])


def build_point_in_time_universe(
    amount: pd.DataFrame,
    source_intervals: pd.DataFrame,
    calendar: pd.DatetimeIndex,
    selection_dates: pd.DatetimeIndex,
    *,
    lookback_days: int,
    min_valid_days: int,
    min_listing_days: int,
    top_n: int,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    required_amount = {"datetime", "instrument", "amount"}
    required_intervals = {"instrument", "start", "end"}
    if required_amount - set(amount.columns) or required_intervals - set(source_intervals.columns):
        raise ValueError("amount or interval input is missing required columns")
    if lookback_days <= 0 or min_valid_days <= 0 or top_n <= 0:
        raise ValueError("lookback_days, min_valid_days, and top_n must be positive")

    dates = pd.DatetimeIndex(calendar).sort_values().unique()
    values = amount.copy(deep=True)
    values["datetime"] = pd.to_datetime(values["datetime"])
    values["instrument"] = values["instrument"].astype(str).str.upper()
    values["amount"] = pd.to_numeric(values["amount"], errors="coerce")
    intervals = source_intervals.copy(deep=True)
    intervals["instrument"] = intervals["instrument"].astype(str).str.upper()
    intervals["start"] = pd.to_datetime(intervals["start"])
    intervals["end"] = pd.to_datetime(intervals["end"])
    listing = intervals.groupby("instrument", as_index=False)["start"].min().rename(columns={"start": "listing_date"})

    snapshot_rows: list[dict] = []
    metric_rows: list[dict] = []
    for selection_date in pd.DatetimeIndex(selection_dates).sort_values():
        position = dates.searchsorted(selection_date)
        if position >= len(dates) or dates[position] != selection_date:
            raise ValueError(f"selection date is not a trading date: {selection_date}")
        window = dates[max(0, position - lookback_days + 1) : position + 1]
        effective_date = _next_trading_date(dates, selection_date)
        active = intervals.loc[(intervals["start"] <= selection_date) & (intervals["end"] >= selection_date), ["instrument"]].drop_duplicates()
        active = active.merge(listing, on="instrument", how="left")
        active["listing_trading_days"] = active["listing_date"].map(lambda value: int(((dates >= value) & (dates <= selection_date)).sum()))
        eligible = active.loc[active["listing_trading_days"] >= min_listing_days]
        history = values.loc[(values["datetime"] >= window[0]) & (values["datetime"] <= selection_date)]
        ranked = (
            history.merge(eligible[["instrument", "listing_trading_days"]], on="instrument", how="inner")
            .groupby(["instrument", "listing_trading_days"], as_index=False)["amount"]
            .agg(median_amount="median", mean_amount="mean", valid_days="count")
        )
        ranked = ranked.loc[ranked["valid_days"] >= min_valid_days].sort_values(
            ["median_amount", "mean_amount", "instrument"], ascending=[False, False, True]
        )
        selected = ranked.head(top_n).copy()
        for rank, row in enumerate(selected.itertuples(index=False), start=1):
            snapshot_rows.append(
                {
                    "selection_date": selection_date,
                    "effective_date": effective_date,
                    "instrument": row.instrument,
                    "rank": rank,
                    "median_amount": row.median_amount,
                    "mean_amount": row.mean_amount,
                    "valid_days": row.valid_days,
                    "listing_trading_days": row.listing_trading_days,
                    "selection_reason": "top_median_amount",
                    "max_source_date": selection_date,
                }
            )
        metric_rows.append(
            {
                "selection_date": selection_date,
                "effective_date": effective_date,
                "lookback_start": window[0],
                "lookback_end": window[-1],
                "active_count": len(active),
                "listing_eligible_count": len(eligible),
                "liquidity_eligible_count": len(ranked),
                "selected_count": len(selected),
                "max_source_date": history["datetime"].max() if not history.empty else pd.NaT,
            }
        )
    snapshots = pd.DataFrame(snapshot_rows)
    metrics = pd.DataFrame(metric_rows)
    changes = membership_changes(snapshots)
    return snapshots, metrics, changes


def membership_changes(snapshots: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict] = []
    previous: set[str] = set()
    for selection_date, group in snapshots.groupby("selection_date", sort=True):
        current = set(group["instrument"].astype(str))
        effective_date = group["effective_date"].iloc[0]
        for instrument in sorted(current - previous):
            rows.append({"selection_date": selection_date, "effective_date": effective_date, "instrument": instrument, "action": "enter"})
        for instrument in sorted(previous - current):
            rows.append({"selection_date": selection_date, "effective_date": effective_date, "instrument": instrument, "action": "exit"})
        previous = current
    return pd.DataFrame(rows, columns=["selection_date", "effective_date", "instrument", "action"])
