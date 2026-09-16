# ruff: noqa: E402
"""Actual native RQAlpha tests; scalar expectations do not import its accounting."""

from copy import deepcopy
from pathlib import Path
import json

import numpy as np
import pytest

pytest.importorskip("rqalpha", reason="optional isolated migration environment")
from rqalpha.const import SIDE, POSITION_EFFECT, INSTRUMENT_TYPE
from rqalpha.interface import TransactionCostArgs
from rqalpha.model.instrument import Instrument
from rqalpha.mod.rqalpha_mod_sys_accounts.position_model import StockPosition
from rqalpha.mod.rqalpha_mod_sys_transaction_cost.deciders import StockTransactionCostDecider

from .adapter import FixtureSource, DatedCost, bounded, event_guard
from .harness import STOCK, advance, bar, native_session, run, trade

RESULTS = {}
DAYS = ["2020-08-20", "2020-08-21", "2020-08-24", "2020-08-25", "2020-08-26"]
FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures/sealed_canary.json").read_text(encoding="utf-8")
)


def source(**kw):
    return FixtureSource(DAYS, {(STOCK, d): bar(d) for d in DAYS}, **kw)


def test_a_sealed_real_canary_and_signal_lag():
    v = FIXTURE["real_canary"]
    s = source()
    # Only 24-Aug prices are real; the idle surrounding calendar rows are synthetic.
    s.bars[STOCK, DAYS[2]].update(
        open=v["open"],
        close=v["close"],
        limit_up=v["state"]["upper_limit"],
        limit_down=v["state"]["lower_limit"],
        capacity=int(v["adv20"] * 0.01) // 100 * 100,
    )
    intent = {}

    def close(c, order):
        if str(c.now.date()) == v["signal_day"]:
            intent.update(signal=v["signal_day"], qty=100)

    def opening(c, order):
        if str(c.now.date()) == v["execution_day"]:
            assert intent == dict(signal=v["signal_day"], qty=100)
            order(STOCK, intent["qty"])

    r = run(s, start=DAYS[1], end=DAYS[2], opening=opening, closing=close, rate=0.0003)
    assert len(r["trades"]) == 1
    t = r["trades"][0]
    assert (t["date"], t["price"], t["shares"]) == (v["execution_day"], 10.57, 100)
    assert t["cost"] == pytest.approx(5.02)
    last = r["snapshots"][-1]
    assert last["cash"] == pytest.approx(8937.98)
    assert last["positions"][STOCK]["mark"] == 10.46
    assert last["positions"][STOCK]["quantity"] == 100
    RESULTS["A"] = dict(
        result=r,
        core_scalar_cash=8937.98,
        old_core_rate=0.0003,
        note="Matched existing C1 scalar oracle; 24-Aug real evidence, idle dates synthetic; no strategy NAV",
    )


def test_b_t1_and_lot():
    def opening(c, order):
        if c.now.date().isoformat() == DAYS[1]:
            order(STOCK, 150)  # native API rounds to one lot
            order(STOCK, -100)
        else:
            order(STOCK, -100)

    r = run(source(), start=DAYS[1], end=DAYS[2], opening=opening)
    assert [t["side"] for t in r["trades"]] == ["BUY", "SELL"]
    assert r["orders"][1] is None
    assert r["snapshots"][0]["positions"][STOCK]["today_non_closable"] == 100
    assert r["snapshots"][0]["positions"][STOCK]["closable"] == 0
    assert r["snapshots"][-1]["cash"] == pytest.approx(9988.96)
    RESULTS["B"] = r


def test_c_partial_parent_fees_estimates_and_restore():
    env = native_session(source())
    ins = env.data_proxy.instrument_not_none(STOCK)
    cost = env.get_transaction_cost_decider(INSTRUMENT_TYPE.CS)

    def args(q, oid):
        return TransactionCostArgs(ins, 10, q, SIDE.BUY, POSITION_EFFECT.OPEN, oid)

    assert cost.calc(args(100, None)).total == pytest.approx(5.02)
    assert not cost.get_state()
    first = cost.calc(args(100, 77))
    restored = DatedCost()
    restored.set_state(cost.get_state())
    second = restored.calc(args(100, 77))
    third = restored.calc(args(2800, 77))
    assert [x.commission for x in (first, second, third)] == [5, 0, 2.5]
    assert sum(x.other_fees for x in (first, second, third)) == pytest.approx(0.6)
    native = StockTransactionCostDecider(0.00025 / 0.0008, 5, 1, True, env.event_bus)
    native_parts = [native.calc(args(q, 88)).commission for q in (100, 100, 2800)]
    assert native_parts == pytest.approx([5, 0, 2.5])
    RESULTS["C_fee"] = dict(
        adapter_commissions=[5, 0, 2.5],
        native_commissions=native_parts,
        transfer=0.6,
        estimates_pure=True,
        custom_fee_restore_exact=True,
    )


