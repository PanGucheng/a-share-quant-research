from __future__ import annotations

import pandas as pd

from universes.interval_writer import (
    intersect_membership_with_lifecycle,
    snapshots_to_intervals,
)
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


def test_membership_is_truncated_to_exact_source_lifecycle() -> None:
    calendar = pd.bdate_range("2024-01-01", periods=10)
    rolling = pd.DataFrame(
        {
            "instrument": ["A"],
            "start_date": [calendar[1]],
            "end_date": [calendar[8]],
            "selection_date": [calendar[0]],
            "effective_date": [calendar[1]],
            "selection_reason": ["top_median_amount"],
        }
    )
    source = pd.DataFrame(
        {"instrument": ["A"], "start": [calendar[0]], "end": [calendar[5]]}
    )
    corrected, differences, removed = intersect_membership_with_lifecycle(
        rolling, source, calendar
    )
    assert corrected.iloc[0]["start_date"] == calendar[1]
    assert corrected.iloc[0]["end_date"] == calendar[5]
    assert differences.iloc[0]["resolution"] == "truncated_to_lifecycle"
    assert differences.iloc[0]["removed_calendar_key_count"] == 3
    assert removed["datetime"].tolist() == list(calendar[6:9])


def test_missing_lifecycle_is_fail_closed() -> None:
    calendar = pd.bdate_range("2024-01-01", periods=5)
    rolling = pd.DataFrame(
        {
            "instrument": ["A"],
            "start_date": [calendar[1]],
            "end_date": [calendar[4]],
            "selection_date": [calendar[0]],
            "effective_date": [calendar[1]],
            "selection_reason": ["top_median_amount"],
        }
    )
    source = pd.DataFrame(
        columns=["instrument", "start", "end"]
    )
    corrected, differences, removed = intersect_membership_with_lifecycle(
        rolling, source, calendar
    )
    assert corrected.empty
    assert differences.iloc[0]["resolution"] == "removed_missing_lifecycle"
    assert len(removed) == 4


def test_disjoint_source_lifecycles_split_membership() -> None:
    calendar = pd.bdate_range("2024-01-01", periods=10)
    rolling = pd.DataFrame(
        {
            "instrument": ["A"],
            "start_date": [calendar[0]],
            "end_date": [calendar[9]],
            "selection_date": [calendar[0]],
            "effective_date": [calendar[0]],
            "selection_reason": ["top_median_amount"],
        }
    )
    source = pd.DataFrame(
        {
            "instrument": ["A", "A"],
            "start": [calendar[0], calendar[6]],
            "end": [calendar[3], calendar[9]],
        }
    )
    corrected, differences, removed = intersect_membership_with_lifecycle(
        rolling, source, calendar
    )
    assert len(corrected) == 2
    assert differences.iloc[0]["resolution"] == "split_by_lifecycle"
    assert removed["datetime"].tolist() == list(calendar[4:6])
