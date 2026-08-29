from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import yaml

from factor_universe_v2.alpha101_canonical import compute_canonical_alpha101_features
from factor_universe_v2.inventory import (
    build_frozen_v2_catalog,
    build_historical_missing_audit,
    build_local_candidate_catalog,
)
from factor_universe_v2.local_recovery import add_local_recovered_factors
from factor_universe_v2.mature_factors import (
    ALL_MATURE_FACTOR_NAMES,
    compute_daily_basic_factors,
    compute_fundamental_factors,
    compute_market_factors,
    compute_moneyflow_factors,
)
from factor_universe_v2.mature_inventory import build_external_research_inventory
from factor_universe_v2.pit import asof_pit_records, prepare_pit_records
from factor_universe_v2.tushare_data import TushareSegmentStore, probe_tushare


ROOT = Path(__file__).resolve().parents[1]


def config() -> dict:
    return yaml.safe_load((ROOT / "configs/factor_universe_v2_pre_network.yaml").read_text(encoding="utf-8"))


def test_pre_network_catalog_preserves_v1_and_has_expected_lineage() -> None:
    frame = build_local_candidate_catalog(ROOT, config())
    assert len(frame) == 716
    assert frame["name"].is_unique
    assert frame["lineage_status"].value_counts().to_dict() == {
        "legacy_v1": 669,
        "canonicalized": 28,
        "recovered": 19,
    }
    assert set(frame.loc[frame["lineage_status"].eq("canonicalized"), "required_fields"].str.contains("$vwap", regex=False)) == {True}


def test_frozen_v2_catalog_has_complete_unique_lineage_and_evidence() -> None:
    frame = build_frozen_v2_catalog(ROOT, config())
    assert len(frame) == 774
    assert frame["name"].is_unique
    assert frame["lineage_status"].value_counts().to_dict() == {
        "legacy_v1": 669,
        "new": 58,
        "canonicalized": 28,
        "recovered": 19,
    }
    new = frame.loc[frame["lineage_status"].eq("new")]
    assert set(new["name"]) == set(ALL_MATURE_FACTOR_NAMES)
    assert new["source_citations"].str.startswith("http").all()
    assert new["required_fields"].ne("").all()
    assert new["candidate_status"].eq("frozen_authoritative_v2").all()


def test_external_research_inventory_separates_admitted_deferred_and_rejected() -> None:
    frame = build_external_research_inventory()
    assert frame.loc[frame["candidate_decision"].eq("admit"), "factor_name"].nunique() == 58
    assert {"admit", "defer", "reject"} == set(frame["candidate_decision"])
    pending_industry = frame.loc[frame["factor_name"].eq("industry_relative_signals")].iloc[0]
    assert pending_industry["implementation_status"] == "research_pending"
    assert "vintage" in pending_industry["decision_reason"]


def test_historical_audit_separates_recoverable_from_correctness_rejections() -> None:
    frame = build_historical_missing_audit(ROOT, config())
    alpha360 = frame.loc[frame["factor_name"].eq("alpha360_CLOSE0")].iloc[0]
    assert not bool(alpha360["recoverable_now"])
    assert alpha360["recommended_action"] == "reject_formula_equivalent_constant"
    rank5 = frame.loc[frame["factor_name"].eq("alpha158_RANK5")].iloc[0]
    assert bool(rank5["recoverable_now"])
    assert rank5["historical_status"] == "evaluation_holdout"
    vpt = frame.loc[frame["factor_name"].eq("ta_volume_vpt")].iloc[0]
    assert vpt["recommended_action"] == "add_canonical_v2_version"


def test_local_ta_recovery_is_instrument_local_and_does_not_fill_missing_prices() -> None:
    frame = pd.DataFrame(
        {
            "datetime": pd.to_datetime(["2025-01-01", "2025-01-02", "2025-01-03"] * 2),
            "instrument": ["A"] * 3 + ["B"] * 3,
            "$close": [10.0, 11.0, 12.0, 20.0, float("nan"), 22.0],
            "$volume": [100.0, 90.0, 80.0, 200.0, 190.0, 180.0],
        }
    )
    result = add_local_recovered_factors(frame)
    a = result.loc[result["instrument"].eq("A")].reset_index(drop=True)
    assert a.loc[1, "ta_volume_vpt_canonical_v2"] == pytest.approx(9.0)
    assert a.loc[1, "ta_volume_nvi_canonical_v2"] == pytest.approx(1100.0)
    b = result.loc[result["instrument"].eq("B")].reset_index(drop=True)
    assert pd.isna(b.loc[1, "ta_volume_vpt_canonical_v2"])
    assert pd.isna(b.loc[2, "ta_volume_nvi_canonical_v2"])


