from __future__ import annotations

import numpy as np
import pandas as pd


def listing_dates(intervals: pd.DataFrame) -> pd.DataFrame:
    """Use the earliest provider interval start as the available listing-date proxy."""

    result = intervals.groupby("instrument", as_index=False)["start"].min()
    return result.rename(columns={"start": "listing_date_proxy"})


def attach_listing_age(frame: pd.DataFrame, dates: pd.DataFrame) -> pd.DataFrame:
    required = {"datetime", "instrument"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"frame is missing required columns: {sorted(missing)}")
    result = frame.copy()
    result["datetime"] = pd.to_datetime(result["datetime"])
    result["instrument"] = result["instrument"].astype(str).str.upper()
    result = result.merge(dates, on="instrument", how="left")
    result["listing_age_days"] = (result["datetime"] - result["listing_date_proxy"]).dt.days
    result.loc[result["listing_age_days"].lt(0), "listing_age_days"] = np.nan
    result["listing_age_bucket"] = pd.cut(
        result["listing_age_days"],
        bins=[-np.inf, 60, 120, 250, 500, np.inf],
        labels=["0_60", "61_120", "121_250", "251_500", "501_plus"],
    ).astype("string")
    return result


def listing_age_as_of(intervals: pd.DataFrame, as_of: str | pd.Timestamp) -> pd.DataFrame:
    date = pd.Timestamp(as_of)
    active = intervals[intervals["start"].le(date) & intervals["end"].ge(date)][["instrument"]].drop_duplicates()
    base = active.assign(datetime=date)
    return attach_listing_age(base, listing_dates(intervals)).sort_values("instrument").reset_index(drop=True)

