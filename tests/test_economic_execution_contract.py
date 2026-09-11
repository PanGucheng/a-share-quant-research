import math

import numpy as np
import pandas as pd
import pytest

from qlib_integration.economic_execution_contract import (
    RawSellableLedger,
    MotherOrderFees,
    CorporateActionBook,
    dated_fees,
    dated_limit_rule,
    price_bounds,
    lot_quantity,
    causal_adv20,
    execution_day,
    quote_universe,
    vacant_slots,
)
from qlib_integration.market_semantics import convert_community_market_units


def test_t1_mixed_partial_multiple_buys_weekend_and_conversion():
    l = RawSellableLedger()
    l.start_day("2023-09-01", {"A": 100})
    l.record_fill("A", "buy", 100)
    l.record_fill("A", "buy", 50)
    assert l.clip_sell("A", 250) == (100, 150)
    l.record_fill("A", "sell", 40)
    assert l.sellable("A") == 60
    l.start_day("2023-09-01", {"A": 210})  # must not re-age today's shares
    assert l.sellable("A") == 60
    with pytest.raises(ValueError, match="oversold"):
        l.record_fill("A", "sell", 61)
    l.convert_existing_shares("A", 2)
    assert l.sellable("A") == 120 and l.bought_today["A"] == 300
    l.start_day("2023-09-04", {"A": 420})
    assert l.sellable("A") == 420
    with pytest.raises(ValueError, match="reversal"):
        l.start_day("2023-09-01", {})


@pytest.mark.parametrize(
    "date,transfer,stamp",
    [
        ("2015-08-03", 0.00002, 0.001),
        ("2022-04-28", 0.00002, 0.001),
        ("2022-04-29", 0.00001, 0.001),
        ("2023-08-25", 0.00001, 0.001),
        ("2023-08-28", 0.00001, 0.0005),
    ],
)
def test_dated_fees(date, transfer, stamp):
    f = dated_fees(date, "SH")
    assert f["transfer_rate"] == transfer and f["stamp_rate"] == stamp


def test_2015_face_basis_is_gated_and_correct_in_explicit_fixture():
    with pytest.raises(ValueError, match="not ready"):
        dated_fees("2015-07-31", "SH")
    with pytest.raises(ValueError, match="par value"):
        dated_fees("2015-07-31", "SH", early2015_evidence_accepted=True)
    f = dated_fees("2015-07-31", "SH", early2015_evidence_accepted=True, par_value=1.0)
    d, _ = MotherOrderFees().quote("x", 10000.0, 1000.0, "buy", f)
    assert d == {"commission": 5.0, "stamp": 0.0, "transfer": 0.3, "implicit": 0.0}
    f = dated_fees("2015-07-31", "SZ", early2015_evidence_accepted=True)
    d, _ = MotherOrderFees().quote("x", 10000.0, 1000.0, "buy", f)
    assert d["transfer"] == 0.26


def test_partial_fill_minimum_fee_aggregation_and_pure_trials():
    fee = dated_fees("2023-08-28", "SH")
    b = MotherOrderFees()
    a, pending = b.quote("mother", 4000, 400, "buy", fee)
    assert b.totals == {} and a["commission"] == 5
    b.commit("mother", pending)
    d, pending = b.quote("mother", 6000, 600, "buy", fee)
    assert d["commission"] == 0
    assert sum(a.values()) + sum(d.values()) == pytest.approx(5.1)
    b.commit("mother", pending)
    zero, _ = b.quote("mother", 0, 0, "buy", fee)
    assert sum(zero.values()) == 0
    sell, _ = b.quote("sell", 10000, 1000, "sell", fee, 10)
    assert sell == {"commission": 5.0, "stamp": 5.0, "transfer": 0.1, "implicit": 10.0}


@pytest.mark.parametrize(
    "day,board,st,ratio",
    [
        ("2015-01-05", "main", False, 0.1),
        ("2015-01-05", "main", True, 0.05),
        ("2020-08-21", "chinext", False, 0.1),
        ("2020-08-21", "chinext", True, 0.05),
        ("2020-08-24", "chinext", False, 0.2),
        ("2020-08-24", "chinext", True, 0.2),
        ("2023-01-03", "star", True, 0.2),
    ],
)
def test_dated_limits(day, board, st, ratio):
    regime = "registration" if board == "star" else "approval"
    assert dated_limit_rule(day, board, st, 200, regime)["limit_ratio"] == ratio


