from __future__ import annotations

import pandas as pd

from portfolio.final_diagnostics import build_period_comparisons, cost_sensitivity


def test_higher_cost_never_improves_adjusted_return() -> None:
    daily = pd.DataFrame({"daily_return": [0.01, 0.0], "turnover": [0.5, 0.5]})
    result = cost_sensitivity(daily, "x", [5, 10, 30], 10).sort_values("cost_bps")
    assert result.annualized_return.is_monotonic_decreasing


def test_common_period_uses_identical_dates_for_every_method() -> None:
    left_dates = pd.bdate_range("2026-01-01", periods=5)
    right_dates = pd.bdate_range("2026-01-05", periods=5)
    frames = {
        "left": pd.DataFrame({"datetime": left_dates, "daily_return": 0.001, "turnover": 0.1, "nav": range(100, 105)}),
        "right": pd.DataFrame({"datetime": right_dates, "daily_return": 0.002, "turnover": 0.2, "nav": range(200, 205)}),
    }
    native, common, contract = build_period_comparisons(frames, ["left", "right"])
    assert set(native.trading_days) == {5}
    assert common.trading_days.nunique() == 1
    assert common.trading_days.iloc[0] == contract["common_trading_days"] == 3
    assert common.start_date.nunique() == common.end_date.nunique() == 1
    assert contract["method_date_mismatch_count"] == 2
