from __future__ import annotations

import pandas as pd
import pytest

from research_validation.purged_split import WalkForwardConfig, build_purged_walk_forward, leakage_audit, purge_against_period


def config(horizon: int = 20) -> WalkForwardConfig:
    return WalkForwardConfig(2, 3, 3, 3, horizon, 1, 5, 300, 30, 40, "expanding")


def test_purged_split_has_no_leakage() -> None:
    outputs = build_purged_walk_forward(pd.bdate_range("2018-01-01", "2025-12-31"), config())
    assert (leakage_audit(outputs)["status"] == "pass").all()


def test_horizon_changes_purge_range() -> None:
    calendar = pd.bdate_range("2018-01-01", "2025-12-31")
    long = build_purged_walk_forward(calendar, config(20))
    short = build_purged_walk_forward(calendar, config(1))
    assert len(long["purged_dates"]) > len(short["purged_dates"])


def test_same_date_never_crosses_fold() -> None:
    outputs = build_purged_walk_forward(pd.bdate_range("2018-01-01", "2025-12-31"), config())
    assert (outputs["date_assignments"].groupby(["split_id", "datetime"])["fold"].nunique() == 1).all()


def test_insufficient_calendar_fails() -> None:
    with pytest.raises(ValueError):
        build_purged_walk_forward(pd.bdate_range("2024-01-01", periods=100), config())


def test_interval_overlap_purge_matches_ml_get_train_times_semantics() -> None:
    samples = pd.DataFrame(
        {
            "feature_time": pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05"]),
            "label_start_time": pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-03", "2024-01-01", "2024-01-05"]),
            "label_end_time": pd.to_datetime(["2024-01-01", "2024-01-03", "2024-01-05", "2024-01-06", "2024-01-06"]),
        }
    )
    kept, purged = purge_against_period(samples, pd.Timestamp("2024-01-03"), pd.Timestamp("2024-01-04"))
    assert kept["feature_time"].tolist() == [pd.Timestamp("2024-01-01"), pd.Timestamp("2024-01-05")]
    assert purged["feature_time"].tolist() == [pd.Timestamp("2024-01-02"), pd.Timestamp("2024-01-03"), pd.Timestamp("2024-01-04")]