def test_ipo_transition_special_unknown_and_tick():
    with pytest.raises(ValueError, match="first-day"):
        dated_limit_rule("2015-01-05", "main", False, 1, "approval")
    assert dated_limit_rule("2015-01-06", "main", False, 2, "approval")["limit_ratio"] == 0.1
    assert dated_limit_rule("2023-04-10", "main", False, 1, "registration")["limit_ratio"] is None
    assert (
        dated_limit_rule("2020-08-24", "chinext", False, 1, "registration")["limit_ratio"] is None
    )
    for special in ("relisting", "delisting_transition", "resume"):
        with pytest.raises(ValueError, match="special"):
            dated_limit_rule("2023-01-03", "main", False, 900, "approval", special=special)
    with pytest.raises(ValueError, match="unknown"):
        dated_limit_rule("2023-01-03", "main", None, 900, "approval")
    assert price_bounds(10.05, 0.1) == (9.05, 11.06)


def test_lots_units_and_odd_disposal():
    assert lot_quantity(199, "main", "buy") == 100
    assert lot_quantity(199, "star", "buy") == 0
    assert lot_quantity(201, "star", "buy") == 201
    assert lot_quantity(101, "star", "sell", 300) == 0
    assert lot_quantity(55, "main", "sell", 55) == 55
    volume, amount = convert_community_market_units(
        10, 2, 4, volume_lot_to_shares_multiplier=100, amount_to_cny_multiplier=1000
    )
    assert (volume, amount) == (2000, 4000)
    assert 20 / 2 == 10  # provider adjusted price / factor -> raw CNY/share
    with pytest.raises(ValueError):
        convert_community_market_units(
            10, 2, 4, volume_lot_to_shares_multiplier=1, amount_to_cny_multiplier=1000
        )


def test_causal_adv_only_twenty_completed_sessions_missing_not_zero():
    cal = pd.bdate_range("2023-01-03", periods=25)
    s = pd.Series(100.0, index=cal)
    s.iloc[3] = 0
    assert causal_adv20(s, cal, cal[20]) == 95
    s.iloc[20] = 1e12
    assert causal_adv20(s, cal, cal[20]) == 95
    s.iloc[2] = np.nan
    with pytest.raises(ValueError, match="missingness"):
        causal_adv20(s, cal, cal[20])
    with pytest.raises(ValueError, match="warmup"):
        causal_adv20(s, cal, cal[3])


def test_corporate_action_manual_cash_share_conservation():
    book = CorporateActionBook()
    ledger = RawSellableLedger()
    ledger.start_day("2023-09-01", {"A": 100})
    # 100 shares at 10 -> ex-dividend 9 + receivable 100, pay-date cash follows.
    receivable = book.dividend_ex("d1", 100, 1.0)
    assert 100 * 9 + receivable == 1000
    cash = book.dividend_pay("d1")
    assert cash == 100 and not book.receivables
    with pytest.raises(ValueError):
        book.dividend_pay("d1")
    ledger.record_fill("A", "buy", 100)
    shares = book.split("split", "A", 200, 2.0, ledger)
    assert shares == 400 and ledger.sellable("A") == 200 and ledger.bought_today["A"] == 200
    assert shares * 5 == 200 * 10  # true proportional split, not arbitrary factor rebasing
    # Synthetic bonus credited to all entitled shares, same-date listable multiplier.
    shares = book.split("bonus", "A", shares, 1.2, ledger)
    assert shares == 480 and ledger.sellable("A") == 240
    assert math.isclose(shares * (5 / 1.2), 2000)
    with pytest.raises(ValueError):
        book.split("bonus", "A", shares, 1.2, ledger)
    for event in ("rights_issue", "share_conversion", "delisting_cash", "delayed_bonus_listing"):
        with pytest.raises(ValueError, match="contract required"):
            book.unsupported(event)
    # Suspension causes no fill but cannot prevent independently dated cash payment.
    book.dividend_ex("suspended_dividend", 50, 0.2)
    assert book.dividend_pay("suspended_dividend") == 10


def test_pending_exit_inventory_year_switch_terminal_and_forbidden_dates():
    assert quote_universe({"B"}, {"A": 100}) == {"A", "B"}
    assert vacant_slots(1, {"A"}, {"A"}) == 0
    cal = pd.to_datetime(["2022-12-30", "2023-01-03", "2023-12-28", "2023-12-29"])
    assert execution_day(cal[0], cal) == (cal[1], "executable")
    assert execution_day(cal[-1], cal) == (None, "out_of_execution_boundary")
    for date in ("2014-12-31", "2024-01-02"):
        with pytest.raises(ValueError, match="boundary"):
            dated_fees(date, "SH")
