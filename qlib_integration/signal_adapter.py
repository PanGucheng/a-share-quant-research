from __future__ import annotations

import pandas as pd

from .contracts import validate_signal_frame


def to_qlib_signal(frame: pd.DataFrame, method: str | None = None) -> pd.Series:
    validated = validate_signal_frame(frame)
    if method is not None:
        validated = validated.loc[validated["method"] == method]
    methods = validated["method"].unique()
    if len(methods) != 1:
        raise ValueError(f"Qlib signal adapter requires exactly one method, got {methods.tolist()}")
    signal = validated.set_index(["datetime", "instrument"])["score"].sort_index()
    signal.name = "score"
    return signal
