from __future__ import annotations

import pandas as pd

from .contracts import validate_market_frame, validate_signal_frame
from .exchange_adapter import PreparedQuoteExchange, to_qlib_quote
from .executor_adapter import AuditedSimulatorExecutor
from .result_normalizer import normalize_execution_results
from .signal_adapter import to_qlib_signal
from .strategy_adapter import EqualWeightTargetStrategy


class UnpriceableHeldPositionError(RuntimeError):
    """Qlib cannot value a held position under the frozen stale-price policy."""

    def __init__(self, *, candidate_rows: pd.DataFrame, cause: Exception) -> None:
        self.candidate_rows = candidate_rows.copy()
        first_date = (
            pd.Timestamp(candidate_rows["datetime"].min()).date().isoformat()
            if not candidate_rows.empty
            else "unknown"
        )
        instruments = (
            ",".join(
                sorted(candidate_rows["instrument"].astype(str).unique())[:10]
            )
            if not candidate_rows.empty
            else "unknown"
        )
        super().__init__(
            "blocked_unpriceable_held_position:"
            f"first_candidate_date={first_date};"
            f"candidate_instruments={instruments};"
            f"cause={type(cause).__name__}:{cause}"
        )


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
        dynamic_lot_rules=bool(config.get("dynamic_lot_rules", False)),
        freq="day",
        start_time=start_time,
        end_time=end_time,
        codes=codes,
        deal_price="$execution_price",
        limit_threshold=("limit_buy", "limit_sell"),
        volume_threshold=("current", "$participation_limit"),
        trade_unit=1 if bool(config.get("dynamic_lot_rules", False)) else int(config["lot_size"]),
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
    try:
        portfolio_metrics, _ = backtest_loop(
            start_time, end_time, strategy, executor
        )
    except TypeError as exc:
        # Qlib multiplies the current amount by the close when valuing an
        # existing holding. A deliberately unavailable close (after the
        # frozen stale-valuation horizon) otherwise surfaces as an opaque
        # ``float * None`` TypeError. Preserve the fail-closed policy and
        # expose a classified capability block instead of silently extending
        # the last price or anticipating a future suspension.
        stale_mask = markets.get(
            "valuation_stale_blocked",
            pd.Series(False, index=markets.index),
        ).fillna(False).astype(bool)
        stale_unpriceable = markets.loc[
            stale_mask
            & pd.to_numeric(
                markets["close"], errors="coerce"
            ).isna(),
            ["datetime", "instrument"],
        ].drop_duplicates()
        exact_requests = pd.DataFrame(
            exchange.unpriceable_price_requests
        )
        if exact_requests.empty:
            stale_candidates = stale_unpriceable
        else:
            exact_keys = exact_requests[
                ["datetime", "instrument"]
            ].tail(1)
            stale_candidates = exact_keys.merge(
                stale_unpriceable,
                on=["datetime", "instrument"],
                how="inner",
            )
        is_none_price_failure = (
            "NoneType" in str(exc)
            and "unsupported operand type" in str(exc)
        )
        if is_none_price_failure and not stale_candidates.empty:
            raise UnpriceableHeldPositionError(
                candidate_rows=stale_candidates,
                cause=exc,
            ) from exc
        raise
    return normalize_execution_results(
        portfolio_metrics=portfolio_metrics,
        events=executor.execution_events,
        account=account,
        calendar=calendar[1:],
        market=markets,
    )
