from __future__ import annotations

import numpy as np
import pandas as pd


def daily_exposure_similarity(frame: pd.DataFrame, factor_map: dict[str, str], max_dates: int | None = None) -> pd.DataFrame:
    data = frame[["datetime", "instrument", *sorted(set(factor_map.values()))]].copy()
    data["datetime"] = pd.to_datetime(data["datetime"])
    dates = sorted(data["datetime"].dropna().unique())
    if max_dates and len(dates) > max_dates:
        positions = np.linspace(0, len(dates) - 1, max_dates, dtype=int)
        dates = [dates[position] for position in positions]
    matrices = []
    for date in dates:
        cross = data.loc[data["datetime"] == date, sorted(set(factor_map.values()))]
        if len(cross) >= 20:
            matrices.append(cross.corr(method="spearman"))
    if not matrices:
        raise ValueError("no eligible cross-sections for exposure similarity")
    base = pd.concat(matrices, keys=range(len(matrices))).groupby(level=1).median()
    factors = list(factor_map)
    result = pd.DataFrame(index=factors, columns=factors, dtype=float)
    for left in factors:
        for right in factors:
            result.loc[left, right] = base.loc[factor_map[left], factor_map[right]]
    return result


def performance_similarity(series_map: dict[str, pd.Series]) -> pd.DataFrame:
    aligned = pd.concat({name: series for name, series in series_map.items()}, axis=1)
    return aligned.corr(method="spearman")


def combined_distance(exposure: pd.DataFrame, performance: pd.DataFrame, exposure_weight: float) -> pd.DataFrame:
    factors = sorted(set(exposure.index) & set(performance.index))
    exp = exposure.loc[factors, factors].abs().fillna(0)
    perf = performance.loc[factors, factors].abs().fillna(0)
    similarity = exposure_weight * exp + (1 - exposure_weight) * perf
    distance = 1 - similarity.clip(0, 1)
    np.fill_diagonal(distance.values, 0.0)
    return distance
