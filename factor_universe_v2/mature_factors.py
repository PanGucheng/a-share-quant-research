from __future__ import annotations

from collections.abc import Iterable

import numpy as np
import pandas as pd


MARKET_FACTOR_NAMES = (
    "mature_momentum_12_1",
    "mature_reversal_1m",
    "mature_high_52w",
    "mature_overnight_return_20",
    "mature_intraday_return_20",
    "mature_max_daily_return_21",
    "mature_realized_volatility_60",
    "mature_downside_volatility_60",
    "mature_return_skewness_60",
    "mature_parkinson_volatility_20",
    "mature_max_drawdown_60",
    "mature_amihud_illiquidity_20",
    "mature_amount_momentum_20",
    "mature_vwap_deviation",
    "mature_vwap_deviation_20",
    "mature_market_beta_60",
    "mature_idiosyncratic_volatility_60",
)

DAILY_BASIC_FACTOR_NAMES = (
    "mature_log_total_market_cap",
    "mature_log_float_market_cap",
    "mature_float_market_cap_ratio",
    "mature_earnings_yield_ttm",
    "mature_book_to_price",
    "mature_sales_to_price_ttm",
    "mature_dividend_yield_ttm",
    "mature_turnover_rate_free_float",
    "mature_turnover_mean_20",
    "mature_turnover_volatility_20",
    "mature_abnormal_turnover_20",
    "mature_volume_ratio",
)

MONEYFLOW_FACTOR_NAMES = (
    "mature_overall_order_imbalance",
    "mature_small_order_imbalance",
    "mature_medium_order_imbalance",
    "mature_large_order_imbalance",
    "mature_extra_large_order_imbalance",
    "mature_institutional_order_imbalance",
    "mature_net_flow_to_traded_amount",
    "mature_net_flow_persistence_5",
    "mature_net_flow_persistence_20",
    "mature_institutional_flow_persistence_20",
)

FUNDAMENTAL_FACTOR_NAMES = (
    "mature_gross_profitability",
    "mature_operating_profitability",
    "mature_return_on_assets",
    "mature_book_leverage",
    "mature_current_ratio",
    "mature_cash_ratio",
    "mature_operating_cashflow_to_assets",
    "mature_cashflow_quality",
    "mature_accruals_to_assets",
    "mature_asset_growth_yoy",
    "mature_revenue_growth_yoy",
    "mature_net_income_growth_yoy",
    "mature_cashflow_to_sales",
    "mature_gross_margin",
    "mature_net_margin",
    "mature_book_to_market_pit",
    "mature_earnings_to_price_pit",
    "mature_sales_to_price_pit",
    "mature_cashflow_to_price_pit",
)

ALL_MATURE_FACTOR_NAMES = (
    MARKET_FACTOR_NAMES
    + DAILY_BASIC_FACTOR_NAMES
    + MONEYFLOW_FACTOR_NAMES
    + FUNDAMENTAL_FACTOR_NAMES
)


def _require(frame: pd.DataFrame, columns: Iterable[str], layer: str) -> None:
    missing = sorted(set(columns) - set(frame.columns))
    if missing:
        raise ValueError(f"{layer} frame missing columns: {missing}")


