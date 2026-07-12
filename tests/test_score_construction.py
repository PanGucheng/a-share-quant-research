from __future__ import annotations

import pandas as pd
import pytest

from portfolio.score_construction import capped_normalize, construct_daily_scores


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
