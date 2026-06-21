from __future__ import annotations

import pandas as pd


def load_benchmark_returns(
    provider_uri: str,
    benchmarks: dict[str, str],
    start: str,
    end: str,
) -> pd.DataFrame:
    """Load benchmark close data and compute T+1 forward returns."""

    import qlib
    from qlib.config import C
    from qlib.data import D

    qlib.init(provider_uri=provider_uri, region="cn")
    C.kernels = 1
    C.joblib_backend = "sequential"
    load_start = (pd.Timestamp(start) - pd.Timedelta(days=10)).strftime("%Y-%m-%d")
    load_end = (pd.Timestamp(end) + pd.Timedelta(days=45)).strftime("%Y-%m-%d")
    frame = D.features(list(benchmarks.values()), ["$close"], start_time=load_start, end_time=load_end).reset_index()
    reverse = {instrument.upper(): name for name, instrument in benchmarks.items()}
    frame["instrument"] = frame["instrument"].astype(str).str.upper()
    frame["benchmark"] = frame["instrument"].map(reverse)
    frame = frame.sort_values(["instrument", "datetime"]).copy()
    group = frame.groupby("instrument", group_keys=False)
    frame["daily_return"] = group["$close"].pct_change(fill_method=None)
    next_close = group["$close"].shift(-1)
    frame["forward_10d_t1"] = group["$close"].shift(-11) / next_close - 1
    frame["forward_20d_t1"] = group["$close"].shift(-21) / next_close - 1
    frame = frame[frame["datetime"].between(pd.Timestamp(start), pd.Timestamp(end))]
    return frame[
        ["datetime", "benchmark", "instrument", "$close", "daily_return", "forward_10d_t1", "forward_20d_t1"]
    ].rename(columns={"$close": "close"}).reset_index(drop=True)

