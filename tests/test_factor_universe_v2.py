from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest
import yaml

from factor_universe_v2.alpha101_canonical import compute_canonical_alpha101_features
from factor_universe_v2.inventory import build_historical_missing_audit, build_local_candidate_catalog
from factor_universe_v2.local_recovery import add_local_recovered_factors
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
