from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from qlib_integration.market_semantics import (
    convert_community_market_units,
    infer_board,
    load_yaml,
    resolve_fee,
    resolve_lot_rule,
    resolve_price_limit_rule,
    stale_valuation,
    validate_field_timing,
)


ROOT = Path(__file__).resolve().parents[1]


def test_fee_schedule_changes_stamp_tax_on_2023_08_28() -> None:
    schedule = load_yaml(ROOT / "configs/a_share_fee_schedule_v1.yaml")
    assert resolve_fee(schedule, "2023-08-27").sell_stamp_tax_rate == pytest.approx(0.001)
    assert resolve_fee(schedule, "2023-08-28").sell_stamp_tax_rate == pytest.approx(0.0005)


def test_fee_schedule_is_fail_closed_outside_coverage() -> None:
    schedule = load_yaml(ROOT / "configs/a_share_fee_schedule_v1.yaml")
    with pytest.raises(ValueError, match="exactly once"):
        resolve_fee(schedule, "2022-04-28")


def test_field_timing_detects_future_market_field() -> None:
    frame = pd.DataFrame([{
        "field_name": "close",
        "observation_timestamp": "2025-01-02 15:00",
        "available_at": "2025-01-02 15:05",
        "execution_timestamp": "2025-01-02 09:30",
        "source_artifact_id": "market:test",
    }])
    assert bool(validate_field_timing(frame).iloc[0]["future_field"])


def test_board_price_limit_and_lot_rules_resolve() -> None:
    rules = load_yaml(ROOT / "configs/a_share_trading_rules_v1.yaml")
    assert infer_board("SH688001") == "star"
    assert infer_board("SZ302132") == "chinext"
    assert infer_board("SZ200002") == "unknown"
    assert infer_board("SH510300") == "unknown"
    limit = resolve_price_limit_rule(
        rules, board="star", st_flag=False, ipo_age=6, trading_date="2025-01-02"
    )
    assert limit["limit_ratio"] == pytest.approx(0.20)
    assert resolve_price_limit_rule(
        rules, board="star", st_flag=False, ipo_age=3, trading_date="2025-01-02"
    )["limit_ratio"] is None
    lot = resolve_lot_rule(rules, board="star", side="buy")
    assert lot["minimum_shares"] == 200 and lot["increment_shares"] == 1


def test_price_limit_resolution_rejects_unknown_state() -> None:
    rules = load_yaml(ROOT / "configs/a_share_trading_rules_v1.yaml")
    with pytest.raises(ValueError, match="incomplete"):
        resolve_price_limit_rule(
            rules, board="main", st_flag=None, ipo_age=100, trading_date="2025-01-02"
        )


def test_community_market_units_are_explicit_and_fail_closed() -> None:
    volume, amount = convert_community_market_units(
        5_641_746.0,
        0.3225237,
        2_102_923.07811,
        volume_lot_to_shares_multiplier=100,
        amount_to_cny_multiplier=1000,
    )
    assert volume == pytest.approx(181_959_699, rel=1e-6)
    assert amount == pytest.approx(2_102_923_078.11)
    with pytest.raises(ValueError, match="100 shares"):
        convert_community_market_units(
            1.0,
            1.0,
            1.0,
            volume_lot_to_shares_multiplier=1,
            amount_to_cny_multiplier=1000,
        )


def test_stale_valuation_never_backfills_and_expires() -> None:
    close = pd.Series([np.nan, 10.0, np.nan, np.nan, 11.0])
    result = stale_valuation(close, maximum_stale_trading_days=1)
    assert np.isnan(result.iloc[0]["valuation_price"])
    assert result.iloc[2]["valuation_price"] == pytest.approx(10.0)
    assert np.isnan(result.iloc[3]["valuation_price"])
    assert result.iloc[4]["valuation_price_age_trading_days"] == 0


def test_stale_valuation_preserves_multiindex_ages() -> None:
    index = pd.MultiIndex.from_product([["SH600000"], pd.date_range("2025-01-01", periods=2)])
    result = stale_valuation(pd.Series([10.0, np.nan], index=index), maximum_stale_trading_days=2)
    assert result["valuation_price_age_trading_days"].tolist() == [0, 1]
