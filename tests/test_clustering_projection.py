import pandas as pd

from scripts.run_clustering_input_projection_v1 import sampled_dates


def test_exposure_date_sampling_is_deterministic_and_bounded() -> None:
    allowed = pd.bdate_range("2024-01-01", periods=100)

    first = sampled_dates(allowed, 10)
    second = sampled_dates(allowed[::-1], 10)

    assert first.equals(second)
    assert len(first) == 10
    assert set(first).issubset(set(allowed))
