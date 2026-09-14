"""PIT entry gates and holding preservation, independent of scores and executions.

This opt-in preflight does not start an Exchange, reprice an Account, or invent
special-session prepared quotes. Existing strict execution checks remain intact.
"""

from dataclasses import dataclass
from decimal import Decimal, ROUND_FLOOR
import math

import pandas as pd

from .economic_execution_contract import bounded_date
from .execution_readiness import execution_state


@dataclass(frozen=True)
class Fact:
    value: object
    observed_on: str
    effective_from: str
    effective_to: str
    known_at: str | None
    source: str
    precision: str = "timestamp"


def visible_fact(history, at, *, prior_session=False):
    """Future revisions are ignored; conflicting equally dated versions deny."""
    cutoff = pd.Timestamp(at)
    day = str(bounded_date(cutoff).date())
    if cutoff.tz is not None:
        raise ValueError("use Asia/Shanghai local naive timestamps")
    visible = []
    for fact in history:
        if not isinstance(fact.source, str) or not fact.source or not fact.known_at:
            continue
        try:
            known = pd.Timestamp(fact.known_at)
            observed = pd.Timestamp(fact.observed_on)
            dates = [fact.observed_on, fact.effective_from, fact.effective_to]
            if any(str(pd.Timestamp(d).date()) != d for d in dates):
                continue
            if (
                known.tz is not None
                or observed.tz is not None
                or pd.isna(known)
                or pd.isna(observed)
            ):
                continue
            if not fact.effective_from <= day <= fact.effective_to:
                continue
            if known >= cutoff or observed.normalize() > known.normalize():
                continue
            if fact.precision == "date":
                if known.normalize() >= cutoff.normalize():
                    continue
            elif fact.precision != "timestamp":
                continue
            if observed.normalize() > cutoff.normalize():
                continue
            if prior_session and observed.normalize() >= cutoff.normalize():
                continue
        except (TypeError, ValueError):
            continue
        visible.append((known, fact))
    if not visible:
        return None
    latest = max(t for t, _ in visible)
    chosen = [f for t, f in visible if t == latest]
    if len({repr(f.value) for f in chosen}) != 1:
        return None
    return chosen[0]


def _value(facts, name, at, *, prior=False):
    fact = visible_fact(facts.get(name, ()), at, prior_session=prior)
    return None if fact is None else fact.value


def _state(instrument, state, at):
    if state is None or state.get("instrument") != instrument:
        return "unresolved"
    try:
        return execution_state(state, at)
    except (TypeError, ValueError):
        return "unresolved"


@dataclass(frozen=True)
class Decision:
    action: str
    reasons: tuple


def entry_eligibility(instrument, at, facts, state, existing_assets=None):
    """No current-day OHLC, retrospective failure list, or empty event inference."""
    bounded_date(at)
    reasons = []
    asset = _value(facts, "asset_id", at)
    if not isinstance(asset, str) or not asset:
        reasons.append("identity_unknown")
    elif asset in (existing_assets or {}) and existing_assets[asset] != instrument:
        reasons.append("duplicate_economic_identity")
    if _value(facts, "quote_quality", at, prior=True) is not True:
        reasons.append("prior_quote_quality_unknown_or_bad")
    if _value(facts, "events_clear", at) is not True:
        reasons.append("event_evidence_unknown_or_pending")
    adv = _value(facts, "adv20_shares", at, prior=True)
    if (
        isinstance(adv, bool)
        or not isinstance(adv, (int, float))
        or not math.isfinite(adv)
        or adv <= 0
    ):
        reasons.append("adv_not_ready")
    status = _state(instrument, state, at)
    if status != "ordinary_known":
        reasons.append("ordinary_execution_not_certified")
    elif state["st"]:
        reasons.append("st_no_new_entry")
    return Decision("NO_NEW_ENTRY" if reasons else "ALLOW_ENTRY", tuple(reasons))


def holding_continuity(instrument, at, facts, state, *, needs_market_mark=True):
    """Unknown trading regime alone can forbid trades while preserving a mark.

    Identity, dated valuation and entitlement uncertainty still block accounting.
    A close observed later today cannot mark the account before open.
    """
    reasons = []
    asset = _value(facts, "asset_id", at)
    if not isinstance(asset, str) or not asset:
        reasons.append("held_identity_unresolved")
    if _value(facts, "events_clear", at) is not True:
        reasons.append("held_entitlement_unresolved")
    mark = visible_fact(facts.get("valuation_mark", ()), at)
    if needs_market_mark and (
        mark is None
        or mark.observed_on != str(bounded_date(at).date())
        or isinstance(mark.value, bool)
        or not isinstance(mark.value, (int, float))
        or not math.isfinite(mark.value)
        or mark.value <= 0
    ):
        reasons.append("held_dated_valuation_unresolved")
    if reasons:
        return Decision("HALT_RETAIN", tuple(reasons))
    if not needs_market_mark:
        return Decision("CARRY_CASH_CLAIM", ("existing_denomination_no_stock_quote_required",))
    status = _state(instrument, state, at)
    if status == "terminal_requires_event":
        return Decision("HALT_RETAIN", ("terminal_equity_requires_resolution",))
    if status != "ordinary_known" or _value(facts, "voluntary_trade_ready", at) is not True:
        return Decision("CARRY_ONLY", ("no_voluntary_trade",))
    return Decision("ORDINARY_EXECUTION_CANDIDATE", ())


