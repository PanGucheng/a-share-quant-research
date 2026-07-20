from __future__ import annotations

import pandas as pd

from universes.point_in_time_universe import build_point_in_time_universe


def test_selection_metric_never_references_future_date() -> None:
    calendar = pd.bdate_range("2024-01-01", periods=30)
    selection = pd.DatetimeIndex([calendar[20]])
    intervals = pd.DataFrame({"instrument": ["A"], "start": [calendar[0]], "end": [calendar[-1]]})
    amount = pd.DataFrame({"datetime": calendar, "instrument": "A", "amount": range(30)})
    _, metrics, _ = build_point_in_time_universe(amount, intervals, calendar, selection, lookback_days=10, min_valid_days=5, min_listing_days=5, top_n=1)
    assert metrics.loc[0, "max_source_date"] <= metrics.loc[0, "selection_date"]
