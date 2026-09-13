"""Single-snapshot arithmetic only; no provider, predictions, account or NAV."""

from __future__ import annotations

import hashlib
import math

from .economic_execution_contract import dated_fees, lot_quantity, MotherOrderFees


def personal_fees(date, exchange):
    fee = dated_fees(date, exchange)
    return dict(fee, commission_rate=0.00025,
                commission_authority="user MVP assumption; stamp/transfer separate")


def charges(value, quantity, side, fee):
    parts, _ = MotherOrderFees().quote("independent_snapshot", value, quantity, side, fee)
    return sum(parts.values())


def affordable_quantity(price, budget, board, fee):
    """Largest legal buy quantity with component-rounded fees inside the budget."""
    if not math.isfinite(budget) or budget < 0:
        raise ValueError("invalid budget")
    if not math.isfinite(price) or price <= 0:
        return None
    q = lot_quantity(max(0, budget - fee["minimum_commission"]) / price, board, "buy")
    step = 1 if board == "star" else 100
    while q and q * price + charges(q * price, q, "buy", fee) > budget:
        q = lot_quantity(max(0, q - step), board, "buy")
    return int(q)


def hash_order(names, date, replicate):
    if len(names) != len(set(names)):
        raise ValueError("duplicate names")
    return sorted(names, key=lambda s: (hashlib.sha256(
        f"small-capital-v1|{date}|{replicate}|{s}".encode()).digest(), s))


def buffered_members(ranked_names, previous, k, hold_cutoff):
    """Prediction-only membership primitive. No execution semantics or prices."""
    if type(k) is not int or k < 1 or type(hold_cutoff) is not int or hold_cutoff < k:
        raise ValueError("invalid cutoffs")
    if len(ranked_names) != len(set(ranked_names)) or len(previous) != len(set(previous)):
        raise ValueError("duplicate members")
    if len(previous) > k:
        raise ValueError("previous membership exceeds K")
    held = set(previous) & set(ranked_names[:hold_cutoff])
    for stock in ranked_names[:k]:
        if len(held) == k:
            break
        held.add(stock)
    return [s for s in ranked_names if s in held]
