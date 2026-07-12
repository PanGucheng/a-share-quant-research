from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path: sys.path.insert(0, str(PROJECT_ROOT))

from portfolio.final_diagnostics import cost_sensitivity, performance_summary


def main() -> int:
    daily = pd.DataFrame({"daily_return": [0.01, -0.005, 0.002], "nav": [101, 100.5, 100.7], "turnover": [0.1, 0.2, 0.1]})
    assert performance_summary(daily, "x")["method"] == "x"
    costs = cost_sensitivity(daily, "x", [5, 30], 10)
    assert costs.loc[costs.cost_bps == 30, "annualized_return"].iloc[0] < costs.loc[costs.cost_bps == 5, "annualized_return"].iloc[0]
    print("All final portfolio diagnostics synthetic validations passed."); return 0


if __name__ == "__main__": raise SystemExit(main())
