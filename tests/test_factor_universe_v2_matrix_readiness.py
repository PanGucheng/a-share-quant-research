from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from factor_universe_v2.historical_data import (
    align_statement_events_to_keys,
    qlib_to_tushare,
    statement_event_timeline,
    tushare_to_qlib,
)
from factor_universe_v2.pit import asof_pit_records, prepare_pit_records
from factor_universe_v2.tushare_data import TushareSegmentStore
from factor_universe_v2.matrix_readiness import audit_partitions, compare_canonical_to_legacy


def test_instrument_mapping_is_reversible() -> None:
    for instrument in ("SH600000", "SZ000001", "BJ430047"):
        assert tushare_to_qlib(qlib_to_tushare(instrument)) == instrument


def test_segment_store_rejects_tampered_cache(tmp_path: Path) -> None:
    store = TushareSegmentStore(tmp_path)
    frame, _ = store.fetch(
        api="daily_basic",
        segment="20210104",
        request=lambda: pd.DataFrame(
            {"ts_code": ["600000.SH"], "trade_date": ["20210104"], "pb": [1.0]}
        ),
        required_columns={"ts_code", "trade_date", "pb"},
        sort_columns=["trade_date", "ts_code"],
        public_parameters={"trade_date": "20210104"},
    )
    assert len(frame) == 1
    data_path, _ = store.paths("daily_basic", "20210104")
    data_path.write_bytes(data_path.read_bytes() + b"tampered")
    with pytest.raises(ValueError, match="hash mismatch"):
        store.validate(api="daily_basic", segment="20210104")


def test_canonical_comparison_handles_boolean_factor_values(tmp_path: Path) -> None:
    keys = {
        "datetime": pd.to_datetime(["2021-01-04", "2021-01-05"]),
        "instrument": ["SH600000", "SH600000"],
    }
    canonical_path = tmp_path / "canonical.parquet"
    legacy_path = tmp_path / "legacy.parquet"
    pd.DataFrame({**keys, "canonical_bool": [True, False]}).to_parquet(
        canonical_path, index=False
    )
    pd.DataFrame({**keys, "legacy_bool": [False, False]}).to_parquet(
        legacy_path, index=False
    )
    inventory = pd.DataFrame(
        [
            {
                "name": "canonical_bool",
                "lineage_status": "canonicalized",
                "canonical_replacement_for": "legacy_bool",
            }
        ]
    )
    partitions = pd.DataFrame(
        [{"factors": "legacy_bool", "partition_path": str(legacy_path)}]
    )

    result = compare_canonical_to_legacy(canonical_path, inventory, partitions)

    assert result.loc[0, "status"] == "pass"
    assert result.loc[0, "different_count"] == 1
    assert result.loc[0, "mean_absolute_difference"] == pytest.approx(0.5)


def test_same_day_update_flag_revision_wins() -> None:
    raw = pd.DataFrame(
        {
            "ts_code": ["600000.SH", "600000.SH"],
            "end_date": ["20201231", "20201231"],
            "ann_date": ["20210331", "20210331"],
            "f_ann_date": ["20210331", "20210331"],
            "report_type": ["1", "1"],
            "comp_type": ["1", "1"],
            "update_flag": ["0", "1"],
            "revenue": [100.0, 120.0],
        }
    )
    prepared = prepare_pit_records(raw, dataset="income")
    selected = asof_pit_records(prepared, as_of_date="2021-03-31")
    assert selected.iloc[0]["revenue"] == 120.0
    assert selected.iloc[0]["revision_priority"] == 1


