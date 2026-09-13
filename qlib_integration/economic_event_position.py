"""Opt-in Qlib Position bridge. Synthetic/accounting validation only, no runner."""

from copy import deepcopy
from dataclasses import dataclass
import math
import pandas as pd

from qlib.backtest.position import Position
from .economic_execution_contract import CorporateActionBook, bounded_date
from .economic_exchange import EconomicOpenExchange
from .execution_readiness import require_continuity, require_distinct_assets


@dataclass(frozen=True)
class Distribution:
    event_id: str
    instrument: str
    record_date: str
    ex_date: str
    pay_date: str
    listable_date: str
    net_cash_per_share: float
    bonus_per_share: float
    announced_date: str
    source: str
    tax_policy: str

    def validate(self):
        for d in (self.record_date, self.ex_date, self.announced_date):
            bounded_date(d)
        for d in (self.pay_date, self.listable_date):
            if d:
                parsed = pd.Timestamp(d)
                if pd.isna(parsed) or str(parsed.date()) != d:
                    raise ValueError("invalid scheduled entitlement date")
        if (
            not (self.announced_date <= self.record_date < self.ex_date)
            or not self.source
            or not self.event_id
        ):
            raise ValueError("event identity/announcement/record ordering")
        if self.tax_policy not in ("explicit_net_entitlement", "synthetic"):
            raise ValueError("tax entitlement unresolved; no guessed universal net rate")
        if any(
            not math.isfinite(v) or v < 0 for v in (self.net_cash_per_share, self.bonus_per_share)
        ):
            raise ValueError("missing event quantity/cash semantics")
        if self.net_cash_per_share and (not self.pay_date or self.pay_date < self.ex_date):
            raise ValueError("payment date unresolved")
        if self.bonus_per_share and (not self.listable_date or self.listable_date < self.ex_date):
            raise ValueError("listable date unresolved")


class EventPosition(Position):
    """Cash receivables and unlisted bonus rights remain outside tradable stocks.

    calculate_value() includes both; get_cash() never includes receivables.
    Process corporate events with already-known ex-reference marks before
    Exchange.begin_session; never pass today's later close into this phase. Capture record-date
    entitlements after that day's fills. No automatic tax or terminal inference.
    """

    def __init__(self, cash=0.0, position_dict=None):
        super().__init__(cash=cash, position_dict=deepcopy(position_dict or {}))
        self.events = {}
        self.entitlements = {}
        self.book = CorporateActionBook()
        self.pending_bonus = {}
        self.event_marks = {}
        self.applied = set()
        self.event_date = None

    def register(self, event):
        event.validate()
        if event.event_id in self.events or (
            self.event_date and event.record_date < self.event_date
        ):
            raise ValueError("duplicate/late event registration")
        self.events[event.event_id] = event

    def capture_record_close(self, date):
        date = str(bounded_date(date).date())
        if self.event_date != date:
            raise ValueError("capture requires same begun session")
        captures = {}
        for key, event in self.events.items():
            if event.record_date == date:
                if key in self.entitlements:
                    raise ValueError("record date already captured")
                if any(self.events[k].instrument == event.instrument for k in self.pending_bonus):
                    raise ValueError(
                        "overlapping unlisted rights require explicit entitlement evidence"
                    )
                shares = self.get_stock_amount(event.instrument)
                bonus = shares * event.bonus_per_share
                if not math.isclose(bonus, round(bonus), abs_tol=1e-8):
                    raise ValueError(
                        "fractional stock entitlement requires explicit allocation evidence"
                    )
                captures[key] = shares
        self.entitlements.update(captures)

    def advance_events(self, date, raw_marks):
        date = str(bounded_date(date).date())
        if self.event_date and date <= self.event_date:
            raise ValueError("event session must advance exactly once")
        # Validate the whole batch before applying any cash/share mutation.
        for key, event in self.events.items():
            if event.record_date < date and key not in self.entitlements:
                raise ValueError("missing record-date entitlement")
            for phase, d in (
                ("ex", event.ex_date),
                ("pay", event.pay_date),
                ("list", event.listable_date),
            ):
                if (
                    d
                    and d < date
                    and (key, phase) not in self.applied
                    and (
                        phase == "ex"
                        or (phase == "pay" and event.net_cash_per_share)
                        or (phase == "list" and event.bonus_per_share)
                    )
                ):
                    raise ValueError("missed scheduled corporate event")
        needed = {self.events[k].instrument for k in self.pending_bonus}
        needed |= {
            e.instrument
            for k, e in self.events.items()
            if e.ex_date == date and e.bonus_per_share and self.entitlements.get(k, 0)
        }
        needed |= set(self.get_stock_list())
        if any(
            s not in raw_marks or not math.isfinite(raw_marks[s]) or raw_marks[s] <= 0
            for s in needed
        ):
            raise ValueError("held/right valuation unresolved")
        self.event_marks = {s: raw_marks[s] for s in needed}
        for stock in self.get_stock_list():
            self.update_stock_price(stock, raw_marks[stock])
        for key, event in self.events.items():
            shares = self.entitlements.get(key, 0)
            if event.ex_date == date:
                if event.net_cash_per_share:
                    self.book.dividend_ex(key, shares, event.net_cash_per_share)
                if event.bonus_per_share and shares:
                    self.pending_bonus[key] = round(shares * event.bonus_per_share)
                self.applied.add((key, "ex"))
            if event.pay_date == date and event.net_cash_per_share:
                self.position["cash"] += self.book.dividend_pay(key)
                self.applied.add((key, "pay"))
            if event.listable_date == date and event.bonus_per_share:
                quantity = self.pending_bonus.pop(key, 0)
                if quantity:
                    if event.instrument not in self.position:
                        self._init_stock(event.instrument, 0, raw_marks[event.instrument])
                    self.position[event.instrument]["amount"] += quantity
                self.applied.add((key, "list"))
        self.event_date = date

    def calculate_value(self):
        # Position.__init__ calls this before the event fields exist.
        rights = sum(
            q * self.event_marks[self.events[k].instrument]
            for k, q in getattr(self, "pending_bonus", {}).items()
        )
        receivables = sum(self.book.receivables.values()) if hasattr(self, "book") else 0
        return super().calculate_value() + rights + receivables

    def rename_identity(self, old, new, *, date, evidence, same_share_rights):
        if (
            str(bounded_date(date).date()) != self.event_date
            or not evidence
            or same_share_rights is not True
        ):
            raise ValueError("identity migration requires explicit same-share evidence/session")
        if old not in self.position or new in self.position:
            raise ValueError("unknown/colliding migration")
        # Distribution IDs refer to their historical instrument. Pending claims
        # require explicit event remapping rather than silent global rename.
        if any(e.instrument == old for e in self.events.values()):
            raise ValueError("migration with registered entitlement requires dedicated mapping")
        self.position[new] = self.position.pop(old)  # includes count/weight metadata

    def terminal_unknown(self, instrument):
        if self.get_stock_amount(instrument) or any(
            self.events[k].instrument == instrument for k in self.pending_bonus
        ):
            raise ValueError("terminal rights unresolved; retain position and halt")


