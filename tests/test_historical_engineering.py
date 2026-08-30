from __future__ import annotations

import numpy as np
import pandas as pd

from research_validation.historical_engineering import (
    audit_practical_pit,
    compare_matrix_overlap,
    earliest_stable_frontier,
    partition_identity,
    practical_market_coverage,
)
from scripts.run_historical_data_engineering_extension_v1 import _year_scope


def test_practical_market_coverage_uses_dated_presence_denominator() -> None:
    expected = pd.DataFrame(
        {
            "datetime": pd.to_datetime(["2010-01-04", "2010-01-04", "2010-01-05"]),
            "instrument": ["SH600000", "SZ000001", "SH600000"],
        }
    )
    observed = pd.DataFrame(
        {
            "datetime": pd.to_datetime(["2010-01-04", "2010-01-05", "2010-01-05"]),
            "instrument": ["SH600000", "SH600000", "SZ000001"],
        }
    )
    result = practical_market_coverage(expected, observed, layer="moneyflow")
    assert result["expected_presence_count"].tolist() == [2, 1]
    assert result["coverage_ratio"].tolist() == [0.5, 1.0]
    assert result["unexpected_count"].tolist() == [0, 1]


def test_earliest_stable_frontier_requires_tail_fraction() -> None:
    coverage = pd.DataFrame(
        {
            "datetime": pd.date_range("2010-01-01", periods=5),
            "coverage_ratio": [0.2, 0.95, 0.8, 0.97, 0.99],
        }
    )
    result = earliest_stable_frontier(
        coverage,
        minimum_coverage=0.9,
        minimum_tail_fraction=1.0,
        minimum_dates=2,
    )
    assert result["frontier"] == pd.Timestamp("2010-01-04")
    assert result["admitted"] is True


def test_practical_pit_fails_on_future_availability() -> None:
    aligned = pd.DataFrame(
        {
            "datetime": pd.to_datetime(["2012-01-10"]),
            "instrument": ["SH600000"],
            "information_available_date": pd.to_datetime(["2012-01-11"]),
        }
    )
    events = pd.DataFrame(
        {
            "instrument": ["SH600000"],
            "information_available_date": pd.to_datetime(["2012-01-11"]),
            "report_period": pd.to_datetime(["2011-12-31"]),
        }
    )
    result = audit_practical_pit(aligned, events).set_index("check")
    assert result.loc["no_future_statement_access", "status"] == "fail"


def test_practical_pit_detects_stale_visible_revision() -> None:
    events = pd.DataFrame(
        {
            "instrument": ["SH600000", "SH600000"],
            "information_available_date": pd.to_datetime(["2012-01-10", "2012-01-12"]),
            "report_period": pd.to_datetime(["2011-09-30", "2011-09-30"]),
        }
    )
    aligned = pd.DataFrame(
        {
            "datetime": pd.to_datetime(["2012-01-13"]),
            "instrument": ["SH600000"],
            "information_available_date": pd.to_datetime(["2012-01-10"]),
        }
    )
    result = audit_practical_pit(aligned, events).set_index("check")
    assert result.loc["selected_event_is_latest_public_event", "status"] == "fail"


def test_overlap_comparison_distinguishes_missingness_and_values() -> None:
    keys = {
        "datetime": pd.to_datetime(["2021-02-01", "2021-02-02"]),
        "instrument": ["SH600000", "SH600000"],
    }
    extended = pd.DataFrame({**keys, "factor": [1.0, np.nan]})
    frozen = pd.DataFrame({**keys, "factor": [1.0 + 1e-12, np.nan]})
    result = compare_matrix_overlap(extended, frozen, ["factor"])
    assert result.loc[0, "value_difference_count"] == 0
    assert result.loc[0, "extended_only_key_count"] == 0


def test_partition_identity_is_order_invariant_and_year_sensitive() -> None:
    rows = pd.DataFrame(
        {
            "year": [2009, 2008],
            "layer": ["price", "price"],
            "partition_id": ["recovered", "recovered"],
            "output_sha256": ["b", "a"],
            "row_count": [2, 1],
            "factor_count": [19, 19],
        }
    )
    assert partition_identity(rows) == partition_identity(rows.iloc[::-1])
    changed = rows.copy()
    changed.loc[0, "year"] = 2010
    assert partition_identity(rows) != partition_identity(changed)


def test_year_scope_separates_historical_parent_and_overlap_canary() -> None:
    config = {
        "full_feature_candidate_start_date": "2010-01-29",
        "historical_end_date": "2021-01-29",
        "overlap_start_date": "2021-02-01",
        "overlap_end_date": "2021-03-31",
    }
    assert _year_scope(config, 2021) == (
        pd.Timestamp("2021-01-01"),
        pd.Timestamp("2021-01-29"),
        True,
    )
    assert _year_scope(config, 2021, overlap=True) == (
        pd.Timestamp("2021-02-01"),
        pd.Timestamp("2021-03-31"),
        True,
    )
