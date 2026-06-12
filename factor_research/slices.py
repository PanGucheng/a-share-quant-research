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
    label: str,
    up_threshold: float = 0.01,
    down_threshold: float = -0.01,
) -> pd.DataFrame:
    result = frame.copy()
    if label not in result.columns:
        result["market_state"] = "unknown"
        return result
    market_return = pd.to_numeric(result[label], errors="coerce").groupby(result["datetime"]).transform("mean")
    result["market_state"] = np.select(
        [market_return >= up_threshold, market_return <= down_threshold],
        ["up", "down"],
        default="sideways",
    )
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