def attach_event_position(account):
    """Opt-in to an existing Qlib Account before events; no portfolio metrics run."""
    if isinstance(account.current_position, EventPosition):
        raise ValueError("already attached")
    original = account.current_position
    position = EventPosition(
        cash=original.get_cash(),
        position_dict={s: deepcopy(original.position[s]) for s in original.get_stock_list()},
    )
    position.position = deepcopy(original.position)
    position._settle_type = original._settle_type
    account.current_position = position
    return position


class EvidenceCheckedOpenExchange(EconomicOpenExchange):
    """Actual Qlib session entry checks held union before resetting any ledger."""

    def begin_evidenced_session(
        self, date, account, candidates, states, valuation_evidence, order_time, identity_map
    ):
        if str(bounded_date(date).date()) != str(bounded_date(order_time).date()):
            raise ValueError("state session mismatch")
        require_distinct_assets(
            set(candidates) | set(account.current_position.get_stock_list()), identity_map
        )
        decisions = require_continuity(
            candidates,
            account.current_position.get_stock_amount_dict(),
            states,
            order_time,
            valuation_evidence,
        )
        for stock, decision in decisions.items():
            key = stock, bounded_date(date)
            if key not in self.execution_rows.index:
                raise ValueError("missing held/candidate prepared quote")
            row = self.execution_rows.loc[key]
            state = states[stock]
            if row.order_time != pd.Timestamp(order_time):
                raise ValueError("prepared order time contradicts state evidence")
            if decision == "ordinary_known" and (
                row.suspended_known
                or row.board != state["board"]
                or abs(row.upper_limit - state["upper_limit"]) > 1e-8
                or abs(row.lower_limit - state["lower_limit"]) > 1e-8
            ):
                raise ValueError("prepared bounds/board contradict ordinary state evidence")
            if decision == "known_suspension" and not row.suspended_known:
                raise ValueError("prepared quote contradicts suspension evidence")
            if decision == "known_special_blocked" and (row.can_buy_known or row.can_sell_known):
                raise ValueError("special session cannot reach normal fill path")
        super().begin_session(date, account, candidates)
        return decisions

    def begin_session(self, date, account, candidates=()):
        raise ValueError("use begin_evidenced_session; unverified session cannot advance")
