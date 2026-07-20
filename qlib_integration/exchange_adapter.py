from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd

from .contracts import validate_market_frame

try:
    from qlib.backtest.decision import Order
    from qlib.backtest.exchange import Exchange
except ImportError:  # pragma: no cover - lightweight CI deliberately omits Qlib
    Order = None  # type: ignore[assignment]
    Exchange = object  # type: ignore[assignment,misc]


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


def to_qlib_quote(market: pd.DataFrame, max_participation_rate: float) -> pd.DataFrame:
    frame = validate_market_frame(market)
    invalid_price = ~np.isfinite(frame["execution_price"]) | frame["execution_price"].le(0)
    # The project boundary uses original prices and raw shares. Qlib internally
    # trades split-adjusted prices and amounts, where raw_shares = amount * factor.
    quote = pd.DataFrame(
        {
            "$open": frame["open"] * frame["factor"],
            "$close": frame["close"] * frame["factor"],
            "$volume": frame["volume"] / frame["factor"],
            "$factor": frame["factor"],
            "$change": frame["change"],
            "$execution_price": frame["execution_price"] * frame["factor"],
            "$participation_limit": frame["volume"] * float(max_participation_rate) / frame["factor"],
            "limit_buy": (~frame["can_buy"]) | frame["limit_up"] | frame["suspended"] | invalid_price,
            "limit_sell": (~frame["can_sell"]) | frame["limit_down"] | frame["suspended"] | invalid_price,
            "audit_suspended": frame["suspended"],
            "audit_limit_up": frame["limit_up"],
            "audit_limit_down": frame["limit_down"],
            "audit_can_buy": frame["can_buy"],
            "audit_can_sell": frame["can_sell"],
            "audit_invalid_execution_price": invalid_price,
            "audit_no_volume": frame["volume"].fillna(0).le(0),
        }
    )
    quote.index = pd.MultiIndex.from_arrays(
        [frame["instrument"], frame["datetime"]], names=["instrument", "datetime"]
    )
    return quote.sort_index()


