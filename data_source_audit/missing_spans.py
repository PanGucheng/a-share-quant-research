from __future__ import annotations

import pandas as pd


def missing_span_summary(frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    keys = {
        source: set(zip(frame["instrument"].astype(str), pd.to_datetime(frame["date"])))
        for source, frame in frames.items()
    }
    union = set().union(*keys.values()) if keys else set()
    rows = []
    for source, present in keys.items():
        missing = union - present
        by_instrument: dict[str, list[pd.Timestamp]] = {}
        for instrument, date in missing:
            by_instrument.setdefault(instrument, []).append(pd.Timestamp(date))
        for instrument, dates in by_instrument.items():
            ordered = sorted(dates)
            rows.append(
                {
                    "source": source,
                    "instrument": instrument,
                    "missing_row_count": len(ordered),
                    "first_missing_date": ordered[0],
                    "last_missing_date": ordered[-1],
                    "classification": "source_missing_vs_union",
                }
            )
    return pd.DataFrame(
        rows,
        columns=[
            "source",
            "instrument",
            "missing_row_count",
            "first_missing_date",
            "last_missing_date",
            "classification",
        ],
    )
