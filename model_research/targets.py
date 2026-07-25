from __future__ import annotations

import pandas as pd


TARGET_TRANSFORM_ID = "daily_cross_sectional_rank_centered_v1"


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
