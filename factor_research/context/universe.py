from __future__ import annotations

from pathlib import Path

import pandas as pd


INTERVAL_COLUMNS = ["instrument", "start", "end"]


def load_instrument_intervals(path: Path) -> pd.DataFrame:
    """Load Qlib instrument intervals without expanding them into daily rows."""

    if not path.exists():
        raise FileNotFoundError(path)
    frame = pd.read_csv(path, sep="\t", header=None, names=INTERVAL_COLUMNS, dtype={"instrument": str})
    frame["instrument"] = frame["instrument"].str.upper()
    frame["start"] = pd.to_datetime(frame["start"])
    frame["end"] = pd.to_datetime(frame["end"])
    invalid = frame["start"] > frame["end"]
    if invalid.any():
        raise ValueError(f"{path} contains {int(invalid.sum())} intervals where start > end")
    return frame.sort_values(["instrument", "start", "end"]).reset_index(drop=True)


def active_members(intervals: pd.DataFrame, as_of: str | pd.Timestamp) -> pd.DataFrame:
    date = pd.Timestamp(as_of)
    active = intervals[intervals["start"].le(date) & intervals["end"].ge(date)].copy()
    return active.sort_values("instrument").reset_index(drop=True)


def membership_counts(
    intervals: pd.DataFrame,
    calendar: pd.DatetimeIndex,
    universe: str,
) -> pd.DataFrame:
    rows = []
    for date in calendar:
        count = int((intervals["start"].le(date) & intervals["end"].ge(date)).sum())
        rows.append({"datetime": date, "universe": universe, "member_count": count})
    return pd.DataFrame(rows)


def attach_membership(
    frame: pd.DataFrame,
    intervals: pd.DataFrame,
    column: str,
) -> pd.DataFrame:
    """Attach point-in-time membership to a datetime/instrument frame."""

    required = {"datetime", "instrument"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"frame is missing required columns: {sorted(missing)}")
    result = frame.copy()
    result["datetime"] = pd.to_datetime(result["datetime"])
    result["instrument"] = result["instrument"].astype(str).str.upper()
    result[column] = False
    interval_map = {
        instrument: list(group[["start", "end"]].itertuples(index=False, name=None))
        for instrument, group in intervals.groupby("instrument", sort=False)
    }
    for instrument, index in result.groupby("instrument", sort=False).groups.items():
        spans = interval_map.get(instrument, [])
        if not spans:
            continue
        dates = result.loc[index, "datetime"]
        mask = pd.Series(False, index=index)
        for start, end in spans:
            mask |= dates.between(start, end)
        result.loc[index, column] = mask
    result[column] = result[column].astype(bool)
    return result