def position_exposures(position):
    """Include receivables and unlisted rights even after original shares sold."""
    exposed = set()
    for stock, quantity in position.get_stock_amount_dict().items():
        if not math.isfinite(quantity) or quantity < 0:
            raise ValueError("invalid holding quantity")
        if quantity:
            exposed.add(stock)
    pending = set()
    for key, amount in getattr(position, "pending_bonus", {}).items():
        if not math.isfinite(amount) or amount < 0:
            raise ValueError("invalid pending bonus quantity")
        if amount:
            pending.add(key)
    book = getattr(position, "book", None)
    if book is not None:
        for key, amount in book.receivables.items():
            if not math.isfinite(amount) or amount < 0:
                raise ValueError("invalid receivable")
            if amount:
                pending.add(key)
    for key in pending:
        if key not in position.events:
            raise ValueError("claim identity missing; retain account")
        exposed.add(position.events[key].instrument)
    return exposed


def scope_account(account, candidates, at, facts_by_id, states):
    """Pure preflight: bad unheld candidates cannot halt unrelated holdings.

    HALT_RETAIN is returned before any account mutation. Callers must honor
    account_action; this is not permission to bypass existing Exchange guards.
    """
    exposed = position_exposures(account.current_position)
    position = account.current_position
    market_exposure = {s for s, q in position.get_stock_amount_dict().items() if q > 0}
    market_exposure |= {
        position.events[k].instrument
        for k, q in getattr(position, "pending_bonus", {}).items()
        if q > 0
    }
    held = {
        s: holding_continuity(
            s, at, facts_by_id.get(s, {}), states.get(s), needs_market_mark=s in market_exposure
        )
        for s in sorted(exposed)
    }
    assets = {}
    for stock in sorted(exposed):
        asset = _value(facts_by_id.get(stock, {}), "asset_id", at)
        if isinstance(asset, str) and asset:
            if asset in assets:
                held[stock] = Decision("HALT_RETAIN", ("held_identity_collision",))
            assets[asset] = stock
    entries = {
        s: entry_eligibility(s, at, facts_by_id.get(s, {}), states.get(s), assets)
        for s in sorted(set(candidates) - exposed)
    }
    # Colliding unheld aliases both deny; never choose a score or winner.
    by_asset = {}
    for stock, decision in entries.items():
        if decision.action == "ALLOW_ENTRY":
            by_asset.setdefault(_value(facts_by_id[stock], "asset_id", at), []).append(stock)
    for stocks in by_asset.values():
        if len(stocks) > 1:
            for stock in stocks:
                entries[stock] = Decision("NO_NEW_ENTRY", ("duplicate_economic_identity",))
    return dict(
        account_action="HALT_RETAIN"
        if any(d.action == "HALT_RETAIN" for d in held.values())
        else "PREFLIGHT_PASSED",
        holdings=held,
        entries=entries,
        preserved_exposures=tuple(sorted(exposed)),
    )


def bonus_claim(shares, ratio):
    """Exact decimal rights inventory; no rounding, waiver or invented proceeds.

    Integral quantities use the existing EventPosition bridge. Fractional claims
    are one handler family and require allocation evidence only when encountered.
    """
    quantity, rate = Decimal(str(shares)), Decimal(str(ratio))
    if not quantity.is_finite() or not rate.is_finite() or quantity < 0 or rate < 0:
        raise ValueError("invalid entitlement")
    total = quantity * rate
    integer = total.to_integral_value(rounding=ROUND_FLOOR)
    residual = total - integer
    return dict(
        total=str(total),
        integer_component=str(integer),
        fractional_claim=str(residual),
        status="PENDING_ALLOCATION" if residual else "EXISTING_INTEGRAL_BRIDGE",
        cash_substitute=None,
        automatically_tradable=False,
    )


def require_scope_order(scope, instrument, *, purpose):
    """Mandatory opt-in order preflight; the Exchange's own checks still apply."""
    if scope.get("account_action") != "PREFLIGHT_PASSED":
        raise ValueError("held account unresolved; retain and halt before orders")
    if purpose == "new_entry":
        decision = scope.get("entries", {}).get(instrument)
        expected = "ALLOW_ENTRY"
    elif purpose == "holding_exit":
        decision = scope.get("holdings", {}).get(instrument)
        expected = "ORDINARY_EXECUTION_CANDIDATE"
    else:
        raise ValueError("unsupported order purpose; no implicit add/rebalance authorization")
    if decision is None or decision.action != expected:
        raise ValueError("scope forbids this voluntary order")
