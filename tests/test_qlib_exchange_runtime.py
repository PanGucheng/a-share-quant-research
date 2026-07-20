from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest


qlib = pytest.importorskip("qlib")

from qlib.config import C, REG_CN  # noqa: E402
from qlib.backtest import create_account_instance  # noqa: E402
from qlib.backtest.decision import Order  # noqa: E402

from qlib_integration.runner import run_qlib_execution  # noqa: E402
from qlib_integration.exchange_adapter import PreparedQuoteExchange, to_qlib_quote  # noqa: E402
from qlib_integration.reference_engine import run_reference_target_execution  # noqa: E402


PROVIDER = Path("E:/qlib_prj/qlib_data/cn_data_community_20260609_derived")


def _frames() -> tuple[pd.DataFrame, pd.DataFrame]:
    dates = pd.bdate_range("2026-06-01", periods=6)
    instruments = ["SH600000", "SZ000001", "SH600519"]
    market_rows = []
    signal_rows = []
    for day_index, date in enumerate(dates):
        for instrument_index, instrument in enumerate(instruments):
            price = 10.0 + instrument_index
            market_rows.append(
                {
                    "datetime": date,
                    "instrument": instrument,
                    "open": price,
                    "close": price,
                    "volume": 1_000_000,
                    "amount": price * 1_000_000,
                    "can_buy": True,
                    "can_sell": True,
                    "limit_up": False,
                    "limit_down": False,
                    "suspended": False,
                    "factor": 1.0,
                    "change": 0.0,
                    "execution_price": price,
                }
            )
            if day_index < len(dates) - 1:
                signal_rows.append(
                    {
                        "datetime": date,
                        "instrument": instrument,
                        "score": float(3 - instrument_index),
                        "method": "synthetic_fixed",
                        "signal_artifact_id": "signal:synthetic",
                        "profile_name": "synthetic",
                        "profile_type": "smoke",
                        "research_run_family_id": "qlib_exchange_v1",
                    }
                )
    return pd.DataFrame(signal_rows), pd.DataFrame(market_rows)


@pytest.mark.skipif(not PROVIDER.exists(), reason="local Qlib provider not available")
def test_synthetic_score_to_account_chain() -> None:
    qlib.init(provider_uri=str(PROVIDER), region=REG_CN)
    C.kernels = 1
    C.joblib_backend = "sequential"
    signal, market = _frames()
    result = run_qlib_execution(
        signal,
        market,
        {
            "initial_cash": 1_000_000,
            "top_k": 2,
            "risk_degree": 0.95,
            "lot_size": 100,
            "buy_commission_rate": 0.0,
            "sell_commission_rate": 0.0,
            "sell_tax_rate": 0.0,
            "minimum_commission": 0.0,
            "slippage_bps": 0.0,
            "max_participation_rate": 1.0,
        },
    )
    assert len(result["daily_accounting"]) == 5
    assert result["daily_accounting"]["calendar_complete"].all()
    assert not result["fills"].empty
    assert (result["fills"]["executed_shares"] % 100 == 0).all()
    assert (result["daily_accounting"]["cash"] >= -1e-8).all()
    assert result["daily_accounting"]["accounting_error"].abs().max() < 1e-8
    reference = run_reference_target_execution(
        signal,
        market,
        {
            "initial_cash": 1_000_000,
            "top_k": 2,
            "risk_degree": 0.95,
            "lot_size": 100,
            "buy_commission_rate": 0.0,
            "sell_commission_rate": 0.0,
            "sell_tax_rate": 0.0,
            "minimum_commission": 0.0,
            "slippage_bps": 0.0,
            "max_participation_rate": 1.0,
        },
    )
    pd.testing.assert_frame_equal(
        result["orders"][["datetime", "instrument", "side", "requested_shares", "executed_shares"]]
        .sort_values(["datetime", "instrument", "side"])
        .reset_index(drop=True),
        reference["orders"][["datetime", "instrument", "side", "requested_shares", "executed_shares"]]
        .sort_values(["datetime", "instrument", "side"])
        .reset_index(drop=True),
        check_dtype=False,
    )
    pd.testing.assert_frame_equal(
        result["daily_accounting"][["datetime", "cash", "nav", "stock_value"]].reset_index(drop=True),
        reference["daily_accounting"][["datetime", "cash", "nav", "stock_value"]].reset_index(drop=True),
        check_dtype=False,
        atol=1e-8,
        rtol=1e-10,
    )


