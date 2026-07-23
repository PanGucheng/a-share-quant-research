from __future__ import annotations

import numpy as np
import pandas as pd

from .schemas import PRICE_COLUMNS


def compare_pair(left: pd.DataFrame, right: pd.DataFrame) -> tuple[dict[str, object], pd.DataFrame]:
    left_name = str(left["source"].iloc[0]) if len(left) else "left_unavailable"
    right_name = str(right["source"].iloc[0]) if len(right) else "right_unavailable"
    keys = ["instrument", "date"]
    merged = left.merge(right, on=keys, how="outer", suffixes=("_left", "_right"), indicator=True)
    both = merged.loc[merged["_merge"].eq("both")].copy()
    for column in PRICE_COLUMNS + ["volume_shares", "amount_cny"]:
        a = pd.to_numeric(both[f"{column}_left"], errors="coerce")
        b = pd.to_numeric(both[f"{column}_right"], errors="coerce")
        both[f"{column}_abs_diff"] = (a - b).abs()
        both[f"{column}_rel_diff"] = (a - b).abs() / np.maximum(b.abs(), 1.0)
    close_rel = both["price_raw_close_rel_diff"].dropna()
    volume_rel = both["volume_shares_rel_diff"].dropna()
    amount_rel = both["amount_cny_rel_diff"].dropna()
    summary = {
        "left_source": left_name,
        "right_source": right_name,
        "left_rows": len(left),
        "right_rows": len(right),
        "aligned_rows": len(both),
        "left_only_rows": int(merged["_merge"].eq("left_only").sum()),
        "right_only_rows": int(merged["_merge"].eq("right_only").sum()),
        "close_tolerance_match_rate": float(close_rel.le(1e-4).mean()) if len(close_rel) else 0.0,
        "volume_tolerance_match_rate": float(volume_rel.le(1e-4).mean()) if len(volume_rel) else 0.0,
        "amount_tolerance_match_rate": float(amount_rel.le(1e-4).mean()) if len(amount_rel) else 0.0,
        "maximum_close_relative_difference": float(close_rel.max()) if len(close_rel) else np.nan,
    }
    differences = both.loc[
        both["price_raw_close_rel_diff"].gt(1e-4)
        | both["volume_shares_rel_diff"].gt(1e-4)
        | both["amount_cny_rel_diff"].gt(1e-4),
        keys
        + [
            "price_raw_close_left",
            "price_raw_close_right",
            "price_raw_close_rel_diff",
            "volume_shares_rel_diff",
            "amount_cny_rel_diff",
        ],
    ]
    return summary, differences
