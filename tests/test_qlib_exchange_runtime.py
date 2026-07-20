from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest


qlib = pytest.importorskip("qlib")

from qlib.config import C, REG_CN  # noqa: E402

from qlib_integration.runner import run_qlib_execution  # noqa: E402


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
