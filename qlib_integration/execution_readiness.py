"""Execution-only evidence gates; no score, outcome, or default-tradable inference."""

from dataclasses import dataclass
import math
import re

import numpy as np
import pandas as pd

from .economic_data_readiness import QuoteSliceReader
from .economic_execution_contract import (
    bounded_date,
    quote_universe,
    price_bounds,
    dated_limit_rule,
)
from .instrument_state_evidence import classify_available_phase


@dataclass(frozen=True)
class UnitRule:
    instrument: str
    effective_from: str
    effective_to: str
    price_mode: str
    volume_multiplier: float
    amount_multiplier: float
    source_id: str
    verified: bool = False


def normalize_quote(row, rule):
    """Explicit independently supplied interval only. No automatic ratio fitting."""
    date = str(bounded_date(row["date"]).date())
    if (
        row["instrument"] != rule.instrument
        or not rule.effective_from <= date <= rule.effective_to
        or not rule.verified
        or not rule.source_id
    ):
        raise ValueError("unknown identity/unit interval")
    if rule.price_mode not in ("raw", "community_adjusted") or any(
        not math.isfinite(x) or x <= 0 for x in (rule.volume_multiplier, rule.amount_multiplier)
    ):
        raise ValueError("invalid unit rule")
    factor = float(row["factor"])
    if not math.isfinite(factor) or factor <= 0:
        raise ValueError("unknown factor")
    divisor = factor if rule.price_mode == "community_adjusted" else 1.0
    result = {c: float(row[c]) / divisor for c in ("open", "high", "low", "close")}
    result["volume"] = float(row["volume"]) * divisor * rule.volume_multiplier
    result["amount"] = float(row["amount"]) * rule.amount_multiplier
    result["factor"] = factor  # source factor retained; execution account remains raw.
    if not all(math.isfinite(v) and v > 0 for v in result.values()):
        raise ValueError("missing/nonpositive quote needs explicit state; no fill")
    if not (
        result["low"] <= result["open"] <= result["high"]
        and result["low"] <= result["close"] <= result["high"]
    ):
        raise ValueError("OHLC contradiction")
    vwap = result["amount"] / result["volume"]
    if not result["low"] * 0.998 <= vwap <= result["high"] * 1.002:
        raise ValueError("implied VWAP unit contradiction")
    return dict(result, instrument=row["instrument"], date=date, source_id=rule.source_id)


def require_distinct_assets(instruments, identity_map):
    """Research aliases cannot silently create two positions in one economic asset."""
    assets = []
    for stock in instruments:
        if stock not in identity_map or not identity_map[stock]:
            raise ValueError("identity unresolved")
        assets.append(identity_map[stock])
    if len(assets) != len(set(assets)):
        raise ValueError(
            "multiple research codes resolve to one economic asset; explicit reconciliation required"
        )


def execution_state(state, order_time):
    """Tri-state evidence. This returns a gate result, never fabricates a quote."""
    required = {
        "instrument",
        "date",
        "board",
        "listed",
        "st",
        "suspended",
        "ordinary_session",
        "special_session",
        "limit_ratio",
        "upper_limit",
        "lower_limit",
        "limit_reference",
        "effective_from",
        "effective_to",
        "known_at",
        "publication_precision",
        "source",
        "evidence_level",
        "ipo_session",
        "listing_regime",
    }
    if state is None or not required <= set(state):
        return "unresolved"
    date = bounded_date(state["date"])
    order = pd.Timestamp(order_time)
    if (
        order.normalize() != date
        or not state["effective_from"] <= str(date.date()) <= state["effective_to"]
    ):
        return "unresolved"
    if not state["source"] or state["evidence_level"] not in {
        "official",
        "cross_source",
        "vendor",
        "synthetic",
    }:
        return "unresolved"
    phase = classify_available_phase(
        published_at=state["known_at"],
        effective_date=date,
        publication_precision=state["publication_precision"],
        before_open_cutoff=order.strftime("%H:%M:%S"),
    )
    if phase != "before_open":
        return "unresolved"
    for key in ("listed", "st", "suspended", "ordinary_session"):
        if type(state[key]) not in (bool, np.bool_):
            return "unresolved"
    if not state["listed"]:
        return "terminal_requires_event"
    if state["suspended"]:
        return "known_suspension"
    if not state["ordinary_session"] or state["special_session"] != "none":
        return "known_special_blocked"
    if state["board"] not in ("main", "chinext", "star"):
        return "unresolved"
    try:
        reference, ratio = float(state["limit_reference"]), float(state["limit_ratio"])
        if not all(
            math.isfinite(float(state[k])) for k in ("upper_limit", "lower_limit", "ipo_session")
        ):
            return "unresolved"
        if state["ipo_session"] < 1 or int(state["ipo_session"]) != state["ipo_session"]:
            return "unresolved"
        rule = dated_limit_rule(
            date, state["board"], bool(state["st"]), state["ipo_session"], state["listing_regime"]
        )
        if rule["kind"] != "ordinary_dated" or rule["limit_ratio"] != ratio:
            return "unresolved"
        if (
            not math.isfinite(reference)
            or not math.isfinite(ratio)
            or ratio not in (0.05, 0.1, 0.2)
        ):
            return "unresolved"
        lo, hi = price_bounds(reference, ratio)
        if abs(lo - state["lower_limit"]) > 1e-8 or abs(hi - state["upper_limit"]) > 1e-8:
            return "unresolved"
    except (ValueError, TypeError):
        return "unresolved"
    return "ordinary_known"