def test_c_cash_partial_volume_and_multisale():
    r = run(
        source(),
        start=DAYS[1],
        end=DAYS[1],
        cash=2500,
        partial=True,
        opening=lambda c, o: o(STOCK, 1000),
    )
    assert r["trades"][0]["shares"] == 200
    assert r["snapshots"][-1]["cash"] == pytest.approx(494.96)
    assert r["orders"][0]["status"] == "CANCELLED"
    s = source()
    s.bars[STOCK, DAYS[1]]["capacity"] = 100
    v = run(s, start=DAYS[1], end=DAYS[1], cash=20000, opening=lambda c, o: o(STOCK, 1000))
    assert v["trades"][0]["shares"] == 100 and v["orders"][0]["status"] == "CANCELLED"

    def opening(c, o):
        if c.now.date().isoformat() == DAYS[1]:
            o(STOCK, 200)
        else:
            o(STOCK, -100)
            o(STOCK, -100)
            o(STOCK, 100)

    m = run(source(), start=DAYS[1], end=DAYS[2], cash=2500, opening=opening)
    assert [t["shares"] for t in m["trades"]] == [200, 100, 100, 100]
    assert m["snapshots"][-1]["cash"] == pytest.approx(1477.9)
    RESULTS["C_execution"] = dict(insufficient_cash=r, volume=v, multisale=m)


def dividend(record=20200722, ex=20200723, pay=20200723, amount=0.6):
    return np.array(
        [(record, 20200716, amount, ex, pay, 1.0)],
        dtype=[
            ("book_closure_date", "i8"),
            ("announcement_date", "i8"),
            ("dividend_cash_before_tax", "f8"),
            ("ex_dividend_date", "i8"),
            ("payable_date", "i8"),
            ("round_lot", "f8"),
        ],
    )


def test_d_real_terms_and_delayed_receivable():
    row = FIXTURE["dividend_rows"][0]
    assert row["status"] == "resolved_gross_entitlement"
    assert row["gross_cash_per_share"] == 0.6 and row["pay_date"] == "20200723"
    days = ["2020-07-21", "2020-07-22", "2020-07-23", "2020-07-24", "2020-07-27"]

    def check(pay):
        s = FixtureSource(
            days, {(STOCK, d): bar(d) for d in days}, dividends={STOCK: dividend(pay=pay)}
        )
        env = native_session(s)
        a = env.portfolio.stock_account
        trade(env, STOCK, 100, 10)
        p = a.get_position(STOCK)
        assert p.dividend_receivable == 0
        advance(env, days[2])
        if pay == 20200724:
            assert a.cash == 9000 and p.dividend_receivable == 60
            trade(env, STOCK, -100, 9.4)
            assert p.quantity == 0 and p.dividend_receivable == 60
            state = deepcopy(a.get_state())
            a.set_state(state)
            advance(env, days[3])
            assert a.cash == pytest.approx(10000)
        else:
            assert a.cash == 9060 and p.dividend_receivable == 0
            assert p.avg_price == pytest.approx(9.4)
        return dict(cash=a.cash, receivable=a.get_position(STOCK).dividend_receivable)

    RESULTS["D"] = dict(
        real_event_terms=check(20200723),
        delayed_synthetic=check(20200724),
        price_basis="synthetic 10; real event terms only",
        tax_basis="gross before dividend income tax",
    )


def test_d_tax_opt_in_and_registration_gap():
    ds = dividend(record=20200821, ex=20200824, pay=20200825)
    env = native_session(source(dividends={STOCK: ds}))
    a = env.portfolio.stock_account
    trade(env, STOCK, 100, 10)
    advance(env, DAYS[2])
    StockPosition.dividend_tax_enabled = True
    # Native tax publishes PAY_TAXES; test that event independently, not fake net entitlement.
    from rqalpha.core.events import EVENT

    taxes = []
    env.event_bus.add_listener(EVENT.PAY_TAXES, lambda e: taxes.append(e.delta_amount))
    trade(env, STOCK, -100, 9.4)
    assert taxes == [12.0]
    # Registration and ex separated by a trading session: native uses ex-day quantity.
    gap = dividend(record=20200821, ex=20200825, pay=20200825)
    env = native_session(source(dividends={STOCK: gap}))
    a = env.portfolio.stock_account
    trade(env, STOCK, 100, 10)
    advance(env, DAYS[2])
    trade(env, STOCK, -100, 10)
    advance(env, DAYS[3])
    assert a.cash == 10000  # missing recorded entitlement vs project +60
    RESULTS["D_gaps"] = dict(
        short_holding_tax_event=12,
        separated_record_ex_native_cash=10000,
        project_oracle_cash=10060,
        disposition="guard non-adjacent record/ex",
    )


