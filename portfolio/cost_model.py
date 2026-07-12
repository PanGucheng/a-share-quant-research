from __future__ import annotations


def transaction_cost(side: str, trade_value: float, commission_rate: float, sell_tax_rate: float, minimum_commission: float) -> dict[str, float]:
    commission = max(minimum_commission, trade_value * commission_rate) if trade_value > 0 else 0.0
    tax = trade_value * sell_tax_rate if side == "sell" else 0.0
    return {"commission": commission, "tax": tax, "total_cost": commission + tax}


def execution_price(mid_price: float, side: str, slippage_bps: float) -> float:
    direction = 1.0 if side == "buy" else -1.0
    return float(mid_price * (1 + direction * slippage_bps / 10_000.0))
