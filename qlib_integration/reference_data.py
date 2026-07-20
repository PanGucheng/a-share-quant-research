from __future__ import annotations

import numpy as np
import pandas as pd


QLIB_FIELDS = ["$open", "$close", "$volume", "$amount", "$factor", "$change"]


def build_market_frame(
    features: pd.DataFrame,
    calendar: pd.DatetimeIndex,
    instruments: list[str],
    *,
    limit_threshold: float,
) -> pd.DataFrame:
    """Convert Qlib features to a complete, valuation-safe execution calendar."""
    dates = pd.DatetimeIndex(calendar).normalize()
    index = pd.MultiIndex.from_product([instruments, dates], names=["instrument", "datetime"])
    raw = features.reset_index().copy()
    raw["datetime"] = pd.to_datetime(raw["datetime"]).dt.normalize()
    raw = raw.set_index(["instrument", "datetime"]).reindex(index).sort_index()
    original_open = pd.to_numeric(raw["$open"], errors="coerce")
    original_close = pd.to_numeric(raw["$close"], errors="coerce")
    original_factor = pd.to_numeric(raw["$factor"], errors="coerce")
    original_volume = pd.to_numeric(raw["$volume"], errors="coerce")
    valid_quote = (
        np.isfinite(original_open) & original_open.gt(0)
        & np.isfinite(original_close) & original_close.gt(0)
        & np.isfinite(original_factor) & original_factor.gt(0)
        & np.isfinite(original_volume) & original_volume.gt(0)
    )
    raw["$factor"] = original_factor.groupby(level="instrument").ffill().groupby(level="instrument").bfill()
    raw["$close"] = original_close.groupby(level="instrument").ffill().groupby(level="instrument").bfill()
    raw["$volume"] = original_volume.fillna(0.0)
    raw["$amount"] = pd.to_numeric(raw["$amount"], errors="coerce").fillna(0.0)
    raw["$change"] = pd.to_numeric(raw["$change"], errors="coerce")
    raw = raw.reset_index()
    raw["open"] = original_open.to_numpy() / raw["$factor"]
    raw["close"] = raw["$close"] / raw["$factor"]
    raw["volume"] = raw["$volume"] * raw["$factor"]
    raw["amount"] = raw["$amount"]
    raw["factor"] = raw["$factor"]
    raw["change"] = raw["$change"]
    raw["limit_up"] = raw["change"].ge(limit_threshold)
    raw["limit_down"] = raw["change"].le(-limit_threshold)
    raw["suspended"] = ~valid_quote.to_numpy()
    raw["can_buy"] = ~raw["suspended"] & ~raw["limit_up"]
    raw["can_sell"] = ~raw["suspended"] & ~raw["limit_down"]
    raw["execution_price"] = raw["open"]
    return raw[
        ["datetime", "instrument", "open", "close", "volume", "amount", "can_buy", "can_sell",
         "limit_up", "limit_down", "suspended", "factor", "change", "execution_price"]
    ].sort_values(["datetime", "instrument"], kind="stable").reset_index(drop=True)


def select_complete_instruments(
    features: pd.DataFrame,
    calendar: pd.DatetimeIndex,
    instrument_count: int,
) -> list[str]:
    required_dates = set(pd.DatetimeIndex(calendar).normalize())
    frame = features.reset_index()
    frame["datetime"] = pd.to_datetime(frame["datetime"]).dt.normalize()
    numeric = ["$open", "$close", "$volume", "$amount", "$factor", "$change"]
    valid = np.isfinite(frame[numeric]).all(axis=1)
    valid &= frame["$open"].gt(0) & frame["$close"].gt(0) & frame["$volume"].gt(0) & frame["$factor"].gt(0)
    eligible: list[str] = []
    for instrument, group in frame.loc[valid].groupby("instrument", sort=True):
        if required_dates.issubset(set(group["datetime"])):
            eligible.append(str(instrument))
    if len(eligible) < instrument_count:
        raise ValueError(f"only {len(eligible)} instruments have complete reference coverage; need {instrument_count}")
    return eligible[:instrument_count]


def build_reference_frames(
    features: pd.DataFrame,
    history_calendar: pd.DatetimeIndex,
    execution_calendar: pd.DatetimeIndex,
    *,
    instrument_count: int,
    momentum_lookback: int,
    limit_threshold: float,
    profile_name: str,
    research_run_family_id: str,
) -> tuple[pd.DataFrame, pd.DataFrame, list[str]]:
    selected = select_complete_instruments(features, history_calendar, instrument_count)
    raw = features.reset_index()
    raw["datetime"] = pd.to_datetime(raw["datetime"]).dt.normalize()
    raw = raw.loc[raw["instrument"].isin(selected)].copy()
    raw = raw.rename(columns={column: column[1:] for column in QLIB_FIELDS})
    raw = raw.sort_values(["instrument", "datetime"], kind="stable")
    raw["momentum"] = raw.groupby("instrument", sort=False)["close"].pct_change(momentum_lookback)

    execution_dates = set(pd.DatetimeIndex(execution_calendar).normalize())
    market = raw.loc[raw["datetime"].isin(execution_dates)].copy()
    market["open"] = market["open"] / market["factor"]
    market["close"] = market["close"] / market["factor"]
    market["volume"] = market["volume"] * market["factor"]
    market["limit_up"] = market["change"].ge(limit_threshold)
    market["limit_down"] = market["change"].le(-limit_threshold)
    market["suspended"] = market["volume"].le(0)
    market["can_buy"] = ~market["suspended"] & ~market["limit_up"]
    market["can_sell"] = ~market["suspended"] & ~market["limit_down"]
    market["execution_price"] = market["open"]
    market = market[
        [
            "datetime",
            "instrument",
            "open",
            "close",
            "volume",
            "amount",
            "can_buy",
            "can_sell",
            "limit_up",
            "limit_down",
            "suspended",
            "factor",
            "change",
            "execution_price",
        ]
    ]

    signal_dates = set(pd.DatetimeIndex(execution_calendar[:-1]).normalize())
    signal = raw.loc[raw["datetime"].isin(signal_dates), ["datetime", "instrument", "momentum"]].copy()
    if not np.isfinite(signal["momentum"]).all():
        raise ValueError("reference momentum contains non-finite values; extend the history window")
    signal = signal.rename(columns={"momentum": "score"})
    signal["method"] = f"transparent_momentum_{momentum_lookback}d"
    signal["signal_artifact_id"] = "signal:qlib-exchange-local-reference-v1"
    signal["profile_name"] = profile_name
    signal["profile_type"] = "reference"
    signal["research_run_family_id"] = research_run_family_id
    return signal, market, selected
