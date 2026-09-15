"""Frozen E3 budget arithmetic; caller must supply A-only certified inputs."""

import math

from .economic_execution_contract import dated_fees, lot_quantity, MotherOrderFees


def personal_fees(date, exchange, *, verified_par_value=None):
    # Reuse dated rates; no change to legacy 0.0003 execution defaults/receipts.
    fee = dated_fees(date, exchange, early2015_evidence_accepted=True, par_value=verified_par_value)
    return dict(fee, commission_rate=0.00025, minimum_commission=5.0,
                commission_authority="E3 frozen user assumption; exchange/regulatory bundled",
                early_transfer_minimum_assumption=0.0)


def entry_quantity(*, prior_close, certified_base, spendable_cash, board, fee, adv20):
    """Fees and reserve included; no unfilled-sale proceeds or receivable argument."""
    if not all(math.isfinite(v) and v >= 0 for v in (certified_base, spendable_cash)):
        raise ValueError("invalid A budget")
    if not all(math.isfinite(v) and v > 0 for v in (prior_close, adv20)):
        return 0
    budget = min(0.95 * certified_base / 8, max(0, spendable_cash - 0.05 * certified_base))
    quantity = lot_quantity(min(budget / prior_close, adv20 * 0.01), board, "buy")
    step = 1 if board == "star" else 100
    while quantity:
        parts, _ = MotherOrderFees().quote("entry", quantity * prior_close, quantity, "buy", fee, 10)
        if quantity * prior_close + sum(parts.values()) <= budget:
            break
        quantity = lot_quantity(max(0, quantity - step), board, "buy")
    return int(quantity)
