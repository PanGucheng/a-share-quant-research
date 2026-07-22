import pandas as pd

from research_validation.selection_projection import build_selection_projections


def test_selection_projection_excludes_test_dates_and_is_canonically_sorted() -> None:
    dates = pd.bdate_range("2024-01-01", periods=6)
    daily = pd.DataFrame([{"datetime": date, "factor": factor, "rank_ic": value, "cross_section_count": 100} for date in dates for factor, value in (("b", 0.2), ("a", 0.1))])
    outer = pd.DataFrame([{"split_id": "split_001", "datetime": date, "fold": "train" if index < 3 else "test"} for index, date in enumerate(dates)])
    inner = pd.DataFrame([{"outer_split_id": "split_001", "inner_split_id": "inner_001", "datetime": dates[index], "fold": "train" if index < 2 else "validation"} for index in range(3)])

    outer_projection, inner_projection = build_selection_projections(daily.sample(frac=1, random_state=1), outer, inner)

    assert set(outer_projection["datetime"]) == set(dates[:3])
    assert set(inner_projection["datetime"]) == set(dates[:3])
    assert outer_projection[["outer_split_id", "datetime", "factor"]].equals(outer_projection[["outer_split_id", "datetime", "factor"]].sort_values(["outer_split_id", "datetime", "factor"], kind="stable").reset_index(drop=True))
