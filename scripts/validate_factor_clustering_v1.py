from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from factor_research.factor_clustering import hierarchical_clusters
from factor_research.representative_selection import select_representatives


def main() -> int:
    distance = pd.DataFrame([[0, 0.1, 0.9], [0.1, 0, 0.8], [0.9, 0.8, 0]], index=list("abc"), columns=list("abc"))
    clusters = hierarchical_clusters(distance, 0.3)
    stability = pd.DataFrame({"factor": list("abc"), "selection_frequency": [0.8, 0.5, 0.7], "direction_agreement_ratio": [1, 1, 1], "fdr_pass_frequency": [1, 0.5, 1], "coverage_median": [1, 1, 1]})
    representatives, _ = select_representatives(clusters, stability)
    assert representatives.cluster_id.nunique() == 2
    assert "a" in set(representatives.factor)
    print("All factor clustering synthetic validations passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
