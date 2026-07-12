from __future__ import annotations

import pandas as pd

from universes.interval_writer import snapshots_to_intervals
from universes.point_in_time_universe import build_point_in_time_universe, monthly_selection_dates


def synthetic_inputs():
    calendar = pd.bdate_range("2024-01-01", periods=90)
    selections = monthly_selection_dates(calendar, "2024-02-01", "2024-04-30")
    intervals = pd.DataFrame({"instrument": ["A", "B", "C"], "start": [calendar[0], calendar[0], calendar[45]], "end": [calendar[-1]] * 3})
    amount = pd.DataFrame([{"datetime": date, "instrument": instrument, "amount": value} for date in calendar for instrument, value in [("A", 100.0), ("B", 50.0)]])
    amount = pd.concat([amount, pd.DataFrame([{"datetime": date, "instrument": "C", "amount": 1000.0} for date in calendar[45:]])], ignore_index=True)
    return calendar, selections, intervals, amount


def test_future_rows_do_not_change_old_snapshot() -> None:
    calendar, selections, intervals, amount = synthetic_inputs()
    base, _, _ = build_point_in_time_universe(amount[amount.datetime <= selections[0]], intervals, calendar, selections[:1], lookback_days=20, min_valid_days=10, min_listing_days=10, top_n=2)
    full, _, _ = build_point_in_time_universe(amount, intervals, calendar, selections[:1], lookback_days=20, min_valid_days=10, min_listing_days=10, top_n=2)
    pd.testing.assert_frame_equal(base, full)


def test_new_listing_respects_minimum_age() -> None:
    calendar, selections, intervals, amount = synthetic_inputs()
    snapshots, _, _ = build_point_in_time_universe(amount, intervals, calendar, selections, lookback_days=20, min_valid_days=5, min_listing_days=15, top_n=2)
    first = set(snapshots.loc[snapshots.selection_date == selections[0], "instrument"])
    assert "C" not in first


def test_input_order_does_not_change_membership() -> None:
    calendar, selections, intervals, amount = synthetic_inputs()
    left, _, _ = build_point_in_time_universe(amount, intervals, calendar, selections, lookback_days=20, min_valid_days=10, min_listing_days=10, top_n=2)
    right, _, _ = build_point_in_time_universe(amount.sample(frac=1, random_state=2), intervals, calendar, selections, lookback_days=20, min_valid_days=10, min_listing_days=10, top_n=2)
    pd.testing.assert_frame_equal(left, right)


def test_continuous_membership_merges_intervals() -> None:
    calendar, selections, intervals, amount = synthetic_inputs()
    snapshots, _, _ = build_point_in_time_universe(amount, intervals, calendar, selections, lookback_days=20, min_valid_days=10, min_listing_days=10, top_n=1)
    result = snapshots_to_intervals(snapshots, calendar, calendar[-1])
    assert len(result[result.instrument == "A"]) == 1
