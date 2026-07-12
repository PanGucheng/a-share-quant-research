from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from portfolio.score_construction import construct_daily_scores


def main() -> int:
    frame = pd.DataFrame({"datetime": ["2026-01-02"] * 3, "instrument": list("ABC"), "f1": [1, 2, 3], "f2": [3, 2, 1]})
    weights = pd.DataFrame({"factor_column": ["f1", "f2"], "cluster_id": ["c1", "c2"], "raw_weight": [1, 1], "direction": [1, -1]})
    scores, _ = construct_daily_scores(frame, weights, method="equal_directional_zscore", min_components=2, clip=3)
    assert scores.loc[scores.instrument == "C", "composite_score"].iloc[0] > scores.loc[scores.instrument == "A", "composite_score"].iloc[0]
    print("All factor score construction synthetic validations passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
