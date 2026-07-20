from __future__ import annotations


def capacity_row(strategy_capital: float, order_value: float, daily_amount: float, participation_rate: float, impact_cost: float) -> dict[str, float]:
    capacity_multiple = daily_amount * participation_rate / order_value if order_value > 0 else float("inf")
    return {"strategy_capital": strategy_capital, "order_value": order_value, "daily_amount": daily_amount, "participation_rate": order_value / daily_amount if daily_amount > 0 else float("inf"), "capacity_multiple": capacity_multiple, "estimated_impact_cost": impact_cost}
