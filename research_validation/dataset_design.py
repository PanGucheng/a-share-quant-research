from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


def canonical_hash(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    ).hexdigest()


def autocorrelations(values: Iterable[float], max_lag: int) -> np.ndarray:
    series = pd.Series(values, dtype="float64").replace([np.inf, -np.inf], np.nan).dropna()
    if len(series) < 3:
        return np.full(max_lag + 1, np.nan)
    centered = series.to_numpy() - float(series.mean())
    denominator = float(np.dot(centered, centered))
    result = np.full(max_lag + 1, np.nan)
    result[0] = 1.0
    if denominator <= 0:
        return result
    for lag in range(1, min(max_lag, len(centered) - 1) + 1):
        result[lag] = float(np.dot(centered[:-lag], centered[lag:]) / denominator)
    return result


def bartlett_variance_inflation(values: Iterable[float], max_lag: int) -> float:
    rho = autocorrelations(values, max_lag)
    finite_lags = min(max_lag, int(np.isfinite(rho[1:]).sum()))
    if finite_lags == 0:
        return 1.0
    weights = 1.0 - np.arange(1, finite_lags + 1) / (finite_lags + 1)
    inflation = 1.0 + 2.0 * float(np.sum(weights * rho[1 : finite_lags + 1]))
    return max(inflation, 1.0 / max(len(pd.Series(values).dropna()), 1))


def effective_sample_size(
    values: Iterable[float], *, nominal_dates: int, max_lag: int
) -> tuple[float, float]:
    inflation = bartlett_variance_inflation(values, max_lag)
    effective = min(float(nominal_dates), max(1.0, float(nominal_dates) / inflation))
    return inflation, effective


def stationary_bootstrap_mean_se(
    values: Iterable[float],
    *,
    mean_block_length: int,
    repetitions: int = 1000,
    seed: int = 20260830,
) -> float:
    array = pd.Series(values, dtype="float64").replace([np.inf, -np.inf], np.nan).dropna().to_numpy()
    if len(array) < 3:
        return float("nan")
    rng = np.random.default_rng(seed)
    restart_probability = 1.0 / float(mean_block_length)
    means = np.empty(repetitions, dtype="float64")
    for repetition in range(repetitions):
        indexes = np.empty(len(array), dtype=np.int64)
        indexes[0] = rng.integers(0, len(array))
        restarts = rng.random(len(array) - 1) < restart_probability
        starts = rng.integers(0, len(array), size=len(array) - 1)
        for position in range(1, len(array)):
            indexes[position] = (
                starts[position - 1]
                if restarts[position - 1]
                else (indexes[position - 1] + 1) % len(array)
            )
        means[repetition] = float(array[indexes].mean())
    return float(means.std(ddof=1))


def theoretical_overlapping_return_ess(nominal_dates: int, horizon: int) -> float:
    """ESS for overlapping h-period sums when one-period innovations are iid.

    The exact finite-sample variance inflation uses the triangular autocorrelation
    rho(k)=(h-k)/h for k<h and the usual finite-sample mean weights.
    """
    if nominal_dates <= 0 or horizon <= 0:
        raise ValueError("nominal_dates and horizon must be positive")
    lags = np.arange(1, min(horizon, nominal_dates) , dtype="float64")
    rho = (horizon - lags) / horizon
    finite_sample_weights = 1.0 - lags / nominal_dates
    inflation = 1.0 + 2.0 * float(np.sum(finite_sample_weights * rho))
    return float(nominal_dates / inflation)


def classify_factor_history_layer(required_fields: str) -> str:
    fields = {value.strip() for value in str(required_fields).split(",") if value.strip()}
    statement = {
        "information_available_date",
        "revenue",
        "oper_cost",
        "operate_profit",
        "n_income_attr_p",
        "total_assets",
        "total_liab",
        "n_cashflow_act",
        "prior_total_assets",
    }
    moneyflow = {
        "buy_sm_amount",
        "sell_sm_amount",
        "buy_md_amount",
        "sell_md_amount",
        "buy_lg_amount",
        "sell_lg_amount",
        "buy_elg_amount",
        "sell_elg_amount",
        "net_mf_amount",
    }
    daily_basic = {
        "turnover_rate_f",
        "volume_ratio",
        "pe_ttm",
        "pb",
        "ps_ttm",
        "dv_ttm",
        "total_mv",
        "circ_mv",
        "total_mv_cny",
    }
    if fields & statement:
        return "fundamental_pit_plus_daily_basic"
    if fields & moneyflow:
        return "moneyflow_plus_price_volume"
    if fields & daily_basic:
        return "daily_basic_plus_price_volume"
    return "price_volume_core"