def _statement_rows(dataset: str) -> pd.DataFrame:
    common = {
        "ts_code": ["600000.SH", "600000.SH", "600000.SH"],
        "ann_date": ["20200331", "20210331", "20210415"],
        "f_ann_date": ["20200331", "20210331", "20210415"],
        "end_date": ["20191231", "20201231", "20201231"],
        "report_type": ["1", "1", "1"],
        "comp_type": ["1", "1", "1"],
        "update_flag": ["0", "0", "1"],
    }
    fields = {
        "income": {
            "revenue": [80.0, 100.0, 110.0],
            "oper_cost": [40.0, 50.0, 55.0],
            "operate_profit": [10.0, 20.0, 22.0],
            "n_income_attr_p": [8.0, 16.0, 18.0],
        },
        "balancesheet": {
            "total_assets": [200.0, 240.0, 250.0],
            "total_liab": [100.0, 110.0, 115.0],
            "total_hldr_eqy_exc_min_int": [100.0, 130.0, 135.0],
            "money_cap": [20.0, 30.0, 32.0],
            "total_cur_assets": [80.0, 90.0, 95.0],
            "total_cur_liab": [40.0, 45.0, 46.0],
        },
        "cashflow": {"n_cashflow_act": [9.0, 17.0, 19.0]},
    }
    return pd.DataFrame({**common, **fields[dataset]})


def test_statement_timeline_is_revision_aware_and_no_future() -> None:
    events, audit = statement_event_timeline(
        _statement_rows("income"),
        _statement_rows("balancesheet"),
        _statement_rows("cashflow"),
    )
    keys = pd.DataFrame(
        {
            "instrument": ["SH600000", "SH600000"],
            "datetime": pd.to_datetime(["2021-04-01", "2021-04-16"]),
        }
    )
    aligned = align_statement_events_to_keys(keys, events)
    assert not events.duplicated(["instrument", "information_available_date"]).any()
    assert aligned["revenue"].tolist() == [100.0, 110.0]
    assert aligned["prior_revenue"].tolist() == [80.0, 80.0]
    assert aligned["information_available_date"].le(aligned["datetime"]).all()
    assert audit["same_day_row_count"].ge(1).all()


def test_statement_timeline_keeps_expected_missing_fields() -> None:
    balance = _statement_rows("balancesheet")
    balance.loc[balance["end_date"].eq("20201231"), "money_cap"] = np.nan
    events, _ = statement_event_timeline(
        _statement_rows("income"), balance, _statement_rows("cashflow")
    )
    latest = events.iloc[-1]
    assert pd.isna(latest["money_cap"])
    assert latest["report_period"] == pd.Timestamp("2020-12-31")


def test_coverage_audit_separates_usable_sparse_and_degenerate(tmp_path: Path) -> None:
    dates = pd.date_range("2021-01-01", periods=6, freq="D")
    frame = pd.DataFrame(
        {
            "datetime": dates,
            "instrument": ["SH600000"] * 6,
            "usable": np.arange(6, dtype=float),
            "sparse": [1.0, np.nan, np.nan, np.nan, np.nan, np.nan],
            "constant": [1.0] * 6,
        }
    )
    path = tmp_path / "factors.parquet"
    frame.to_parquet(path, index=False)
    partitions = pd.DataFrame(
        [
            {
                "partition_path": path.as_posix(),
                "factors": "usable,sparse,constant",
            }
        ]
    )
    inventory = pd.DataFrame(
        {
            "name": ["usable", "sparse", "constant"],
            "economic_family": ["Test"] * 3,
            "source": ["synthetic"] * 3,
            "lineage_status": ["new"] * 3,
        }
    )
    split_ranges = pd.DataFrame(
        [
            {
                "split_id": "split_001",
                "train_start": dates[0],
                "train_end": dates[1],
                "validation_start": dates[2],
                "validation_end": dates[3],
                "test_start": dates[4],
                "test_end": dates[5],
            }
        ]
    )
    audit = audit_partitions(
        partitions,
        inventory,
        split_ranges,
        minimum_factor_coverage=0.5,
        minimum_month_coverage=0.5,
        minimum_qualified_month_fraction=1.0,
    )["factor"].set_index("factor")
    assert bool(audit.loc["usable", "research_usable"])
    assert audit.loc["sparse", "block_reason"] == "insufficient_historical_coverage"
    assert audit.loc["constant", "block_reason"] == "constant_or_degenerate"
