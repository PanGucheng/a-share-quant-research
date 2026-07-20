from __future__ import annotations

import pandas as pd
import pytest

from qlib_integration.contracts import normalize_instrument, validate_market_frame, validate_signal_frame
from qlib_integration.exchange_adapter import TPlusOneLedger, apply_slippage, component_costs, to_qlib_quote
from qlib_integration.reconciliation import semantic_difference, unknown_difference_count
from qlib_integration.signal_adapter import to_qlib_signal


def signal_frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "datetime": "2026-01-05",
                "instrument": "600000.SH",
                "score": 1.0,
                "method": "fixed",
                "signal_artifact_id": "signal:1",
                "profile_name": "synthetic",
                "profile_type": "smoke",
                "research_run_family_id": "qlib_exchange_v1",
            }
        ]
    )


def market_frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "datetime": "2026-01-06",
                "instrument": "SH600000",
                "open": 10.0,
                "close": 10.2,
                "volume": 100_000,
                "amount": 1_000_000,
                "can_buy": True,
                "can_sell": True,
                "limit_up": False,
                "limit_down": False,
                "suspended": False,
                "factor": 1.0,
                "change": 0.02,
                "execution_price": 10.0,
            }
        ]
    )


def test_instrument_normalization_is_explicit() -> None:
    assert normalize_instrument("600000.SH") == "SH600000"
    assert normalize_instrument("sz.000001") == "SZ000001"
    with pytest.raises(ValueError, match="ambiguous"):
        normalize_instrument("600000")


def test_signal_adapter_builds_qlib_multiindex() -> None:
    validated = validate_signal_frame(signal_frame())
    signal = to_qlib_signal(validated)
    assert signal.index.names == ["datetime", "instrument"]
    assert signal.index[0][1] == "SH600000"


def test_signal_rejects_profile_mix_and_duplicates() -> None:
    duplicated = pd.concat([signal_frame(), signal_frame()], ignore_index=True)
    with pytest.raises(ValueError, match="duplicate"):
        validate_signal_frame(duplicated)
    mixed = pd.concat([signal_frame(), signal_frame().assign(profile_name="other")], ignore_index=True)
    mixed.loc[1, "instrument"] = "000001.SZ"
    with pytest.raises(ValueError, match="mixes profile_name"):
        validate_signal_frame(mixed)


def test_market_contract_enforces_directional_limits() -> None:
    assert len(validate_market_frame(market_frame())) == 1
    invalid = market_frame().assign(limit_up=True, can_buy=True)
    with pytest.raises(ValueError, match="limit-up"):
        validate_market_frame(invalid)


def test_qlib_quote_converts_raw_units_at_adapter_boundary() -> None:
    quote = to_qlib_quote(market_frame().assign(factor=2.0), 0.05)
    row = quote.iloc[0]
    assert row["$open"] == 20.0
    assert row["$volume"] == 50_000
    assert row["$participation_limit"] == 2_500


def test_component_costs_do_not_apply_minimum_to_stamp_tax() -> None:
    fill_price = apply_slippage(10.0, "sell", 10.0)
    costs = component_costs(
        side="sell",
        gross_value=999.0,
        executed_shares=100,
        base_price=10.0,
        fill_price=fill_price,
        commission_rate=0.0003,
        sell_tax_rate=0.001,
        minimum_commission=5.0,
    )
    assert costs.commission == 5.0
    assert costs.stamp_tax == pytest.approx(0.999)
    assert costs.cash_fee == pytest.approx(5.999)
    assert costs.slippage_cost == pytest.approx(1.0)


def test_t_plus_one_uses_opening_sellable_shares() -> None:
    ledger = TPlusOneLedger()
    ledger.start_day(pd.Timestamp("2026-01-06"), {"SH600000": 100})
    ledger.record_fill("SH600000", "buy", 200)
    allowed, rejected = ledger.clip_sell("SH600000", 300)
    assert allowed == 100
    assert rejected == 200
    ledger.record_fill("SH600000", "sell", allowed)
    assert ledger.sellable("SH600000") == 0
    ledger.start_day(pd.Timestamp("2026-01-07"), {"SH600000": 200})
    assert ledger.sellable("SH600000") == 200


def test_unknown_semantic_differences_are_counted() -> None:
    row = semantic_difference(
        scenario_id="s1",
        category="unknown",
        field="cash",
        reference_value=1,
        qlib_value=2,
        expected=False,
        reason="unclassified",
    )
    assert unknown_difference_count(pd.DataFrame([row])) == 1
