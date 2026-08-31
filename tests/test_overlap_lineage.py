from __future__ import annotations

import numpy as np
import pandas as pd

from factor_research.alpha101_source import alpha101_rank_eligibility
from research_validation.historical_engineering import compare_matrix_overlap
from research_validation.overlap_lineage import (
    causal_kama,
    exact_or_close_counts,
    replace_factor_columns,
)


def test_rank_eligibility_keeps_filled_structural_nan_out_of_rank() -> None:
    class Source:
        @staticmethod
        def rank(values: pd.DataFrame) -> pd.DataFrame:
            return values.rank(axis=1, pct=True)

    original = Source.rank
    values = pd.DataFrame([[5.0, 0.0]], columns=["active", "future"])
    eligible = pd.DataFrame([[True, False]], columns=values.columns)
    with alpha101_rank_eligibility(Source, eligible):
        ranked = Source.rank(values)
    assert ranked.loc[0, "active"] == 1.0
    assert np.isnan(ranked.loc[0, "future"])
    assert Source.rank is original


def test_causal_kama_prefix_is_invariant_to_future_suffix() -> None:
    prefix = pd.Series(np.linspace(10.0, 20.0, 80))
    suffix = pd.Series([500.0, 1.0, 900.0])
    short = causal_kama(prefix)
    long = causal_kama(pd.concat([prefix, suffix], ignore_index=True)).iloc[: len(prefix)]
    pd.testing.assert_series_equal(short.reset_index(drop=True), long.reset_index(drop=True))


def test_replace_factor_columns_preserves_keys_and_unaffected_values() -> None:
    parent = pd.DataFrame(
        {
            "datetime": pd.to_datetime(["2021-01-01", "2021-01-02"]),
            "instrument": ["A", "A"],
            "fixed": [1.0, 2.0],
            "other": [3.0, 4.0],
        }
    )
    corrected = parent[["datetime", "instrument"]].assign(fixed=[10.0, 20.0])
    result = replace_factor_columns(parent, corrected, ["fixed"])
    assert result["fixed"].tolist() == [10.0, 20.0]
    assert result["other"].tolist() == [3.0, 4.0]


def test_lineage_comparisons_treat_same_signed_infinity_as_exact() -> None:
    keys = {
        "datetime": pd.to_datetime(["2021-01-01"]),
        "instrument": ["A"],
    }
    left = pd.DataFrame({**keys, "factor": [-np.inf]})
    right = pd.DataFrame({**keys, "factor": [-np.inf]})
    overlap = compare_matrix_overlap(left, right, ["factor"])
    assert overlap.loc[0, "value_difference_count"] == 0
    counts = exact_or_close_counts(left["factor"], right["factor"])
    assert counts["exact_count"] == 1
