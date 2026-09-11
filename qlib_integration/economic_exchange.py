"""E2 opt-in strict-open extension of the existing Qlib integration.

No real strategy runner is provided. Legacy adapters/configs remain immutable.
"""

from __future__ import annotations

from copy import deepcopy
import math

import numpy as np
import pandas as pd

from .exchange_adapter import PreparedQuoteExchange, ExecutionCostBreakdown, to_qlib_quote, Order
from .economic_execution_contract import (
    bounded_date,
    execution_day,
    dated_fees,
    MotherOrderFees,
    RawSellableLedger,
    lot_quantity,
    quote_universe,
)

FIELDS = {
    "datetime",
    "instrument",
    "raw_open",
    "raw_close",
    "previous_close",
    "adv20_shares",
    "upper_limit",
    "lower_limit",
    "can_buy_known",
    "can_sell_known",
    "suspended_known",
    "open_evidence",
    "board",
    "signal_time",
    "known_at",
    "state_known_at",
    "adv_asof",
    "order_time",
    "executable_at",
    "valuation_time",
    "source_id",
}


def validate_prepared(frame):
    if set(frame.columns) != FIELDS:
        raise ValueError(
            f"prepared quote exact schema required: missing={FIELDS - set(frame.columns)}, extra={set(frame.columns) - FIELDS}"
        )
    f = frame.copy()
    for col in (
        "datetime",
        "signal_time",
        "known_at",
        "state_known_at",
        "adv_asof",
        "order_time",
        "executable_at",
        "valuation_time",
    ):
        f[col] = pd.to_datetime(f[col], errors="raise")
        if f[col].isna().any() or f[col].dt.tz is not None:
            raise ValueError("timestamps must be explicit Asia/Shanghai local naive values")
    for d in f.datetime:
        bounded_date(d)
    if (
        f.duplicated(["datetime", "instrument"]).any()
        or f.instrument.isna().any()
        or f.source_id.isna().any()
        or f.source_id.eq("").any()
    ):
        raise ValueError("invalid prepared keys/source")
    if not (f.datetime == f.datetime.dt.normalize()).all():
        raise ValueError("prepared dates must be normalized")
    temporal = (
        (f.signal_time.dt.normalize() < f.datetime)
        & (f.known_at >= f.signal_time)
        & (f.known_at < f.order_time)
        & (f.state_known_at < f.order_time)
        & (f.adv_asof.dt.normalize() < f.datetime)
        & (f.adv_asof < f.order_time)
        & (f.order_time < f.executable_at)
        & (f.executable_at < f.valuation_time)
        & (f.order_time.dt.normalize() == f.datetime)
        & (f.executable_at.dt.normalize() == f.datetime)
        & (f.valuation_time.dt.normalize() == f.datetime)
    )
    if not temporal.all():
        raise ValueError("field timing lookahead or same-close execution")
    if not f.board.isin(["main", "chinext", "star"]).all():
        raise ValueError("unknown board")
    for col in ("can_buy_known", "can_sell_known", "suspended_known", "open_evidence"):
        if f[col].isna().any() or not pd.api.types.is_bool_dtype(f[col]):
            raise ValueError(f"unknown state is not false: {col}")
    for col in ("previous_close", "adv20_shares", "upper_limit", "lower_limit"):
        if not np.isfinite(f[col]).all() or (f[col] < 0).any():
            raise ValueError(f"unknown execution field: {col}")
    if (
        (f.previous_close <= 0).any()
        or (f.lower_limit <= 0).any()
        or (f.upper_limit <= f.lower_limit).any()
    ):
        raise ValueError("exact regular-session price bounds required; special day blocked")
    return f


def prepared_to_legacy(f):
    """Feed Qlib in raw units ($factor=1); capacity is known lagged ADV only."""
    invalid = ~np.isfinite(f.raw_open) | f.raw_open.le(0) | ~f.open_evidence | f.adv20_shares.le(0)
    x = pd.DataFrame(
        dict(
            datetime=f.datetime,
            instrument=f.instrument,
            open=f.raw_open,
            close=f.previous_close,
            volume=f.adv20_shares * 0.01,
            amount=f.previous_close * f.adv20_shares * 0.01,
            execution_price=f.raw_open,
            factor=1.0,
            change=0.0,
            can_buy=f.can_buy_known & ~invalid & ~f.suspended_known & f.raw_open.lt(f.upper_limit),
            can_sell=f.can_sell_known
            & ~invalid
            & ~f.suspended_known
            & f.raw_open.gt(f.lower_limit),
            limit_up=f.raw_open.ge(f.upper_limit),
            limit_down=f.raw_open.le(f.lower_limit),
            suspended=f.suspended_known,
            lot_minimum_buy=np.where(f.board.eq("star"), 200, 100),
            lot_increment_buy=np.where(f.board.eq("star"), 1, 100),
            lot_increment_sell=np.where(f.board.eq("star"), 1, 100),
        )
    )
    quote = to_qlib_quote(x, 1.0)
    # Legacy validation assumes every non-suspended close is present. E2 separates
    # open execution from end-of-day valuation; never substitute an execution price.
    quote["$close"] = f.set_index(["instrument", "datetime"]).raw_close.reindex(quote.index)
    return quote


