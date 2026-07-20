from __future__ import annotations

import sys
from multiprocessing import freeze_support
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from universes.interval_writer import snapshots_to_intervals
from universes.point_in_time_universe import build_point_in_time_universe, monthly_selection_dates


def main() -> int:
    calendar = pd.bdate_range("2024-01-01", periods=90)
    selections = monthly_selection_dates(calendar, "2024-02-01", "2024-04-30")
    intervals = pd.DataFrame({"instrument": ["A", "B", "C"], "start": [calendar[0], calendar[0], calendar[45]], "end": [calendar[-1]] * 3})
    rows = []
    for date in calendar:
        rows.extend([{"datetime": date, "instrument": "A", "amount": 100.0}, {"datetime": date, "instrument": "B", "amount": 50.0}])
        if date >= calendar[45]:
            rows.append({"datetime": date, "instrument": "C", "amount": 1000.0})
    amount = pd.DataFrame(rows)
    snapshots, metrics, _ = build_point_in_time_universe(amount, intervals, calendar, selections, lookback_days=20, min_valid_days=10, min_listing_days=10, top_n=2)
    assert (metrics["max_source_date"] <= metrics["selection_date"]).all()
    assert (metrics["effective_date"] > metrics["selection_date"]).all()
    first_members = set(snapshots.loc[snapshots["selection_date"] == selections[0], "instrument"])
    assert "C" not in first_members
    shuffled, _, _ = build_point_in_time_universe(amount.sample(frac=1, random_state=7), intervals, calendar, selections, lookback_days=20, min_valid_days=10, min_listing_days=10, top_n=2)
    pd.testing.assert_frame_equal(snapshots.reset_index(drop=True), shuffled.reset_index(drop=True))
    output_intervals = snapshots_to_intervals(snapshots, calendar, calendar[-1])
    assert not output_intervals.empty
    print("All point-in-time universe synthetic validations passed.")
    return 0


if __name__ == "__main__":
    freeze_support()
    raise SystemExit(main())
