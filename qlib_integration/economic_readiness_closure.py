"""Bounded E2 audit helpers; no score, strategy, Account or outcome computation."""

from __future__ import annotations

import re
import numpy as np

from .economic_data_readiness import QuoteSliceReader
from .economic_execution_contract import dated_fees, lot_quantity, MotherOrderFees, price_bounds


def validate_regular_limit_quote(pre_close, upper, lower, rule):
    """Vendor placeholder prices must never become ordinary executable bounds.

    This validates an independently established dated regime. It does not infer
    ST, IPO, relisting or ex-rights state from the vendor prices themselves.
    """
    ratio = rule.get("limit_ratio")
    if rule.get("kind") != "ordinary_dated" or ratio is None:
        raise ValueError("special/no-limit session is not an ordinary executable quote")
    if not all(np.isfinite(x) and x > 0 for x in (pre_close, upper, lower)):
        raise ValueError("missing price-limit evidence")
    expected_lower, expected_upper = price_bounds(pre_close, ratio)
    if abs(upper - expected_upper) > 1e-8 or abs(lower - expected_lower) > 1e-8:
        raise ValueError("source limit disagrees with independently dated regime/reference")
    return dict(upper_limit=upper, lower_limit=lower, kind="ordinary_dated")


class ClosureQuoteReader(QuoteSliceReader):
    """Reuse exact-byte reader with an explicit precommitted audit inventory."""

    def __init__(self, provider, instruments, dates):
        self.instruments = tuple(sorted(set(instruments)))
        dates = tuple(sorted(set(dates)))
        if not self.instruments or any(
            not re.fullmatch(r"(sh|sz)\d{6}", s) for s in self.instruments
        ):
            raise ValueError("invalid closed instrument inventory")
        if not dates or any(
            not re.fullmatch(r"\d{4}-\d{2}-\d{2}", d) or not "2015-01-01" <= d <= "2023-12-29"
            for d in dates
        ):
            raise ValueError("date boundary denied before provider IO")
        self.windows = tuple((d, d) for d in dates)
        super().__init__(provider)
        if self.approved != dates:
            raise ValueError("off-calendar audit date")


def quote_checks(frame):
    """Raw-unit consistency, including close; unknowns remain explicit."""
    f = frame
    finite = np.isfinite(f[["open", "high", "low", "close", "volume", "amount", "factor"]]).all(
        axis=1
    )
    positive = (f[["open", "high", "low", "close", "factor"]] > 0).all(axis=1)
    valid = finite & positive & f.volume.gt(0) & f.amount.gt(0)
    bounds = (
        f.high.ge(f.low)
        & f.open.between(f.low - 0.001, f.high + 0.001)
        & f.close.between(f.low - 0.001, f.high + 0.001)
    )
    vwap = f.amount / f.volume.where(f.volume.gt(0))
    inside = vwap.between(f.low * 0.998, f.high * 1.002)
    return dict(
        rows=len(f),
        finite_all=int(finite.sum()),
        valid_positive_pairs=int(valid.sum()),
        missing_any=int((~finite).sum()),
        nonpositive_price_factor=int((~positive & finite).sum()),
        negative_volume_amount=int(((f.volume < 0) | (f.amount < 0)).sum()),
        zero_volume=int(f.volume.eq(0).sum()),
        ohlc_bad=int((valid & ~bounds).sum()),
        implied_vwap_outside=int((valid & ~inside).sum()),
    )


def static_ew_feasibility(frame, date, aum):
    """One independent static basket. No carried positions or wealth path.

    Counts unknowns in the original denominator; never silently deletes a name.
    Quantities use previous-close reference, capacity uses lagged ADV. Opening
    price is only an ex-post affordability check, never an optimizer input.
    """
    n = len(frame)
    if not n or not np.isfinite(aum) or aum <= 0:
        raise ValueError("invalid static basket")
    budget = 0.95 * aum / n
    counts = dict(
        names=n,
        unknown_price=0,
        unknown_adv=0,
        unknown_open=0,
        below_lot=0,
        adv_below_minimum=0,
        adv_cap_binds=0,
        open_budget_breach=0,
        known_reference_buildable=0,
    )
    total_reference_value = total_reference_fees = 0.0
    for row in frame.itertuples():
        if not np.isfinite(row.adv20) or row.adv20 < 0:
            counts["unknown_adv"] += 1
        if not np.isfinite(row.open) or row.open <= 0:
            counts["unknown_open"] += 1
        if not np.isfinite(row.reference_close) or row.reference_close <= 0:
            counts["unknown_price"] += 1
            continue
        minimum = 200 if row.board == "star" else 100
        if np.isfinite(row.adv20) and 0.01 * row.adv20 < minimum:
            counts["adv_below_minimum"] += 1
        fee = dated_fees(date, row.instrument[:2].upper())
        q = lot_quantity(max(0, budget - 5) / row.reference_close, row.board, "buy")
        charge, _ = MotherOrderFees().quote("static", q * row.reference_close, q, "buy", fee)
        while q and q * row.reference_close + sum(charge.values()) > budget:
            q = lot_quantity(max(0, q - (1 if row.board == "star" else 100)), row.board, "buy")
            charge, _ = MotherOrderFees().quote("static", q * row.reference_close, q, "buy", fee)
        if not q:
            counts["below_lot"] += 1
        else:
            counts["known_reference_buildable"] += 1
            if np.isfinite(row.adv20):
                counts["adv_cap_binds"] += int(q > 0.01 * row.adv20)
            total_reference_value += q * row.reference_close
            total_reference_fees += sum(charge.values())
            if np.isfinite(row.open) and row.open > 0:
                opening_charge, _ = MotherOrderFees().quote("static", q * row.open, q, "buy", fee)
                counts["open_budget_breach"] += int(
                    q * row.open + sum(opening_charge.values()) > budget
                )
    return dict(
        date=date,
        aum_cny=aum,
        per_name_budget=budget,
        **counts,
        reference_fee_cny=total_reference_fees,
        reference_unallocated_fraction=1 - (total_reference_value + total_reference_fees) / aum,
        actual_execution_certified=False,
    )