class EconomicOpenExchange(PreparedQuoteExchange):
    """Qlib Account/Position update path with explicit begin_session and pure previews.

    Live fills require trade_account. position-only calls are speculative and roll
    back all mutable exchange state, while still updating the caller's copied Position.
    Dates, cash budget and opening sellability must be established before either.
    """

    def __init__(self, *, execution_quotes, calendar, implicit_bps=0.0, **kwargs):
        f = validate_prepared(execution_quotes)
        self.execution_rows = f.set_index(["instrument", "datetime"]).sort_index()
        self.execution_calendar = pd.DatetimeIndex(calendar)
        for date in self.execution_calendar:
            bounded_date(date)
        for row in f.itertuples():
            nxt, status = execution_day(row.signal_time.normalize(), self.execution_calendar)
            if status != "executable" or nxt != row.datetime:
                raise ValueError("quote does not execute on next canonical session")
        self.implicit_bps = float(implicit_bps)
        if not math.isfinite(self.implicit_bps) or self.implicit_bps < 0:
            raise ValueError("invalid implicit cost assumption")
        self.mother_fees = MotherOrderFees()
        self.session_date = None
        self.buy_budget = 0.0
        self.session_filled = {}
        self.session_account = None
        super().__init__(
            prepared_quote=prepared_to_legacy(f),
            buy_commission_rate=0.0003,
            sell_commission_rate=0.0003,
            sell_tax_rate=0.001,
            minimum_commission=5.0,
            slippage_bps=0.0,
            dynamic_lot_rules=True,
            fee_schedule=None,
            freq="day",
            start_time=f.datetime.min(),
            end_time=f.datetime.max(),
            codes=sorted(f.instrument.unique()),
            deal_price="$execution_price",
            limit_threshold=("limit_buy", "limit_sell"),
            volume_threshold=None,
            trade_unit=100,
            **kwargs,
        )
        self.t_plus_one = RawSellableLedger()

    def begin_session(self, date, account, candidates=()):
        date = bounded_date(date)
        if date not in self.execution_calendar:
            raise ValueError("session off calendar")
        if self.session_date is not None and date <= self.session_date:
            raise ValueError("session must advance once; no ledger reset after buying")
        position = account.current_position
        holdings = position.get_stock_amount_dict()
        for stock in quote_universe(candidates, holdings):
            if (stock, date) not in self.execution_rows.index:
                raise ValueError("held stock/candidate missing execution and valuation coverage")
        self.session_date = date
        self.session_account = account
        self.buy_budget = position.get_cash()
        self.session_filled = {}
        self.t_plus_one.start_day(date, holdings)

    def _row(self, stock, start, end):
        date = bounded_date(start)
        end_date = bounded_date(end)
        # Qlib's daily bar ends just before the next trading session, including
        # intervening weekends. Resolve the single approved session, not EOD data.
        included = self.execution_calendar[
            (self.execution_calendar >= date) & (self.execution_calendar <= end_date)
        ]
        if list(included) != [date]:
            raise ValueError("daily open request spans trading sessions")
        key = (stock, date)
        if key not in self.execution_rows.index:
            raise ValueError("missing prepared quote; never consult provider fallback")
        return self.execution_rows.loc[key]

    def get_deal_price(self, stock_id, start_time, end_time, direction, method="ts_data_last"):
        row = self._row(stock_id, start_time, end_time)
        value = float(row.raw_open)
        return value if math.isfinite(value) and value > 0 and row.open_evidence else np.nan

    def check_stock_suspended(self, stock_id, start_time, end_time):
        row = self._row(stock_id, start_time, end_time)
        return bool(
            row.suspended_known
            or not row.open_evidence
            or not np.isfinite(row.raw_open)
            or row.raw_open <= 0
        )

    def is_stock_tradable(self, stock_id, start_time, end_time, direction=None):
        row = self._row(stock_id, start_time, end_time)
        if self.check_stock_suspended(stock_id, start_time, end_time):
            return False
        # Outside valid bounds is a data error, not a profitable synthetic fill.
        if not row.lower_limit <= row.raw_open <= row.upper_limit:
            raise ValueError("raw open outside approved price bounds")
        buy = bool(row.can_buy_known and row.raw_open < row.upper_limit)
        sell = bool(row.can_sell_known and row.raw_open > row.lower_limit)
        return buy if direction == Order.BUY else sell if direction == Order.SELL else buy or sell

    def _calc_trade_info_by_order(self, order, position, dealt_order_amount):
        row = self._row(order.stock_id, order.start_time, order.end_time)
        price = float(row.raw_open)
        side = "buy" if order.direction == Order.BUY else "sell"
        fee = dated_fees(
            self.session_date, order.stock_id[:2]
        )  # early-2015 blocked until evidence resolved
        key = (
            str(self.session_date.date()),
            order.stock_id,
            side,
        )  # one consolidated mother per day/security/side
        cap = max(0.0, row.adv20_shares * 0.01 - self.session_filled.get(order.stock_id, 0.0))
        amount = min(float(order.amount), cap)
        sellable = self.t_plus_one.sellable(order.stock_id)
        amount = lot_quantity(amount, row.board, side, sellable)
        # Qlib internally uses exactly raw shares here; factor ratios never add dividends.
        order.factor = 1.0
        available = (
            min(position.get_cash(), self.buy_budget) if side == "buy" else position.get_cash()
        )
        delta, pending = self.mother_fees.quote(
            key, amount * price, amount, side, fee, self.implicit_bps
        )
        while amount > 0 and (
            (amount * price + sum(delta.values()) > available + 1e-8)
            if side == "buy"
            else (sum(delta.values()) > available + amount * price + 1e-8)
        ):
            increment = 1 if row.board == "star" else 100
            amount = lot_quantity(max(0.0, amount - increment), row.board, side, sellable)
            delta, pending = self.mother_fees.quote(
                key, amount * price, amount, side, fee, self.implicit_bps
            )
        order.deal_amount = amount
        if amount:
            self.mother_fees.commit(key, pending)
            self.session_filled[order.stock_id] = (
                self.session_filled.get(order.stock_id, 0.0) + amount
            )
            if side == "buy":
                self.buy_budget -= amount * price + sum(delta.values())
        self._last_sell_stamp_tax_rate = fee["stamp_rate"]
        self._last_transfer_fee_rate = fee["transfer_rate"]
        self._last_fee_schedule_id = "economic_dated_v1"
        explicit = delta["commission"] + delta["stamp"] + delta["transfer"]
        self._last_cost = ExecutionCostBreakdown(
            delta["commission"],
            delta["stamp"],
            delta["transfer"],
            delta["implicit"],
            explicit,
            explicit + delta["implicit"],
        )
        return (
            price,
            amount * price,
            sum(delta.values()),
        )  # implicit charge in cash; raw fill stays in bounds

    def deal_order(self, order, trade_account=None, position=None, dealt_order_amount=None):
        date = bounded_date(order.start_time)
        if (
            not math.isfinite(order.amount)
            or order.amount < 0
            or order.direction not in (Order.BUY, Order.SELL)
        ):
            raise ValueError("invalid raw-share order")
        if date != self.session_date or (trade_account is None and position is None):
            raise ValueError("begin_session with live account required before execution/preview")
        if trade_account is not None and (
            trade_account is not self.session_account or position is not None
        ):
            raise ValueError("different account or ambiguous mutation")
        # Parent records successful fills and updates Qlib Account/Position. Restore
        # every exchange-side mutable object for Topk-style copied-position preview.
        mutable = (
            "t_plus_one",
            "mother_fees",
            "session_filled",
            "buy_budget",
            "audit_events",
            "_event_counter",
            "_last_cost",
            "_last_sell_stamp_tax_rate",
            "_last_transfer_fee_rate",
            "_last_fee_schedule_id",
            "unpriceable_price_requests",
        )
        preview = trade_account is None
        saved = {name: deepcopy(getattr(self, name)) for name in mutable} if preview else {}
        try:
            return super().deal_order(
                order,
                trade_account=trade_account,
                position=position,
                dealt_order_amount=deepcopy(dealt_order_amount) if preview else dealt_order_amount,
            )
        finally:
            for name, value in saved.items():
                setattr(self, name, value)
