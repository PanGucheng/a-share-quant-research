from __future__ import annotations

from pathlib import Path

import pandas as pd

from scripts.validate_matrix_v3_reproducibility_v1 import compare_partition


def test_partition_comparison_detects_value_and_nan_mutations(tmp_path: Path) -> None:
    legacy = tmp_path / "legacy.parquet"
    current = tmp_path / "current.parquet"
    base = pd.DataFrame(
        {
            "datetime": pd.to_datetime(["2024-01-02", "2024-01-03"]),
            "instrument": ["SH600000", "SH600000"],
            "factor": [1.0, float("nan")],
        }
    )
    base.to_parquet(legacy, index=False)
    mutated = base.copy()
    mutated.loc[0, "factor"] = 2.0
    mutated.loc[1, "factor"] = 3.0
    mutated.to_parquet(current, index=False)

    result = compare_partition(legacy, current, 0.0)

    assert result["key_match"] is True
    assert result["nan_mismatch_count"] == 1
    assert result["nonzero_difference_count"] == 1


def test_partition_comparison_accepts_exact_copy(tmp_path: Path) -> None:
    legacy = tmp_path / "legacy.parquet"
    current = tmp_path / "current.parquet"
    frame = pd.DataFrame(
        {
            "datetime": pd.to_datetime(["2024-01-02"]),
            "instrument": ["SH600000"],
            "factor": [1.0],
        }
    )
    frame.to_parquet(legacy, index=False)
    frame.to_parquet(current, index=False)

    result = compare_partition(legacy, current, 0.0)

    assert result["nonzero_difference_count"] == 0
    assert result["nan_mismatch_count"] == 0