def require_continuity(candidates, holdings, states, order_time, valuation_evidence):
    """Unknown held state or valuation halts before any account mutation."""
    result = {}
    for stock in sorted(quote_universe(candidates, holdings)):
        if states.get(stock) and states[stock].get("instrument") != stock:
            raise ValueError(f"{stock}: state identity mismatch; account cannot advance")
        status = execution_state(states.get(stock), order_time)
        if status in ("unresolved", "terminal_requires_event"):
            raise ValueError(f"{stock}: {status}; account cannot advance")
        if holdings.get(stock, 0) > 0:
            evidence = valuation_evidence.get(stock)
            # Exact dated reviewed marks; no automatic unbounded forward fill.
            if (
                not evidence
                or evidence.get("date") != str(pd.Timestamp(order_time).date())
                or not evidence.get("source")
            ):
                raise ValueError(f"{stock}: held valuation unresolved")
            if not math.isfinite(evidence["price"]) or evidence["price"] <= 0:
                raise ValueError("invalid held valuation")
        result[stock] = status
    return result


class WarmupReader(QuoteSliceReader):
    """Only the twenty December 2014 sessions; volume-unit diagnosis, never scores."""

    windows = (("2014-12-04", "2014-12-31"),)

    def __init__(self, provider, instruments, exact_dates):
        if len(exact_dates) != 20 or any(
            not "2014-12-04" <= d <= "2014-12-31" for d in exact_dates
        ):
            raise ValueError("warmup allowlist denied before provider IO")
        if any(not re.fullmatch(r"(sh|sz)\d{6}", s) for s in instruments):
            raise ValueError("invalid warmup instruments")
        self.instruments = tuple(instruments)
        super().__init__(provider)
        if list(self.approved) != list(exact_dates):
            raise ValueError("warmup calendar mismatch")


def adv20_with_warmup(series, prior_dates, known_suspensions=(), *, order_date):
    dates = list(prior_dates)
    order = str(bounded_date(order_date).date())
    if (
        len(dates) != 20
        or dates != sorted(set(dates))
        or not all("2014-12-04" <= d <= "2023-12-29" for d in dates)
    ):
        raise ValueError("exact twenty historical sessions required")
    if dates[-1] >= order:
        raise ValueError("ADV window must precede order date")
    values = series.reindex(dates).copy()
    for date in known_suspensions:
        if date in dates and pd.isna(values.loc[date]):
            values.loc[date] = 0.0
    if not np.isfinite(values).all() or (values < 0).any():
        raise ValueError("unknown volume is not zero suspension")
    return float(values.mean())


def overnight_timing(
    signal_date, order_time, required_available_dates, batch_completed_at, *, accept_date_pit=False
):
    """Date-granularity PIT contract, explicitly distinct from source-vintage proof."""
    signal = bounded_date(signal_date)
    order = pd.Timestamp(order_time)
    bounded_date(order)
    batch = pd.Timestamp(batch_completed_at)
    if not accept_date_pit or not required_available_dates or pd.isna(batch):
        raise ValueError("date-PIT contract/required input receipt missing")
    available = pd.to_datetime(list(required_available_dates.values()))
    if available.isna().any() or (available.normalize() > signal).any():
        raise ValueError("required input unavailable by signal day")
    if not signal + pd.Timedelta(hours=15) <= batch < order or not signal < order.normalize():
        raise ValueError("overnight batch must finish before next-session order")
    return "READY WITH MVP APPROXIMATION"
