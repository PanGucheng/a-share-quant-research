from __future__ import annotations

import numpy as np
import pandas as pd


def _filter_allowed_dates(frame: pd.DataFrame, allowed_dates: pd.DatetimeIndex | list[pd.Timestamp] | None) -> pd.DataFrame:
    if allowed_dates is None:
        raise ValueError("allowed_dates is required for holdout-clean similarity")
    allowed = pd.DatetimeIndex(allowed_dates).normalize().unique()
    values = frame.copy()
    values["datetime"] = pd.to_datetime(values["datetime"]).dt.normalize()
    return values.loc[values["datetime"].isin(allowed)].copy()


def daily_exposure_similarity(
    frame: pd.DataFrame,
    factor_map: dict[str, str],
    max_dates: int | None = None,
    *,
    allowed_dates: pd.DatetimeIndex | list[pd.Timestamp] | None = None,
    minimum_pair_observations: int = 20,
) -> pd.DataFrame:
    data = frame[["datetime", "instrument", *sorted(set(factor_map.values()))]].copy()
    data = _filter_allowed_dates(data, allowed_dates)
    dates = sorted(data["datetime"].dropna().unique())
    if max_dates and len(dates) > max_dates:
        positions = np.linspace(0, len(dates) - 1, max_dates, dtype=int)
        dates = [dates[position] for position in positions]
    matrices = []
    for date in dates:
        cross = data.loc[data["datetime"] == date, sorted(set(factor_map.values()))]
        if len(cross) >= 20:
            matrices.append(cross.corr(method="spearman", min_periods=minimum_pair_observations))
    if not matrices:
        raise ValueError("no eligible cross-sections for exposure similarity")
    base = pd.concat(matrices, keys=range(len(matrices))).groupby(level=1).median()
    factors = list(factor_map)
    result = pd.DataFrame(index=factors, columns=factors, dtype=float)
    for left in factors:
        for right in factors:
            result.loc[left, right] = base.loc[factor_map[left], factor_map[right]]
    return result


def performance_similarity(
    series_map: dict[str, pd.Series],
    *,
    allowed_dates: pd.DatetimeIndex | list[pd.Timestamp] | None = None,
    minimum_pair_dates: int = 20,
) -> pd.DataFrame:
    if allowed_dates is None:
        raise ValueError("allowed_dates is required for holdout-clean similarity")
    allowed = pd.DatetimeIndex(allowed_dates).normalize().unique()
    aligned = pd.concat({name: series for name, series in series_map.items()}, axis=1)
    aligned.index = pd.to_datetime(aligned.index).normalize()
    aligned = aligned.loc[aligned.index.isin(allowed)]
    return aligned.corr(method="spearman", min_periods=minimum_pair_dates)


def combined_distance(exposure: pd.DataFrame, performance: pd.DataFrame, exposure_weight: float) -> pd.DataFrame:
    factors = sorted(set(exposure.index) & set(performance.index))
    exp = exposure.loc[factors, factors].abs().fillna(0)
    perf = performance.loc[factors, factors].abs().fillna(0)
    similarity = exposure_weight * exp + (1 - exposure_weight) * perf
    distance = 1 - similarity.clip(0, 1)
    np.fill_diagonal(distance.values, 0.0)
    return distance
