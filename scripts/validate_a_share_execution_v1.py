from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path: sys.path.insert(0, str(PROJECT_ROOT))

from portfolio.cost_model import transaction_cost
from portfolio.execution_assumptions import ExecutionAssumptions
from portfolio.execution_engine import run_execution
from portfolio.portfolio_constraints import round_lot


def main() -> int:
    assert round_lot(101, 100) == 100
    assert transaction_cost("buy", 1000, 0.0003, 0.001, 5)["tax"] == 0
    assert transaction_cost("sell", 1000, 0.0003, 0.001, 5)["tax"] == 1
    dates = pd.bdate_range("2026-01-02", periods=3)
    scores = pd.DataFrame({"datetime": dates, "instrument": "A", "composite_score": 1.0})
    market = pd.DataFrame([{"datetime": date, "instrument": "A", "open": 10.0, "close": 10.0, "volume": 1000, "amount": 10000, "can_buy": True, "can_sell": True, "limit_up": False, "limit_down": False, "suspended": False} for date in dates])
    result = run_execution(scores, market, ExecutionAssumptions(top_k=1, rebalance_every=1, initial_cash=100000, max_participation_rate=0.2))
    assert result["daily_accounting"].accounting_error.abs().max() <= 1e-6
    assert (pd.to_datetime(result["executed_orders"].signal_date) < pd.to_datetime(result["executed_orders"].execution_date)).all()
    print("All A-share execution synthetic validations passed.")
    return 0


if __name__ == "__main__": raise SystemExit(main())
