from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd


def canonical_hash(value: object) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def filter_to_pit_intervals(frame: pd.DataFrame, intervals: pd.DataFrame) -> pd.DataFrame:
    required = {"datetime", "instrument"}
    if not required.issubset(frame.columns):
        raise ValueError(f"feature frame missing keys: {sorted(required - set(frame.columns))}")
    interval_columns = {"instrument", "start_date", "end_date"}
    if not interval_columns.issubset(intervals.columns):
        raise ValueError(f"interval frame missing columns: {sorted(interval_columns - set(intervals.columns))}")
    values = frame.copy()
    values["datetime"] = pd.to_datetime(values["datetime"]).dt.normalize()
    values["instrument"] = values["instrument"].astype(str).str.upper()
    membership = intervals[["instrument", "start_date", "end_date"]].copy()
    membership["instrument"] = membership["instrument"].astype(str).str.upper()
    membership["start_date"] = pd.to_datetime(membership["start_date"]).dt.normalize()
    membership["end_date"] = pd.to_datetime(membership["end_date"]).dt.normalize()
    merged = values.merge(membership, on="instrument", how="inner")
    included = merged["datetime"].between(merged["start_date"], merged["end_date"])
    result = merged.loc[included].drop(columns=["start_date", "end_date"])
    result = result.drop_duplicates(["datetime", "instrument"], keep="last")
    return result.sort_values(["datetime", "instrument"], kind="stable").reset_index(drop=True)


def build_pit_key_grid(intervals: pd.DataFrame, calendar: pd.DatetimeIndex) -> pd.DataFrame:
    dates = pd.DatetimeIndex(calendar).normalize()
    rows: list[pd.DataFrame] = []
    for item in intervals[["instrument", "start_date", "end_date"]].itertuples(index=False):
        start = pd.Timestamp(item.start_date).normalize()
        end = pd.Timestamp(item.end_date).normalize()
        active = dates[(dates >= start) & (dates <= end)]
        if len(active):
            rows.append(pd.DataFrame({"datetime": active, "instrument": str(item.instrument).upper()}))
    if not rows:
        return pd.DataFrame(columns=["datetime", "instrument"])
    result = pd.concat(rows, ignore_index=True).drop_duplicates(["datetime", "instrument"])
    return result.sort_values(["datetime", "instrument"], kind="stable").reset_index(drop=True)


def resumable_batch_valid(row: dict[str, object], expected_input_hash: str, path: Path) -> bool:
    return (
        str(row.get("status")) == "pass"
        and str(row.get("input_hash")) == expected_input_hash
        and path.is_file()
        and str(row.get("output_sha256")) == file_sha256(path)
    )


def atomic_parquet(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    frame.to_parquet(temporary, index=False, compression="zstd")
    temporary.replace(path)


def forward_return_label(frame: pd.DataFrame, price_column: str, entry_lag: int, holding_days: int) -> pd.Series:
    values = frame.sort_values(["instrument", "datetime"], kind="stable")
    group = values.groupby("instrument", sort=False)[price_column]
    entry = group.shift(-entry_lag)
    exit_price = group.shift(-(entry_lag + holding_days))
    return (exit_price / entry - 1.0).reindex(values.index)
