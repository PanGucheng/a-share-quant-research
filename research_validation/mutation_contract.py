from __future__ import annotations

import hashlib

import numpy as np
import pandas as pd


def frame_content_hash(frame: pd.DataFrame, *, sort_keys: list[str] | None = None) -> str:
    ordered = frame.copy()
    if sort_keys:
        ordered = ordered.sort_values(sort_keys, kind="stable")
    ordered = ordered.reset_index(drop=True)
    for column in ordered.columns:
        if pd.api.types.is_datetime64_any_dtype(ordered[column]):
            ordered[column] = ordered[column].dt.strftime("%Y-%m-%dT%H:%M:%S.%f")
    values = pd.util.hash_pandas_object(ordered, index=False, categorize=True).to_numpy(dtype="uint64")
    digest = hashlib.sha256()
    digest.update("|".join(map(str, ordered.columns)).encode("utf-8"))
    digest.update(values.tobytes())
    return digest.hexdigest()


def canonical_frame_hash(frame: pd.DataFrame, *, sort_keys: list[str]) -> str:
    return frame_content_hash(frame, sort_keys=sort_keys)


def mutate_test_rows(
    frame: pd.DataFrame,
    *,
    test_dates: pd.DatetimeIndex,
    mutation: str,
    value_columns: list[str],
) -> pd.DataFrame:
    result = frame.copy()
    result["datetime"] = pd.to_datetime(result["datetime"])
    mask = result["datetime"].isin(pd.DatetimeIndex(test_dates))
    if mutation == "row_order":
        return pd.concat([result.loc[~mask], result.loc[mask].iloc[::-1]], ignore_index=True)
    if mutation == "extreme_missing":
        result.loc[mask, value_columns] = np.nan
    elif mutation in {"test_ic", "factor_exposure"}:
        result.loc[mask, value_columns] = -7.0 * result.loc[mask, value_columns]
    elif mutation == "labels":
        result.loc[mask, value_columns] = result.loc[mask, value_columns] + 99.0
    elif mutation == "raw_ohlcva":
        result.loc[mask, value_columns] = -5.0 * result.loc[mask, value_columns]
    else:
        raise ValueError(f"unknown mutation: {mutation}")
    return result
