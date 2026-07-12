from __future__ import annotations

from pathlib import Path

import pandas as pd


def snapshots_to_intervals(snapshots: pd.DataFrame, calendar: pd.DatetimeIndex, final_date: str | pd.Timestamp) -> pd.DataFrame:
    if snapshots.empty:
        return pd.DataFrame(columns=["instrument", "start_date", "end_date", "selection_date", "effective_date", "selection_reason"])
    dates = pd.DatetimeIndex(calendar).sort_values().unique()
    selection_groups = list(snapshots.groupby("selection_date", sort=True))
    open_members: dict[str, dict] = {}
    rows: list[dict] = []
    for index, (selection_date, group) in enumerate(selection_groups):
        members = set(group["instrument"].astype(str))
        effective_date = pd.Timestamp(group["effective_date"].iloc[0])
        leaving = set(open_members) - members
        previous_dates = dates[dates < effective_date]
        if leaving and previous_dates.empty:
            raise ValueError("cannot close an interval before the first calendar date")
        for instrument in sorted(leaving):
            item = open_members.pop(instrument)
            item["end_date"] = pd.Timestamp(previous_dates[-1])
            rows.append(item)
        reason_map = group.set_index("instrument")["selection_reason"].to_dict()
        for instrument in sorted(members - set(open_members)):
            open_members[instrument] = {
                "instrument": instrument,
                "start_date": effective_date,
                "end_date": pd.NaT,
                "selection_date": pd.Timestamp(selection_date),
                "effective_date": effective_date,
                "selection_reason": reason_map[instrument],
            }
    end = pd.Timestamp(final_date)
    for instrument in sorted(open_members):
        item = open_members[instrument]
        item["end_date"] = end
        rows.append(item)
    return pd.DataFrame(rows).sort_values(["instrument", "start_date"]).reset_index(drop=True)


def write_qlib_instruments(intervals: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"{row.instrument}\t{row.start_date:%Y-%m-%d}\t{row.end_date:%Y-%m-%d}" for row in intervals.itertuples(index=False)]
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
