import numpy as np
import pandas as pd


BASE_FIELDS = ["$open", "$high", "$low", "$close", "$volume", "$amount"]


def add_basic_factors(frame: pd.DataFrame) -> pd.DataFrame:
    frame = frame.sort_values(["instrument", "datetime"]).copy()
    group = frame.groupby("instrument", group_keys=False)

    close = frame["$close"]
    volume = frame["$volume"]
    amount = frame["$amount"]
    high = frame["$high"]
    low = frame["$low"]

    frame["ret_5"] = group["$close"].pct_change(5, fill_method=None)
    frame["ret_10"] = group["$close"].pct_change(10, fill_method=None)
    frame["ret_20"] = group["$close"].pct_change(20, fill_method=None)
    frame["rev_5"] = -frame["ret_5"]

    daily_return = group["$close"].pct_change(fill_method=None)
    frame["std_20"] = daily_return.groupby(frame["instrument"]).rolling(20).std().reset_index(level=0, drop=True)
    frame["amplitude_20"] = ((high - low) / close).groupby(frame["instrument"]).rolling(20).mean().reset_index(
        level=0, drop=True
    )
    frame["amount_mean_20"] = amount.groupby(frame["instrument"]).rolling(20).mean().reset_index(level=0, drop=True)
    frame["amount_std_20"] = amount.groupby(frame["instrument"]).rolling(20).std().reset_index(level=0, drop=True)

    volume_mean_5 = volume.groupby(frame["instrument"]).rolling(5).mean().reset_index(level=0, drop=True)
    volume_mean_20 = volume.groupby(frame["instrument"]).rolling(20).mean().reset_index(level=0, drop=True)
    frame["volume_ratio_5_20"] = volume_mean_5 / volume_mean_20

    frame["corr_ret_volume_20"] = np.nan
    for _, index in frame.groupby("instrument", sort=False).groups.items():
        inst_return = daily_return.loc[index]
        inst_volume = volume.loc[index]
        frame.loc[index, "corr_ret_volume_20"] = inst_return.rolling(20).corr(inst_volume).to_numpy()

    # A-share T+1 style labels: buy on next close, then hold for N trading days.
    next_close = group["$close"].shift(-1)
    next_next_close = group["$close"].shift(-2)
    next_6_close = group["$close"].shift(-6)
    next_11_close = group["$close"].shift(-11)
    next_21_close = group["$close"].shift(-21)
    frame["label_1d_t1"] = next_next_close / next_close - 1
    frame["label_5d_t1"] = next_6_close / next_close - 1
    frame["label_10d_t1"] = next_11_close / next_close - 1
    frame["label_20d_t1"] = next_21_close / next_close - 1
    return frame


FACTOR_COLUMNS = [
    "ret_5",
    "ret_10",
    "ret_20",
    "rev_5",
    "std_20",
    "amplitude_20",
    "amount_mean_20",
    "amount_std_20",
    "volume_ratio_5_20",
    "corr_ret_volume_20",
]

FACTOR_METADATA = {
    "ret_5": {"category": "momentum", "expected_direction": "watch"},
    "ret_10": {"category": "momentum", "expected_direction": "watch"},
    "ret_20": {"category": "momentum", "expected_direction": "watch"},
    "rev_5": {"category": "reversal", "expected_direction": "positive"},
    "std_20": {"category": "risk", "expected_direction": "negative"},
    "amplitude_20": {"category": "risk", "expected_direction": "negative"},
    "amount_mean_20": {"category": "liquidity", "expected_direction": "watch"},
    "amount_std_20": {"category": "liquidity", "expected_direction": "watch"},
    "volume_ratio_5_20": {"category": "liquidity", "expected_direction": "watch"},
    "corr_ret_volume_20": {"category": "price_volume", "expected_direction": "watch"},
}

LABEL_COLUMNS = ["label_1d_t1", "label_5d_t1", "label_10d_t1", "label_20d_t1"]
