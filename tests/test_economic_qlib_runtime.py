"""Actual Qlib runtime, temporary 2015-2023-only calendar, no market provider values."""

from copy import deepcopy

import numpy as np
import pandas as pd
import pytest

qlib = pytest.importorskip("qlib")
from qlib.config import C, REG_CN
from qlib.data import D
from qlib.backtest.account import Account
from qlib.backtest.decision import Order
from qlib.backtest.utils import CommonInfrastructure, LevelInfrastructure
from qlib.contrib.strategy.signal_strategy import TopkDropoutStrategy
from qlib_integration.economic_exchange import EconomicOpenExchange, validate_prepared

CAL = pd.to_datetime(
    [
        "2022-12-29",
        "2022-12-30",
        "2023-01-03",
        "2023-08-24",
        "2023-08-25",
        "2023-08-28",
        "2023-12-28",
        "2023-12-29",
    ]
)
STOCKS = ["SH600000", "SZ000001", "SZ300001"]


@pytest.fixture(autouse=True)
def isolated_provider(tmp_path, monkeypatch):
    provider = tmp_path / "provider"
    (provider / "calendars").mkdir(parents=True)
    (provider / "calendars/day.txt").write_text(
        "\n".join(d.strftime("%Y-%m-%d") for d in CAL) + "\n"
    )
    qlib.init(provider_uri=str(provider), region=REG_CN, expression_cache=None, dataset_cache=None)
    C.kernels = 1
    C.joblib_backend = "sequential"

    def deny(*args, **kwargs):
        raise AssertionError("E2 synthetic runtime must never read provider research values")

    monkeypatch.setattr(D, "features", deny)


def quotes():
    rows = []
    for i, d in enumerate(CAL[1:], 1):
        for stock in STOCKS:
            rows.append(
                dict(
                    datetime=d,
                    instrument=stock,
                    raw_open=10.0,
                    raw_close=10.0,
                    previous_close=10.0,
                    adv20_shares=100000.0,
                    upper_limit=11.0,
                    lower_limit=9.0,
                    can_buy_known=True,
                    can_sell_known=True,
                    suspended_known=False,
                    open_evidence=True,
                    board="main",
                    signal_time=CAL[i - 1] + pd.Timedelta(hours=15),
                    known_at=CAL[i - 1] + pd.Timedelta(hours=18),
                    state_known_at=CAL[i - 1] + pd.Timedelta(hours=18),
                    adv_asof=CAL[i - 1] + pd.Timedelta(hours=18),
                    order_time=d + pd.Timedelta(hours=9),
                    executable_at=d + pd.Timedelta(hours=9, minutes=25),
                    valuation_time=d + pd.Timedelta(hours=15),
                    source_id="synthetic dated fixture; no real data",
                )
            )
    return pd.DataFrame(rows)


def account(cash=100000.0, holdings=None):
    assets = {"cash": cash}
    for stock, shares in (holdings or {}).items():
        assets[stock] = {"amount": shares, "price": 10.0, "count_day": 10}
    assets.pop("cash")
    return Account(
        init_cash=cash,
        position_dict=assets,
        benchmark_config={"benchmark": None},
        port_metr_enabled=False,
    )


def order(stock=STOCKS[0], side=Order.BUY, qty=100, date=CAL[1]):
    return Order(stock_id=stock, amount=qty, direction=side, start_time=date, end_time=date)


def setup(frame=None, holdings=None, cash=100000.0, date=CAL[1], **kwargs):
    ex = EconomicOpenExchange(
        execution_quotes=quotes() if frame is None else frame, calendar=CAL, **kwargs
    )
    acc = account(cash, holdings)
    ex.begin_session(date, acc, STOCKS)
    return ex, acc


@pytest.mark.parametrize("close", [0.1, 1000.0, np.nan])
def test_next_close_independence_actual_fill(close):
    q = quotes()
    q["raw_close"] = close
    ex, acc = setup(q)
    value, cost, price = ex.deal_order(order(), trade_account=acc)
    assert (value, price) == (1000.0, 10.0)
    assert cost == pytest.approx(5.01) and acc.current_position.get_cash() == pytest.approx(
        98994.99
    )


@pytest.mark.parametrize(
    "field,value",
    [("raw_open", np.nan), ("raw_open", 0.0), ("open_evidence", False), ("suspended_known", True)],
)
def test_open_missing_or_suspension_never_close_fallback(field, value):
    q = quotes()
    q[field] = value
    ex, acc = setup(q)
    v, c, p = ex.deal_order(order(), trade_account=acc)
    assert v == c == 0 and np.isnan(p)
    assert acc.current_position.get_cash() == 100000 and not acc.current_position.get_stock_list()


@pytest.mark.parametrize(
    "open_price,side,expected",
    [(11, Order.BUY, 0), (11, Order.SELL, 1100), (9, Order.SELL, 0), (9, Order.BUY, 900)],
)
def test_directional_limits(open_price, side, expected):
    q = quotes()
    q.raw_open = float(open_price)
    ex, acc = setup(q, holdings={STOCKS[0]: 100})
    v, _, _ = ex.deal_order(order(side=side), trade_account=acc)
    assert v == expected


def test_account_t1_old_new_partial_weekend_without_liquidation():
    ex, acc = setup(holdings={STOCKS[0]: 100}, date=CAL[4])
    ex.deal_order(order(qty=100, date=CAL[4]), trade_account=acc)
    ex.deal_order(order(side=Order.SELL, qty=200, date=CAL[4]), trade_account=acc)
    assert acc.current_position.get_stock_amount(STOCKS[0]) == 100
    assert ex.t_plus_one.sellable(STOCKS[0]) == 0
    with pytest.raises(ValueError, match="advance"):
        ex.begin_session(CAL[4], acc)
    ex.begin_session(CAL[5], acc)
    assert ex.t_plus_one.sellable(STOCKS[0]) == 100
    assert ex.deal_order(order(side=Order.SELL, qty=100, date=CAL[5]), trade_account=acc)[0] == 1000


