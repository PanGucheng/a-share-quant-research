from __future__ import annotations

from pathlib import Path

import pandas as pd


FIELDS = [
    "$open",
    "$high",
    "$low",
    "$close",
    "$volume",
    "$amount",
    "$factor",
    "$vwap",
    "$change",
    "$adjclose",
]


def collect(
    instruments: list[str], start_date: str, end_date: str, provider_uri: Path
) -> pd.DataFrame:
    import qlib
    from qlib.config import C, REG_CN
    from qlib.data import D

    qlib.init(provider_uri=str(provider_uri), region=REG_CN)
    C.kernels = 1
    C.joblib_backend = "sequential"
    frame = D.features(
        instruments, FIELDS, start_time=start_date, end_time=end_date, freq="day"
    ).reset_index()
    frame["datetime"] = pd.to_datetime(frame["datetime"]).dt.normalize()
    return frame.rename(columns={"datetime": "date"})
