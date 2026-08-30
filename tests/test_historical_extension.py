from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd

from research_validation.historical_extension import (
    audit_statement_revisions,
    compare_market_sources,
    normalize_market_frame,
)


def test_normalize_market_frame_converts_tushare_identity_and_units() -> None:
    source = pd.DataFrame(
        {
            "ts_code": ["600000.SH"],
            "trade_date": ["20000104"],
            "close": [10.0],
            "vol": [100.0],
            "amount": [12.0],
        }
    )
    result = normalize_market_frame(
        source,
        source="tushare",
        instrument_column="ts_code",
        date_column="trade_date",
        close_column="close",
        volume_column="vol",
        amount_column="amount",
        volume_multiplier=100.0,
        amount_multiplier=1000.0,
    )
    assert result.loc[0, "instrument"] == "SH600000"
    assert result.loc[0, "volume"] == 10000.0
    assert result.loc[0, "amount"] == 12000.0


def test_compare_market_sources_groups_segments_and_skips_unrelated_instruments() -> None:
    left_a = pd.DataFrame({"instrument": ["SH600000"], "date": [pd.Timestamp("2020-01-01")], "close": [10.0], "volume": [100.0], "amount": [1000.0], "source": ["tushare:SH600000"]})
    left_b = left_a.assign(date=pd.Timestamp("2020-01-02"), close=10.5)
    right = left_a.assign(close=10.0, source="baostock:SH600000")
    unrelated = left_a.assign(instrument="SZ000001", source="baostock:SZ000001")
    summary, differences = compare_market_sources([left_a, left_b, right, unrelated])
    assert len(summary) == 1
    assert summary.loc[0, "aligned_rows"] == 1
    assert differences.empty


def test_statement_revision_audit_exposes_row_cap_and_revisions() -> None:
    frame = pd.DataFrame(
        {
            "ts_code": ["600000.SH", "600000.SH"],
            "end_date": ["20001231", "20001231"],
            "report_type": ["1", "1"],
            "ann_date": ["20010301", "20010305"],
            "f_ann_date": ["20010301", "20010305"],
            "update_flag": ["0", "1"],
        }
    )
    audit = audit_statement_revisions(frame)
    assert audit["earliest_report_end"] == "2000-12-31"
    assert audit["update_flag_one_rows"] == 1
    assert audit["duplicate_report_keys"] == 2
    assert audit["availability_before_report_end"] == 0


def test_qualification_manifest_is_explicitly_non_authoritative_for_models() -> None:
    root = Path(__file__).resolve().parents[1]
    output = root / "reports" / "maximum_historical_extension_qualification_v1"
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["artifact_status"] == "qualification_complete_no_extended_matrix"
    assert manifest["extended_matrix_generated"] is False
    assert manifest["formal_structured_ml_competition_started"] is False
    assert manifest["research_protocol_v2_changed"] is False
    assert manifest["factor_universe_v2_definitions_changed"] is False
    assert manifest["model_outcomes_read"] is False
    for name, expected in manifest["output_file_hashes"].items():
        assert hashlib.sha256((output / name).read_bytes()).hexdigest() == expected