@pytest.mark.skipif(not PROVIDER.exists(), reason="local Qlib provider not available")
def test_strict_t_plus_one_blocks_same_day_sale() -> None:
    qlib.init(provider_uri=str(PROVIDER), region=REG_CN)
    C.kernels = 1
    C.joblib_backend = "sequential"
    _, market = _frames()
    one_day = market.loc[market["datetime"] == market["datetime"].min()].copy()
    exchange = PreparedQuoteExchange(
        prepared_quote=to_qlib_quote(one_day, 1.0),
        buy_commission_rate=0.0,
        sell_commission_rate=0.0,
        sell_tax_rate=0.0,
        minimum_commission=0.0,
        slippage_bps=0.0,
        freq="day",
        start_time=one_day["datetime"].min(),
        end_time=one_day["datetime"].min(),
        codes=sorted(one_day["instrument"].unique()),
        deal_price="$execution_price",
        limit_threshold=("limit_buy", "limit_sell"),
        volume_threshold=("current", "$participation_limit"),
        trade_unit=100,
    )
    date = pd.Timestamp(one_day["datetime"].min())
    account = create_account_instance(date, date, None, 100_000.0)
    dealt = {}
    buy = Order("SH600000", 200, Order.BUY, date, date)
    exchange.deal_order(buy, trade_account=account, dealt_order_amount=dealt)
    sell = Order("SH600000", 200, Order.SELL, date, date)
    exchange.deal_order(sell, trade_account=account, dealt_order_amount=dealt)
    assert buy.deal_amount == 200
    assert sell.deal_amount == 0
    assert exchange.audit_events[-1]["reason"] == "t_plus_one"


@pytest.mark.skipif(not PROVIDER.exists(), reason="local Qlib provider not available")
def test_volume_limit_and_component_costs_are_audited() -> None:
    qlib.init(provider_uri=str(PROVIDER), region=REG_CN)
    C.kernels = 1
    C.joblib_backend = "sequential"
    _, market = _frames()
    one_day = market.loc[market["datetime"] == market["datetime"].min()].copy()
    one_day.loc[one_day["instrument"] == "SH600000", "volume"] = 100
    exchange = PreparedQuoteExchange(
        prepared_quote=to_qlib_quote(one_day, 0.5),
        buy_commission_rate=0.0003,
        sell_commission_rate=0.0003,
        sell_tax_rate=0.001,
        minimum_commission=5.0,
        slippage_bps=10.0,
        freq="day",
        start_time=one_day["datetime"].min(),
        end_time=one_day["datetime"].min(),
        codes=sorted(one_day["instrument"].unique()),
        deal_price="$execution_price",
        limit_threshold=("limit_buy", "limit_sell"),
        volume_threshold=("current", "$participation_limit"),
        trade_unit=None,
    )
    date = pd.Timestamp(one_day["datetime"].min())
    account = create_account_instance(date, date, None, 100_000.0)
    order = Order("SH600000", 100, Order.BUY, date, date)
    exchange.deal_order(order, trade_account=account, dealt_order_amount={})
    event = exchange.audit_events[-1]
    assert event["executed_shares"] == 50
    assert event["status"] == "partial"
    assert event["commission"] == 5.0
    assert event["stamp_tax"] == 0.0
    assert event["slippage_cost"] == pytest.approx(0.5)
