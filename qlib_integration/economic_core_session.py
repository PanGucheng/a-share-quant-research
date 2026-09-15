"""Atomic E2 day integration on Qlib. No strategies, metrics or real-data runner."""

from copy import deepcopy
from dataclasses import dataclass
import math

import pandas as pd
from qlib.backtest.decision import Order

from .economic_core_inputs import prepared_rows
from .economic_event_position import EventPosition
from .economic_exchange import EconomicOpenExchange
from .economic_execution_contract import bounded_date, execution_day
from .economic_mvp_scope import (
    Decision, holding_continuity, position_exposures, require_scope_order, scope_account, visible_fact,
)


@dataclass(frozen=True)
class Intent:
    instrument: str
    shares: float
    side: str


class CoreHalt(ValueError):
    pass


def exposures(position):
    result = position_exposures(position)
    for key, shares in position.entitlements.items():
        if key not in position.events or not math.isfinite(shares) or shares < 0:
            raise ValueError("invalid registered entitlement snapshot")
        if shares > 0 and (key, "ex") not in position.applied:
            result.add(position.events[key].instrument)
    return result


def check_scope(account, candidates, phase):
    historical = phase.mode == "historical"
    result = scope_account(account, candidates, phase.at, phase.facts, phase.states, historical=historical)
    p = account.current_position
    for stock in exposures(p) - set(result["holdings"]):
        needs_mark = any(e.instrument == stock and e.bonus_per_share > 0 for e in p.events.values())
        result["holdings"][stock] = holding_continuity(
            stock, phase.at, phase.facts.get(stock, {}), phase.states.get(stock), needs_market_mark=needs_mark,
            historical=historical
        )
        result["entries"].pop(stock, None)
    for key, event in p.events.items():
        pending = (p.entitlements.get(key, 0) > 0 and (
            (key, "ex") not in p.applied
            or (event.entitlement_cash_per_share > 0 and (key, "pay") not in p.applied)
            or (event.bonus_per_share > 0 and (key, "list") not in p.applied)
        )) or key in p.pending_bonus or key in p.book.receivables
        if event.instrument in exposures(p) and pending and key not in phase.covered_events.get(event.instrument, ()):
            result["holdings"][event.instrument] = Decision("HALT_RETAIN", ("event_coverage_omits_registered_right",))
    if phase.phase == "C":
        for stock in exposures(p):
            if not set(phase.covered_events.get(stock, ())) <= set(p.events):
                result["holdings"][stock] = Decision("HALT_RETAIN", ("new_close_event_requires_terms_and_record_capture",))
    assets = set()
    for stock in result["holdings"]:
        fact = visible_fact(phase.facts.get(stock, {}).get("asset_id", ()), phase.at, historical=historical)
        if fact and fact.value in assets:
            result["holdings"][stock] = Decision("HALT_RETAIN", ("duplicate_held_asset",))
        if fact:
            assets.add(fact.value)
    for stock in result["entries"]:
        fact = visible_fact(phase.facts.get(stock, {}).get("asset_id", ()), phase.at, historical=historical)
        if fact and fact.value in assets:
            result["entries"][stock] = Decision("NO_NEW_ENTRY", ("pending_right_asset_collision",))
    result["preserved_exposures"] = tuple(sorted(exposures(p)))
    if any(x.action == "HALT_RETAIN" for x in result["holdings"].values()):
        result["account_action"] = "HALT_RETAIN"
    return result


def marks(phase):
    result = {}
    for stock, facts in phase.facts.items():
        mark = visible_fact(facts.get("valuation_mark", ()), phase.at, historical=phase.mode == "historical")
        if mark and mark.observed_on == phase.date and not isinstance(mark.value, bool):
            if isinstance(mark.value, (int, float)) and math.isfinite(mark.value) and mark.value > 0:
                result[stock] = mark.value
    return result


class _ScopedExchange(EconomicOpenExchange):
    def _opening_raw_shares(self, position, trading_date):
        # Carry assets deliberately have no ordinary quote/factor row.
        return position.get_stock_amount_dict()

    def begin_session(self, date, account, candidates=()):
        raise ValueError("CoreSession owns session entry")

    def activate(self, date, account, scope):
        self.scope = scope
        self.session_date = bounded_date(date)
        self.session_account = account
        self.buy_budget = account.current_position.get_cash()
        self.session_filled = {}
        self.t_plus_one.start_day(self.session_date, account.current_position.get_stock_amount_dict())

    def deal_order(self, order, **kwargs):
        purpose = "new_entry" if order.direction == Order.BUY else "holding_exit"
        require_scope_order(self.scope, order.stock_id, purpose=purpose)
        return super().deal_order(order, **kwargs)


