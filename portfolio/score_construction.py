from __future__ import annotations

import numpy as np
import pandas as pd


def capped_normalize(raw_weights: pd.Series, maximum: float) -> pd.Series:
    weights = pd.to_numeric(raw_weights, errors="coerce").fillna(0).clip(lower=0)
    if weights.sum() <= 0 or maximum <= 0 or maximum * len(weights) < 1 - 1e-12:
        raise ValueError("weights cannot satisfy normalization and maximum constraints")
    result = pd.Series(0.0, index=weights.index)
    remaining = set(weights.index)
    remaining_total = 1.0
    while remaining:
        base = weights.loc[list(remaining)]
        proposal = base / base.sum() * remaining_total if base.sum() > 0 else pd.Series(remaining_total / len(remaining), index=base.index)
        over = proposal[proposal > maximum + 1e-12]
        if over.empty:
            result.loc[proposal.index] = proposal
            break
        for index in over.index:
            result.loc[index] = maximum
            remaining.remove(index)
            remaining_total -= maximum
    return result / result.sum()


def cross_sectional_zscore(series: pd.Series, clip: float) -> pd.Series:
    median = series.median()
    scale = (series - median).abs().median() * 1.4826
    if not np.isfinite(scale) or scale <= 0:
        scale = series.std(ddof=0)
    if not np.isfinite(scale) or scale <= 0:
        return pd.Series(np.nan, index=series.index)
    return ((series - median) / scale).clip(-clip, clip)


def construct_daily_scores(
    frame: pd.DataFrame,
    component_weights: pd.DataFrame,
    *,
    method: str,
    min_components: int,
    clip: float,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    required = {"datetime", "instrument"}
    if required - set(frame.columns):
        raise ValueError("factor frame requires datetime and instrument")
    if component_weights["cluster_id"].duplicated().any():
        raise ValueError("component weights contain duplicate cluster votes")
    weights = component_weights.copy()
    weights["weight"] = weights["raw_weight"] / weights["raw_weight"].sum()
    data = frame[["datetime", "instrument", *weights["factor_column"]]].copy()
    parts = []
    for row in weights.itertuples(index=False):
        values = data.groupby("datetime", sort=False)[row.factor_column].transform(lambda series: cross_sectional_zscore(series, clip))
        parts.append(values * float(row.direction) * float(row.weight))
    matrix = pd.concat(parts, axis=1)
    valid = matrix.notna()
    component_count = valid.sum(axis=1)
    effective_weight = valid.mul(weights["weight"].to_numpy(), axis=1).sum(axis=1)
    score = matrix.sum(axis=1, skipna=True) / effective_weight.replace(0, np.nan)
    score.loc[component_count < min_components] = np.nan
    result = data[["datetime", "instrument"]].assign(method=method, composite_score=score, component_count=component_count)
    diagnostics = pd.DataFrame({"method": method, "datetime": data["datetime"], "component_count": component_count}).groupby(["method", "datetime"]).agg(rows=("component_count", "size"), minimum_components=("component_count", "min"), median_components=("component_count", "median")).reset_index()
    return result, diagnostics
