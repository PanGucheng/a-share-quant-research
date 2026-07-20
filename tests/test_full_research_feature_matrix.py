from __future__ import annotations

import pandas as pd

from research_validation.feature_matrix import atomic_parquet, build_pit_key_grid, canonical_hash, file_sha256, filter_to_pit_intervals, forward_return_label, resumable_batch_valid


def test_pit_filter_uses_effective_intervals_without_static_membership() -> None:
    frame = pd.DataFrame(
        {
            "datetime": pd.to_datetime(["2024-01-02", "2024-02-01", "2024-02-02"]),
            "instrument": ["SH600000"] * 3,
            "factor": [1.0, 2.0, 3.0],
        }
    )
    intervals = pd.DataFrame({"instrument": ["SH600000"], "start_date": ["2024-02-01"], "end_date": ["2024-02-02"]})
    result = filter_to_pit_intervals(frame, intervals)
    assert result["factor"].tolist() == [2.0, 3.0]


def test_batch_resume_requires_matching_input_and_output_hash(tmp_path) -> None:
    path = tmp_path / "batch.parquet"
    atomic_parquet(pd.DataFrame({"x": [1, 2]}), path)
    row = {"status": "pass", "input_hash": canonical_hash({"batch": 1}), "output_sha256": file_sha256(path)}
    assert resumable_batch_valid(row, canonical_hash({"batch": 1}), path)
    path.write_bytes(b"changed")
    assert not resumable_batch_valid(row, canonical_hash({"batch": 1}), path)


def test_pit_key_grid_keeps_complete_calendar_rows() -> None:
    calendar = pd.DatetimeIndex(["2024-01-02", "2024-01-03", "2024-01-04"])
    intervals = pd.DataFrame({"instrument": ["SH600000"], "start_date": ["2024-01-02"], "end_date": ["2024-01-04"]})
    keys = build_pit_key_grid(intervals, calendar)
    assert len(keys) == 3


def test_forward_label_enters_t_plus_one_and_holds_exact_horizon() -> None:
    frame = pd.DataFrame({"datetime": pd.date_range("2024-01-01", periods=4), "instrument": ["SH600000"] * 4, "close": [10.0, 11.0, 12.0, 13.0]})
    label = forward_return_label(frame, "close", 1, 2)
    assert label.iloc[0] == 13.0 / 11.0 - 1.0
    assert label.iloc[1:].isna().all()
