from __future__ import annotations

import numpy as np
import pandas as pd

from research_validation.bootstrap import (
    gap_aware_moving_block_mean_test,
    moving_block_mean_test,
)


def test_gap_aware_bootstrap_is_reproducible() -> None:
    values = pd.Series(np.sin(np.arange(100) / 10))
    values.iloc[40:45] = np.nan
    first = gap_aware_moving_block_mean_test(
        values, samples=100, block_length=10, seed=7
    )
    second = gap_aware_moving_block_mean_test(
        values, samples=100, block_length=10, seed=7
    )
    assert first == second
    assert first["contiguous_segment_count"] == 2


def test_gap_aware_blocks_do_not_bridge_injected_gap() -> None:
    values = pd.Series(np.arange(80, dtype=float))
    baseline = gap_aware_moving_block_mean_test(
        values, samples=50, block_length=10, seed=3
    )
    values.iloc[35:40] = np.nan
    injected = gap_aware_moving_block_mean_test(
        values, samples=50, block_length=10, seed=3
    )
    assert baseline["contiguous_segment_count"] == 1
    assert injected["contiguous_segment_count"] == 2
    assert injected["eligible_block_count"] == (35 - 10 + 1) + (40 - 10 + 1)


def test_legacy_bootstrap_now_reports_mean_interval_without_changing_core_fields() -> None:
    values = pd.Series(np.random.default_rng(1).normal(0.01, 0.1, 100))
    result = moving_block_mean_test(values, samples=100, block_length=10, seed=4)
    assert result["mean_ci_lower"] <= result["raw_statistic"] <= result["mean_ci_upper"]
    assert result["observation_count"] == 100
