from __future__ import annotations

import pandas as pd


def st_boundaries(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty or frame["is_st"].isna().all():
        return pd.DataFrame(
            columns=["instrument", "date", "old_is_st", "new_is_st", "available_before_open"]
        )
    ordered = frame.sort_values(["instrument", "date"]).copy()
    ordered["old_is_st"] = ordered.groupby("instrument")["is_st"].shift(1)
    changed = ordered["old_is_st"].notna() & ordered["is_st"].ne(ordered["old_is_st"])
    return ordered.loc[
        changed,
        ["instrument", "date", "old_is_st", "is_st", "available_before_open"],
    ].rename(columns={"is_st": "new_is_st"})
