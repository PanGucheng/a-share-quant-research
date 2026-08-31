from __future__ import annotations

from pathlib import Path

import pandas as pd

from research_validation.canonical_dataset import (
    canonical_dataset_identity,
    dated_membership_axis,
    read_effective_partition,
    validate_partition_segments,
    validate_semantic_continuity,
)


def _manifest(path: Path) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "segment_id": "historical_2020",
                "partition_id": "alpha",
                "effective_start": "2020-01-02",
                "effective_end": "2020-12-31",
                "partition_path": path.as_posix(),
                "output_sha256": "a",
                "row_count": 2,
                "factor_count": 1,
                "lineage_action": "parent_reference",
            },
            {
                "segment_id": "continuation_2021",
                "partition_id": "alpha",
                "effective_start": "2021-01-04",
                "effective_end": "2021-12-31",
                "partition_path": path.as_posix(),
                "output_sha256": "b",
                "row_count": 2,
                "factor_count": 1,
                "lineage_action": "corrected_recompute",
            },
        ]
    )


def _lineage(continuation: str = "pit_rank_v1") -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "factor": "alpha",
                "authoritative_semantics": "pit_rank_v1",
                "historical_semantics": "pit_rank_v1",
                "continuation_semantics": continuation,
                "historical_action": "corrected_parent_reference",
                "continuation_action": "corrected_recompute",
                "research_usable": True,
            }
        ]
    )


def test_canonical_identity_is_order_independent(tmp_path: Path) -> None:
    manifest = _manifest(tmp_path / "unused.parquet")
    lineage = _lineage()
    assert canonical_dataset_identity(manifest, lineage) == canonical_dataset_identity(
        manifest.iloc[::-1], lineage.iloc[::-1]
    )


def test_semantic_continuity_fails_closed_on_regime_break() -> None:
    passed = validate_semantic_continuity(_lineage())
    failed = validate_semantic_continuity(_lineage("frozen_bug_v0"))
    assert passed["status"].tolist() == ["pass"]
    assert failed["implementation_regime_break"].tolist() == [True]


def test_partition_segments_reject_overlap(tmp_path: Path) -> None:
    manifest = _manifest(tmp_path / "unused.parquet")
    assert validate_partition_segments(manifest)["status"].tolist() == ["pass"]
    manifest.loc[1, "effective_start"] = "2020-12-31"
    checked = validate_partition_segments(manifest)
    assert checked["overlap_count"].tolist() == [1]
    assert checked["status"].tolist() == ["fail"]


def test_effective_partition_reader_enforces_declared_range(tmp_path: Path) -> None:
    path = tmp_path / "partition.parquet"
    pd.DataFrame(
        {
            "datetime": pd.to_datetime(["2019-12-31", "2020-01-02", "2021-01-04"]),
            "instrument": ["sh600000", "sh600000", "sh600000"],
            "alpha": [1.0, 2.0, 3.0],
        }
    ).to_parquet(path, index=False)
    row = _manifest(path).iloc[0]
    loaded = read_effective_partition(row, columns=["alpha"])
    assert loaded["datetime"].dt.strftime("%Y-%m-%d").tolist() == ["2020-01-02"]
    assert loaded["instrument"].tolist() == ["SH600000"]


def test_dated_membership_axis_includes_warmup_only_members() -> None:
    intervals = pd.DataFrame(
        {
            "instrument": ["sh600000", "sz000001", "sz300001", "sh600001"],
            "start_date": ["2020-01-01", "2021-01-01", "2022-01-01", "2019-01-01"],
            "end_date": ["2020-12-31", "2021-12-31", "2022-12-31", "2019-12-31"],
        }
    )
    assert dated_membership_axis(intervals, "2020-06-01", "2021-03-31") == [
        "SH600000",
        "SZ000001",
    ]
