from __future__ import annotations

import pandas as pd
import json
from pathlib import Path

from research_validation.historical_frontier_admission import (
    audit_adjustment_continuity,
    audit_cross_sectional_coverage,
    continuous_frontier,
    stratified_stock_sample,
)


def _stock_basic() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "ts_code": ["600000.SH", "000003.SZ", "300750.SZ", "688981.SH"],
            "list_date": ["19991110", "19910703", "20180611", "20200716"],
            "delist_date": [None, "20020614", None, None],
            "list_status": ["L", "D", "L", "L"],
        }
    )


def test_stratified_sample_keeps_delisted_and_is_reproducible() -> None:
    left = stratified_stock_sample(_stock_basic(), sample_per_stratum=1, seed=7)
    right = stratified_stock_sample(_stock_basic(), sample_per_stratum=1, seed=7)
    assert left["ts_code"].tolist() == right["ts_code"].tolist()
    assert "000003.SZ" in left["ts_code"].tolist()


def test_market_coverage_and_continuous_frontier_reject_isolated_pass() -> None:
    rows = []
    canary = _stock_basic().assign(list_date="19900101", delist_date=None)
    for date, ratio in zip(["2010-01-04", "2010-04-01", "2010-07-01", "2010-10-08", "2011-01-04"], [0.95, 0.40, 0.96, 0.96, 0.97]):
        observed_count = round(len(canary) * ratio)
        observed = pd.DataFrame({"ts_code": canary["ts_code"].head(observed_count), "trade_date": date.replace("-", "")})
        rows.append((date, "daily_basic", observed))
    coverage = audit_cross_sectional_coverage(canary, rows)
    result = continuous_frontier(coverage, layer="daily_basic", minimum_coverage=0.90, consecutive_periods=2)
    assert result["stable"] is True
    assert result["frontier"] == "2010-07-01"


def test_adjustment_continuity_flags_duplicate_dates() -> None:
    frame = pd.DataFrame(
        {
            "instrument": ["SH600000", "SH600000"],
            "date": ["2000-01-04", "2000-01-04"],
            "adj_factor": [1.0, 1.0],
            "daily_present": [True, True],
        }
    )
    result = audit_adjustment_continuity(frame)
    assert result.loc[0, "duplicate_date_rows"] == 1


def test_admission_manifest_keeps_matrix_and_model_stages_closed() -> None:
    root = Path(__file__).resolve().parents[1]
    manifest = json.loads((root / "reports" / "historical_frontier_admission_v1" / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["artifact_status"] == "market_qualification_complete_no_extended_matrix"
    assert manifest["extended_matrix_generated"] is False
    assert manifest["model_outcomes_read"] is False
