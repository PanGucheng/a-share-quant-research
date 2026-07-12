from __future__ import annotations

import pandas as pd
import pytest

from research_validation.rolling_evaluation import select_factor_window, stability_board


def selection_row() -> pd.Series:
    return pd.Series({"factor": "a", "split_id": "s", "train_mean_ic": 0.03, "validation_mean_ic": 0.02, "train_count": 100, "validation_count": 50, "fdr_bh_pass": True, "fdr_bh_q_value": 0.01})


def test_selection_rejects_test_columns() -> None:
    row = selection_row(); row["test_mean_ic"] = 10.0
    with pytest.raises(ValueError):
        select_factor_window(row, min_abs_validation_ic=0.01, min_dates=40)


def test_selection_freezes_direction() -> None:
    decision = select_factor_window(selection_row(), min_abs_validation_ic=0.01, min_dates=40)
    assert decision == {"selected": True, "frozen_direction": 1, "selection_reason": "selected"}


def test_stability_role_requires_multiple_windows() -> None:
    rows = pd.DataFrame([{"factor": "a", "selected": True, "eligible": True, "frozen_direction": 1, "train_mean_ic": 0.03, "validation_mean_ic": 0.02, "test_mean_ic": 0.01, "fdr_bh_pass": True, "train_coverage": 1.0, "validation_coverage": 1.0, "test_coverage": 1.0}] * 3)
    assert stability_board(rows).iloc[0]["stability_role"] == "stable_core"
