from __future__ import annotations

import pandas as pd
import pytest

from model_research.historical_comparison import (
    _daily_ic,
    _method_summary,
    load_config,
)


def test_comparison_config_remains_research_only() -> None:
    config = load_config("configs/historical_model_comparison_v1.yaml")
    assert config["experiment_class"] == "post_observation_research"
    assert (
        config["execution"]["portfolio_comparison_status"]
        == "blocked_execution_capability"
    )
    assert config["governance"]["production_model_selected"] is False
    assert config["governance"]["unbiased_final_estimate"] is False


def test_daily_ic_uses_cross_sectional_spearman() -> None:
    frame = pd.DataFrame(
        {
            "datetime": pd.to_datetime(
                ["2024-01-02"] * 3 + ["2024-01-03"] * 3
            ),
            "prediction": [1, 2, 3, 3, 2, 1],
            "__label": [10, 20, 30, 10, 20, 30],
        }
    )
    result = _daily_ic(
        frame,
        split_id="split_001",
        method="equal_weight",
        minimum_daily_pairs=3,
    )
    assert result["status"].eq("pass").all()
    assert result["rank_ic"].tolist() == pytest.approx([1.0, -1.0])


def test_method_summary_uses_frozen_equal_split_primary_metric() -> None:
    split_metrics = pd.DataFrame(
        [
            {
                "outer_split_id": split_id,
                "method": method,
                "mean_daily_rank_ic": value,
                "daily_rank_ic_ir": value,
                "prediction_coverage": 1.0,
            }
            for split_id in ("split_001", "split_002", "split_003")
            for method, value in (("equal_weight", 0.1), ("lightgbm", 0.2))
        ]
    )
    daily = pd.DataFrame(
        [
            {
                "outer_split_id": split_id,
                "method": method,
                "rank_ic": value,
            }
            for split_id in ("split_001", "split_002", "split_003")
            for method, value in (("equal_weight", 0.1), ("lightgbm", 0.2))
        ]
    )
    config = {
        "comparison": {
            "methods": ["equal_weight", "lightgbm"],
            "method_complexity": {"equal_weight": 1, "lightgbm": 5},
        }
    }
    summary = _method_summary(split_metrics, daily, config)
    assert summary.iloc[0]["method"] == "lightgbm"
    assert summary.iloc[0]["equal_split_mean_daily_rank_ic"] == pytest.approx(0.2)
