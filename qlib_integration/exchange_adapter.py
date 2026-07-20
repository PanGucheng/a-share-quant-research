from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class ExecutionCostBreakdown:
    commission: float
    stamp_tax: float
    slippage_cost: float
    cash_fee: float
    implementation_cost: float


def apply_slippage(base_price: float, side: str, slippage_bps: float) -> float:
    if base_price <= 0:
        raise ValueError("base execution price must be positive")
    if side not in {"buy", "sell"}:
        raise ValueError(f"unsupported side: {side}")
    direction = 1.0 if side == "buy" else -1.0
    return float(base_price) * (1.0 + direction * float(slippage_bps) / 10_000.0)


def component_costs(
    *,
    side: str,
    gross_value: float,
    executed_shares: float,
    base_price: float,
    fill_price: float,
    commission_rate: float,
    sell_tax_rate: float,
    minimum_commission: float,
) -> ExecutionCostBreakdown:
    if side not in {"buy", "sell"}:
        raise ValueError(f"unsupported side: {side}")
    if gross_value <= 0 or executed_shares <= 0:
        return ExecutionCostBreakdown(0.0, 0.0, 0.0, 0.0, 0.0)
    commission = max(float(minimum_commission), float(gross_value) * float(commission_rate))
    stamp_tax = float(gross_value) * float(sell_tax_rate) if side == "sell" else 0.0
    slippage_cost = abs(float(fill_price) - float(base_price)) * float(executed_shares)
    cash_fee = commission + stamp_tax
    return ExecutionCostBreakdown(
        commission=commission,
        stamp_tax=stamp_tax,
        slippage_cost=slippage_cost,
        cash_fee=cash_fee,
        implementation_cost=cash_fee + slippage_cost,
    )


class TPlusOneLedger:
    """Track raw shares that may be sold on a given trading day."""

    def __init__(self) -> None:
        self.current_date = None
        self.opening_sellable: dict[str, float] = {}
        self.sold_today: dict[str, float] = {}
        self.bought_today: dict[str, float] = {}

    def start_day(self, trading_date: object, opening_raw_shares: dict[str, float]) -> None:
        if self.current_date == trading_date:
            return
        self.current_date = trading_date
        self.opening_sellable = {key: max(0.0, float(value)) for key, value in opening_raw_shares.items()}
        self.sold_today = {}
        self.bought_today = {}

    def sellable(self, instrument: str) -> float:
        return max(0.0, self.opening_sellable.get(instrument, 0.0) - self.sold_today.get(instrument, 0.0))

    def clip_sell(self, instrument: str, requested_raw_shares: float) -> tuple[float, float]:
        allowed = min(max(0.0, float(requested_raw_shares)), self.sellable(instrument))
        return allowed, max(0.0, float(requested_raw_shares) - allowed)

    def record_fill(self, instrument: str, side: str, raw_shares: float) -> None:
        if raw_shares < 0:
            raise ValueError("filled shares must be non-negative")
        target = self.bought_today if side == "buy" else self.sold_today
        if side not in {"buy", "sell"}:
            raise ValueError(f"unsupported side: {side}")
        target[instrument] = target.get(instrument, 0.0) + float(raw_shares)

    def snapshot(self) -> dict[str, dict[str, float]]:
        instruments = sorted(set(self.opening_sellable) | set(self.sold_today) | set(self.bought_today))
        return {
            instrument: {
                "opening_sellable_shares": self.opening_sellable.get(instrument, 0.0),
                "sold_today_shares": self.sold_today.get(instrument, 0.0),
                "bought_today_shares": self.bought_today.get(instrument, 0.0),
                "remaining_sellable_shares": self.sellable(instrument),
            }
            for instrument in instruments
        }


def cost_dict(cost: ExecutionCostBreakdown) -> dict[str, float]:
    return asdict(cost)