def test_multiple_partial_fills_mother_cost_cap_and_conservation():
    q = quotes()
    q.adv20_shares = 55000.0
    ex, acc = setup(q)
    a = order(qty=300)
    b = order(qty=300)
    v1, c1, _ = ex.deal_order(a, trade_account=acc)
    v2, c2, _ = ex.deal_order(b, trade_account=acc)
    assert (a.deal_amount, b.deal_amount) == (300, 200)
    assert c1 + c2 == pytest.approx(5.05)  # one 5000 mother, not twice the minimum
    assert acc.current_position.get_cash() + v1 + v2 + c1 + c2 == pytest.approx(100000)
    assert ex.deal_order(order(qty=100), trade_account=acc)[0] == 0


def test_pending_sale_cannot_fund_same_open_buy_and_preview_is_pure():
    ex, acc = setup(holdings={STOCKS[0]: 100}, cash=0.0)
    copied = deepcopy(acc.current_position)
    preview = order(side=Order.SELL)
    before = ex.t_plus_one.snapshot()
    assert ex.deal_order(preview, position=copied)[0] == 1000
    assert (
        ex.t_plus_one.snapshot() == before and ex.audit_events == [] and ex.mother_fees.totals == {}
    )
    assert acc.current_position.get_stock_amount(STOCKS[0]) == 100
    assert ex.deal_order(order(side=Order.SELL), trade_account=acc)[0] == 1000
    assert ex.deal_order(order(stock=STOCKS[1]), trade_account=acc)[0] == 0
    assert ex.buy_budget == 0 and acc.current_position.get_cash() > 0


def test_outside_universe_held_missing_quote_fails_and_limit_down_keeps_inventory():
    q = quotes()
    q.loc[q.instrument.eq(STOCKS[0]), "raw_open"] = 9.0
    ex, acc = setup(q, holdings={STOCKS[0]: 100})
    assert ex.deal_order(order(side=Order.SELL), trade_account=acc)[0] == 0
    ex.begin_session(CAL[2], acc, candidates={STOCKS[1]})
    assert (
        acc.current_position.get_stock_amount(STOCKS[0]) == 100
    )  # year switch/universe exit retains inventory
    bad = quotes().query("instrument != @STOCKS[0]")
    broken = EconomicOpenExchange(execution_quotes=bad, calendar=CAL)
    with pytest.raises(ValueError, match="held stock"):
        broken.begin_session(CAL[1], acc)


@pytest.mark.parametrize(
    "column,value", [("label", 0), ("score", 1), ("volume", 100), ("nav", 1), ("high", 12)]
)
def test_schema_has_no_score_label_full_day_volume_nav(column, value):
    q = quotes()
    q[column] = value
    with pytest.raises(ValueError, match="exact schema"):
        validate_prepared(q)


def test_timing_same_close_future_fields_and_terminal_fail():
    q = quotes()
    q.signal_time = q.executable_at
    with pytest.raises(ValueError, match="timing"):
        validate_prepared(q)
    q = quotes()
    q.known_at = q.valuation_time
    with pytest.raises(ValueError, match="timing"):
        validate_prepared(q)
    q = quotes()
    q.datetime = pd.Timestamp("2024-01-02")
    with pytest.raises(ValueError, match="boundary"):
        validate_prepared(q)
    ex, acc = setup(date=CAL[-1])
    with pytest.raises(ValueError, match="boundary"):
        ex.deal_order(order(date=pd.Timestamp("2024-01-02")), trade_account=acc)
    assert acc.current_position.get_cash() == 100000


def test_native_topk_n_drop_hold_threshold_and_no_preview_side_effects():
    ex, acc = setup(holdings={STOCKS[0]: 100, STOCKS[1]: 100})
    common = CommonInfrastructure(trade_account=acc, trade_exchange=ex)
    level = LevelInfrastructure()
    level.reset_cal("day", CAL[1], CAL[1])
    scores = pd.Series(
        [1.0, 3.0, 2.0],
        index=pd.MultiIndex.from_product([[CAL[0]], STOCKS], names=["datetime", "instrument"]),
    )
    strategy = TopkDropoutStrategy(
        topk=2,
        n_drop=1,
        hold_thresh=1,
        signal=scores,
        common_infra=common,
        level_infra=level,
        forbid_all_trade_at_limit=False,
    )
    before = deepcopy(acc.current_position.position)
    result = strategy.generate_trade_decision().get_decision()
    assert [(x.stock_id, x.direction) for x in result] == [
        (STOCKS[0], Order.SELL),
        (STOCKS[2], Order.BUY),
    ]
    assert ex.t_plus_one.sold_today == {} and ex.audit_events == [] and ex.mother_fees.totals == {}
    assert acc.current_position.position == before
    # Native hold_thresh suppresses preferred replacement, separately from T+1.
    acc.current_position.update_stock_count(STOCKS[0], "day", 0)
    held = strategy.generate_trade_decision().get_decision()
    assert not any(x.direction == Order.SELL for x in held)
    assert any(
        x.direction == Order.BUY for x in held
    )  # native candidate count precedes failed sale
    # If the incumbent is better than the candidate, n_drop does not force a sale.
    strong = pd.Series([3.0, 2.0, 1.0], index=scores.index)
    strategy = TopkDropoutStrategy(
        topk=2, n_drop=1, signal=strong, common_infra=common, level_infra=level
    )
    assert strategy.generate_trade_decision().get_decision() == []
