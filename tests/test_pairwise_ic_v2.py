from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from scipy.stats import spearmanr

from research_validation.pairwise_ic import pairwise_daily_spearman


def test_pairwise_rank_matches_scipy_per_factor_missing_pattern() -> None:
    frame = pd.DataFrame(
        {
            "a": [1.0, 2.0, np.nan, 4.0, 4.0],
            "b": [5.0, np.nan, 3.0, 2.0, 1.0],
            "label": [5.0, 1.0, 4.0, np.nan, 2.0],
        }
    )
    result = pairwise_daily_spearman(
        frame, ["a", "b"], label_column="label", minimum_cross_section=2
    ).set_index("factor")
    for factor in ("a", "b"):
        pair = frame[[factor, "label"]].dropna()
        expected = spearmanr(pair[factor], pair["label"]).statistic
        assert result.loc[factor, "rank_ic"] == pytest.approx(expected)
        assert result.loc[factor, "pair_count"] == len(pair)


def test_label_mutation_outside_factor_pair_cannot_change_ic() -> None:
    frame = pd.DataFrame(
        {
            "factor": [1.0, 2.0, np.nan, 4.0],
            "label": [4.0, 3.0, 2.0, 1.0],
        }
    )
    baseline = pairwise_daily_spearman(
        frame, ["factor"], label_column="label", minimum_cross_section=2
    )
    changed = frame.copy()
    changed.loc[2, "label"] = 1_000_000.0
    mutated = pairwise_daily_spearman(
        changed, ["factor"], label_column="label", minimum_cross_section=2
    )
    assert baseline.loc[0, "rank_ic"] == mutated.loc[0, "rank_ic"]
    assert baseline.loc[0, "pair_count"] == mutated.loc[0, "pair_count"]


def test_pairwise_ic_is_row_order_invariant() -> None:
    frame = pd.DataFrame(
        {"factor": [1.0, 3.0, 2.0], "label": [3.0, 1.0, 2.0]}
    )
    first = pairwise_daily_spearman(
        frame, ["factor"], label_column="label", minimum_cross_section=2
    )
    second = pairwise_daily_spearman(
        frame.iloc[::-1], ["factor"], label_column="label", minimum_cross_section=2
    )
    assert first.loc[0, "rank_ic"] == second.loc[0, "rank_ic"]
