from __future__ import annotations

import pandas as pd

from factor_research.factor_clustering import hierarchical_clusters
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
