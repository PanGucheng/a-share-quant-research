from __future__ import annotations

import numpy as np
import pandas as pd

from research_validation.bootstrap import moving_block_mean_test
from research_validation.multiple_testing import apply_fdr


def test_bootstrap_reproducible() -> None:
    series = pd.Series(np.random.default_rng(1).normal(0.03, 0.1, 300))
    assert moving_block_mean_test(series, samples=500, block_length=10, seed=5) == moving_block_mean_test(series, samples=500, block_length=10, seed=5)


def test_stable_signal_passes() -> None:
    series = pd.Series(np.random.default_rng(2).normal(0.05, 0.1, 500))
    assert moving_block_mean_test(series, samples=1000, block_length=20, seed=2)["raw_p_value"] < 0.05


def test_fdr_order_invariant_and_nan_safe() -> None:
    frame = pd.DataFrame({"factor": ["a", "b", "c"], "test_family": ["family"] * 3, "metric": ["ic"] * 3, "raw_p_value": [0.01, 0.2, np.nan]})
    left = apply_fdr(frame, 0.05).sort_values("factor").reset_index(drop=True)
    right = apply_fdr(frame.sample(frac=1, random_state=4), 0.05).sort_values("factor").reset_index(drop=True)
    pd.testing.assert_series_equal(left["fdr_bh_q_value"], right["fdr_bh_q_value"])
    assert not left.loc[left.factor == "c", "fdr_bh_pass"].iloc[0]
