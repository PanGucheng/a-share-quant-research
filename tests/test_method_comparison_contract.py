from __future__ import annotations

import pandas as pd

from portfolio.final_diagnostics import cost_sensitivity


def test_higher_cost_never_improves_adjusted_return() -> None:
    daily = pd.DataFrame({"daily_return": [0.01, 0.0], "turnover": [0.5, 0.5]})
    result = cost_sensitivity(daily, "x", [5, 10, 30], 10).sort_values("cost_bps")
    assert result.annualized_return.is_monotonic_decreasing
