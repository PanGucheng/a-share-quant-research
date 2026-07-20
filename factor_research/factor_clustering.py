from __future__ import annotations

import pandas as pd
from scipy.cluster.hierarchy import fcluster, linkage
from scipy.spatial.distance import squareform


def hierarchical_clusters(distance: pd.DataFrame, threshold: float, method: str = "average") -> pd.DataFrame:
    if not distance.index.equals(distance.columns) or not distance.equals(distance.T):
        raise ValueError("distance matrix must be symmetric with identical labels")
    condensed = squareform(distance.to_numpy(dtype=float), checks=True)
    labels = fcluster(linkage(condensed, method=method), t=threshold, criterion="distance")
    return pd.DataFrame({"factor": distance.index, "cluster_id": [f"cluster_{value:03d}" for value in labels]})
