from __future__ import annotations

import pandas as pd


EVENT_COLUMNS = [
    "event_id",
    "datetime",
    "instrument",
    "side",
    "requested_shares",
    "executed_shares",
    "unfilled_shares",
    "base_price",
    "fill_price",
    "gross_value",
    "status",
    "reason",
    "commission",
    "stamp_tax",
    "slippage_cost",
    "cash_fee",
    "implementation_cost",
]


def normalize_execution_results(
    *,
    portfolio_metrics: dict,
    events: list[dict[str, object]],
    account: object,
    calendar: pd.DatetimeIndex,
) -> dict[str, pd.DataFrame]:
    event_frame = pd.DataFrame(events, columns=EVENT_COLUMNS)
    orders = event_frame.copy()
    fills = event_frame.loc[event_frame["executed_shares"].fillna(0).gt(0)].copy()
    rejected = event_frame.loc[event_frame["status"].eq("rejected")].copy()
    partial = event_frame.loc[event_frame["status"].eq("partial")].copy()
    costs = fills[
        [
            "event_id",
            "datetime",
            "instrument",
            "side",
            "commission",
            "stamp_tax",
            "slippage_cost",
            "cash_fee",
            "implementation_cost",
        ]
    ].copy()

    metric = portfolio_metrics["1day"][0].copy().reset_index()
    metric = metric.rename(columns={"account": "nav"})
    daily = pd.DataFrame({"datetime": pd.DatetimeIndex(calendar).normalize()}).merge(metric, on="datetime", how="left")
    daily["calendar_complete"] = daily["nav"].notna()
    daily["accounting_error"] = 0.0

    position_rows: list[dict[str, object]] = []
    for date, position in sorted(account.get_hist_positions().items()):
        nav = float(position.calculate_value())
        for instrument in position.get_stock_list():
            shares = float(position.get_stock_amount(instrument))
            price = float(position.get_stock_price(instrument))
            position_rows.append(
                {
                    "datetime": pd.Timestamp(date).normalize(),
                    "instrument": instrument,
                    "shares": shares,
                    "close": price,
                    "market_value": shares * price,
                    "weight": shares * price / nav if nav > 0 else 0.0,
                }
            )
    positions = pd.DataFrame(
        position_rows,
        columns=["datetime", "instrument", "shares", "close", "market_value", "weight"],
    )
    summary = pd.DataFrame(
        [
            {
                "trading_day_count": len(calendar),
                "accounting_day_count": int(daily["nav"].notna().sum()),
                "order_count": len(orders),
                "fill_count": len(fills),
                "partial_count": len(partial),
                "rejected_count": len(rejected),
                "ending_nav": float(daily["nav"].dropna().iloc[-1]) if daily["nav"].notna().any() else float("nan"),
                "total_cash_fee": float(costs["cash_fee"].sum()) if not costs.empty else 0.0,
                "total_slippage_cost": float(costs["slippage_cost"].sum()) if not costs.empty else 0.0,
            }
        ]
    )
    return {
        "orders": orders,
        "fills": fills,
        "rejected_orders": rejected,
        "partial_fills": partial,
        "transaction_costs": costs,
        "daily_accounting": daily,
        "positions": positions,
        "execution_summary": summary,
    }
