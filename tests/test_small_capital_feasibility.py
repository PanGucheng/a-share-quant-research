from decimal import Decimal, ROUND_HALF_UP

import numpy as np
import pandas as pd
import pytest

from qlib_integration.small_capital_feasibility import (
    affordable_quantity, buffered_members, hash_order, personal_fees,
)
from scripts.study_small_capital_feasibility import quantities, basket_summary


def independent_fee(value, sell=False, transfer=.00001):
    def cents(x):
        return float(Decimal(str(x)).quantize(Decimal(".01"), rounding=ROUND_HALF_UP))
    return cents(max(5, value * .00025)) + cents(value * transfer) + (cents(value * .0005) if sell else 0)


@pytest.mark.parametrize("board", ["main", "star"])
def test_max_affordable_against_exhaustive_oracle(board):
    for price in (1.23, 10, 100.01):
        for budget in (5, 205, 1005.01, 4750, 20005, 31666.6666667):
            unit, minimum = (1, 200) if board == "star" else (100, 100)
            valid = [q for q in range(minimum, int(budget / price) + 1, unit)
                     if q * price + independent_fee(q * price) <= budget]
            assert affordable_quantity(price, budget, board, personal_fees("2023-08-28", "SH")) == (valid[-1] if valid else 0)


def test_unknown_retained_open_not_quantity_input_and_roundtrip_fees():
    f = pd.DataFrame(dict(reference_close=[10., np.nan], open=[100., 1.], adv20=[1e6, np.nan],
                          board=["main", "main"], unit_anomaly=[False, True]), index=["SH600000", "SZ000001"])
    q = quantities(f, "2023-08-28", 4750)
    assert q.iloc[0].quantity == 400 and np.isnan(q.iloc[1].quantity)
    r = basket_summary(q, q, "2023-08-28", 10000, 2)
    assert r["unknown_price"] == 1 and r["unknown_or_bad_adv"] == 1
    assert r["reference_invested_fraction"] == .4
    assert r["reference_cash_fraction"] == pytest.approx(1 - (4000 + 5.04) / 10000)
    assert r["replacement_sell_buy_fee_bps"] == pytest.approx(12.08)
    # Observing a much cheaper next open cannot increase the planned quantity.
    f["open"] = .1
    assert quantities(f, "2023-08-28", 4750).iloc[0].quantity == 400


def test_fee_assumption_does_not_modify_historical_authority():
    from qlib_integration.economic_execution_contract import dated_fees
    assert personal_fees("2020-08-28", "SH")["commission_rate"] == .00025
    assert dated_fees("2020-08-28", "SH")["commission_rate"] == .0003
    for date in ("2015-01-05", "2024-01-02"):
        with pytest.raises(ValueError):
            personal_fees(date, "SH")


def test_fixed_k_state_against_naive_membership_and_absence():
    rng = np.random.default_rng(8)
    for k in (1, 5, 12):
        prior = []
        for _ in range(60):
            ranked = list(rng.permutation([f"s{i}" for i in range(40)]))[:int(rng.integers(0, 41))]
            keep = {s for s in prior if s in ranked and ranked.index(s) < 2 * k}
            need = max(0, k - len(keep))
            incoming = [s for s in ranked[:k] if s not in keep][:need]
            expected = keep | set(incoming)
            actual = buffered_members(ranked, prior, k, 2 * k)
            assert set(actual) == expected and len(actual) <= k
            prior = actual
    assert buffered_members(["b", "c", "a"], ["a"], 1, 2) == ["b"]
    with pytest.raises(ValueError):
        buffered_members(["a", "a"], [], 1, 2)


def test_hash_baskets_are_order_invariant_and_nested():
    names = [f"SH{i:06}" for i in range(500)]
    order = hash_order(names, "2020-08-28", 1)
    assert order == hash_order(names[::-1], "2020-08-28", 1)
    assert set(order[:200]).isdisjoint(order[200:400])
    assert order != hash_order(names, "2020-08-28", 2)
