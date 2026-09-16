"""Bounded fixture DataSource and existing fee-ledger bridge, not production adapters."""

from copy import deepcopy
from datetime import date
import math

import numpy as np
import pandas as pd
from rqalpha.const import INSTRUMENT_TYPE, SIDE, TRADING_CALENDAR_TYPE
from rqalpha.environment import Environment
from rqalpha.interface import (
    AbstractDataSource,
    AbstractMod,
    AbstractTransactionCostDecider,
    TransactionCost,
)
from rqalpha.model.instrument import Instrument
from qlib_integration.economic_execution_contract import MotherOrderFees, dated_fees


def bounded(value):
    day = pd.Timestamp(value).date()
    if not date(2015, 1, 1) <= day <= date(2023, 12, 29):
        raise ValueError("PoC date outside 2015-2023")
    return day


def event_guard(kind, *, quantity=0, ratio=1, ex_date=None, list_date=None):
    """A refusal is not a settlement. Caller must keep the last account checkpoint."""
    if kind not in {"cash", "split", "transformation"}:
        raise ValueError("HALT_RETAIN: unsupported/unknown event")
    if kind in {"split", "transformation"}:
        if (
            not math.isfinite(ratio)
            or ratio <= 0
            or not math.isclose(quantity * ratio, round(quantity * ratio))
        ):
            raise ValueError("HALT_RETAIN: fractional allocation evidence required")
    if kind == "split" and (not list_date or ex_date != list_date):
        raise ValueError("HALT_RETAIN: pending bonus is not a native immediate split")


class FixtureSource(AbstractDataSource):
    """Explicit tiny fixtures only; no bundle, remote client, research scores or fallback."""

    def __init__(
        self, calendar, bars, instruments=None, dividends=None, splits=None, transforms=None
    ):
        self.calendar = pd.DatetimeIndex([bounded(d) for d in calendar])
        if not self.calendar.is_unique or not self.calendar.is_monotonic_increasing:
            raise ValueError("calendar must be ordered and unique")
        self.bars = deepcopy(bars)
        self.dividends, self.splits, self.transforms = (
            dividends or {},
            splits or {},
            transforms or {},
        )
        self.access = []
        self.instruments = instruments or {
            s: Instrument(
                dict(
                    order_book_id=s,
                    symbol=s,
                    type="CS",
                    exchange=s.split(".")[1],
                    board_type="MainBoard",
                    round_lot=100,
                    market_tplus=1,
                    listed_date="2015-01-01",
                    de_listed_date="0000-00-00",
                )
            )
            for s, _ in bars
        }

    def get_instruments(self, id_or_syms=None, types=None):
        return [
            i
            for k, i in self.instruments.items()
            if (id_or_syms is None or k in id_or_syms) and (types is None or i.type in types)
        ]

    def get_trading_calendars(self):
        return {TRADING_CALENDAR_TYPE.CN_STOCK: self.calendar}

    def available_data_range(self, frequency):
        return self.calendar[0].date(), self.calendar[-1].date()

    def row(self, stock, dt, fields=("open", "close", "limit_up", "limit_down")):
        day = str(bounded(dt))
        self.access.append((stock, day))
        row = self.bars[(stock, day)]  # absence raises, never returns tradable defaults
        if row.get("state") not in {"ordinary", "suspended", "st"}:
            raise ValueError("unknown execution state")
        for f in fields:
            if not math.isfinite(row[f]) or row[f] <= 0:
                raise ValueError("missing price/limit evidence")
        return row

    def get_bar(self, instrument, dt, frequency):
        if frequency != "1d":
            raise ValueError("daily fixtures only")
        return self.row(instrument.order_book_id, dt)

    def get_open_auction_bar(self, instrument, dt):
        r = self.row(instrument.order_book_id, dt, fields=("open", "limit_up", "limit_down"))
        # Only open and independent limits. No high/low/close/daily volume leak.
        return dict(
            datetime=dt,
            open=r["open"],
            last=r["open"],
            limit_up=r["limit_up"],
            limit_down=r["limit_down"],
            volume=r["capacity"],
            total_turnover=0,
        )

    def get_open_auction_volume(self, instrument, dt):
        # EXPLICIT PoC capacity proxy, not measured auction volume.
        r = self.row(instrument.order_book_id, dt, fields=("open", "limit_up", "limit_down"))
        if (
            r.get("capacity_basis") != "prior_adv_proxy"
            or not math.isfinite(r["capacity"])
            or r["capacity"] < 0
        ):
            raise ValueError("missing causal capacity evidence")
        return 0 if r["state"] == "suspended" else r["capacity"]

    def history_bars(self, instrument, bar_count, frequency, fields, dt, **kwargs):
        bounded(dt)
        days = [d for d in self.calendar if d.date() <= pd.Timestamp(dt).date()][-bar_count:]
        if fields != "close" or frequency != "1d":
            raise ValueError("PoC supports previous close only")
        return np.array([self.row(instrument.order_book_id, d)["close"] for d in days])

    def is_suspended(self, order_book_id, dates):
        return [self.row(order_book_id, d, fields=())["state"] == "suspended" for d in dates]

    def is_st_stock(self, order_book_id, dates):
        return [self.row(order_book_id, d, fields=())["state"] == "st" for d in dates]

    def get_dividend(self, instrument):
        return self.dividends.get(instrument.order_book_id)

    def get_split(self, instrument):
        return self.splits.get(instrument.order_book_id)

    def get_share_transformation(self, order_book_id):
        return self.transforms.get(order_book_id)


class DatedCost(AbstractTransactionCostDecider):
    """Reuse the project schedule/rounding. No-id estimates never commit state."""

    def __init__(self, rate=0.00025):
        self.rate = rate
        self.ledger = MotherOrderFees()

    def calc(self, args):
        if args.quantity <= 0:
            return TransactionCost.zero()
        env = Environment.get_instance()
        day = str(bounded(env.trading_dt))
        exchange = {"XSHG": "SH", "XSHE": "SZ"}[args.instrument.order_book_id.split(".")[1]]
        fee = dated_fees(day, exchange)  # early-2015 unresolved -> rejects
        fee["commission_rate"] = self.rate
        side = "buy" if args.side == SIDE.BUY else "sell"
        key = (day, args.instrument.order_book_id, side, args.order_id)
        charges, pending = self.ledger.quote(
            key, args.price * args.quantity, args.quantity, side, fee
        )
        if args.order_id is not None:
            self.ledger.commit(key, pending)
        return TransactionCost(charges["commission"], charges["stamp"], charges["transfer"])

    def get_state(self):
        return deepcopy(self.ledger.totals)

    def set_state(self, state):
        self.ledger.totals = deepcopy(state)


# Only the test runner sets this object; no filesystem or data discovery on import.
ACTIVE_SOURCE = None
ACTIVE_RATE = 0.00025


class FixtureMod(AbstractMod):
    def start_up(self, env, mod_config):
        if ACTIVE_SOURCE is None:
            raise ValueError("explicit fixture required")
        env.set_data_source(ACTIVE_SOURCE)
        env.set_transaction_cost_decider(INSTRUMENT_TYPE.CS, DatedCost(ACTIVE_RATE))

    def tear_down(self, code, exception=None):
        return None


def load_mod():
    return FixtureMod()
