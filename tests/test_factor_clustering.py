from __future__ import annotations

import pandas as pd

from factor_research.factor_clustering import hierarchical_clusters
from factor_research.factor_similarity import daily_exposure_similarity, performance_similarity
from factor_research.representative_selection import select_representatives


def test_similar_factors_share_cluster_and_one_representative() -> None:
    distance = pd.DataFrame([[0, 0.1, 0.9], [0.1, 0, 0.8], [0.9, 0.8, 0]], index=list("abc"), columns=list("abc"))
    clusters = hierarchical_clusters(distance, 0.3)
    assert clusters.set_index("factor").loc["a", "cluster_id"] == clusters.set_index("factor").loc["b", "cluster_id"]
    stability = pd.DataFrame({"factor": list("abc"), "selection_frequency": [0.9, 0.5, 0.7], "direction_agreement_ratio": [1, 1, 1], "fdr_pass_frequency": [1, 0.5, 1], "coverage_median": [1, 1, 1]})
    representatives, excluded = select_representatives(clusters, stability)
    assert not representatives.cluster_id.duplicated().any()
    assert "a" in set(representatives.factor)
    assert "b" in set(excluded.factor)


def test_similarity_requires_and_applies_exact_allowed_dates() -> None:
    dates = pd.to_datetime(["2024-01-02", "2024-01-03"])
    frame = pd.DataFrame([
        {"datetime": date, "instrument": f"s{i}", "a": float(i), "b": float(i)}
        for date in dates for i in range(25)
    ])
    exposure = daily_exposure_similarity(
        frame, {"a": "a", "b": "b"}, allowed_dates=[dates[0]], minimum_pair_observations=20
    )
    series = {"a": pd.Series([1.0, -1.0], index=dates), "b": pd.Series([1.0, 1.0], index=dates)}
    performance = performance_similarity(series, allowed_dates=[dates[0]], minimum_pair_dates=1)

    assert exposure.loc["a", "b"] == 1.0
    assert pd.isna(performance.loc["a", "b"])
