from __future__ import annotations

import pandas as pd


TARGET_TRANSFORM_ID = "daily_cross_sectional_rank_centered_v1"
TARGET_TRANSFORM_V2_ID = "daily_cross_sectional_rank_centered_v2"


def daily_cross_sectional_rank_centered(
    frame: pd.DataFrame,
    *,
    label_column: str,
    minimum_daily_pairs: int,
) -> tuple[pd.Series, pd.DataFrame]:
    valid = frame[label_column].notna()
    counts = frame.loc[valid].groupby("datetime", sort=True).size()
    eligible_dates = counts.loc[counts >= minimum_daily_pairs].index
    eligible = valid & frame["datetime"].isin(eligible_dates)
    transformed = pd.Series(float("nan"), index=frame.index, dtype=float)
    transformed.loc[eligible] = (
        frame.loc[eligible]
        .groupby("datetime", sort=False)[label_column]
        .rank(method="average", pct=True)
        - 0.5
    )
    receipt = pd.DataFrame(
        {
            "datetime": counts.index,
            "valid_pair_count": counts.values,
            "status": [
                "pass"
                if count >= minimum_daily_pairs
                else "blocked_insufficient_daily_pairs"
                for count in counts.values
            ],
        }
    )
    return transformed, receipt


def eligible_daily_cross_sectional_rank_centered(
    frame: pd.DataFrame,
    *,
    label_column: str,
    feature_columns: list[str] | tuple[str, ...],
    expected_dates: pd.DatetimeIndex,
    minimum_daily_pairs: int,
) -> tuple[pd.Series, pd.Series, pd.DataFrame]:
    if not feature_columns:
        raise ValueError("feature_columns cannot be empty")
    missing = sorted(
        {label_column, "datetime", *feature_columns} - set(frame.columns)
    )
    if missing:
        raise ValueError(f"sample eligibility missing columns: {missing}")
    values = frame.loc[:, feature_columns].replace(
        [float("inf"), float("-inf")], float("nan")
    )
    label_valid = frame[label_column].notna()
    feature_valid = values.notna().any(axis=1)
    eligible = label_valid & feature_valid
    counts = (
        frame.loc[eligible]
        .groupby("datetime", sort=True)
        .size()
        .reindex(pd.DatetimeIndex(expected_dates).normalize(), fill_value=0)
        .astype(int)
    )
    eligible_dates = counts.loc[counts >= minimum_daily_pairs].index
    fit_eligible = eligible & frame["datetime"].isin(eligible_dates)
    transformed = pd.Series(float("nan"), index=frame.index, dtype=float)
    transformed.loc[fit_eligible] = (
        frame.loc[fit_eligible]
        .groupby("datetime", sort=False)[label_column]
        .rank(method="average", pct=True)
        - 0.5
    )
    receipt = pd.DataFrame(
        {
            "datetime": counts.index,
            "valid_pair_count": counts.values,
            "status": [
                "pass"
                if count >= minimum_daily_pairs
                else "blocked_insufficient_daily_pairs"
                for count in counts.values
            ],
        }
    )
    return transformed, eligible, receipt
