from __future__ import annotations

import pandas as pd

from portfolio.execution_assumptions import ExecutionAssumptions
from portfolio.execution_engine import run_execution


def base_market(**overrides):
    rows = []
    for date in pd.bdate_range("2026-01-02", periods=3):
        row = {"datetime": date, "instrument": "A", "open": 10.0, "close": 10.0, "volume": 10000, "amount": 100000, "can_buy": True, "can_sell": True, "limit_up": False, "limit_down": False, "suspended": False}; row.update(overrides); rows.append(row)
    return pd.DataFrame(rows)


def scores():
    return pd.DataFrame({"datetime": pd.bdate_range("2026-01-02", periods=3), "instrument": "A", "composite_score": 1.0})


def test_limit_up_buy_rejected() -> None:
    result = run_execution(scores(), base_market(limit_up=True), ExecutionAssumptions(top_k=1, rebalance_every=1, initial_cash=100000))
    assert "limit_or_tradability" in set(result["rejected_orders"].reason)


def test_suspension_rejected() -> None:
    result = run_execution(scores(), base_market(suspended=True), ExecutionAssumptions(top_k=1, rebalance_every=1, initial_cash=100000))
    assert "suspended" in set(result["rejected_orders"].reason)


def test_volume_limit_produces_partial_fill_and_lot() -> None:
    result = run_execution(scores(), base_market(volume=1000), ExecutionAssumptions(top_k=1, rebalance_every=1, initial_cash=100000, max_participation_rate=0.2))
    assert not result["partial_fills"].empty
    assert (result["executed_orders"].shares % 100 == 0).all()


def test_missing_holding_quote_uses_last_close_not_zero() -> None:
    dates = pd.bdate_range("2026-01-02", periods=3)
    market = base_market().loc[lambda frame: ~((frame.datetime == dates[2]) & (frame.instrument == "A"))]
    market = pd.concat([market, pd.DataFrame([{"datetime": dates[2], "instrument": "B", "open": 20.0, "close": 20.0, "volume": 10000, "amount": 200000, "can_buy": True, "can_sell": True, "limit_up": False, "limit_down": False, "suspended": False}])], ignore_index=True)
    result = run_execution(scores(), market, ExecutionAssumptions(top_k=1, rebalance_every=1, initial_cash=100000))
    final = result["daily_accounting"].iloc[-1]
    assert final["holding_valuation_missing_count"] == 1
    assert final["nav"] > final["cash"]


def test_buy_affordability_reserves_commission() -> None:
    result = run_execution(scores(), base_market(), ExecutionAssumptions(top_k=1, rebalance_every=1, initial_cash=1005, slippage_bps=0))
    daily = result["daily_accounting"]
    assert (daily["cash"] >= -1e-9).all()
    assert result["executed_orders"].empty


def test_reference_calendar_is_explicitly_signal_date_only() -> None:
    result = run_execution(scores(), base_market(), ExecutionAssumptions(top_k=1, rebalance_every=1, initial_cash=100000))
    assert set(result["daily_accounting"]["calendar_mode"]) == {"signal_date_only"}