class CoreSession:
    """One whole day is the transaction/checkpoint; errors discard the working copy.

    Loader is called A then B then C. Intents are supplied before B and copied.
    The failed day may be replayed unchanged; successful dates cannot run twice.
    Only the Qlib account is durable; intraday fee/capacity/T+1 state is day-local.
    """

    def __init__(self, account, calendar, *, mode="strict"):
        if mode not in {"strict", "historical"}:
            raise ValueError("CoreSession is research only; live execution is not implemented")
        self.mode = mode
        if account.is_port_metr_enabled() or account.benchmark_config.get("benchmark") is not None:
            raise ValueError("core requires metrics and benchmark return access disabled")
        if not isinstance(account.current_position, EventPosition):
            raise ValueError("attach existing EventPosition explicitly")
        self.account = account
        self.calendar = pd.DatetimeIndex(calendar)
        if not self.calendar.is_unique or not self.calendar.is_monotonic_increasing:
            raise ValueError("invalid calendar")
        for date in self.calendar:
            bounded_date(date)
        self.last_date = account.current_position.event_date
        self.receipts = []

    def run_day(self, date, candidates, intents, loader, *, failpoint=None):
        date = str(bounded_date(date).date())
        if pd.Timestamp(date) not in self.calendar:
            raise ValueError("day off calendar")
        if self.last_date and execution_day(self.last_date, self.calendar)[0] != pd.Timestamp(date):
            raise ValueError("must process exactly the next session; no duplicate or skipped day")
        intents = deepcopy(tuple(intents))
        candidates = tuple(sorted(set(candidates)))
        for intent in intents:
            if intent.side not in {"buy", "sell"} or not math.isfinite(intent.shares) or intent.shares < 0:
                raise ValueError("invalid intent")
        work = deepcopy(self.account)
        p = work.current_position
        stage = "A"

        def checkpoint(name):
            if failpoint:
                failpoint(name)

        def load(phase):
            snapshot = loader(phase)
            if snapshot.phase != phase or snapshot.date != date or snapshot.mode != self.mode:
                raise ValueError("loader phase/date mismatch")
            instant = pd.Timestamp(snapshot.at)
            clock = instant.strftime("%H:%M:%S")
            if instant.tz is not None or str(instant.date()) != date or not {
                "A": clock < "09:25:00", "B": "09:25:00" <= clock <= "09:30:00", "C": clock > "15:00:00"
            }[phase]:
                raise ValueError("loader phase clock boundary")
            return deepcopy(snapshot)

        try:
            a = load("A")
            for stock in set(candidates) - exposures(p):
                provided = {e.event_id for e in a.distributions.get(stock, ())}
                if not set(a.covered_events.get(stock, ())) <= provided | set(p.events):
                    a.facts.get(stock, {}).pop("events_clear", None)
            scope = check_scope(work, candidates, a)
            if scope["account_action"] != "PREFLIGHT_PASSED":
                raise ValueError(str(scope["holdings"]))
            relevant = exposures(p) | {s for s, d in scope["entries"].items() if d.action == "ALLOW_ENTRY"}
            for stock in relevant:
                provided = {e.event_id for e in a.distributions.get(stock, ())}
                if not set(a.covered_events.get(stock, ())) <= provided | set(p.events):
                    raise ValueError("coverage names an event without a handler input")
                for event in a.distributions.get(stock, ()):
                    if event.event_id not in a.covered_events.get(stock, ()):
                        raise ValueError("distribution omitted from coverage")
                    if event.event_id not in p.events:
                        p.register(event)
                    elif p.events[event.event_id] != event:
                        raise ValueError("registered event changed without reconciliation")
            p.advance_events(date, marks(a))
            scope = check_scope(work, candidates, a)
            if scope["account_action"] != "PREFLIGHT_PASSED":
                raise ValueError(str(scope["holdings"]))
            checkpoint("after_events")
            allowed, denied = [], []
            for intent in intents:
                purpose = "new_entry" if intent.side == "buy" else "holding_exit"
                try:
                    require_scope_order(scope, intent.instrument, purpose=purpose)
                except ValueError:
                    denied.append(intent.instrument)
                else:
                    allowed.append(intent)
            stage = "B"
            b = load("B")
            frame = prepared_rows(a, b, {x.instrument for x in allowed}, self.calendar)
            filled = 0
            if frame is not None:
                exchange = _ScopedExchange(execution_quotes=frame, calendar=self.calendar,
                                           historical_inputs=self.mode == "historical")
                exchange.activate(date, work, scope)
                for intent in allowed:
                    order = Order(stock_id=intent.instrument, amount=intent.shares,
                                  direction=Order.BUY if intent.side == "buy" else Order.SELL,
                                  start_time=pd.Timestamp(date), end_time=pd.Timestamp(date))
                    exchange.deal_order(order, trade_account=work)
                    filled += int(order.deal_amount > 0)
                    checkpoint("after_fill")
            stage = "C"
            c = load("C")
            if not pd.Timestamp(a.at) < pd.Timestamp(b.at) < pd.Timestamp(c.at):
                raise ValueError("phase time ordering")
            final_scope = check_scope(work, (), c)
            if final_scope["account_action"] != "PREFLIGHT_PASSED":
                raise ValueError(str(final_scope["holdings"]))
            closing = marks(c)
            for stock in p.get_stock_list():
                p.update_stock_price(stock, closing[stock])
            for key in p.pending_bonus:
                stock = p.events[key].instrument
                p.event_marks[stock] = closing[stock]
            p.capture_record_close(date)
            p.add_count_all("day")
            p.position["now_account_value"] = p.calculate_value()
            p.update_weight_all()
            checkpoint("after_close")
            # Construct every replacement before modifying the durable Account.
            replacement = deepcopy(work.__dict__)
            position_state = replacement.pop("current_position").__dict__
            checkpoint("before_commit")
        except Exception as exc:
            receipt = dict(date=date, status="HALT_RETAIN", stage=stage, checkpoint=self.last_date, reason=str(exc))
            self.receipts.append(receipt)
            raise CoreHalt(str(receipt)) from exc
        durable_position = self.account.current_position
        durable_position.__dict__.clear()
        durable_position.__dict__.update(position_state)
        self.account.__dict__.clear()
        self.account.__dict__.update(replacement, current_position=durable_position)
        self.last_date = date
        receipt = dict(date=date, status="COMMITTED", fills=filled, denied=denied, input_mode=self.mode,
                       exposed=len(exposures(durable_position)), metrics_enabled=False)
        self.receipts.append(receipt)
        return receipt
