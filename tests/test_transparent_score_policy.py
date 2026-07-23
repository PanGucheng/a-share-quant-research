import pandas as pd

from scripts.audit_transparent_score_policy_v1 import sampled_dates


def test_policy_date_sampling_is_deterministic_and_bounded() -> None:
    dates = pd.bdate_range("2024-01-01", periods=50)
    assert sampled_dates(dates, 7).equals(sampled_dates(dates[::-1], 7))
    assert len(sampled_dates(dates, 7)) == 7
