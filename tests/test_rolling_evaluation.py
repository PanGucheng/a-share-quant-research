from __future__ import annotations

import pandas as pd
import pytest

from research_validation.rolling_evaluation import development_stability_board, select_development_factor_window, select_factor_window, stability_board


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


def test_low_coverage_cannot_become_stable_core() -> None:
    rows = pd.DataFrame([{"factor": "a", "selected": True, "eligible": False, "frozen_direction": 1, "train_mean_ic": 0.03, "validation_mean_ic": 0.02, "test_mean_ic": 0.01, "fdr_bh_pass": True, "train_coverage": 0.074, "validation_coverage": 1.0, "test_coverage": 1.0}] * 3)
    result = stability_board(rows).iloc[0]
    assert result["stability_role"] == "holdout"
    assert result["eligible_window_count"] == 0


def test_negative_direction_uses_direction_adjusted_success() -> None:
    rows = pd.DataFrame([{"factor": "short_signal", "selected": True, "eligible": True, "frozen_direction": -1, "train_mean_ic": -0.03, "validation_mean_ic": -0.02, "test_mean_ic": -0.01, "fdr_bh_pass": True, "train_coverage": 1.0, "validation_coverage": 1.0, "test_coverage": 1.0}] * 3)
    result = stability_board(rows).iloc[0]
    assert result["direction_adjusted_positive_window_ratio"] == 1.0
    assert result["stability_role"] == "stable_core"


def test_development_selection_rejects_any_extra_test_field() -> None:
    row = pd.Series({
        "outer_split_id": "split_001", "inner_split_id": "inner_001", "factor": "a",
        "train_mean_ic": 0.03, "validation_mean_ic": 0.02, "train_count": 100,
        "validation_count": 50, "train_coverage": 1.0, "validation_coverage": 1.0,
        "selection_eligible": True, "fdr_bh_pass": True, "fdr_bh_q_value": 0.01,
        "test_mean_ic": 99.0,
    })
    with pytest.raises(ValueError, match="schema mismatch"):
        select_development_factor_window(row, min_abs_validation_ic=0.01, min_dates=40)


def test_development_board_has_no_test_metrics() -> None:
    rows = pd.DataFrame([{
        "outer_split_id": "split_001", "factor": "a", "selected": True, "eligible": True,
        "frozen_direction": 1, "train_mean_ic": 0.03, "validation_mean_ic": 0.02,
        "fdr_bh_pass": True, "fdr_bh_q_value": 0.01, "train_coverage": 1.0,
        "validation_coverage": 1.0,
    }] * 3)
    result = development_stability_board(rows)
    assert result.iloc[0]["stability_role"] == "stable_core"
    assert not any(column.startswith("test_") or "oos" in column for column in result.columns)
