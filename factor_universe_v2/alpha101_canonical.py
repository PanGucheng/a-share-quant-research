from __future__ import annotations

import warnings
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from factor_research.alpha101_source import alpha101_rank_eligibility, import_ref_alpha101


CANONICAL_FIELD_TO_WIND = {
    "$open": "S_DQ_OPEN",
    "$high": "S_DQ_HIGH",
    "$low": "S_DQ_LOW",
    "$close": "S_DQ_CLOSE",
    "$volume": "S_DQ_VOLUME",
    "$amount": "S_DQ_AMOUNT",
    "$vwap": "S_DQ_VWAP",
}


def canonical_wide_inputs(frame: pd.DataFrame) -> dict[str, pd.DataFrame]:
    required = {"datetime", "instrument", *CANONICAL_FIELD_TO_WIND}
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"canonical Alpha101 frame missing columns: {missing}")
    if frame.duplicated(["datetime", "instrument"]).any():
        raise ValueError("canonical Alpha101 frame contains duplicate keys")
    result = {}
    for field, wind_name in CANONICAL_FIELD_TO_WIND.items():
        result[wind_name] = (
            frame.pivot(index="datetime", columns="instrument", values=field)
            .sort_index()
            .sort_index(axis=1)
        )
    return result


def compute_canonical_alpha101_features(
    frame: pd.DataFrame,
    *,
    registry_names: Iterable[str],
    source_local_path: Path,
    alpha_factory: Callable[[dict[str, pd.DataFrame]], Any] | None = None,
    rank_eligibility: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Evaluate existing Alpha101 methods with the provider's direct VWAP field.

    V1's reference class derives VWAP as amount / volume. V2 constructs the same
    reference object for formula reuse, then explicitly replaces only ``stock.vwap``
    with the provider's canonical field. V1 code and artifacts remain unchanged.
    """
    wide = canonical_wide_inputs(frame)
    source_module = None
    if alpha_factory is None:
        source_module = import_ref_alpha101(source_local_path)
        alpha_factory = source_module.Alphas
    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore",
            message="The default fill_method='pad' in DataFrame.pct_change is deprecated",
            category=FutureWarning,
        )
        stock = alpha_factory(wide)
    stock.vwap = wide["S_DQ_VWAP"]
    stock.returns = stock.close.pct_change(fill_method=None)
    output: list[pd.Series] = []
    reference_axes = wide["S_DQ_CLOSE"]
    with alpha101_rank_eligibility(source_module, rank_eligibility):
        for registry_name in registry_names:
            if not hasattr(stock, registry_name):
                raise ValueError(f"Alpha101 reference missing method: {registry_name}")
            values = getattr(stock, registry_name)()
            if not isinstance(values, pd.DataFrame):
                raise TypeError(f"{registry_name} returned {type(values).__name__}, expected DataFrame")
            if not values.index.equals(reference_axes.index) or not values.columns.equals(reference_axes.columns):
                raise ValueError(f"{registry_name} returned axes inconsistent with canonical inputs")
            name = f"kunquant_alpha101_{registry_name}_canonical_vwap_v2"
            output.append(values.stack(future_stack=True).rename(name))
    if not output:
        return frame[["datetime", "instrument"]].iloc[0:0].copy()
    combined = pd.concat(output, axis=1).reset_index()
    combined = combined.rename(columns={"level_0": "datetime", "level_1": "instrument"})
    for column in combined.columns.difference(["datetime", "instrument"]):
        combined[column] = pd.to_numeric(combined[column], errors="coerce").replace(
            [np.inf, -np.inf], np.nan
        )
    return combined.sort_values(["instrument", "datetime"]).reset_index(drop=True)
