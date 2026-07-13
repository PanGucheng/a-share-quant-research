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


def build_period_comparisons(
    daily_by_method: dict[str, pd.DataFrame],
    required_methods: list[str],
    aliases: dict[str, str] | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, object]]:
    aliases = aliases or {}
    resolved = {method: aliases.get(method, method) for method in required_methods}
    missing = [method for method, source in resolved.items() if source not in daily_by_method]
    if missing:
        raise ValueError(f"required methods missing daily performance: {missing}")
    date_sets = {
        method: set(pd.to_datetime(daily_by_method[source]["datetime"]).dropna())
        for method, source in resolved.items()
    }
    common_dates = set.intersection(*date_sets.values()) if date_sets else set()
    if not common_dates:
        raise ValueError("required methods have no common valid trading dates")
    native_rows = []
    common_rows = []
    for method, source in resolved.items():
        native = daily_by_method[source].copy()
        common = native.loc[pd.to_datetime(native["datetime"]).isin(common_dates)].sort_values("datetime")
        native_row = performance_summary(native, method)
        native_row.update({"source_method": source, "start_date": pd.to_datetime(native.datetime).min().date(), "end_date": pd.to_datetime(native.datetime).max().date()})
        common_row = performance_summary(common, method)
        common_row.update({"source_method": source, "start_date": min(common_dates).date(), "end_date": max(common_dates).date()})
        native_rows.append(native_row)
        common_rows.append(common_row)
    contract = {
        "common_start_date": min(common_dates).date().isoformat(),
        "common_end_date": max(common_dates).date().isoformat(),
        "common_trading_days": len(common_dates),
        "method_date_mismatch_count": sum(date_set != common_dates for date_set in date_sets.values()),
    }
    return pd.DataFrame(native_rows), pd.DataFrame(common_rows), contract
