from __future__ import annotations

import numpy as np
import pandas as pd


def build_label_date_map(
    feature_dates: pd.Series | pd.DatetimeIndex,
    calendar: pd.DatetimeIndex,
    *,
    entry_lag: int,
    holding_days: int,
) -> pd.DataFrame:
    """Map every feature date to exact canonical entry and exit dates."""

    if entry_lag < 1:
        raise ValueError("entry_lag must be at least one trading day")
    if holding_days < 1:
        raise ValueError("holding_days must be positive")
    canonical = pd.DatetimeIndex(calendar).drop_duplicates().sort_values()
    if canonical.empty:
        raise ValueError("canonical calendar is empty")
    dates = pd.DatetimeIndex(pd.to_datetime(feature_dates)).drop_duplicates().sort_values()
    positions = canonical.get_indexer(dates)
    if (positions < 0).any():
        missing = dates[positions < 0]
        raise ValueError(f"feature dates absent from canonical calendar: {missing[:5].tolist()}")

    entry_positions = positions + int(entry_lag)
    exit_positions = entry_positions + int(holding_days)
    entry_dates = np.full(len(dates), np.datetime64("NaT"), dtype="datetime64[ns]")
    exit_dates = np.full(len(dates), np.datetime64("NaT"), dtype="datetime64[ns]")
    entry_valid = entry_positions < len(canonical)
    exit_valid = exit_positions < len(canonical)
    entry_dates[entry_valid] = canonical.to_numpy()[entry_positions[entry_valid]]
    exit_dates[exit_valid] = canonical.to_numpy()[exit_positions[exit_valid]]
    return pd.DataFrame(
        {
            "datetime": dates,
            "calendar_position": positions,
            "entry_position": entry_positions,
            "exit_position": exit_positions,
            "entry_date": pd.to_datetime(entry_dates),
            "exit_date": pd.to_datetime(exit_dates),
            "terminal_entry_missing": ~entry_valid,
            "terminal_exit_missing": ~exit_valid,
        }
    )


def build_exact_calendar_label(
    keys: pd.DataFrame,
    prices: pd.DataFrame,
    calendar: pd.DatetimeIndex,
    *,
    price_column: str,
    label_name: str,
    entry_lag: int,
    holding_days: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Build T+1 labels without physical-row shifts or price filling."""

    required_keys = {"datetime", "instrument"}
    if not required_keys.issubset(keys):
        raise ValueError("label keys require datetime and instrument")
    if keys.duplicated(["datetime", "instrument"]).any():
        raise ValueError("label keys must be unique")
    required_prices = {*required_keys, price_column}
    if not required_prices.issubset(prices):
        raise ValueError(f"prices missing columns: {sorted(required_prices - set(prices))}")
    if prices.duplicated(["datetime", "instrument"]).any():
        raise ValueError("price keys must be unique")

    base = keys[["datetime", "instrument"]].copy()
    base["datetime"] = pd.to_datetime(base["datetime"])
    base["instrument"] = base["instrument"].astype(str).str.upper()
    price = prices[["datetime", "instrument", price_column]].copy()
    price["datetime"] = pd.to_datetime(price["datetime"])
    price["instrument"] = price["instrument"].astype(str).str.upper()
    price[price_column] = pd.to_numeric(price[price_column], errors="coerce").replace(
        [np.inf, -np.inf], np.nan
    )
    date_map = build_label_date_map(
        base["datetime"],
        calendar,
        entry_lag=entry_lag,
        holding_days=holding_days,
    )
    result = base.merge(date_map, on="datetime", how="left", validate="many_to_one")
    entry = price.rename(
        columns={"datetime": "entry_date", price_column: "entry_close"}
    )
    exit_prices = price.rename(
        columns={"datetime": "exit_date", price_column: "exit_close"}
    )
    result = result.merge(
        entry,
        on=["entry_date", "instrument"],
        how="left",
        validate="many_to_one",
    )
    result = result.merge(
        exit_prices,
        on=["exit_date", "instrument"],
        how="left",
        validate="many_to_one",
    )
    result[label_name] = result["exit_close"] / result["entry_close"] - 1.0
    invalid_price = (
        result["entry_close"].isna()
        | result["exit_close"].isna()
        | result["entry_close"].le(0)
        | result["exit_close"].le(0)
    )
    result.loc[invalid_price, label_name] = np.nan
    return result, date_map
