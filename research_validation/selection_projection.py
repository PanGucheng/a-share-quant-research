from __future__ import annotations

import pandas as pd


def build_selection_projections(
    daily_ic: pd.DataFrame,
    outer_assignments: pd.DataFrame,
    inner_assignments: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    daily = daily_ic.copy()
    daily["datetime"] = pd.to_datetime(daily["datetime"])
    outer = outer_assignments.copy()
    outer["datetime"] = pd.to_datetime(outer["datetime"])
    inner = inner_assignments.copy()
    inner["datetime"] = pd.to_datetime(inner["datetime"])
    outer_train_dates = outer.loc[outer["fold"].eq("train"), ["split_id", "datetime"]].rename(
        columns={"split_id": "outer_split_id"}
    )
    outer_train = outer_train_dates.merge(daily, on="datetime", how="left", validate="many_to_many")
    inner_development = inner.merge(daily, on="datetime", how="left", validate="many_to_many")
    daily_columns = [column for column in daily.columns if column != "datetime"]
    if outer_train[daily_columns].isna().all(axis=1).any() or inner_development[daily_columns].isna().all(axis=1).any():
        raise ValueError("selection projection contains assignment dates missing from daily IC")
    outer_train = outer_train.sort_values(["outer_split_id", "datetime", "factor"], kind="stable").reset_index(drop=True)
    inner_development = inner_development.sort_values(
        ["outer_split_id", "inner_split_id", "fold", "datetime", "factor"], kind="stable"
    ).reset_index(drop=True)
    return outer_train, inner_development
