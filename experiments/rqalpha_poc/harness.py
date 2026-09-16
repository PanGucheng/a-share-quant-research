"""Tiny offline RQAlpha runs with analyser disabled; engineering accounting only."""

from contextlib import contextmanager
from datetime import datetime
import socket

from rqalpha import run_func
from rqalpha.api import order_shares
from rqalpha.core.events import EVENT
from rqalpha.environment import Environment
from . import adapter

STOCK = "600000.XSHG"


def bar(day, price=10.0, close=None, capacity=10000, state="ordinary"):
    return dict(
        datetime=int(day.replace("-", "") + "000000"),
        open=price,
        close=close or price,
        high=max(price, close or price),
        low=min(price, close or price),
        volume=987654,
        total_turnover=9876540.0,
        limit_up=100.0,
        limit_down=1.0,
        state=state,
        capacity=capacity,
        capacity_basis="prior_adv_proxy",
    )


@contextmanager
def offline():
    original = socket.socket.connect, socket.socket.connect_ex

    def deny(*args, **kwargs):
        raise RuntimeError("PoC runtime network forbidden")

    socket.socket.connect = socket.socket.connect_ex = deny
    try:
        yield
    finally:
        socket.socket.connect, socket.socket.connect_ex = original


def run(
    source,
    *,
    start,
    end,
    cash=10000,
    opening=None,
    closing=None,
    rate=0.00025,
    partial=False,
    matching="current_bar",
    dividend_tax=False,
):
    adapter.ACTIVE_SOURCE, adapter.ACTIVE_RATE = source, rate
    trades, snapshots, orders = [], [], []

    def capture(context, phase):
        env = Environment.get_instance()
        a = context.portfolio.stock_account
        positions = {
            p.order_book_id: dict(
                quantity=p.quantity,
                closable=p.closable,
                today_non_closable=p.get_state()["non_closable"],
                avg=p.avg_price,
                mark=p.last_price,
                receivable=p.dividend_receivable,
            )
            for p in a.get_positions()
        }
        snapshots.append(
            dict(date=str(env.trading_dt.date()), phase=phase, cash=a.cash, positions=positions)
        )

    def init(context):
        def on_trade(event):
            t = event.trade
            trades.append(
                dict(
                    date=str(t.trading_datetime.date()),
                    instrument=t.order_book_id,
                    side=t.side.name,
                    shares=t.last_quantity,
                    price=t.last_price,
                    cost=t.transaction_cost,
                    commission=t.commission,
                    tax=t.tax,
                )
            )

        Environment.get_instance().event_bus.add_listener(EVENT.TRADE, on_trade)
        Environment.get_instance().event_bus.add_listener(
            EVENT.POST_SETTLEMENT, lambda event: capture(context, "settlement")
        )

    def open_auction(context, bars):
        def submit(stock, shares, **kwargs):
            orders.append(order_shares(stock, shares, **kwargs))

        if opening:
            opening(context, submit)
        capture(context, "open")

    def handle_bar(context, bars):
        if closing:
            closing(context, lambda stock, shares: orders.append(order_shares(stock, shares)))
        capture(context, "close")

    config = dict(
        base=dict(
            start_date=start,
            end_date=end,
            frequency="1d",
            accounts={"stock": cash},
            rqdatac_uri="disabled",
            auto_update_bundle=False,
            forced_liquidation=False,
            capital_gain_tax_rate=0,
            partial_fill_on_insufficient_cash=partial,
        ),
        extra=dict(log_level="error"),
        mod=dict(
            sys_analyser=dict(enabled=False),
            sys_progress=dict(enabled=False),
            sys_transaction_cost=dict(enabled=False),
            sys_accounts=dict(
                dividend_reinvestment=False,
                dividend_tax_enabled=dividend_tax,
                cash_return_by_stock_delisted=False,
            ),
            sys_simulation=dict(
                matching_type=matching,
                slippage=0,
                volume_limit=True,
                volume_percent=1,
                price_limit=True,
            ),
            fixture=dict(enabled=True, lib=adapter.__name__, priority=90),
        ),
    )
    with offline():
        run_func(config=config, init=init, open_auction=open_auction, handle_bar=handle_bar)
    orders = [
        None
        if o is None
        else dict(
            status=o.status.name, quantity=o.quantity, filled=o.filled_quantity, message=o.message
        )
        for o in orders
    ]
    return dict(
        trades=trades, snapshots=snapshots, orders=orders, source_access=sorted(set(source.access))
    )


def native_session(source, cash=10000):
    """Real Environment/DataProxy/Portfolio for direct event and restore probes."""
    from rqalpha.utils import RqAttrDict
    from rqalpha.data.data_proxy import DataProxy
    from rqalpha.portfolio import Portfolio
    from rqalpha.const import INSTRUMENT_TYPE
    from rqalpha.mod.rqalpha_mod_sys_accounts.position_model import StockPosition
    from types import SimpleNamespace

    day = source.calendar[1].date()
    config = RqAttrDict(
        dict(
            base=dict(
                start_date=day,
                market="CN",
                accounts={"STOCK": cash},
                frequency="1d",
                round_price=False,
                forced_liquidation=False,
                capital_gain_tax_rate=0,
                partial_fill_on_insufficient_cash=False,
            ),
            extra=dict(),
        )
    )
    env = Environment(config, False)
    env.set_broker(SimpleNamespace(get_open_orders=lambda stock=None: []))
    env.set_data_source(source)
    price_board = SimpleNamespace(
        get_last_price=lambda stock: source.row(stock, env.trading_dt)["close"]
    )
    env.set_price_board(price_board)
    env.set_data_proxy(DataProxy(source, price_board))
    env.set_transaction_cost_decider(INSTRUMENT_TYPE.CS, adapter.DatedCost())
    StockPosition.t_plus_enabled = True
    StockPosition.dividend_reinvestment = StockPosition.dividend_tax_enabled = False
    StockPosition.cash_return_by_stock_delisted = False
    env.set_portfolio(Portfolio({"STOCK": cash}, [], 0, env))
    return env


def advance(env, day):
    from rqalpha.core.events import Event

    dt = datetime.fromisoformat(day)
    env.update_time(dt, dt)
    env.event_bus.publish_event(Event(EVENT.PRE_BEFORE_TRADING, trading_dt=dt))


def trade(env, stock, shares, price, *, fee=None):
    from rqalpha.const import SIDE, POSITION_EFFECT
    from rqalpha.interface import TransactionCost
    from rqalpha.model.trade import Trade

    t = Trade.__from_create__(
        None,
        price,
        abs(shares),
        SIDE.BUY if shares > 0 else SIDE.SELL,
        POSITION_EFFECT.OPEN if shares > 0 else POSITION_EFFECT.CLOSE,
        stock,
        transaction_cost=fee or TransactionCost.zero(),
    )
    env.portfolio.stock_account.apply_trade(t)
    return t