def test_canonical_alpha101_overrides_amount_volume_proxy_with_direct_vwap() -> None:
    dates = pd.to_datetime(["2025-01-01", "2025-01-02"])
    frame = pd.DataFrame(
        {
            "datetime": dates,
            "instrument": ["A", "A"],
            "$open": [10.0, 11.0],
            "$high": [11.0, 12.0],
            "$low": [9.0, 10.0],
            "$close": [10.0, 11.0],
            "$volume": [100.0, 100.0],
            "$amount": [1000.0, 1100.0],
            "$vwap": [10.2, 11.3],
        }
    )

    class FakeAlphas:
        def __init__(self, wide: dict[str, pd.DataFrame]):
            self.close = wide["S_DQ_CLOSE"]
            self.vwap = wide["S_DQ_AMOUNT"] / wide["S_DQ_VOLUME"]

        def alpha005(self) -> pd.DataFrame:
            return self.vwap

    result = compute_canonical_alpha101_features(
        frame,
        registry_names=["alpha005"],
        source_local_path=Path("unused"),
        alpha_factory=FakeAlphas,
    )
    assert result["kunquant_alpha101_alpha005_canonical_vwap_v2"].tolist() == [10.2, 11.3]


def test_pit_records_block_preannouncement_and_select_latest_revision() -> None:
    raw = pd.DataFrame(
        {
            "ts_code": ["600000.SH", "600000.SH"],
            "end_date": ["20250331", "20250331"],
            "ann_date": ["20250420", "20250425"],
            "f_ann_date": ["20250420", "20250425"],
            "report_type": ["1", "1"],
            "value": [10.0, 12.0],
        }
    )
    prepared = prepare_pit_records(raw, dataset="income")
    assert asof_pit_records(prepared, as_of_date="2025-04-19").empty
    first = asof_pit_records(prepared, as_of_date="2025-04-22")
    assert first["value"].tolist() == [10.0]
    revised = asof_pit_records(prepared, as_of_date="2025-04-26")
    assert revised["value"].tolist() == [12.0]
    assert revised["revision_sequence"].tolist() == [2]


def test_pit_never_falls_back_to_report_period() -> None:
    raw = pd.DataFrame({"ts_code": ["600000.SH"], "end_date": ["20250331"], "ann_date": [None]})
    prepared = prepare_pit_records(raw, dataset="fina_indicator")
    assert prepared.loc[0, "pit_status"] == "research_pending"
    assert asof_pit_records(prepared, as_of_date="2025-12-31").empty


def test_segment_store_is_restartable_and_receipt_contains_no_token(tmp_path: Path) -> None:
    calls = 0

    def request() -> pd.DataFrame:
        nonlocal calls
        calls += 1
        return pd.DataFrame({"ts_code": ["600000.SH"], "trade_date": ["20250805"], "value": [1.0]})

    store = TushareSegmentStore(tmp_path)
    first, receipt = store.fetch(
        api="daily_basic",
        segment="20250805",
        request=request,
        required_columns={"ts_code", "trade_date"},
        sort_columns=["ts_code"],
        public_parameters={"trade_date": "20250805"},
    )
    second, cached_receipt = store.fetch(
        api="daily_basic",
        segment="20250805",
        request=request,
        required_columns={"ts_code", "trade_date"},
        sort_columns=["ts_code"],
        public_parameters={"trade_date": "20250805"},
    )
    assert calls == 1
    pd.testing.assert_frame_equal(first, second)
    assert receipt == cached_receipt
    assert "token" not in json.dumps(receipt).lower()
    assert store.missing_segments("daily_basic", ["20250805", "20250806"]) == ["20250806"]


