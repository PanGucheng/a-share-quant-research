from __future__ import annotations

from pathlib import Path
from typing import Mapping, Sequence

import numpy as np
import pandas as pd

from factor_research.context.listing import attach_listing_age, listing_dates
from factor_research.context.universe import attach_membership, load_instrument_intervals


def build_context_keys(
    frame: pd.DataFrame,
    provider_uri: str | Path,
    universes: Mapping[str, str],
    listing_source: str,
    segment_priority: Sequence[str],
) -> tuple[pd.DataFrame, dict[str, str]]:
    """Attach point-in-time context to unique date/instrument keys."""

    required = {"datetime", "instrument"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"frame is missing context key columns: {sorted(missing)}")

    provider = Path(provider_uri)
    result = frame[["datetime", "instrument"]].drop_duplicates().copy()
    result["datetime"] = pd.to_datetime(result["datetime"])
    result["instrument"] = result["instrument"].astype(str).str.upper()

    membership_columns: dict[str, str] = {}
    for context_name, instrument_file in universes.items():
        column = f"is_{context_name}"
        intervals = load_instrument_intervals(provider / "instruments" / f"{instrument_file}.txt")
        result = attach_membership(result, intervals, column)
        membership_columns[context_name] = column

    listing_intervals = load_instrument_intervals(provider / "instruments" / f"{listing_source}.txt")
    result = attach_listing_age(result, listing_dates(listing_intervals))

    missing_priority = [name for name in segment_priority if name not in membership_columns]
    if missing_priority:
        raise ValueError(f"segment_priority references unknown universes: {missing_priority}")
    priority_columns = [membership_columns[name] for name in segment_priority]
    result["major_index_membership_count"] = result[priority_columns].sum(axis=1).astype(int)
    result["index_segment"] = np.select(
        [result[column] for column in priority_columns],
        list(segment_priority),
        default="outside_major_indices",
    )
    return result.sort_values(["datetime", "instrument"]).reset_index(drop=True), membership_columns


def context_coverage(keys: pd.DataFrame, membership_columns: Mapping[str, str]) -> pd.DataFrame:
    total_rows = len(keys)
    rows: list[dict] = []

    def append(dimension: str, value: str, selected: pd.DataFrame) -> None:
        rows.append(
            {
                "dimension": dimension,
                "value": value,
                "row_count": int(len(selected)),
                "row_fraction": float(len(selected) / total_rows) if total_rows else np.nan,
                "date_count": int(selected["datetime"].nunique()),
                "instrument_count": int(selected["instrument"].nunique()),
            }
        )

    for name, column in membership_columns.items():
        append("universe_membership", name, keys[keys[column]])
    for value, selected in keys.groupby("index_segment", dropna=False, observed=False):
        append("index_segment", str(value), selected)
    for value, selected in keys.groupby("listing_age_bucket", dropna=False, observed=False):
        append("listing_age_bucket", str(value), selected)
    append("integrity", "major_index_overlap", keys[keys["major_index_membership_count"].gt(1)])
    append("integrity", "missing_listing_age", keys[keys["listing_age_days"].isna()])
    return pd.DataFrame(rows)


def attach_context(frame: pd.DataFrame, keys: pd.DataFrame) -> pd.DataFrame:
    context_columns = [column for column in keys.columns if column not in {"datetime", "instrument"}]
    return frame.merge(
        keys[["datetime", "instrument", *context_columns]],
        on=["datetime", "instrument"],
        how="left",
        validate="many_to_one",
    )


def load_benchmark_context(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path, parse_dates=["datetime"])
    required = {"datetime", "benchmark"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"benchmark context is missing columns: {sorted(missing)}")
    return frame


def attach_benchmark_relative_returns(
    factor_data: pd.DataFrame,
    benchmark_returns: pd.DataFrame,
    benchmark_by_segment: Mapping[str, str],
    label_return_columns: Mapping[str, str],
) -> pd.DataFrame:
    """Attach matching benchmark returns and derive arithmetic excess returns."""

    required = {"datetime", "index_segment", "label", "forward_return"}
    missing = required - set(factor_data.columns)
    if missing:
        raise ValueError(f"factor_data is missing benchmark-relative columns: {sorted(missing)}")

    long_frames = []
    for label, return_column in label_return_columns.items():
        if return_column not in benchmark_returns.columns:
            raise ValueError(f"benchmark context is missing return column: {return_column}")
        values = benchmark_returns[["datetime", "benchmark", return_column]].copy()
        values["label"] = label
        values = values.rename(columns={return_column: "benchmark_forward_return"})
        long_frames.append(values)
    benchmark_long = pd.concat(long_frames, ignore_index=True)

    result = factor_data.copy()
    result["benchmark"] = result["index_segment"].map(benchmark_by_segment)
    result = result.merge(
        benchmark_long,
        on=["datetime", "benchmark", "label"],
        how="left",
        validate="many_to_one",
    )
    result["excess_forward_return"] = result["forward_return"] - result["benchmark_forward_return"]
    return result
