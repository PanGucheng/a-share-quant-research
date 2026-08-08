from __future__ import annotations

import pandas as pd
import pytest

from research_validation.external_style import (
    audit_external_style_capability,
    instrument_to_tushare,
    point_effective_industry_join,
    tushare_to_instrument,
    validate_external_style_frame,
)


def _frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "datetime": ["2025-01-02"],
            "instrument": ["sh600000"],
            "total_mv": [100.0],
            "circ_mv": [80.0],
            "size_quantile": [0.5],
            "size_bucket": ["mid"],
            "sw_l1_code": ["801780"],
            "sw_l1_name": ["Bank"],
            "industry_effective_from": ["2024-01-01"],
            "industry_effective_to": [None],
            "source": ["tushare"],
            "source_dataset": ["daily_basic+index_member_all"],
            "source_snapshot_time": ["2026-08-08T00:00:00Z"],
            "source_hash": ["a" * 64],
        }
    )


def test_external_style_contract_normalizes_keys_and_detects_capabilities() -> None:
    result, capability = validate_external_style_frame(_frame())
    assert result.loc[0, "instrument"] == "SH600000"
    assert capability.historical_pit_market_cap_available
    assert capability.historical_pit_industry_available
    assert capability.external_style_extension_status == "available"


def test_external_style_rejects_future_industry_backfill() -> None:
    frame = _frame()
    frame.loc[0, "industry_effective_from"] = "2026-01-01"
    with pytest.raises(ValueError, match="effective intervals"):
        validate_external_style_frame(frame)


def test_missing_optional_input_is_warning_capability_not_failure(tmp_path) -> None:
    result = audit_external_style_capability(
        {"input_path": None, "required_for_core": False}, project_root=tmp_path
    )
    assert result.loc[0, "external_style_extension_status"] == "unavailable_data"
    assert not bool(result.loc[0, "required_for_core"])


@pytest.mark.parametrize(
    ("ts_code", "instrument"),
    [
        ("600000.SH", "SH600000"),
        ("000001.SZ", "SZ000001"),
        ("300750.SZ", "SZ300750"),
        ("688981.SH", "SH688981"),
        ("600298.SH", "SH600298"),
    ],
)
def test_tushare_project_code_mapping_is_explicit_and_reversible(ts_code, instrument) -> None:
    assert tushare_to_instrument(ts_code) == instrument
    assert instrument_to_tushare(instrument) == ts_code


def test_code_mapping_rejects_unsupported_exchange() -> None:
    with pytest.raises(ValueError, match="unsupported"):
        tushare_to_instrument("920002.BJ")


def test_point_effective_industry_join_has_no_future_backfill() -> None:
    decisions = pd.DataFrame(
        {
            "datetime": ["2024-12-31", "2025-01-01", "2025-06-30", "2025-07-01"],
            "instrument": ["SH600000"] * 4,
        }
    )
    intervals = pd.DataFrame(
        {
            "instrument": ["SH600000"],
            "sw_l1_code": ["801780.SI"],
            "sw_l1_name": ["Bank"],
            "industry_effective_from": ["2025-01-01"],
            "industry_effective_to": ["2025-06-30"],
        }
    )
    joined, ambiguous = point_effective_industry_join(decisions, intervals)
    assert pd.isna(joined.loc[0, "sw_l1_code"])
    assert joined.loc[1:2, "sw_l1_code"].eq("801780.SI").all()
    assert pd.isna(joined.loc[3, "sw_l1_code"])
    assert ambiguous.empty


def test_point_effective_industry_join_reports_overlap() -> None:
    decisions = pd.DataFrame({"datetime": ["2025-01-02"], "instrument": ["SH600000"]})
    intervals = pd.DataFrame(
        {
            "instrument": ["SH600000", "SH600000"],
            "sw_l1_code": ["A", "B"],
            "sw_l1_name": ["A", "B"],
            "industry_effective_from": ["2025-01-01", "2025-01-01"],
            "industry_effective_to": [None, None],
        }
    )
    joined, ambiguous = point_effective_industry_join(decisions, intervals)
    assert pd.isna(joined.loc[0, "sw_l1_code"])
    assert ambiguous.loc[0, "active_memberships"] == 2
