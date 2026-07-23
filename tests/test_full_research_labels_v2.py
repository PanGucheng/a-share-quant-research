from __future__ import annotations

import pandas as pd
import pytest

from research_validation.labels import (
    build_exact_calendar_label,
    build_label_date_map,
)


def test_label_date_map_uses_exact_calendar_positions() -> None:
    calendar = pd.bdate_range("2024-01-02", periods=25)
    mapping = build_label_date_map(
        pd.Series(calendar[:5]),
        calendar,
        entry_lag=1,
        holding_days=3,
    )
    assert (mapping["entry_position"] - mapping["calendar_position"]).eq(1).all()
    assert (mapping["exit_position"] - mapping["entry_position"]).eq(3).all()
    assert mapping.loc[0, "entry_date"] == calendar[1]
    assert mapping.loc[0, "exit_date"] == calendar[4]


def test_missing_physical_price_row_does_not_shorten_horizon_or_fill() -> None:
    calendar = pd.bdate_range("2024-01-02", periods=6)
    keys = pd.DataFrame(
        {"datetime": [calendar[0]], "instrument": ["SH600000"]}
    )
    prices = pd.DataFrame(
        {
            "datetime": [calendar[0], calendar[2], calendar[3]],
            "instrument": ["SH600000"] * 3,
            "close": [10.0, 11.0, 12.0],
        }
    )
    label, _ = build_exact_calendar_label(
        keys,
        prices,
        calendar,
        price_column="close",
        label_name="label",
        entry_lag=1,
        holding_days=2,
    )
    assert pd.isna(label.loc[0, "entry_close"])
    assert pd.isna(label.loc[0, "label"])
    assert label.loc[0, "exit_date"] == calendar[3]


def test_label_is_invariant_to_price_row_order() -> None:
    calendar = pd.bdate_range("2024-01-02", periods=6)
    keys = pd.DataFrame(
        {"datetime": [calendar[0]], "instrument": ["SH600000"]}
    )
    prices = pd.DataFrame(
        {
            "datetime": [calendar[1], calendar[3]],
            "instrument": ["SH600000", "SH600000"],
            "close": [10.0, 12.0],
        }
    )
    first, _ = build_exact_calendar_label(
        keys,
        prices,
        calendar,
        price_column="close",
        label_name="label",
        entry_lag=1,
        holding_days=2,
    )
    second, _ = build_exact_calendar_label(
        keys,
        prices.iloc[::-1],
        calendar,
        price_column="close",
        label_name="label",
        entry_lag=1,
        holding_days=2,
    )
    assert first.loc[0, "label"] == second.loc[0, "label"]
    assert first.loc[0, "label"] == pytest.approx(0.2)
