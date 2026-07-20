from __future__ import annotations

import math

import pandas as pd

from .contracts import validate_market_frame, validate_signal_frame
from .exchange_adapter import apply_slippage, component_costs
from .strategy_adapter import equal_weight_targets


def _floor_lot(shares: float, lot_size: int) -> int:
    return max(0, int(math.floor(float(shares) / lot_size + 1e-12)) * lot_size)


def run_reference_target_execution(
    signal: pd.DataFrame,
    market: pd.DataFrame,
    config: dict[str, object],
) -> dict[str, pd.DataFrame]:
    signals = validate_signal_frame(signal)
    markets = validate_market_frame(market)
    calendar = pd.DatetimeIndex(sorted(markets["datetime"].unique()))
    market_by_date = {date: group.set_index("instrument") for date, group in markets.groupby("datetime", sort=False)}
    signal_by_date = {date: group.set_index("instrument")["score"] for date, group in signals.groupby("datetime", sort=False)}
    cash = float(config["initial_cash"])
    positions: dict[str, int] = {}
    events: list[dict[str, object]] = []
    daily_rows: list[dict[str, object]] = []
    position_rows: list[dict[str, object]] = []
    event_counter = 0
    previous_nav = cash

    for step, execution_date in enumerate(calendar[1:], start=1):
        signal_date = calendar[step - 1]
        day = market_by_date[execution_date]
        target_weights = equal_weight_targets(signal_by_date[signal_date], int(config["top_k"]))
        mark_prices = {instrument: float(day.loc[instrument, "execution_price"]) for instrument in positions}
        nav_before = cash + sum(positions[instrument] * mark_prices[instrument] for instrument in positions)
        target_capital = nav_before * float(config["risk_degree"])
        desired: dict[str, float] = {}
        for instrument, weight in target_weights.items():
            price = float(day.loc[instrument, "execution_price"])
            desired[instrument] = target_capital * weight / price
        instruments = sorted(set(positions) | set(desired))
        orders = [
            (
                instrument,
                "sell",
                positions.get(instrument, 0)
                if desired.get(instrument, 0.0) <= 0
                else _floor_lot(
                    positions.get(instrument, 0) - desired.get(instrument, 0.0), int(config["lot_size"])
                ),
            )
            for instrument in instruments
            if positions.get(instrument, 0) - desired.get(instrument, 0.0) >= int(config["lot_size"])
            or (positions.get(instrument, 0) > 0 and desired.get(instrument, 0.0) <= 0)
        ]
        orders.extend(
            (
                instrument,
                "buy",
                _floor_lot(
                    desired.get(instrument, 0.0) - positions.get(instrument, 0), int(config["lot_size"])
                ),
            )
            for instrument in instruments
            if desired.get(instrument, 0.0) - positions.get(instrument, 0) >= int(config["lot_size"])
        )
        used_volume: dict[str, int] = {}
        for instrument, side, requested in orders:
            row = day.loc[instrument]
            blocked_reason = ""
            if bool(row["suspended"]):
                blocked_reason = "suspended"
            elif side == "buy" and bool(row["limit_up"]):
                blocked_reason = "limit_up"
            elif side == "sell" and bool(row["limit_down"]):
                blocked_reason = "limit_down"
            elif side == "buy" and not bool(row["can_buy"]):
                blocked_reason = "cannot_buy"
            elif side == "sell" and not bool(row["can_sell"]):
                blocked_reason = "cannot_sell"
            participation_cap = _floor_lot(
                float(row["volume"]) * float(config["max_participation_rate"]), int(config["lot_size"])
            )
            available_volume = max(0, participation_cap - used_volume.get(instrument, 0))
            executed = 0 if blocked_reason else min(requested, available_volume)
            base_price = float(row["execution_price"])
            fill_price = apply_slippage(base_price, side, float(config["slippage_bps"]))
            if side == "buy":
                while executed > 0:
                    gross = executed * fill_price
                    costs = component_costs(
                        side=side,
                        gross_value=gross,
                        executed_shares=executed,
                        base_price=base_price,
                        fill_price=fill_price,
                        commission_rate=float(config["buy_commission_rate"]),
                        sell_tax_rate=float(config["sell_tax_rate"]),
                        minimum_commission=float(config["minimum_commission"]),
                    )
                    if gross + costs.cash_fee <= cash + 1e-9:
                        break
                    executed -= int(config["lot_size"])
            gross = executed * fill_price
            costs = component_costs(
                side=side,
                gross_value=gross,
                executed_shares=executed,
                base_price=base_price,
                fill_price=fill_price,
                commission_rate=float(config["buy_commission_rate"] if side == "buy" else config["sell_commission_rate"]),
                sell_tax_rate=float(config["sell_tax_rate"]),
                minimum_commission=float(config["minimum_commission"]),
            )
            if executed > 0:
                used_volume[instrument] = used_volume.get(instrument, 0) + executed
                if side == "buy":
                    cash -= gross + costs.cash_fee
                    positions[instrument] = positions.get(instrument, 0) + executed
                else:
                    cash += gross - costs.cash_fee
                    positions[instrument] -= executed
                    if positions[instrument] == 0:
                        del positions[instrument]
            unfilled = requested - executed
            if not blocked_reason and unfilled > 0:
                blocked_reason = "cash_volume_or_lot"
            event_counter += 1
            events.append(
                {
                    "event_id": f"event_{event_counter:06d}",
                    "datetime": execution_date,
                    "instrument": instrument,
                    "side": side,
                    "requested_shares": requested,
                    "executed_shares": executed,
                    "unfilled_shares": unfilled,
                    "base_price": base_price,
                    "fill_price": fill_price if executed > 0 else float("nan"),
                    "gross_value": gross,
                    "status": "filled" if unfilled == 0 else ("partial" if executed > 0 else "rejected"),
                    "reason": blocked_reason,
                    "commission": costs.commission,
                    "stamp_tax": costs.stamp_tax,
                    "slippage_cost": costs.slippage_cost,
                    "cash_fee": costs.cash_fee,
                    "implementation_cost": costs.implementation_cost,
                }
            )
        stock_value = sum(positions[instrument] * float(day.loc[instrument, "close"]) for instrument in positions)
        nav = cash + stock_value
        daily_rows.append(
            {
                "datetime": execution_date,
                "cash": cash,
                "nav": nav,
                "stock_value": stock_value,
                "return": nav / previous_nav - 1.0,
                "calendar_complete": True,
                "accounting_error": nav - cash - stock_value,
            }
        )
        previous_nav = nav
        for instrument, shares in sorted(positions.items()):
            close = float(day.loc[instrument, "close"])
            position_rows.append(
                {
                    "datetime": execution_date,
                    "instrument": instrument,
                    "shares": shares,
                    "close": close,
                    "market_value": shares * close,
                    "weight": shares * close / nav if nav > 0 else 0.0,
                }
            )
    event_frame = pd.DataFrame(events)
    return {
        "orders": event_frame,
        "fills": event_frame.loc[event_frame["executed_shares"].gt(0)].copy(),
        "daily_accounting": pd.DataFrame(daily_rows),
        "positions": pd.DataFrame(position_rows),
    }
