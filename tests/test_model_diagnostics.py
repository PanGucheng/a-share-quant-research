from __future__ import annotations

import numpy as np
import pandas as pd

from model_research.diagnostics import (
    _BoosterEstimator,
    _daily_ic,
    assign_rank_buckets,
    forward_returns_t1,
    prediction_equivalence,
    ranking_stability,
)
import pytest


def test_forward_returns_use_t_plus_one_entry() -> None:
    prices = pd.DataFrame(
        {
            "datetime": pd.date_range("2026-01-01", periods=5),
            "instrument": "A",
            "$close": [10.0, 20.0, 30.0, 60.0, 120.0],
        }
    )
    result = forward_returns_t1(prices, [1, 2])
    assert result.loc[0, "return_1d_t1"] == 0.5
    assert result.loc[0, "return_2d_t1"] == 2.0


def test_fixed_rank_bucket_boundaries() -> None:
    buckets = [
        {"name": "1-10", "start": 1, "end": 10},
        {"name": "11-20", "start": 11, "end": 20},
        {"name": "21+", "start": 21, "end": None},
    ]
    actual = assign_rank_buckets(pd.Series([1, 10, 11, 20, 21, 500]), buckets)
    assert actual.tolist() == ["1-10", "1-10", "11-20", "11-20", "21+", "21+"]


def test_prediction_equivalence_uses_relative_and_absolute_tolerance() -> None:
    result = prediction_equivalence(
        np.array([1.0, 1_000_000.0]),
        np.array([1.0 + 5e-12, 1_000_000.0 + 5e-5]),
        atol=1e-11,
        rtol=1e-10,
    )
    assert result["status"] == "pass"
    assert result["exact_match"] is False
    assert result["mismatch_count"] == 0


def test_ranking_retention_and_edge_churn_are_bounded() -> None:
    rows = []
    for date, ordered in [("2026-01-01", ["A", "B", "C", "D"]), ("2026-01-02", ["A", "C", "B", "D"])]:
        rows.extend(
            {"datetime": date, "instrument": instrument, "prediction": 4 - rank}
            for rank, instrument in enumerate(ordered)
        )
    result = ranking_stability(
        pd.DataFrame(rows),
        lags=[1],
        topks=[2],
        edge_topk=2,
        edge_start=2,
        edge_end=3,
    )
    retention = result.loc[result["metric"].eq("retention"), "value"].iloc[0]
    churn = result.loc[result["metric"].eq("edge_churn_share"), "value"].iloc[0]
    assert retention == 0.5
    assert 0.0 <= churn <= 1.0


def test_conditional_daily_ic_respects_date_cross_sections() -> None:
    frame = pd.DataFrame(
        {
            "datetime": ["2026-01-01"] * 3 + ["2026-01-02"] * 3,
            "factor": [1, 2, 3, 3, 2, 1],
            "target": [10, 20, 30, 30, 20, 10],
        }
    )
    values = _daily_ic(frame, "factor", "target", 3)
    assert values.tolist() == [1.0, 1.0]


def test_diagnostic_estimator_cannot_fit() -> None:
    estimator = _BoosterEstimator(object(), np.array([]))
    with pytest.raises(RuntimeError, match="forbids model fitting"):
        estimator.fit(np.empty((0, 0)), np.empty(0))