def factor_history_map(inventory: pd.DataFrame, qualification: pd.DataFrame) -> pd.DataFrame:
    required = {"name", "required_fields", "economic_family", "source"}
    missing = required - set(inventory.columns)
    if missing:
        raise ValueError(f"factor inventory missing columns: {sorted(missing)}")
    usable = qualification[["factor", "research_usable", "block_reason"]].rename(
        columns={"factor": "name"}
    )
    merged = inventory.merge(usable, on="name", how="left", validate="one_to_one")
    merged["history_layer"] = merged["required_fields"].map(classify_factor_history_layer)
    summary = (
        merged.groupby(["history_layer", "economic_family"], dropna=False, as_index=False)
        .agg(
            defined_factors=("name", "size"),
            research_usable_factors=("research_usable", lambda value: int(value.fillna(False).sum())),
            sources=("source", lambda value: ",".join(sorted(set(map(str, value))))),
        )
        .sort_values(["history_layer", "economic_family"])
        .reset_index(drop=True)
    )
    return summary


def qlib_binary_field_coverage(provider_uri: Path, fields: Iterable[str]) -> pd.DataFrame:
    calendar = pd.DatetimeIndex(
        pd.to_datetime(
            (provider_uri / "calendars/day.txt").read_text(encoding="utf-8").splitlines()
        )
    )
    year_indexes = {year: np.flatnonzero(calendar.year == year) for year in sorted(set(calendar.year))}
    features_root = provider_uri / "features"
    rows: list[dict[str, Any]] = []
    field_names = [str(field).lstrip("$").lower() for field in fields]
    for field in field_names:
        finite_by_year = {year: 0 for year in year_indexes}
        instruments_by_year = {year: 0 for year in year_indexes}
        total_instruments = 0
        earliest: pd.Timestamp | None = None
        latest: pd.Timestamp | None = None
        for instrument_dir in sorted(path for path in features_root.iterdir() if path.is_dir()):
            path = instrument_dir / f"{field}.day.bin"
            if not path.is_file():
                continue
            raw = np.fromfile(path, dtype="<f4")
            if len(raw) <= 1:
                continue
            start_index = int(raw[0])
            values = raw[1:]
            positions = start_index + np.flatnonzero(np.isfinite(values))
            positions = positions[(positions >= 0) & (positions < len(calendar))]
            if not len(positions):
                continue
            total_instruments += 1
            first = calendar[positions[0]]
            last = calendar[positions[-1]]
            earliest = first if earliest is None else min(earliest, first)
            latest = last if latest is None else max(latest, last)
            years = calendar[positions].year
            for year, count in zip(*np.unique(years, return_counts=True)):
                finite_by_year[int(year)] += int(count)
                instruments_by_year[int(year)] += 1
        for year in year_indexes:
            rows.append(
                {
                    "field": f"${field}",
                    "year": int(year),
                    "finite_observations": finite_by_year[year],
                    "instruments_with_data": instruments_by_year[year],
                    "provider_instruments_with_field": total_instruments,
                    "field_earliest_observation": earliest,
                    "field_latest_observation": latest,
                }
            )
    return pd.DataFrame(rows)

def regime_window_coverage(
    descriptors: pd.DataFrame,
    windows: pd.DataFrame,
    descriptor_columns: Iterable[str],
) -> pd.DataFrame:
    frame = descriptors.copy()
    frame["datetime"] = pd.to_datetime(frame["datetime"])
    columns = list(descriptor_columns)
    thresholds: dict[str, tuple[float, float]] = {}
    for column in columns:
        values = pd.to_numeric(frame[column], errors="coerce")
        thresholds[column] = (float(values.quantile(1 / 3)), float(values.quantile(2 / 3)))
    rows: list[dict[str, Any]] = []
    for window in windows.itertuples(index=False):
        part = frame.loc[
            frame["datetime"].between(pd.Timestamp(window.start), pd.Timestamp(window.end))
        ]
        for column in columns:
            low, high = thresholds[column]
            values = pd.to_numeric(part[column], errors="coerce").dropna()
            counts = {
                "low": int(values.le(low).sum()),
                "middle": int(values.gt(low).mul(values.lt(high)).sum()),
                "high": int(values.ge(high).sum()),
            }
            represented = sum(count >= 5 for count in counts.values())
            rows.append(
                {
                    "window_id": window.window_id,
                    "window_dates": len(part),
                    "descriptor": column,
                    "global_low_threshold": low,
                    "global_high_threshold": high,
                    "low_dates": counts["low"],
                    "middle_dates": counts["middle"],
                    "high_dates": counts["high"],
                    "represented_terciles_min_5_dates": represented,
                }
            )
    return pd.DataFrame(rows)
