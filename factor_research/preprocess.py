from __future__ import annotations

import numpy as np
import pandas as pd


def numeric_series(values: pd.Series) -> pd.Series:
    result = pd.to_numeric(values, errors="coerce").astype(float)
    return result.replace([np.inf, -np.inf], np.nan)


def winsorize_mad(values: pd.Series, scale: float = 4.5) -> pd.Series:
    x = numeric_series(values)
    valid = x.dropna()
    if valid.empty:
        return x
    median = valid.median()
    mad = (valid - median).abs().median()
    if pd.isna(mad) or mad == 0:
        return x
    lower = median - scale * mad
    upper = median + scale * mad
    return x.clip(lower=lower, upper=upper)


def cross_sectional_zscore(values: pd.Series, robust: bool = True, clip: float | None = 3.0) -> pd.Series:
    x = numeric_series(values)
    valid = x.dropna()
    if len(valid) < 2:
        return pd.Series(np.nan, index=values.index)
    if robust:
        center = valid.median()
        scale = (valid - center).abs().median() * 1.4826
    else:
        center = valid.mean()
        scale = valid.std()
    if pd.isna(scale) or scale == 0:
        return pd.Series(np.nan, index=values.index)
    z = (x - center) / scale
    if clip is not None:
        z = z.clip(lower=-clip, upper=clip)
    return z


def cross_sectional_rank_norm(values: pd.Series) -> pd.Series:
    x = numeric_series(values)
    if x.notna().sum() < 2:
        return pd.Series(np.nan, index=values.index)
    return (x.rank(pct=True) - 0.5) * 3.46


def groupwise_zscore(frame: pd.DataFrame, factor: str, group_col: str, robust: bool = True) -> pd.Series:
    if factor not in frame.columns or group_col not in frame.columns:
        return pd.Series(np.nan, index=frame.index)
    return frame.groupby(["datetime", group_col], group_keys=False)[factor].transform(
        lambda values: cross_sectional_zscore(values, robust=robust)
    )


def _design_matrix(frame: pd.DataFrame, exposures: list[str]) -> pd.DataFrame:
    parts = []
    for exposure in exposures:
        if exposure not in frame.columns:
            continue
        values = frame[exposure]
        if pd.api.types.is_bool_dtype(values) or pd.api.types.is_numeric_dtype(values):
            numeric = numeric_series(values)
            if numeric.notna().any():
                parts.append(numeric.rename(exposure))
        else:
            dummies = pd.get_dummies(values.astype("string"), prefix=exposure, dummy_na=False)
            if not dummies.empty:
                parts.append(dummies.astype(float))
    if not parts:
        return pd.DataFrame(index=frame.index)
    design = pd.concat(parts, axis=1)
    design = design.loc[:, design.notna().any(axis=0)]
    return design


def residual_neutralize_daily(
    frame: pd.DataFrame,
    factor: str,
    exposures: list[str],
    min_count: int = 50,
    add_constant: bool = True,
) -> pd.Series:
    rows = []
    for _, group in frame.groupby("datetime", sort=True):
        y = numeric_series(group[factor]) if factor in group.columns else pd.Series(np.nan, index=group.index)
        x = _design_matrix(group, exposures)
        valid = y.notna()
        if not x.empty:
            valid &= x.notna().all(axis=1)
        if valid.sum() < max(min_count, len(x.columns) + 2):
            rows.append(pd.Series(np.nan, index=group.index))
            continue
        yv = y.loc[valid].to_numpy(dtype=float)
        xv = x.loc[valid].to_numpy(dtype=float) if not x.empty else np.empty((len(yv), 0))
        if add_constant:
            xv = np.column_stack([np.ones(len(yv)), xv])
        try:
            beta = np.linalg.lstsq(xv, yv, rcond=None)[0]
            fitted = xv @ beta
        except np.linalg.LinAlgError:
            rows.append(pd.Series(np.nan, index=group.index))
            continue
        residual = pd.Series(np.nan, index=group.index)
        residual.loc[valid] = yv - fitted
        rows.append(residual)
    return pd.concat(rows).sort_index() if rows else pd.Series(dtype=float)


def add_log_amount_proxy(frame: pd.DataFrame, source: str = "amount_mean_20") -> pd.DataFrame:
    result = frame.copy()
    if source in result.columns:
        values = numeric_series(result[source])
        result["log_amount_mean_20"] = np.log(values.where(values > 0))
    return result
