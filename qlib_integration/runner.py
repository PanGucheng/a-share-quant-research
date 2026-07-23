from __future__ import annotations

import pandas as pd

from .contracts import validate_market_frame, validate_signal_frame
from .exchange_adapter import PreparedQuoteExchange, to_qlib_quote
from .executor_adapter import AuditedSimulatorExecutor
from .result_normalizer import normalize_execution_results
from .signal_adapter import to_qlib_signal
from .strategy_adapter import EqualWeightTargetStrategy


def run_qlib_execution(signal: pd.DataFrame, market: pd.DataFrame, config: dict[str, object]) -> dict[str, pd.DataFrame]:
    from qlib.backtest import create_account_instance
    from qlib.backtest.backtest import backtest_loop
    from qlib.backtest.utils import CommonInfrastructure

    signals = validate_signal_frame(signal)
    markets = validate_market_frame(market)
    methods = signals["method"].unique()
    if len(methods) != 1:
        raise ValueError("one execution run requires exactly one signal method")

    calendar = pd.DatetimeIndex(sorted(markets["datetime"].unique()))
    if len(calendar) < 2:
        raise ValueError("execution requires at least two trading days")
    start_time = calendar[1]
    end_time = calendar[-1]
    codes = sorted(markets["instrument"].unique())
    quote = to_qlib_quote(markets, float(config["max_participation_rate"]))
    exchange = PreparedQuoteExchange(
        prepared_quote=quote,
        buy_commission_rate=float(config["buy_commission_rate"]),
        sell_commission_rate=float(config["sell_commission_rate"]),
        sell_tax_rate=float(config["sell_tax_rate"]),
        minimum_commission=float(config["minimum_commission"]),
        slippage_bps=float(config["slippage_bps"]),
        fee_schedule=config.get("fee_schedule"),
        freq="day",
        start_time=start_time,
        end_time=end_time,
        codes=codes,
        deal_price="$execution_price",
        limit_threshold=("limit_buy", "limit_sell"),
        volume_threshold=("current", "$participation_limit"),
        trade_unit=int(config["lot_size"]),
    )
    zero_benchmark = pd.Series(0.0, index=calendar[1:])
    account = create_account_instance(start_time, end_time, zero_benchmark, float(config["initial_cash"]))
    common = CommonInfrastructure(trade_account=account, trade_exchange=exchange)
    strategy = EqualWeightTargetStrategy(
        signal=to_qlib_signal(signals),
        top_k=int(config["top_k"]),
        risk_degree=float(config["risk_degree"]),
        common_infra=common,
    )
    executor = AuditedSimulatorExecutor(
        time_per_step="day",
        start_time=start_time,
        end_time=end_time,
        generate_portfolio_metrics=True,
        trade_type="serial",
        common_infra=common,
    )
    portfolio_metrics, _ = backtest_loop(start_time, end_time, strategy, executor)
    return normalize_execution_results(
        portfolio_metrics=portfolio_metrics,
        events=executor.execution_events,
        account=account,
        calendar=calendar[1:],
        market=markets,
    )