def _ratio(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    value = numerator.astype(float) / denominator.astype(float).where(denominator.ne(0))
    return value.replace([np.inf, -np.inf], np.nan)


def _ordered(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.Index]:
    _require(frame, {"instrument", "datetime"}, "factor")
    original = frame.index
    result = frame.copy()
    result["datetime"] = pd.to_datetime(result["datetime"], errors="raise")
    result["__factor_v2_order"] = np.arange(len(result))
    result = result.sort_values(["instrument", "datetime", "__factor_v2_order"])
    return result, original


def _restore(frame: pd.DataFrame, original: pd.Index) -> pd.DataFrame:
    result = frame.sort_values("__factor_v2_order").drop(columns="__factor_v2_order")
    result.index = original
    return result


def compute_market_factors(frame: pd.DataFrame) -> pd.DataFrame:
    """Compute mature price/liquidity/risk factors at the close of row ``t``.

    Values using row-t observations are first tradable at the next session. ``$market_return``
    must be a contemporaneous broad-market return and is never shifted backward.
    """
    required = {
        "instrument", "datetime", "$open", "$high", "$low", "$close", "$amount", "$vwap",
        "$market_return",
    }
    _require(frame, required, "market")
    result, original = _ordered(frame)
    grouped = result.groupby("instrument", sort=False, group_keys=False)
    ret = grouped["$close"].pct_change(fill_method=None)
    previous_close = grouped["$close"].shift(1)
    result["__ret"] = ret
    result["__overnight"] = _ratio(result["$open"], previous_close) - 1.0
    result["__intraday"] = _ratio(result["$close"], result["$open"]) - 1.0
    result["__range_sq"] = np.log(_ratio(result["$high"], result["$low"])) ** 2
    result["__amihud"] = _ratio(ret.abs(), result["$amount"])
    result["__vwap_dev"] = _ratio(result["$close"], result["$vwap"]) - 1.0
    grouped = result.groupby("instrument", sort=False, group_keys=False)

    result["mature_momentum_12_1"] = _ratio(grouped["$close"].shift(21), grouped["$close"].shift(252)) - 1.0
    result["mature_reversal_1m"] = -(_ratio(result["$close"], grouped["$close"].shift(21)) - 1.0)
    result["mature_high_52w"] = _ratio(
        result["$close"], grouped["$close"].transform(lambda x: x.rolling(252, min_periods=126).max())
    )
    result["mature_overnight_return_20"] = grouped["__overnight"].transform(
        lambda x: x.rolling(20, min_periods=10).mean()
    )
    result["mature_intraday_return_20"] = grouped["__intraday"].transform(
        lambda x: x.rolling(20, min_periods=10).mean()
    )
    result["mature_max_daily_return_21"] = grouped["__ret"].transform(
        lambda x: x.rolling(21, min_periods=11).max()
    )
    result["mature_realized_volatility_60"] = grouped["__ret"].transform(
        lambda x: x.rolling(60, min_periods=30).std(ddof=1)
    )
    result["mature_downside_volatility_60"] = grouped["__ret"].transform(
        lambda x: x.where(x.lt(0)).rolling(60, min_periods=15).std(ddof=1)
    )
    result["mature_return_skewness_60"] = grouped["__ret"].transform(
        lambda x: x.rolling(60, min_periods=30).skew()
    )
    result["mature_parkinson_volatility_20"] = np.sqrt(
        grouped["__range_sq"].transform(lambda x: x.rolling(20, min_periods=10).mean())
        / (4.0 * np.log(2.0))
    )

    def max_drawdown(series: pd.Series) -> pd.Series:
        return series.rolling(60, min_periods=30).apply(
            lambda x: float(np.min(x / np.maximum.accumulate(x) - 1.0)), raw=True
        )

    result["mature_max_drawdown_60"] = grouped["$close"].transform(max_drawdown)
    result["mature_amihud_illiquidity_20"] = grouped["__amihud"].transform(
        lambda x: x.rolling(20, min_periods=10).mean()
    )
    previous_amount_mean = grouped["$amount"].transform(
        lambda x: x.shift(1).rolling(20, min_periods=10).mean()
    )
    result["mature_amount_momentum_20"] = _ratio(result["$amount"], previous_amount_mean) - 1.0
    result["mature_vwap_deviation"] = result["__vwap_dev"]
    result["mature_vwap_deviation_20"] = grouped["__vwap_dev"].transform(
        lambda x: x.rolling(20, min_periods=10).mean()
    )

    beta = pd.Series(np.nan, index=result.index, dtype=float)
    idio = pd.Series(np.nan, index=result.index, dtype=float)
    for _, group in result.groupby("instrument", sort=False):
        market = group["$market_return"].astype(float)
        stock = group["__ret"].astype(float)
        rolling_var = market.rolling(60, min_periods=40).var(ddof=1)
        group_beta = stock.rolling(60, min_periods=40).cov(market) / rolling_var.where(rolling_var.ne(0))
        residual = stock - group_beta * market
        beta.loc[group.index] = group_beta
        idio.loc[group.index] = residual.rolling(60, min_periods=40).std(ddof=1)
    result["mature_market_beta_60"] = beta
    result["mature_idiosyncratic_volatility_60"] = idio
    result = result.drop(columns=["__ret", "__overnight", "__intraday", "__range_sq", "__amihud", "__vwap_dev"])
    return _restore(result.replace([np.inf, -np.inf], np.nan), original)


def compute_daily_basic_factors(frame: pd.DataFrame) -> pd.DataFrame:
    """Compute post-close Tushare ``daily_basic`` factors, usable from t+1."""
    required = {
        "instrument", "datetime", "total_mv", "circ_mv", "pe_ttm", "pb", "ps_ttm",
        "dv_ttm", "turnover_rate_f", "volume_ratio",
    }
    _require(frame, required, "daily_basic")
    result, original = _ordered(frame)
    positive_total = result["total_mv"].where(result["total_mv"].gt(0))
    positive_float = result["circ_mv"].where(result["circ_mv"].gt(0))
    result["mature_log_total_market_cap"] = np.log(positive_total)
    result["mature_log_float_market_cap"] = np.log(positive_float)
    result["mature_float_market_cap_ratio"] = _ratio(result["circ_mv"], result["total_mv"])
    result["mature_earnings_yield_ttm"] = _ratio(pd.Series(1.0, index=result.index), result["pe_ttm"].where(result["pe_ttm"].gt(0)))
    result["mature_book_to_price"] = _ratio(pd.Series(1.0, index=result.index), result["pb"].where(result["pb"].gt(0)))
    result["mature_sales_to_price_ttm"] = _ratio(pd.Series(1.0, index=result.index), result["ps_ttm"].where(result["ps_ttm"].gt(0)))
    result["mature_dividend_yield_ttm"] = result["dv_ttm"].astype(float) / 100.0
    result["mature_turnover_rate_free_float"] = result["turnover_rate_f"].astype(float) / 100.0
    grouped = result.groupby("instrument", sort=False, group_keys=False)
    result["mature_turnover_mean_20"] = grouped["mature_turnover_rate_free_float"].transform(
        lambda x: x.rolling(20, min_periods=10).mean()
    )
    result["mature_turnover_volatility_20"] = grouped["mature_turnover_rate_free_float"].transform(
        lambda x: x.rolling(20, min_periods=10).std(ddof=1)
    )
    previous_turnover = grouped["mature_turnover_rate_free_float"].transform(
        lambda x: x.shift(1).rolling(20, min_periods=10).mean()
    )
    result["mature_abnormal_turnover_20"] = _ratio(
        result["mature_turnover_rate_free_float"], previous_turnover
    ) - 1.0
    result["mature_volume_ratio"] = result["volume_ratio"].astype(float)
    return _restore(result.replace([np.inf, -np.inf], np.nan), original)


def compute_moneyflow_factors(frame: pd.DataFrame) -> pd.DataFrame:
    """Compute Tushare order-size imbalance factors after the trade-date close."""
    amount_columns = {
        f"{side}_{size}_amount" for side in ("buy", "sell") for size in ("sm", "md", "lg", "elg")
    }
    _require(frame, {"instrument", "datetime", "net_mf_amount", "traded_amount_cny", *amount_columns}, "moneyflow")
    result, original = _ordered(frame)

    def imbalance(sizes: tuple[str, ...]) -> pd.Series:
        buy = sum((result[f"buy_{size}_amount"].astype(float) for size in sizes), start=pd.Series(0.0, index=result.index))
        sell = sum((result[f"sell_{size}_amount"].astype(float) for size in sizes), start=pd.Series(0.0, index=result.index))
        return _ratio(buy - sell, buy + sell)

    result["mature_overall_order_imbalance"] = imbalance(("sm", "md", "lg", "elg"))
    result["mature_small_order_imbalance"] = imbalance(("sm",))
    result["mature_medium_order_imbalance"] = imbalance(("md",))
    result["mature_large_order_imbalance"] = imbalance(("lg",))
    result["mature_extra_large_order_imbalance"] = imbalance(("elg",))
    result["mature_institutional_order_imbalance"] = imbalance(("lg", "elg"))
    # Tushare moneyflow amounts are in CNY 10,000; the normalized traded amount is CNY.
    result["mature_net_flow_to_traded_amount"] = _ratio(
        result["net_mf_amount"].astype(float) * 10_000.0, result["traded_amount_cny"]
    )
    grouped = result.groupby("instrument", sort=False, group_keys=False)
    result["mature_net_flow_persistence_5"] = grouped["mature_net_flow_to_traded_amount"].transform(
        lambda x: x.rolling(5, min_periods=3).mean()
    )
    result["mature_net_flow_persistence_20"] = grouped["mature_net_flow_to_traded_amount"].transform(
        lambda x: x.rolling(20, min_periods=10).mean()
    )
    result["mature_institutional_flow_persistence_20"] = grouped[
        "mature_institutional_order_imbalance"
    ].transform(lambda x: x.rolling(20, min_periods=10).mean())
    return _restore(result.replace([np.inf, -np.inf], np.nan), original)


def compute_fundamental_factors(frame: pd.DataFrame) -> pd.DataFrame:
    """Compute statement factors from already PIT-materialized rows.

    The function fails closed if a row's selected statement was not public by its decision date.
    Monetary statement fields and ``total_mv_cny`` must all use CNY.
    """
    required = {
        "instrument", "datetime", "information_available_date", "revenue", "oper_cost",
        "operate_profit", "n_income_attr_p", "total_assets", "total_liab",
        "total_hldr_eqy_exc_min_int", "money_cap", "total_cur_assets", "total_cur_liab",
        "n_cashflow_act", "prior_total_assets", "prior_revenue", "prior_n_income_attr_p",
        "total_mv_cny",
    }
    _require(frame, required, "fundamental")
    result = frame.copy()
    decision = pd.to_datetime(result["datetime"], errors="raise").dt.normalize()
    available = pd.to_datetime(result["information_available_date"], errors="coerce").dt.normalize()
    invalid = available.isna() | available.gt(decision)
    if invalid.any():
        raise ValueError("fundamental frame contains unavailable or post-decision statement rows")
    assets = result["total_assets"].astype(float)
    revenue = result["revenue"].astype(float)
    income = result["n_income_attr_p"].astype(float)
    cashflow = result["n_cashflow_act"].astype(float)
    equity = result["total_hldr_eqy_exc_min_int"].astype(float)
    market_cap = result["total_mv_cny"].astype(float)
    result["mature_gross_profitability"] = _ratio(revenue - result["oper_cost"], assets)
    result["mature_operating_profitability"] = _ratio(result["operate_profit"], assets)
    result["mature_return_on_assets"] = _ratio(income, assets)
    result["mature_book_leverage"] = _ratio(result["total_liab"], assets)
    result["mature_current_ratio"] = _ratio(result["total_cur_assets"], result["total_cur_liab"])
    result["mature_cash_ratio"] = _ratio(result["money_cap"], result["total_cur_liab"])
    result["mature_operating_cashflow_to_assets"] = _ratio(cashflow, assets)
    result["mature_cashflow_quality"] = _ratio(cashflow, income.abs())
    result["mature_accruals_to_assets"] = _ratio(income - cashflow, assets)
    result["mature_asset_growth_yoy"] = _ratio(assets, result["prior_total_assets"]) - 1.0
    result["mature_revenue_growth_yoy"] = _ratio(revenue, result["prior_revenue"]) - 1.0
    result["mature_net_income_growth_yoy"] = _ratio(income, result["prior_n_income_attr_p"].abs()) - np.sign(result["prior_n_income_attr_p"].astype(float))
    result["mature_cashflow_to_sales"] = _ratio(cashflow, revenue)
    result["mature_gross_margin"] = _ratio(revenue - result["oper_cost"], revenue)
    result["mature_net_margin"] = _ratio(income, revenue)
    result["mature_book_to_market_pit"] = _ratio(equity, market_cap)
    result["mature_earnings_to_price_pit"] = _ratio(income, market_cap)
    result["mature_sales_to_price_pit"] = _ratio(revenue, market_cap)
    result["mature_cashflow_to_price_pit"] = _ratio(cashflow, market_cap)
    return result.replace([np.inf, -np.inf], np.nan)