@pytest.mark.parametrize("qty,ratio,expected", [(100, 1.1, 110), (101, 1.5, 152)])
def test_e_split_rounding(qty, ratio, expected):
    splits = np.array([(20200824000000, ratio)], dtype=[("ex_date", "i8"), ("split_factor", "f8")])
    env = native_session(source(splits={STOCK: splits}))
    a = env.portfolio.stock_account
    trade(env, STOCK, qty, 15)
    advance(env, DAYS[2])
    p = a.get_position(STOCK)
    assert p.quantity == expected and p.avg_price == pytest.approx(15 / ratio)
    if qty == 101:
        with pytest.raises(ValueError, match="fractional"):
            event_guard("split", quantity=qty, ratio=ratio, ex_date=DAYS[2], list_date=DAYS[2])
    with pytest.raises(ValueError, match="pending bonus"):
        event_guard("split", quantity=100, ratio=1.1, ex_date=DAYS[2], list_date=DAYS[3])
    RESULTS[f"E_{qty}"] = dict(
        native_shares=p.quantity,
        avg=p.avg_price,
        closable=p.closable,
        fractional_guard=qty == 101,
        delayed_bonus_guard=True,
        real_event=False,
    )


def test_f_transformation_and_terminal_default():
    new = "600001.XSHG"
    s = source(transforms={STOCK: (new, 2.0)})
    s.instruments[STOCK] = Instrument(
        dict(
            order_book_id=STOCK,
            symbol=STOCK,
            type="CS",
            exchange="XSHG",
            board_type="MainBoard",
            round_lot=100,
            market_tplus=1,
            listed_date="2015-01-01",
            de_listed_date=DAYS[2],
        )
    )
    s.instruments[new] = Instrument(
        dict(
            order_book_id=new,
            symbol=new,
            type="CS",
            exchange="XSHG",
            board_type="MainBoard",
            round_lot=100,
            market_tplus=1,
            listed_date="2015-01-01",
            de_listed_date="0000-00-00",
        )
    )
    s.bars.update({(new, d): bar(d, 5) for d in DAYS})
    env = native_session(s)
    a = env.portfolio.stock_account
    trade(env, STOCK, 100, 8)
    p = a.get_position(STOCK)
    p.update_last_price(10)
    before = a.cash
    from rqalpha.core.events import Event, EVENT

    env.event_bus.publish_event(Event(EVENT.SETTLEMENT, trading_dt=env.trading_dt))
    assert a.cash == before
    successor = a.get_position(new)
    assert (p.quantity, successor.quantity, successor.avg_price, successor.last_price) == (
        0,
        200,
        4,
        5,
    )
    s.transforms = {}
    env = native_session(s)
    a = env.portfolio.stock_account
    trade(env, STOCK, 100, 8)
    p = a.get_position(STOCK)
    p.update_last_price(10)
    StockPosition.cash_return_by_stock_delisted = True
    assert p.settlement(env.trading_dt.date()) == 1000 and p.quantity == 0
    with pytest.raises(ValueError, match="HALT_RETAIN"):
        event_guard("terminal_unknown", quantity=100)
    RESULTS["F"] = dict(
        synthetic_transform=dict(old=0, new=200, cost=4, mark=5, cash_continuous=True),
        unsafe_default_terminal_cash=1000,
        guard_required=True,
        real_migration_accepted=False,
    )


@pytest.mark.parametrize("state,price", [("suspended", 10), ("ordinary", 100)])
def test_state_and_limits(state, price):
    s = source()
    s.bars[STOCK, DAYS[1]].update(state=state, open=price)
    r = run(s, start=DAYS[1], end=DAYS[1], opening=lambda c, o: o(STOCK, 100))
    assert not r["trades"]
    RESULTS[f"guard_{state}_{price}"] = r


def test_same_parent_native_partial_fills():
    from rqalpha.model.order import LimitOrder

    s = source()
    s.bars[STOCK, DAYS[1]].update(capacity=100, volume=100)
    r = run(s, start=DAYS[1], end=DAYS[1], opening=lambda c, o: o(STOCK, 300, style=LimitOrder(10)))
    assert [t["shares"] for t in r["trades"]] == [100, 100]
    assert [t["commission"] for t in r["trades"]] == [5, 0]
    assert r["orders"][0]["filled"] == 200
    assert r["snapshots"][-1]["cash"] == pytest.approx(7994.96)
    RESULTS["C_native_parent_partial"] = r


