from __future__ import annotations

import pandas as pd

from .cost_model import execution_price, transaction_cost
from .execution_assumptions import ExecutionAssumptions
from .portfolio_constraints import round_lot


def run_execution(scores: pd.DataFrame, market: pd.DataFrame, assumptions: ExecutionAssumptions) -> dict[str, pd.DataFrame]:
    data = market.copy()
    data["datetime"] = pd.to_datetime(data["datetime"])
    scores = scores.copy(); scores["datetime"] = pd.to_datetime(scores["datetime"])
    market_dates = pd.DatetimeIndex(sorted(data.datetime.unique()))
    signal_dates = pd.DatetimeIndex(sorted(set(scores.datetime) & set(market_dates)))
    market_by_date = {date: group.set_index("instrument") for date, group in data.groupby("datetime", sort=False)}
    scores_by_date = {date: group for date, group in scores.groupby("datetime", sort=False)}
    cash = assumptions.initial_cash
    positions: dict[str, int] = {}
    buy_dates: dict[str, pd.Timestamp] = {}
    last_close: dict[str, float] = {}
    intents, fills, rejects, partials, costs, daily_rows = [], [], [], [], [], []
    previous_nav = assumptions.initial_cash
    for date_index, signal_date in enumerate(signal_dates):
        later = market_dates[market_dates > signal_date]
        if later.empty:
            break
        execution_date = later[0]
        day_market = market_by_date[execution_date]
        close_prices = day_market["close"].to_dict()
        missing_valuations = [instrument for instrument in positions if instrument not in close_prices]
        valuation_prices = {instrument: close_prices.get(instrument, last_close.get(instrument)) for instrument in positions}
        if any(price is None for price in valuation_prices.values()):
            raise ValueError("held position has no current or prior close for valuation")
        nav_before = cash + sum(quantity * float(valuation_prices[instrument]) for instrument, quantity in positions.items())
        if date_index % assumptions.rebalance_every != 0:
            daily_rows.append({"datetime": execution_date, "cash": cash, "nav": nav_before, "turnover": 0.0, "accounting_error": 0.0, "daily_return": nav_before / previous_nav - 1, "holding_valuation_missing_count": len(missing_valuations), "unfilled_shares": 0, "calendar_mode": "signal_date_only"})
            previous_nav = nav_before
            last_close.update({key: float(value) for key, value in close_prices.items() if pd.notna(value)})
            continue
        ranked = scores_by_date[signal_date].dropna(subset=["composite_score"]).nlargest(assumptions.top_k, "composite_score")
        targets = set(ranked.instrument)
        target_value = nav_before / max(1, len(targets))
        cash_start = cash; buy_gross = sell_gross = total_cost = turnover_value = 0.0
        orders = [(instrument, "sell") for instrument in sorted(set(positions) - targets)] + [(instrument, "buy") for instrument in ranked.instrument]
        for instrument, side in orders:
            if instrument not in day_market.index:
                requested = positions.get(instrument, 0) if side == "sell" else 0
                rejects.append({"signal_date": signal_date, "execution_date": execution_date, "instrument": instrument, "side": side, "reason": "missing_market_data", "unfilled_shares": requested}); continue
            row = day_market.loc[instrument]
            suspended = bool(row.get("suspended", False)) or float(row.get("volume", 0)) <= 0
            blocked = suspended or (side == "buy" and (not bool(row.get("can_buy", True)) or bool(row.get("limit_up", False)))) or (side == "sell" and (not bool(row.get("can_sell", True)) or bool(row.get("limit_down", False))))
            current = positions.get(instrument, 0)
            desired = round_lot(target_value / float(row.open), assumptions.lot_size) if side == "buy" else 0
            requested = max(0, desired - current) if side == "buy" else current
            intents.append({"signal_date": signal_date, "execution_date": execution_date, "instrument": instrument, "side": side, "requested_shares": requested})
            if requested <= 0: continue
            if side == "sell" and buy_dates.get(instrument) == execution_date:
                rejects.append({"signal_date": signal_date, "execution_date": execution_date, "instrument": instrument, "side": side, "reason": "t_plus_one", "unfilled_shares": requested}); continue
            if blocked:
                reason = "suspended" if suspended else "limit_or_tradability"
                rejects.append({"signal_date": signal_date, "execution_date": execution_date, "instrument": instrument, "side": side, "reason": reason, "unfilled_shares": requested}); continue
            max_shares = round_lot(float(row.volume) * assumptions.max_participation_rate, assumptions.lot_size)
            executed = min(requested, max_shares)
            price = execution_price(float(row.open), side, assumptions.slippage_bps)
            if side == "buy":
                cash_after_minimum_fee = max(0.0, cash - assumptions.minimum_commission)
                affordable = round_lot(cash_after_minimum_fee / max(price * (1 + assumptions.buy_commission_rate), 1e-12), assumptions.lot_size)
                while affordable > 0:
                    affordable_value = affordable * price
                    affordable_fee = transaction_cost("buy", affordable_value, assumptions.buy_commission_rate, assumptions.sell_tax_rate, assumptions.minimum_commission)
                    if affordable_value + affordable_fee["total_cost"] <= cash + 1e-9:
                        break
                    affordable -= assumptions.lot_size
                executed = min(executed, affordable)
            if executed <= 0:
                rejects.append({"signal_date": signal_date, "execution_date": execution_date, "instrument": instrument, "side": side, "reason": "cash_or_participation", "unfilled_shares": requested}); continue
            value = executed * price
            fee = transaction_cost(side, value, assumptions.buy_commission_rate if side == "buy" else assumptions.sell_commission_rate, assumptions.sell_tax_rate, assumptions.minimum_commission)
            if side == "buy":
                cash -= value + fee["total_cost"]; positions[instrument] = current + executed; buy_dates[instrument] = execution_date; buy_gross += value
            else:
                cash += value - fee["total_cost"]; positions[instrument] = current - executed; sell_gross += value
                if positions[instrument] == 0: positions.pop(instrument); buy_dates.pop(instrument, None)
            total_cost += fee["total_cost"]; turnover_value += value
            fills.append({"signal_date": signal_date, "execution_date": execution_date, "instrument": instrument, "side": side, "shares": executed, "price": price, "trade_value": value})
            costs.append({"execution_date": execution_date, "instrument": instrument, "side": side, **fee})
            if executed < requested:
                partials.append({"execution_date": execution_date, "instrument": instrument, "side": side, "requested_shares": requested, "executed_shares": executed, "unfilled_shares": requested - executed})
        expected_cash = cash_start - buy_gross - total_cost + sell_gross
        post_trade_prices = {instrument: close_prices.get(instrument, last_close.get(instrument)) for instrument in positions}
        if any(price is None for price in post_trade_prices.values()):
            raise ValueError("held position has no current or prior close after execution")
        nav_after = cash + sum(quantity * float(post_trade_prices[instrument]) for instrument, quantity in positions.items())
        unfilled_shares = sum(int(item["unfilled_shares"]) for item in partials if item["execution_date"] == execution_date) + sum(int(item.get("unfilled_shares", 0)) for item in rejects if item["execution_date"] == execution_date)
        daily_rows.append({"datetime": execution_date, "cash": cash, "nav": nav_after, "turnover": turnover_value / max(nav_before, 1e-12), "accounting_error": cash - expected_cash, "daily_return": nav_after / previous_nav - 1, "holding_valuation_missing_count": len(missing_valuations), "unfilled_shares": unfilled_shares, "calendar_mode": "signal_date_only"})
        previous_nav = nav_after
        last_close.update({key: float(value) for key, value in close_prices.items() if pd.notna(value)})
    return {
        "order_intents": pd.DataFrame(intents), "executed_orders": pd.DataFrame(fills), "rejected_orders": pd.DataFrame(rejects),
        "partial_fills": pd.DataFrame(partials), "transaction_costs": pd.DataFrame(costs), "daily_accounting": pd.DataFrame(daily_rows),
        "positions": pd.DataFrame([{"instrument": key, "shares": value, "buy_date": buy_dates.get(key)} for key, value in positions.items()]),
    }
