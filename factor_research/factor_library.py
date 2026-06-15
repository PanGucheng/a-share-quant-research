import numpy as np
import pandas as pd


BASE_FIELDS = ["$open", "$high", "$low", "$close", "$volume", "$amount"]


def rolling_max_drawdown(values: pd.Series, window: int = 20) -> pd.Series:
    def max_drawdown(array: np.ndarray) -> float:
        peaks = np.maximum.accumulate(array)
        drawdowns = array / peaks - 1
        return -float(np.nanmin(drawdowns))

    return values.rolling(window, min_periods=window).apply(max_drawdown, raw=True)


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
    downside_return = daily_return.clip(upper=0)
    frame["downside_std_20"] = (
        downside_return.groupby(frame["instrument"]).rolling(20).std().reset_index(level=0, drop=True)
    )
    frame["max_drawdown_20"] = group["$close"].transform(lambda values: rolling_max_drawdown(values, window=20))
    frame["amplitude_20"] = ((high - low) / close).groupby(frame["instrument"]).rolling(20).mean().reset_index(
        level=0, drop=True
    )
    frame["amount_mean_20"] = amount.groupby(frame["instrument"]).rolling(20).mean().reset_index(level=0, drop=True)
    frame["amount_std_20"] = amount.groupby(frame["instrument"]).rolling(20).std().reset_index(level=0, drop=True)
    frame["amount_cv_20"] = frame["amount_std_20"] / frame["amount_mean_20"]

    volume_mean_5 = volume.groupby(frame["instrument"]).rolling(5).mean().reset_index(level=0, drop=True)
    volume_mean_20 = volume.groupby(frame["instrument"]).rolling(20).mean().reset_index(level=0, drop=True)
    frame["volume_ratio_5_20"] = volume_mean_5 / volume_mean_20

    frame["rev_20_exclude_5"] = -(group["$close"].shift(5) / group["$close"].shift(20) - 1)
    frame["corr_ret_volume_20"] = frame.groupby("instrument", group_keys=False)[["$close", "$volume"]].apply(
        lambda inst: inst["$close"].pct_change(fill_method=None).rolling(20).corr(inst["$volume"])
    )
    frame["corr_ret_amount_20"] = frame.groupby("instrument", group_keys=False)[["$close", "$amount"]].apply(
        lambda inst: inst["$close"].pct_change(fill_method=None).rolling(20).corr(inst["$amount"])
    )

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
    "rev_20_exclude_5",
    "std_20",
    "downside_std_20",
    "max_drawdown_20",
    "amplitude_20",
    "amount_mean_20",
    "amount_std_20",
    "amount_cv_20",
    "volume_ratio_5_20",
    "corr_ret_volume_20",
    "corr_ret_amount_20",
]

FACTOR_METADATA = {
    "ret_5": {"category": "momentum", "expected_direction": "watch"},
    "ret_10": {"category": "momentum", "expected_direction": "watch"},
    "ret_20": {"category": "momentum", "expected_direction": "watch"},
    "rev_5": {"category": "reversal", "expected_direction": "positive"},
    "rev_20_exclude_5": {"category": "reversal", "expected_direction": "positive"},
    "std_20": {"category": "risk", "expected_direction": "negative"},
    "downside_std_20": {"category": "risk", "expected_direction": "negative"},
    "max_drawdown_20": {"category": "risk", "expected_direction": "negative"},
    "amplitude_20": {"category": "risk", "expected_direction": "negative"},
    "amount_mean_20": {"category": "liquidity", "expected_direction": "watch"},
    "amount_std_20": {"category": "liquidity", "expected_direction": "watch"},
    "amount_cv_20": {"category": "liquidity", "expected_direction": "negative"},
    "volume_ratio_5_20": {"category": "liquidity", "expected_direction": "watch"},
    "corr_ret_volume_20": {"category": "price_volume", "expected_direction": "watch"},
    "corr_ret_amount_20": {"category": "price_volume", "expected_direction": "watch"},
}

LABEL_COLUMNS = ["label_1d_t1", "label_5d_t1", "label_10d_t1", "label_20d_t1"]
