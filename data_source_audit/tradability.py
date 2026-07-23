from __future__ import annotations

import pandas as pd


def tradability_disagreements(frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    tables = []
    for source, frame in frames.items():
        tables.append(
            frame[["instrument", "date", "is_trading", "available_before_open"]]
            .rename(
                columns={
                    "is_trading": f"is_trading_{source}",
                    "available_before_open": f"available_before_open_{source}",
                }
            )
        )
    if not tables:
        return pd.DataFrame()
    merged = tables[0]
    for table in tables[1:]:
        merged = merged.merge(table, on=["instrument", "date"], how="outer")
    trading = [column for column in merged if column.startswith("is_trading_")]
    merged["known_source_count"] = merged[trading].notna().sum(axis=1)
    merged["trading_state_disagreement"] = (
        merged[trading].astype("boolean").nunique(axis=1, dropna=True).gt(1)
    )
    return merged.loc[
        merged["trading_state_disagreement"] | merged[trading].isna().any(axis=1)
    ]
