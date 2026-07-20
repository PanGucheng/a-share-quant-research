from __future__ import annotations

import math


def test_669_partition_count_and_bound() -> None:
    counts = {"alpha158": 155, "alpha360": 358, "ta": 77, "alpha101": 64, "project_basic": 15}
    assert sum(counts.values()) == 669
    partitions = sum(math.ceil(count / 25) for count in counts.values())
    assert partitions == 30
    assert all(count % 25 <= 25 for count in counts.values())
