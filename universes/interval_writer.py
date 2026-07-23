from __future__ import annotations

from pathlib import Path

import pandas as pd


INTERVAL_COLUMNS = [
    "instrument",
    "start_date",
    "end_date",
    "selection_date",
    "effective_date",
    "selection_reason",
]


def snapshots_to_intervals(snapshots: pd.DataFrame, calendar: pd.DatetimeIndex, final_date: str | pd.Timestamp) -> pd.DataFrame:
    if snapshots.empty:
        return pd.DataFrame(columns=INTERVAL_COLUMNS)
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


def intersect_membership_with_lifecycle(
    intervals: pd.DataFrame,
    source_intervals: pd.DataFrame,
    calendar: pd.DatetimeIndex,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Intersect rolling membership intervals with exact source lifecycle spans.

    The returned difference and removed-key tables make truncation observable.
    Missing lifecycle rows are fail-closed: they produce no corrected membership.
    """

    required_membership = set(INTERVAL_COLUMNS)
    required_source = {"instrument", "start", "end"}
    missing_membership = sorted(required_membership - set(intervals.columns))
    missing_source = sorted(required_source - set(source_intervals.columns))
    if missing_membership or missing_source:
        raise ValueError(
            "membership or lifecycle input is missing required columns: "
            f"membership={missing_membership}, source={missing_source}"
        )

    dates = pd.DatetimeIndex(calendar).sort_values().unique().normalize()
    membership = intervals[INTERVAL_COLUMNS].copy()
    membership["instrument"] = membership["instrument"].astype(str).str.upper()
    for column in ["start_date", "end_date", "selection_date", "effective_date"]:
        membership[column] = pd.to_datetime(membership[column]).dt.normalize()
    if membership[["start_date", "end_date"]].isna().any().any():
        raise ValueError("membership intervals contain missing boundaries")
    if (membership["start_date"] > membership["end_date"]).any():
        raise ValueError("membership intervals contain start_date > end_date")
    membership["_rolling_interval_id"] = range(len(membership))

    lifecycle = source_intervals[["instrument", "start", "end"]].copy()
    lifecycle["instrument"] = lifecycle["instrument"].astype(str).str.upper()
    lifecycle["start"] = pd.to_datetime(lifecycle["start"]).dt.normalize()
    lifecycle["end"] = pd.to_datetime(lifecycle["end"]).dt.normalize()
    if lifecycle[["start", "end"]].isna().any().any():
        raise ValueError("source lifecycle contains missing boundaries")
    if (lifecycle["start"] > lifecycle["end"]).any():
        raise ValueError("source lifecycle contains start > end")
    lifecycle = lifecycle.sort_values(["instrument", "start", "end"]).reset_index(drop=True)

    merged = membership.merge(lifecycle, on="instrument", how="left")
    merged["_intersection_start"] = merged[["start_date", "start"]].max(axis=1)
    merged["_intersection_end"] = merged[["end_date", "end"]].min(axis=1)
    valid = merged[
        merged["start"].notna()
        & merged["_intersection_start"].le(merged["_intersection_end"])
    ].copy()
    valid["start_date"] = valid["_intersection_start"]
    valid["end_date"] = valid["_intersection_end"]
    corrected = (
        valid[["_rolling_interval_id", *INTERVAL_COLUMNS]]
        .drop_duplicates()
        .sort_values(["instrument", "start_date", "end_date", "_rolling_interval_id"])
        .reset_index(drop=True)
    )

    difference_rows: list[dict[str, object]] = []
    removed_rows: list[dict[str, object]] = []
    corrected_by_id = {
        int(interval_id): group
        for interval_id, group in corrected.groupby("_rolling_interval_id", sort=False)
    }
    lifecycle_by_instrument = {
        str(instrument): group
        for instrument, group in lifecycle.groupby("instrument", sort=False)
    }
    for row in membership.to_dict(orient="records"):
        interval_id = int(row["_rolling_interval_id"])
        segments = corrected_by_id.get(interval_id)
        original_dates = dates[
            (dates >= row["start_date"]) & (dates <= row["end_date"])
        ]
        corrected_dates = pd.DatetimeIndex([])
        if segments is not None:
            segment_dates = [
                dates[
                    (dates >= segment.start_date)
                    & (dates <= segment.end_date)
                ]
                for segment in segments.itertuples(index=False)
            ]
            if segment_dates:
                corrected_dates = pd.DatetimeIndex(
                    sorted(set().union(*(set(values) for values in segment_dates)))
                )
        removed_dates = original_dates.difference(corrected_dates)
        unchanged = (
            segments is not None
            and len(segments) == 1
            and pd.Timestamp(segments.iloc[0]["start_date"]) == row["start_date"]
            and pd.Timestamp(segments.iloc[0]["end_date"]) == row["end_date"]
        )
        if unchanged:
            continue

        source = lifecycle_by_instrument.get(str(row["instrument"]))
        if source is None:
            resolution = "removed_missing_lifecycle"
            source_spans = ""
        elif segments is None or segments.empty:
            resolution = "removed_outside_lifecycle"
            source_spans = "|".join(
                f"{item.start:%Y-%m-%d}:{item.end:%Y-%m-%d}"
                for item in source.itertuples(index=False)
            )
        elif len(segments) > 1:
            resolution = "split_by_lifecycle"
            source_spans = "|".join(
                f"{item.start:%Y-%m-%d}:{item.end:%Y-%m-%d}"
                for item in source.itertuples(index=False)
            )
        else:
            resolution = "truncated_to_lifecycle"
            source_spans = "|".join(
                f"{item.start:%Y-%m-%d}:{item.end:%Y-%m-%d}"
                for item in source.itertuples(index=False)
            )
        corrected_spans = (
            ""
            if segments is None
            else "|".join(
                f"{item.start_date:%Y-%m-%d}:{item.end_date:%Y-%m-%d}"
                for item in segments.itertuples(index=False)
            )
        )
        difference_rows.append(
            {
                "rolling_interval_id": interval_id,
                "instrument": row["instrument"],
                "original_start_date": row["start_date"],
                "original_end_date": row["end_date"],
                "source_lifecycle_spans": source_spans,
                "corrected_membership_spans": corrected_spans,
                "corrected_segment_count": 0 if segments is None else len(segments),
                "removed_calendar_key_count": len(removed_dates),
                "resolution": resolution,
            }
        )
        for date in removed_dates:
            removed_rows.append(
                {
                    "rolling_interval_id": interval_id,
                    "datetime": pd.Timestamp(date),
                    "instrument": row["instrument"],
                    "resolution": resolution,
                }
            )

    corrected = corrected.drop(columns="_rolling_interval_id").reset_index(drop=True)
    differences = pd.DataFrame(
        difference_rows,
        columns=[
            "rolling_interval_id",
            "instrument",
            "original_start_date",
            "original_end_date",
            "source_lifecycle_spans",
            "corrected_membership_spans",
            "corrected_segment_count",
            "removed_calendar_key_count",
            "resolution",
        ],
    )
    removed_keys = pd.DataFrame(
        removed_rows,
        columns=["rolling_interval_id", "datetime", "instrument", "resolution"],
    )
    return corrected, differences, removed_keys


def write_qlib_instruments(intervals: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"{row.instrument}\t{row.start_date:%Y-%m-%d}\t{row.end_date:%Y-%m-%d}" for row in intervals.itertuples(index=False)]
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
