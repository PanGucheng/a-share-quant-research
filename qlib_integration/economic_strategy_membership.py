"""E3 membership intent/confirmation only. No Account, price, provider or outcomes."""

from dataclasses import dataclass
import math

from .economic_mvp_scope import Decision


@dataclass(frozen=True)
class Slot:
    instrument: str
    asset_id: str
    has_shares: bool = True
    pending_rights: bool = False


@dataclass(frozen=True)
class Plan:
    sell: str | None
    entries: tuple
    buy_cap: int
    rejected: tuple
    blocked_exit: bool
    buffer_retained: int
    exit_backlog: int


def rank_scores(pairs):
    if not pairs or any(not isinstance(s, str) or not s or not math.isfinite(float(v)) for s, v in pairs):
        raise ValueError("invalid score identity/value")
    if len({s for s, _ in pairs}) != len(pairs):
        raise ValueError("duplicate score identity")
    return [s for s, _ in sorted(pairs, key=lambda row: (-float(row[1]), row[0]))]


def plan_membership(ranked, slots, entry_gates, exit_gates, identities, *, first_decision=False):
    """Only explicit E2 decisions allow intents. Ranking remains over original pool."""
    if len(ranked) != len(set(ranked)) or len(slots) > 8:
        raise ValueError("duplicate ranking or excess slots")
    stocks = {s.instrument for s in slots}
    assets = {s.asset_id for s in slots}
    if len(stocks) != len(slots) or len(assets) != len(slots) or any(not s.asset_id for s in slots):
        raise ValueError("HALT_RETAIN duplicate/unknown held identity")
    if first_decision and slots:
        raise ValueError("cold start requires flat account")
    if any(d.action == "HALT_RETAIN" for s, d in exit_gates.items() if s in stocks):
        raise ValueError("HALT_RETAIN E2 held continuity")
    ranks = {s: i + 1 for i, s in enumerate(ranked)}
    worst = sorted((s for s in slots if s.has_shares and ranks.get(s.instrument, math.inf) > 16),
                   key=lambda s: (-ranks.get(s.instrument, math.inf), s.instrument))
    sell = worst[0].instrument if worst else None
    blocked = bool(sell and exit_gates.get(sell, Decision("CARRY_ONLY", ())).action != "ORDINARY_EXECUTION_CANDIDATE")
    rejected, candidates = [], []
    for stock in ranked[:8]:
        if stock in stocks:
            continue
        asset = identities.get(stock)
        decision = entry_gates.get(stock, Decision("NO_NEW_ENTRY", ("missing_gate",)))
        if not asset or asset in assets:
            rejected.append((stock, "duplicate_or_unknown_economic_identity"))
        elif decision.action != "ALLOW_ENTRY":
            rejected.append((stock, "|".join(decision.reasons) or decision.action))
        else:
            candidates.append(stock)
            assets.add(asset)  # Do not admit two candidate aliases into one batch.
    return Plan(sell, tuple(candidates), 8 if first_decision else 1, tuple(rejected), blocked,
                sum(s.has_shares and 8 < ranks.get(s.instrument, math.inf) <= 16 for s in slots),
                max(0, len(worst) - 1))


def eligible_buys(plan, slots, *, full_sale_confirmed=False):
    """Phase-B caller uses actual confirmation, never projected sale proceeds/slots."""
    remaining = list(slots)
    if plan.sell:
        if plan.blocked_exit or not full_sale_confirmed:
            return ()
        remaining = [s for s in slots if s.instrument != plan.sell or s.pending_rights]
    return plan.entries[:min(plan.buy_cap, max(0, 8 - len(remaining)))]


def confirm_membership(plan, slots, identities, *, full_sale_confirmed=False, bought=()):
    """Caller supplies verified positive fills and retained rights; no numeric fill assumption."""
    if full_sale_confirmed and (not plan.sell or plan.blocked_exit):
        raise ValueError("unplanned/blocked sale confirmation")
    allowed = eligible_buys(plan, slots, full_sale_confirmed=full_sale_confirmed)
    if len(bought) != len(set(bought)) or not set(bought) <= set(allowed):
        raise ValueError("unplanned new identity confirmation")
    remaining = []
    for slot in slots:
        if slot.instrument == plan.sell and full_sale_confirmed:
            if slot.pending_rights:
                remaining.append(Slot(slot.instrument, slot.asset_id, False, True))
        else:
            remaining.append(slot)
    assets = {s.asset_id for s in remaining}
    for stock in bought:
        asset = identities.get(stock)
        if not asset or asset in assets:
            raise ValueError("confirmed identity collision")
        remaining.append(Slot(stock, asset))
        assets.add(asset)
    if len(remaining) > 8:
        raise ValueError("slot overflow")
    return tuple(sorted(remaining, key=lambda s: s.instrument))
