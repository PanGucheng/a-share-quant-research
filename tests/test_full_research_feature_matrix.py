from __future__ import annotations

import pandas as pd

from research_validation.feature_matrix import atomic_parquet, canonical_hash, filter_to_pit_intervals, file_sha256, resumable_batch_valid


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
