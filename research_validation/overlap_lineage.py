from __future__ import annotations

import hashlib
from typing import Iterable

import numpy as np
import pandas as pd


KEYS = ["datetime", "instrument"]


def causal_kama(
    close: pd.Series,
    *,
    window: int = 10,
    fast_period: int = 2,
    slow_period: int = 30,
) -> pd.Series:
    """Compute KAMA without the upstream ``np.roll`` wraparound.

    The vendored TA implementation uses ``np.roll`` for lagged values, so its
    initialization reads the end of the supplied series and changes when the
    calculation end date changes.  This implementation uses causal differences,
    retains recursive state across ordinary missing observations, and emits NaN
    while the current rolling input is unavailable.
    """

    values = pd.to_numeric(close, errors="coerce").astype(float)
    change = values.diff(window).abs()
    volatility = values.diff().abs().rolling(window, min_periods=window).sum()
    efficiency = change.divide(volatility.where(volatility.ne(0)))
    efficiency = efficiency.where(volatility.ne(0), 0.0)
    fast = 2.0 / (fast_period + 1.0)
    slow = 2.0 / (slow_period + 1.0)
    smoothing = (efficiency * (fast - slow) + slow) ** 2
    output = np.full(len(values), np.nan, dtype=float)
    state = np.nan
    raw = values.to_numpy(dtype=float)
    weights = smoothing.to_numpy(dtype=float)
    for position, (price, weight) in enumerate(zip(raw, weights, strict=True)):
        if not np.isfinite(price) or not np.isfinite(weight):
            continue
        if not np.isfinite(state):
            state = price
        else:
            state = state + weight * (price - state)
        output[position] = state
    return pd.Series(output, index=close.index, name="ta_momentum_kama")


def causal_kama_frame(raw: pd.DataFrame) -> pd.DataFrame:
    required = {"datetime", "instrument", "$close"}
    missing = sorted(required - set(raw.columns))
    if missing:
        raise ValueError(f"KAMA input missing columns: {missing}")
    frame = raw[["datetime", "instrument", "$close"]].copy()
    frame["datetime"] = pd.to_datetime(frame["datetime"])
    frame["instrument"] = frame["instrument"].astype(str).str.upper()
    if frame.duplicated(KEYS).any():
        raise ValueError("KAMA input contains duplicate keys")
    parts: list[pd.DataFrame] = []
    for _, group in frame.groupby("instrument", sort=True):
        ordered = group.sort_values("datetime", kind="stable").copy()
        ordered["ta_momentum_kama"] = causal_kama(ordered["$close"])
        parts.append(ordered[[*KEYS, "ta_momentum_kama"]])
    if not parts:
        return pd.DataFrame(columns=[*KEYS, "ta_momentum_kama"])
    return pd.concat(parts, ignore_index=True).sort_values(KEYS, kind="stable").reset_index(drop=True)


def project_to_keys(
    values: pd.DataFrame,
    keys: pd.DataFrame,
    names: Iterable[str],
) -> pd.DataFrame:
    factors = list(names)
    source = values[[*KEYS, *factors]].copy()
    source["datetime"] = pd.to_datetime(source["datetime"])
    source["instrument"] = source["instrument"].astype(str).str.upper()
    if source.duplicated(KEYS).any():
        raise ValueError("corrected factor values contain duplicate keys")
    result = keys[KEYS].merge(source, on=KEYS, how="left", validate="one_to_one")
    result[factors] = result[factors].replace([np.inf, -np.inf], np.nan)
    return result.sort_values(KEYS, kind="stable").reset_index(drop=True)


def replace_factor_columns(
    parent: pd.DataFrame,
    corrected: pd.DataFrame,
    names: Iterable[str],
) -> pd.DataFrame:
    factors = list(names)
    left = parent.drop(columns=factors).copy()
    right = corrected[[*KEYS, *factors]].copy()
    output = left.merge(right, on=KEYS, how="left", validate="one_to_one")
    if len(output) != len(parent):
        raise ValueError("corrected partition changed the parent key count")
    return output[parent.columns].sort_values(KEYS, kind="stable").reset_index(drop=True)


def partition_set_identity(rows: pd.DataFrame) -> str:
    required = {"year", "partition_id", "output_sha256", "row_count", "factor_count"}
    missing = sorted(required - set(rows.columns))
    if missing:
        raise ValueError(f"partition identity missing columns: {missing}")
    ordered = rows.sort_values(["year", "partition_id"], kind="stable")
    material = "\n".join(
        "|".join(
            [
                str(item.year),
                str(item.partition_id),
                str(item.output_sha256),
                str(item.row_count),
                str(item.factor_count),
            ]
        )
        for item in ordered.itertuples(index=False)
    )
    return "extended-matrix:" + hashlib.sha256(material.encode("utf-8")).hexdigest()


def exact_or_close_counts(
    left: pd.Series,
    right: pd.Series,
    *,
    absolute_tolerance: float = 1e-10,
    relative_tolerance: float = 1e-8,
) -> dict[str, int | float]:
    a = pd.to_numeric(left, errors="coerce").to_numpy(dtype=np.float64)
    b = pd.to_numeric(right, errors="coerce").to_numpy(dtype=np.float64)
    if len(a) != len(b):
        raise ValueError("value comparison requires equal lengths")
    both_nan = np.isnan(a) & np.isnan(b)
    same_infinity = np.isinf(a) & np.isinf(b) & (np.signbit(a) == np.signbit(b))
    exact = both_nan | same_infinity | (a.view(np.uint64) == b.view(np.uint64))
    close = both_nan | same_infinity
    finite = np.isfinite(a) & np.isfinite(b)
    close[finite] = np.isclose(
        a[finite],
        b[finite],
        atol=absolute_tolerance,
        rtol=relative_tolerance,
    )
    return {
        "row_count": len(a),
        "exact_count": int(exact.sum()),
        "close_count": int(close.sum()),
        "difference_count": int((~close).sum()),
        "match_ratio": float(close.mean()) if len(close) else np.nan,
    }
