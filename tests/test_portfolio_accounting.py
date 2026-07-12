from __future__ import annotations

from portfolio.cost_model import transaction_cost
from portfolio.portfolio_constraints import round_lot


def test_round_lot() -> None:
    assert round_lot(101, 100) == 100


def test_minimum_commission_and_sell_tax() -> None:
    buy = transaction_cost("buy", 1000, 0.0003, 0.001, 5)
    sell = transaction_cost("sell", 1000, 0.0003, 0.001, 5)
    assert buy["commission"] == 5 and buy["tax"] == 0
    assert sell["commission"] == 5 and sell["tax"] == 1