def test_open_and_state_do_not_consume_current_close():
    s = source()
    row = s.bars[STOCK, DAYS[1]]
    for field in ("close", "high", "low", "volume", "total_turnover"):
        row[field] = float("nan")
    ins = s.instruments[STOCK]
    assert s.get_open_auction_bar(ins, DAYS[1])["open"] == 10
    assert s.get_open_auction_volume(ins, DAYS[1]) == 10000
    assert s.is_suspended(STOCK, [DAYS[1]]) == [False]
    RESULTS["phase_isolation"] = "open/state independent of current end-of-day fields"


def test_native_daily_next_bar_is_close_not_next_open():
    s = source()
    s.bars[STOCK, DAYS[1]]["close"] = 12
    r = run(s, start=DAYS[1], end=DAYS[1], matching="next_bar", closing=lambda c, o: o(STOCK, 100))
    assert r["trades"][0]["price"] == 12 and r["trades"][0]["date"] == DAYS[1]
    RESULTS["native_daily_next_bar_counterexample"] = r


def test_real_bonus_must_not_be_mapped_to_immediate_split():
    row = FIXTURE["bonus_rows"][0]  # earliest sealed SH600000 bonus; no outcome search
    assert row["event_id"] == "ff5570414a4164a1f6117327"
    days = ["2016-06-21", "2016-06-22", "2016-06-23", "2016-06-24", "2016-06-27"]
    splits = np.array([(20160623000000, 1.1)], dtype=[("ex_date", "i8"), ("split_factor", "f8")])
    s = FixtureSource(days, {(STOCK, d): bar(d) for d in days}, splits={STOCK: splits})
    env = native_session(s)
    trade(env, STOCK, 100, 11)
    advance(env, days[2])
    p = env.portfolio.stock_account.get_position(STOCK)
    assert p.closable == 110
    with pytest.raises(ValueError, match="pending bonus"):
        event_guard(
            "split",
            quantity=100,
            ratio=1 + row["bonus_per_share"],
            ex_date=row["ex_date"],
            list_date=row["listable_date"],
        )
    RESULTS["E_real_bonus"] = dict(
        event_id=row["event_id"],
        ex_date=row["ex_date"],
        listable_date=row["listable_date"],
        native_immediate_closable=110,
        project_required_closable=100,
        pending_bonus_required=10,
        status="INCOMPATIBLE DIRECT MAPPING / GUARD PASSED",
        price_basis="synthetic",
    )


@pytest.mark.parametrize(
    "day,transfer,stamp",
    [
        ("2022-04-28", 0.2, 10),
        ("2022-04-29", 0.1, 10),
        ("2023-08-25", 0.1, 10),
        ("2023-08-28", 0.1, 5),
    ],
)
def test_dated_fee_boundaries(day, transfer, stamp):
    env = native_session(source())
    from datetime import datetime

    env.update_time(datetime.fromisoformat(day), datetime.fromisoformat(day))
    ins = env.data_proxy.instrument_not_none(STOCK)
    args = TransactionCostArgs(ins, 10, 1000, SIDE.SELL, POSITION_EFFECT.CLOSE)
    c = env.calc_transaction_cost(args)
    assert (c.commission, c.tax, c.other_fees) == pytest.approx((5, stamp, transfer))
    RESULTS["fee_" + day] = c._asdict()


def test_early_fee_stays_unresolved_and_missing_limits_native_default():
    env = native_session(source())
    from datetime import datetime

    env.update_time(datetime(2015, 1, 5), datetime(2015, 1, 5))
    with pytest.raises(ValueError, match="early-2015"):
        env.calc_transaction_cost(
            TransactionCostArgs(
                env.data_proxy.instrument_not_none(STOCK), 10, 100, SIDE.BUY, POSITION_EFFECT.OPEN
            )
        )
    from rqalpha.utils.price_limits import reaches_limit_up

    assert reaches_limit_up(10, float("nan"), 0.01) is False
    RESULTS["missing_limit_native"] = "native returns False; adapter rejects NaN before matching"


@pytest.mark.parametrize(
    "case",
    [
        "future",
        "unknown_state",
        "missing_open",
        "missing_limit",
        "missing_capacity",
        "rights",
        "terminal",
    ],
)
def test_fail_closed(case):
    s = source()
    with pytest.raises((ValueError, KeyError)):
        if case == "future":
            bounded("2024-01-02")
        elif case in {"rights", "terminal"}:
            event_guard(case, quantity=100)
        else:
            row = s.bars[STOCK, DAYS[1]]
            if case == "unknown_state":
                row["state"] = "unresolved"
            if case == "missing_open":
                row["open"] = float("nan")
            if case == "missing_limit":
                row["limit_up"] = float("nan")
            if case == "missing_capacity":
                row["capacity"] = float("nan")
            s.get_open_auction_volume(s.instruments[STOCK], DAYS[1])
