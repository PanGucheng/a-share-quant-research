from __future__ import annotations

import numpy as np
import pandas as pd


def performance_summary(daily: pd.DataFrame, method: str) -> dict:
    returns = pd.to_numeric(daily["daily_return"], errors="coerce").fillna(0)
    nav = (1 + returns).cumprod()
    drawdown = nav / nav.cummax() - 1
    return {"method": method, "trading_days": len(returns), "net_annualized_return": returns.mean() * 252, "net_ir": returns.mean() / returns.std(ddof=1) * np.sqrt(252) if returns.std(ddof=1) > 0 else np.nan, "maximum_drawdown": drawdown.min(), "average_turnover": daily.turnover.mean(), "positive_day_ratio": (returns > 0).mean(), "final_nav": daily.nav.iloc[-1]}


def cost_sensitivity(daily: pd.DataFrame, method: str, scenarios_bps: list[int], base_bps: int) -> pd.DataFrame:
    rows = []
    for bps in scenarios_bps:
        adjusted = daily.daily_return.fillna(0) - daily.turnover.fillna(0) * (bps - base_bps) / 10_000
        rows.append({"method": method, "cost_bps": bps, "annualized_return": adjusted.mean() * 252, "ir": adjusted.mean() / adjusted.std(ddof=1) * np.sqrt(252) if adjusted.std(ddof=1) > 0 else np.nan})
    return pd.DataFrame(rows)