class PreparedQuoteExchange(Exchange):  # type: ignore[misc]
    """Qlib Exchange backed by a validated in-memory quote with A-share auditing."""

    def __init__(
        self,
        *,
        prepared_quote: pd.DataFrame,
        buy_commission_rate: float,
        sell_commission_rate: float,
        sell_tax_rate: float,
        minimum_commission: float,
        slippage_bps: float,
        **kwargs: object,
    ) -> None:
        if Order is None:
            raise ImportError("pyqlib is required for PreparedQuoteExchange")
        self._prepared_quote = prepared_quote.copy()
        self.buy_commission_rate = float(buy_commission_rate)
        self.sell_commission_rate = float(sell_commission_rate)
        self.sell_tax_rate = float(sell_tax_rate)
        self.minimum_commission = float(minimum_commission)
        self.slippage_bps = float(slippage_bps)
        self.t_plus_one = TPlusOneLedger()
        self.audit_events: list[dict[str, object]] = []
        self._event_counter = 0
        self._last_cost = ExecutionCostBreakdown(0.0, 0.0, 0.0, 0.0, 0.0)
        super().__init__(
            open_cost=0.0,
            close_cost=0.0,
            min_cost=0.0,
            impact_cost=0.0,
            **kwargs,
        )

    def get_quote_from_qlib(self) -> None:
        missing = sorted(set(self.all_fields) - set(self._prepared_quote.columns))
        if missing:
            raise ValueError(f"prepared quote missing Qlib fields: {missing}")
        self.quote_df = self._prepared_quote.loc[:, self.all_fields].copy()
        self.trade_w_adj_price = bool(
            (self.quote_df["$factor"].isna() & self.quote_df["$close"].notna()).any()
        )
        self._update_limit(self.limit_threshold)

    def _opening_raw_shares(self, position: object, trading_date: pd.Timestamp) -> dict[str, float]:
        if position is None:
            return {}
        result: dict[str, float] = {}
        for instrument in position.get_stock_list():
            try:
                factor = float(self.get_factor(instrument, trading_date, trading_date))
            except (TypeError, ValueError):
                factor = 1.0
            result[instrument] = float(position.get_stock_amount(instrument)) * factor
        return result

    def _calc_trade_info_by_order(self, order: object, position: object, dealt_order_amount: dict) -> tuple[float, float, float]:
        base_adjusted_price, _, _ = super()._calc_trade_info_by_order(order, position, dealt_order_amount)
        if order.deal_amount <= 0 or not np.isfinite(base_adjusted_price):
            self._last_cost = ExecutionCostBreakdown(0.0, 0.0, 0.0, 0.0, 0.0)
            return base_adjusted_price, 0.0, 0.0

        factor = float(order.factor or 1.0)
        side = "buy" if order.direction == Order.BUY else "sell"
        fill_adjusted_price = apply_slippage(base_adjusted_price, side, self.slippage_bps)

        def calculate() -> tuple[float, ExecutionCostBreakdown]:
            raw_shares = float(order.deal_amount) * factor
            gross_value = float(order.deal_amount) * fill_adjusted_price
            costs = component_costs(
                side=side,
                gross_value=gross_value,
                executed_shares=raw_shares,
                base_price=base_adjusted_price / factor,
                fill_price=fill_adjusted_price / factor,
                commission_rate=self.buy_commission_rate if side == "buy" else self.sell_commission_rate,
                sell_tax_rate=self.sell_tax_rate,
                minimum_commission=self.minimum_commission,
            )
            return gross_value, costs

        gross_value, costs = calculate()
        if side == "buy" and position is not None:
            unit = float(self.trade_unit or 0.0) / factor if self.trade_unit else 0.0
            while order.deal_amount > 0 and position.get_cash() + 1e-9 < gross_value + costs.cash_fee:
                order.deal_amount = max(0.0, float(order.deal_amount) - unit) if unit > 0 else 0.0
                gross_value, costs = calculate()

        self._last_cost = costs
        return fill_adjusted_price, gross_value, costs.cash_fee

    def _blocked_reason(self, order: object) -> str:
        key = (order.stock_id, pd.Timestamp(order.start_time).normalize())
        if key in self._prepared_quote.index:
            row = self._prepared_quote.loc[key]
            if bool(row["audit_invalid_execution_price"]):
                return "missing_execution_price"
            if bool(row["audit_suspended"]):
                return "suspended"
            if bool(row["audit_no_volume"]):
                return "no_volume"
            if order.direction == Order.BUY and bool(row["audit_limit_up"]):
                return "limit_up"
            if order.direction == Order.SELL and bool(row["audit_limit_down"]):
                return "limit_down"
            if order.direction == Order.BUY and not bool(row["audit_can_buy"]):
                return "cannot_buy"
            if order.direction == Order.SELL and not bool(row["audit_can_sell"]):
                return "cannot_sell"
        if self.check_stock_suspended(order.stock_id, order.start_time, order.end_time):
            return "suspended"
        return ""

    def deal_order(self, order: object, trade_account: object = None, position: object = None, dealt_order_amount: dict = None) -> tuple[float, float, float]:
        if dealt_order_amount is None:
            dealt_order_amount = {}
        actual_position = trade_account.current_position if trade_account is not None else position
        trading_date = pd.Timestamp(order.start_time).normalize()
        self.t_plus_one.start_day(trading_date, self._opening_raw_shares(actual_position, trading_date))
        factor = float(self.get_factor(order.stock_id, order.start_time, order.end_time) or 1.0)
        requested_adjusted = float(order.amount)
        requested_raw = requested_adjusted * factor
        t1_rejected = 0.0
        if order.direction == Order.SELL:
            allowed_raw, t1_rejected = self.t_plus_one.clip_sell(order.stock_id, requested_raw)
            order.amount = allowed_raw / factor

        preblocked_reason = self._blocked_reason(order)
        self._last_cost = ExecutionCostBreakdown(0.0, 0.0, 0.0, 0.0, 0.0)
        trade_val, trade_cost, trade_price = super().deal_order(
            order,
            trade_account=trade_account,
            position=position,
            dealt_order_amount=dealt_order_amount,
        )
        executed_raw = float(order.deal_amount) * factor
        side = "buy" if order.direction == Order.BUY else "sell"
        if executed_raw > 0:
            self.t_plus_one.record_fill(order.stock_id, side, executed_raw)

        reasons: list[str] = []
        if preblocked_reason:
            reasons.append(preblocked_reason)
        if t1_rejected > 1e-8:
            reasons.append("t_plus_one")
        if executed_raw + 1e-8 < requested_raw - t1_rejected and not preblocked_reason:
            reasons.append("cash_volume_or_lot")
        unfilled_raw = max(0.0, requested_raw - executed_raw)
        status = "filled" if unfilled_raw <= 1e-8 else ("partial" if executed_raw > 0 else "rejected")
        base_price = float(self.get_deal_price(order.stock_id, order.start_time, order.end_time, direction=order.direction))
        self._event_counter += 1
        self.audit_events.append(
            {
                "event_id": f"event_{self._event_counter:06d}",
                "datetime": trading_date,
                "instrument": order.stock_id,
                "side": side,
                "requested_shares": requested_raw,
                "executed_shares": executed_raw,
                "unfilled_shares": unfilled_raw,
                "base_price": base_price / factor if np.isfinite(base_price) else np.nan,
                "fill_price": trade_price / factor if np.isfinite(trade_price) else np.nan,
                "gross_value": trade_val,
                "status": status,
                "reason": ";".join(dict.fromkeys(reasons)),
                **cost_dict(self._last_cost),
            }
        )
        return trade_val, trade_cost, trade_price
