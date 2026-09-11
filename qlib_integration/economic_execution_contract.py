"""E2 execution primitives: raw units, dated constraints; no research score access."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP
import math

import numpy as np
import pandas as pd

from .exchange_adapter import TPlusOneLedger

START, END = pd.Timestamp("2015-01-01"), pd.Timestamp("2023-12-29")


def bounded_date(value):
    date = pd.Timestamp(value).normalize()
    if pd.isna(date) or not START <= date <= END:
        raise ValueError("outside E2 development boundary")
    return date


def execution_day(signal_date, calendar):
    signal_date = bounded_date(signal_date)
    days = pd.DatetimeIndex(calendar)
    if not days.is_unique or not days.is_monotonic_increasing:
        raise ValueError("invalid execution calendar")
    if days.min() < START or days.max() > END:
        raise ValueError("execution calendar outside boundary")
    if signal_date not in days:
        raise ValueError("signal off calendar")
    index = days.get_loc(signal_date) + 1
    return (
        (None, "out_of_execution_boundary") if index == len(days) else (days[index], "executable")
    )


def causal_adv20(volume_shares, calendar, order_date):
    date = bounded_date(order_date)
    days = pd.DatetimeIndex(calendar)
    if date not in days or not days.is_unique or not days.is_monotonic_increasing:
        raise ValueError("ADV calendar")
    prior = days[days < date][-20:]
    if len(prior) != 20 or prior.min() < START:
        raise ValueError("insufficient approved warmup")
    series = volume_shares.reindex(prior)
    if series.isna().any() or not np.isfinite(series).all() or (series < 0).any():
        raise ValueError("ADV missingness is not a zero-volume suspension")
    return float(series.mean())  # explicit suspension zeros stay in the denominator


def lot_quantity(requested, board, side, sellable=None):
    if (
        not math.isfinite(requested)
        or requested < 0
        or board not in ("main", "chinext", "star")
        or side not in ("buy", "sell")
    ):
        raise ValueError("invalid lot inputs")
    minimum, increment = (200, 1) if board == "star" else (100, 100)
    if side == "buy":
        return (
            0.0
            if requested < minimum
            else float(minimum + math.floor((requested - minimum) / increment) * increment)
        )
    if sellable is None or not math.isfinite(sellable) or sellable < 0:
        raise ValueError("sellable shares required")
    amount = min(requested, sellable)
    if amount == sellable:
        return float(amount)  # one residual disposal, including < board minimum
    if board == "star":
        return 0.0 if amount < minimum else float(math.floor(amount))
    return float(math.floor(amount / 100) * 100)


def dated_limit_rule(date, board, st, ipo_session, listing_regime, *, special="ordinary"):
    """Regular regimes only; special-day exact bounds require separate authority.

    No date alone is used to infer whether a pre-reform listing became a new IPO.
    Unknown/relisting/legacy first-day inputs fail instead of assuming 10%/no-limit.
    """
    date = bounded_date(date)
    if board not in ("main", "chinext", "star") or type(st) is not bool or ipo_session < 1:
        raise ValueError("unknown dated state")
    if listing_regime not in ("approval", "registration") or special != "ordinary":
        raise ValueError("special session needs exact dated price bounds/authority")
    if board == "star" and (date < pd.Timestamp("2019-07-22") or listing_regime != "registration"):
        raise ValueError("impossible STAR regime")
    registration_start = {
        "main": pd.Timestamp("2023-04-10"),
        "chinext": pd.Timestamp("2020-08-24"),
        "star": pd.Timestamp("2019-07-22"),
    }[board]
    if listing_regime == "registration" and date < registration_start:
        raise ValueError("registration not effective")
    if ipo_session <= 5 and listing_regime == "registration":
        return dict(
            limit_ratio=None, kind="registration_first_five", source="SSE2023/SZSE2020/STAR2019"
        )
    if ipo_session == 1:
        raise ValueError("legacy IPO first-day auction bounds required")
    ratio = (
        0.2
        if board == "star" or (board == "chinext" and date >= pd.Timestamp("2020-08-24"))
        else (0.05 if st else 0.1)
    )
    return dict(limit_ratio=ratio, kind="ordinary_dated", source="dated_rules_v1")


def price_bounds(reference, ratio, tick=0.01):
    if reference <= 0 or tick <= 0 or ratio is None:
        raise ValueError("exact bounds required for special/no-limit session")

    def round_tick(value):
        return float(
            (Decimal(str(value)) / Decimal(str(tick))).quantize(
                Decimal("1"), rounding=ROUND_HALF_UP
            )
            * Decimal(str(tick))
        )

    ref, r = Decimal(str(reference)), Decimal(str(ratio))
    return round_tick(ref * (1 - r)), round_tick(ref * (1 + r))


def dated_fees(date, exchange, *, early2015_evidence_accepted=False, par_value=None):
    date = bounded_date(date)
    if exchange not in ("SH", "SZ"):
        raise ValueError("uncovered exchange")
    transfer = 0.00001 if date >= pd.Timestamp("2022-04-29") else 0.00002
    basis = "consideration_cny"
    if date < pd.Timestamp("2015-08-01"):
        if not early2015_evidence_accepted:
            raise ValueError("early-2015 transfer evidence/rounding not ready")
        transfer = 0.0003 if exchange == "SH" else 0.0000255
        basis = "par_value_cny" if exchange == "SH" else basis
        if exchange == "SH" and (
            par_value is None or not math.isfinite(par_value) or par_value <= 0
        ):
            raise ValueError("SH early-2015 requires verified par value")
    return dict(
        commission_rate=0.0003,
        minimum_commission=5.0,
        stamp_rate=0.0005 if date >= pd.Timestamp("2023-08-28") else 0.001,
        transfer_rate=transfer,
        transfer_basis=basis,
        par_value=par_value,
        rounding="mother_order_component_half_up_cent",
        commission_authority="MVP assumption, not broker universal tariff",
    )


def cents(value):
    return float(Decimal(str(value)).quantize(Decimal(".01"), rounding=ROUND_HALF_UP))


@dataclass
class MotherOrderFees:
    """Cumulative charges with marginal debits; trial calculation is pure."""

    totals: dict = field(default_factory=dict)

    def quote(self, key, value, shares, side, fee, implicit_bps=0.0):
        if side not in ("buy", "sell") or not all(
            math.isfinite(x) and x >= 0 for x in (value, shares, implicit_bps)
        ):
            raise ValueError("invalid fee inputs")
        old = self.totals.get(
            key,
            dict(
                value=0.0,
                shares=0.0,
                charges=dict(commission=0.0, stamp=0.0, transfer=0.0, implicit=0.0),
            ),
        )
        if value == 0 or shares == 0:
            return dict(commission=0.0, stamp=0.0, transfer=0.0, implicit=0.0), old
        v, q = old["value"] + value, old["shares"] + shares
        basis = q * fee["par_value"] if fee["transfer_basis"] == "par_value_cny" else v
        charges = dict(
            commission=cents(max(fee["minimum_commission"], v * fee["commission_rate"])),
            stamp=cents(v * fee["stamp_rate"]) if side == "sell" else 0.0,
            transfer=cents(basis * fee["transfer_rate"]),
            implicit=cents(v * implicit_bps / 10000),
        )
        delta = {name: cents(amount - old["charges"][name]) for name, amount in charges.items()}
        return delta, dict(value=v, shares=q, charges=charges)

    def commit(self, key, pending):
        self.totals[key] = pending


class RawSellableLedger(TPlusOneLedger):
    def start_day(self, trading_date, opening_raw_shares):
        date = bounded_date(trading_date)
        if self.current_date is not None and date < self.current_date:
            raise ValueError("T+1 time reversal")
        if any(not math.isfinite(v) or v < 0 for v in opening_raw_shares.values()):
            raise ValueError("invalid opening shares")
        super().start_day(date, opening_raw_shares)

    def record_fill(self, instrument, side, raw_shares):
        if self.current_date is None or not math.isfinite(raw_shares):
            raise ValueError("uninitialized ledger or nonfinite fill")
        if side == "sell" and raw_shares > self.sellable(instrument) + 1e-8:
            raise ValueError("oversold regulatory ledger")
        super().record_fill(instrument, side, raw_shares)

    def convert_existing_shares(self, instrument, multiplier):
        if not math.isfinite(multiplier) or multiplier <= 0:
            raise ValueError("invalid share conversion")
        for values in (self.opening_sellable, self.sold_today, self.bought_today):
            if instrument in values:
                values[instrument] *= multiplier


@dataclass
class CorporateActionBook:
    """Explicit entitlements bridge, separate from Qlib price/factor adjustments.

    Requires verified record-date holdings and dated event instructions. No event
    is inferred from factor ratios. Rights/conversions not covered here fail closed.
    Account/NAV integration for real events remains an E4 readiness blocker.
    """

    receivables: dict = field(default_factory=dict)
    processed: set = field(default_factory=set)

    def dividend_ex(self, event_id, entitled_shares, cash_per_share):
        if event_id in self.processed or not all(
            math.isfinite(x) and x >= 0 for x in (entitled_shares, cash_per_share)
        ):
            raise ValueError("duplicate/invalid dividend")
        value = entitled_shares * cash_per_share
        self.receivables[event_id] = value
        self.processed.add(event_id)
        return value

    def dividend_pay(self, event_id):
        if event_id not in self.receivables:
            raise ValueError("unknown/already paid entitlement")
        return self.receivables.pop(event_id)

    def split(self, event_id, stock, shares, multiplier, ledger):
        if event_id in self.processed or not math.isfinite(shares) or shares < 0:
            raise ValueError("duplicate/invalid split")
        ledger.convert_existing_shares(stock, multiplier)
        self.processed.add(event_id)
        return shares * multiplier

    def unsupported(self, kind):
        raise ValueError(f"{kind}: dated cash/quantity/listability contract required")


def quote_universe(candidates, holdings):
    return set(candidates) | {k for k, v in holdings.items() if v > 0}


def vacant_slots(target, actual_holdings, pending_sells):
    if not set(pending_sells).issubset(actual_holdings):
        raise ValueError("pending sale without actual holding")
    return max(0, target - len(actual_holdings))
