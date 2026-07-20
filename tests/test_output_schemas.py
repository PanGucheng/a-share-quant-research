from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from research_validation.schemas import (
    DataContractError,
    validate_factor_frame,
    validate_judgement_frame,
    validate_label_frame,
    validate_screening_frame,
    validate_tradability_frame,
    validate_universe_intervals,
)


def factor_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "datetime": ["2026-01-02", "2026-01-02"],
            "instrument": ["SH600000", "SZ000001"],
            "factor_a": [1.0, np.nan],
        }
    )


def test_factor_frame_does_not_mutate_input() -> None:
    frame = factor_frame()
    original = frame.copy(deep=True)
    result = validate_factor_frame(frame, ["factor_a"])
    pd.testing.assert_frame_equal(frame, original)
    assert pd.api.types.is_datetime64_any_dtype(result["datetime"])


@pytest.mark.parametrize("value", [np.inf, -np.inf])
def test_factor_frame_rejects_infinity(value: float) -> None:
    frame = factor_frame()
    frame.loc[0, "factor_a"] = value
    with pytest.raises(Exception):
        validate_factor_frame(frame, ["factor_a"])


def test_factor_frame_rejects_duplicate_key() -> None:
    frame = pd.concat([factor_frame().iloc[[0]], factor_frame().iloc[[0]]], ignore_index=True)
    with pytest.raises(Exception):
        validate_factor_frame(frame, ["factor_a"])


def test_label_time_order() -> None:
    valid = pd.DataFrame({"feature_time": ["2026-01-02"], "label_start_time": ["2026-01-05"], "label_end_time": ["2026-01-09"], "instrument": ["SH600000"], "label": [0.1]})
    validate_label_frame(valid)
    with pytest.raises(Exception):
        validate_label_frame(valid.assign(label_start_time=valid["feature_time"]))


def test_tradability_ranges_and_enums() -> None:
    valid = pd.DataFrame({"can_buy": [True], "can_sell": [False], "tradability_score": [100.0], "liquidity_bucket": [5]})
    validate_tradability_frame(valid)
    with pytest.raises(Exception):
        validate_tradability_frame(valid.assign(liquidity_bucket=6))


def test_tradability_allows_missing_score_for_unmatched_rows() -> None:
    frame = pd.DataFrame({"can_buy": [False], "can_sell": [False], "tradability_score": [np.nan], "liquidity_bucket": [np.nan]})
    validate_tradability_frame(frame)


def test_universe_selection_precedes_effective() -> None:
    valid = pd.DataFrame({"instrument": ["SH600000"], "start_date": ["2026-02-02"], "end_date": ["2026-02-27"], "selection_date": ["2026-01-30"], "effective_date": ["2026-02-02"], "selection_reason": ["top_amount"]})
    validate_universe_intervals(valid)
    with pytest.raises(Exception):
        validate_universe_intervals(valid.assign(effective_date=valid["selection_date"]))


def test_universe_rejects_overlapping_intervals() -> None:
    frame = pd.DataFrame({"instrument": ["SH600000", "SH600000"], "start_date": ["2026-02-02", "2026-02-20"], "end_date": ["2026-02-27", "2026-03-31"], "selection_date": ["2026-01-30", "2026-02-27"], "effective_date": ["2026-02-02", "2026-03-02"], "selection_reason": ["top_amount", "top_amount"]})
    with pytest.raises(DataContractError):
        validate_universe_intervals(frame)


def test_holdout_cannot_be_included() -> None:
    frame = pd.DataFrame({"factor": ["factor_a"], "role": ["holdout"], "coverage": [0.8], "missing_rate": [0.2], "included": [True]})
    with pytest.raises(DataContractError):
        validate_screening_frame(frame)


def test_probe_cannot_enter_downstream_default() -> None:
    frame = pd.DataFrame({"factor": ["factor_a"], "judgement_role": ["new_source_alpha_probe"], "coverage": [0.8], "missing_rate": [0.2], "research_included": [True], "downstream_default_included": [True]})
    with pytest.raises(DataContractError):
        validate_judgement_frame(frame)
