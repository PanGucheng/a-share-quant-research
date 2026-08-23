from __future__ import annotations

import numpy as np
import pandas as pd


LOCAL_RECOVERED_FACTOR_METADATA = {
    "ta_volume_vpt_canonical_v2": {
        "source_family": "ta",
        "economic_family": "TradingBehavior",
        "economic_subfamily": "VolumePriceTrend",
        "required_fields": ("$close", "$volume"),
        "canonical_replacement_for": "ta_volume_vpt",
        "evidence_tier": "B",
    },
    "ta_volume_nvi_canonical_v2": {
        "source_family": "ta",
        "economic_family": "TradingBehavior",
        "economic_subfamily": "NegativeVolumeIndex",
        "required_fields": ("$close", "$volume"),
        "canonical_replacement_for": "ta_volume_nvi",
        "evidence_tier": "B",
    },
}


def _negative_volume_index(close: pd.Series, volume: pd.Series) -> pd.Series:
    """Compute NVI without pandas' historical implicit forward-fill behavior."""
    result = pd.Series(np.nan, index=close.index, dtype="float64")
    state: float | None = None
    for position in range(len(close)):
        current_close = close.iloc[position]
        current_volume = volume.iloc[position]
        if position == 0:
            if pd.notna(current_close) and pd.notna(current_volume):
                state = 1000.0
                result.iloc[position] = state
            continue
        previous_close = close.iloc[position - 1]
        previous_volume = volume.iloc[position - 1]
        if any(pd.isna(value) for value in (current_close, current_volume, previous_close, previous_volume)):
            continue
        if state is None:
            state = 1000.0
        if current_volume < previous_volume:
            state *= float(current_close) / float(previous_close)
        result.iloc[position] = state
    return result


def _instrument_recovery(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.sort_values("datetime").copy()
    price_return = result["$close"].pct_change(fill_method=None)
    result["ta_volume_vpt_canonical_v2"] = (price_return * result["$volume"]).cumsum()
    result["ta_volume_nvi_canonical_v2"] = _negative_volume_index(
        result["$close"], result["$volume"]
    )
    return result


def add_local_recovered_factors(frame: pd.DataFrame) -> pd.DataFrame:
    """Add repaired TA VPT/NVI columns while preserving instrument-local time semantics."""
    required = {"datetime", "instrument", "$close", "$volume"}
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"local recovery frame missing columns: {missing}")
    if frame.duplicated(["datetime", "instrument"]).any():
        raise ValueError("local recovery frame contains duplicate datetime/instrument keys")
    result = pd.concat(
        [_instrument_recovery(group) for _, group in frame.groupby("instrument", sort=False)],
        ignore_index=True,
    )
    return result.sort_values(["instrument", "datetime"]).reset_index(drop=True)
