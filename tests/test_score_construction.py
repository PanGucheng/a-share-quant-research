from __future__ import annotations

import pandas as pd
import pytest

from portfolio.score_construction import capped_normalize, construct_daily_scores, filter_eligible_representatives


def test_equal_directional_score_matches_order() -> None:
    frame = pd.DataFrame({"datetime": ["2026-01-02"] * 3, "instrument": list("ABC"), "f1": [1, 2, 3], "f2": [3, 2, 1]})
    weights = pd.DataFrame({"factor_column": ["f1", "f2"], "cluster_id": ["c1", "c2"], "raw_weight": [1, 1], "direction": [1, -1]})
    scores, _ = construct_daily_scores(frame, weights, method="equal_directional_zscore", min_components=2, clip=3)
    assert scores.sort_values("composite_score").instrument.tolist() == ["A", "B", "C"]


def test_duplicate_cluster_vote_rejected() -> None:
    frame = pd.DataFrame({"datetime": ["2026-01-02"] * 2, "instrument": list("AB"), "f1": [1, 2], "f2": [2, 1]})
    weights = pd.DataFrame({"factor_column": ["f1", "f2"], "cluster_id": ["c1", "c1"], "raw_weight": [1, 1], "direction": [1, 1]})
    with pytest.raises(ValueError):
        construct_daily_scores(frame, weights, method="x", min_components=1, clip=3)


def test_capped_normalization_respects_limit() -> None:
    weights = capped_normalize(pd.Series([100.0, 1.0, 1.0]), 0.6)
    assert abs(weights.sum() - 1) < 1e-12
    assert weights.max() <= 0.6 + 1e-12


def test_unselected_ineligible_and_zero_direction_factors_are_excluded() -> None:
    values = pd.DataFrame([
        {"factor": "ok", "selected": True, "selection_eligible": True, "eligible": True, "frozen_direction": -1},
        {"factor": "not_selected", "selected": False, "selection_eligible": True, "eligible": True, "frozen_direction": 1},
        {"factor": "not_eligible", "selected": True, "selection_eligible": True, "eligible": False, "frozen_direction": 1},
        {"factor": "zero", "selected": True, "selection_eligible": True, "eligible": True, "frozen_direction": 0},
    ])
    included, excluded = filter_eligible_representatives(values)
    assert included.factor.tolist() == ["ok"]
    assert set(excluded.factor) == {"not_selected", "not_eligible", "zero"}
    assert excluded.set_index("factor").loc["zero", "reason"] == "excluded_zero_direction"
