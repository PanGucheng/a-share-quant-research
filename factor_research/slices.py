from __future__ import annotations

import numpy as np
import pandas as pd

from factor_research.diagnostics import assign_daily_bucket


def add_year_slice(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    result["year_slice"] = pd.to_datetime(result["datetime"]).dt.year.astype(str)
    return result


def add_volatility_bucket(frame: pd.DataFrame, source: str = "amplitude_20", quantiles: int = 5) -> pd.DataFrame:
    result = frame.copy()
    if source not in result.columns:
        result["volatility_bucket"] = pd.NA
        return result
    result["volatility_bucket"] = result.groupby("datetime")[source].transform(
        lambda values: assign_daily_bucket(pd.to_numeric(values, errors="coerce"), quantiles)
    )
    return result


def add_market_state(
    frame: pd.DataFrame,
    label: str | None = None,
    up_threshold: float = 0.03,
    down_threshold: float = -0.03,
    lookback: int = 20,
    min_periods: int = 10,
) -> pd.DataFrame:
    result = frame.copy()
    if "$close" not in result.columns:
        result["market_state"] = "unknown"
        return result

    ordered = result[["datetime", "instrument", "$close"]].copy()
    ordered["$close"] = pd.to_numeric(ordered["$close"], errors="coerce")
    ordered = ordered.sort_values(["instrument", "datetime"])
    ordered["daily_return"] = ordered.groupby("instrument", sort=False)["$close"].pct_change()
    market_daily = ordered.groupby("datetime", sort=True)["daily_return"].mean().dropna()
    market_past_return = (1 + market_daily).rolling(lookback, min_periods=min_periods).apply(np.prod, raw=True) - 1
    market_past_vol = market_daily.rolling(lookback, min_periods=min_periods).std()

    result["market_past_20d_return"] = result["datetime"].map(market_past_return)
    result["market_past_20d_vol"] = result["datetime"].map(market_past_vol)
    result["market_state"] = np.select(
        [
            result["market_past_20d_return"] >= up_threshold,
            result["market_past_20d_return"] <= down_threshold,
        ],
        ["up", "down"],
        default="sideways",
    )
    result.loc[result["market_past_20d_return"].isna(), "market_state"] = "unknown"
    return result


def add_default_slices(frame: pd.DataFrame, label: str, quantiles: int = 5) -> pd.DataFrame:
    result = add_year_slice(frame)
    result = add_volatility_bucket(result, source="amplitude_20", quantiles=quantiles)
    result = add_market_state(result, label=label)
    return result


def slice_definitions(frame: pd.DataFrame) -> list[tuple[str, str]]:
    definitions: list[tuple[str, str]] = []
    for column in ["year_slice", "liquidity_bucket", "volatility_bucket", "market_state"]:
        if column not in frame.columns:
            continue
        values = frame[column].dropna().unique().tolist()
        for value in sorted(values, key=lambda item: str(item)):
            definitions.append((column, str(value)))
    return definitions