def test_segment_store_retries_transient_errors_with_request_context(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = 0
    monkeypatch.setattr("factor_universe_v2.tushare_data.time.sleep", lambda _: None)

    def request() -> pd.DataFrame:
        nonlocal calls
        calls += 1
        raise RuntimeError("temporary provider failure")

    store = TushareSegmentStore(tmp_path)
    with pytest.raises(
        RuntimeError, match=r"income:600512\.SH request failed after 5 attempts"
    ):
        store.fetch(
            api="income",
            segment="600512.SH",
            request=request,
            required_columns={"ts_code", "ann_date"},
            sort_columns=["ts_code"],
        )
    assert calls == 5


def test_probe_distinguishes_empty_slice_from_permission_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("factor_universe_v2.tushare_data.time.sleep", lambda _: None)

    class Pro:
        def query(self, api: str, **_: object) -> pd.DataFrame:
            if api == "empty":
                return pd.DataFrame(columns=["ts_code"])
            raise RuntimeError("积分不足，无权限")

    result = probe_tushare(Pro(), [{"api": "empty"}, {"api": "denied"}])
    assert result.set_index("api").loc["empty", "probe_status"] == "accessible_empty"
    assert result.set_index("api").loc["denied", "probe_status"] == "permission_denied"


def test_daily_basic_formulas_use_provider_units_and_do_not_invent_negative_yield() -> None:
    dates = pd.date_range("2025-01-01", periods=21, freq="D")
    frame = pd.DataFrame(
        {
            "instrument": "A",
            "datetime": dates,
            "total_mv": 1000.0,
            "circ_mv": 600.0,
            "pe_ttm": [10.0] * 20 + [-2.0],
            "pb": 2.0,
            "ps_ttm": 4.0,
            "dv_ttm": 3.0,
            "turnover_rate_f": list(range(1, 22)),
            "volume_ratio": 1.5,
        }
    )
    result = compute_daily_basic_factors(frame)
    assert result.loc[0, "mature_earnings_yield_ttm"] == pytest.approx(0.1)
    assert pd.isna(result.loc[20, "mature_earnings_yield_ttm"])
    assert result.loc[0, "mature_book_to_price"] == pytest.approx(0.5)
    assert result.loc[0, "mature_dividend_yield_ttm"] == pytest.approx(0.03)
    assert result.loc[0, "mature_turnover_rate_free_float"] == pytest.approx(0.01)
    assert result.loc[20, "mature_abnormal_turnover_20"] == pytest.approx(21 / 10.5 - 1)


def test_moneyflow_formulas_convert_tushare_wan_yuan_and_preserve_order() -> None:
    dates = pd.date_range("2025-01-01", periods=5, freq="D")
    frame = pd.DataFrame(
        {
            "instrument": "A",
            "datetime": dates,
            "buy_sm_amount": 10.0,
            "sell_sm_amount": 5.0,
            "buy_md_amount": 20.0,
            "sell_md_amount": 20.0,
            "buy_lg_amount": 30.0,
            "sell_lg_amount": 10.0,
            "buy_elg_amount": 40.0,
            "sell_elg_amount": 20.0,
            "net_mf_amount": 10.0,
            "traded_amount_cny": 1_000_000.0,
        }
    ).iloc[::-1]
    result = compute_moneyflow_factors(frame)
    assert result.index.equals(frame.index)
    assert result["mature_small_order_imbalance"].dropna().iloc[0] == pytest.approx(1 / 3)
    assert result["mature_institutional_order_imbalance"].dropna().iloc[0] == pytest.approx(0.4)
    assert result["mature_net_flow_to_traded_amount"].dropna().iloc[0] == pytest.approx(0.1)


def _fundamental_frame(available: str = "2025-04-25") -> pd.DataFrame:
    return pd.DataFrame(
        {
            "instrument": ["A"],
            "datetime": ["2025-04-26"],
            "information_available_date": [available],
            "revenue": [200.0],
            "oper_cost": [120.0],
            "operate_profit": [30.0],
            "n_income_attr_p": [20.0],
            "total_assets": [400.0],
            "total_liab": [160.0],
            "total_hldr_eqy_exc_min_int": [240.0],
            "money_cap": [50.0],
            "total_cur_assets": [100.0],
            "total_cur_liab": [50.0],
            "n_cashflow_act": [15.0],
            "prior_total_assets": [320.0],
            "prior_revenue": [160.0],
            "prior_n_income_attr_p": [10.0],
            "total_mv_cny": [1000.0],
        }
    )


def test_fundamental_formulas_are_unit_consistent_and_pit_guarded() -> None:
    result = compute_fundamental_factors(_fundamental_frame())
    assert result.loc[0, "mature_gross_profitability"] == pytest.approx(0.2)
    assert result.loc[0, "mature_accruals_to_assets"] == pytest.approx(0.0125)
    assert result.loc[0, "mature_asset_growth_yoy"] == pytest.approx(0.25)
    assert result.loc[0, "mature_book_to_market_pit"] == pytest.approx(0.24)
    with pytest.raises(ValueError, match="post-decision"):
        compute_fundamental_factors(_fundamental_frame("2025-04-27"))
    with pytest.raises(ValueError, match="unavailable"):
        compute_fundamental_factors(_fundamental_frame("not-a-date"))


def test_market_formulas_are_instrument_local_deterministic_and_finite_when_defined() -> None:
    dates = pd.date_range("2024-01-01", periods=260, freq="D")
    close = pd.Series(100.0 * (1.001 ** pd.Series(range(260))), dtype=float)
    frame = pd.DataFrame(
        {
            "instrument": "A",
            "datetime": dates,
            "$open": close * 0.999,
            "$high": close * 1.01,
            "$low": close * 0.99,
            "$close": close,
            "$amount": 1_000_000.0,
            "$vwap": close * 0.998,
            "$market_return": 0.0005,
        }
    )
    first = compute_market_factors(frame)
    second = compute_market_factors(frame.copy())
    pd.testing.assert_frame_equal(first, second)
    assert first.loc[259, "mature_momentum_12_1"] == pytest.approx(float(close.iloc[238] / close.iloc[7] - 1))
    assert first.loc[259, "mature_vwap_deviation"] == pytest.approx(1 / 0.998 - 1)
    assert first.loc[259, "mature_parkinson_volatility_20"] > 0
    values = first.loc[:, list(ALL_MATURE_FACTOR_NAMES[:17])]
    assert not np.isinf(values.to_numpy(dtype=float)).any()
