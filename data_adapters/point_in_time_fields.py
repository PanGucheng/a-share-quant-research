from __future__ import annotations

import pandas as pd


PIT_COLUMNS = ["instrument", "field_name", "field_value", "source", "source_record_date", "announcement_date", "effective_from", "effective_to", "collected_at", "raw_snapshot_id", "is_point_in_time_valid", "historical_research_eligible"]


def normalize_instrument(code: str) -> str:
    value = str(code).zfill(6)
    if value.startswith(("6", "9")): return f"SH{value}"
    if value.startswith(("0", "2", "3")): return f"SZ{value}"
    if value.startswith(("4", "8")): return f"BJ{value}"
    return value.upper()


def current_spot_to_pit(frame: pd.DataFrame, collected_at: pd.Timestamp, snapshot_id: str) -> pd.DataFrame:
    required = {"代码", "总市值", "流通市值"}
    missing = required - set(frame.columns)
    if missing: raise ValueError(f"spot snapshot missing columns: {sorted(missing)}")
    rows = []
    for _, values in frame.iterrows():
        instrument = normalize_instrument(values["代码"])
        for source_column, field_name in [("总市值", "market_cap"), ("流通市值", "float_market_cap")]:
            value = pd.to_numeric(pd.Series([values[source_column]]), errors="coerce").iloc[0]
            rows.append({"instrument": instrument, "field_name": field_name, "field_value": value, "source": "akshare.stock_zh_a_spot_em", "source_record_date": collected_at.normalize(), "announcement_date": pd.NaT, "effective_from": collected_at.normalize(), "effective_to": pd.NaT, "collected_at": collected_at, "raw_snapshot_id": snapshot_id, "is_point_in_time_valid": True, "historical_research_eligible": False})
    return pd.DataFrame(rows, columns=PIT_COLUMNS)


def audit_pit_fields(frame: pd.DataFrame, research_start: pd.Timestamp | None = None) -> dict[str, int]:
    if frame.empty:
        return {"historical_current_snapshot_backfill_count": 0, "missing_effective_date_count": 0, "untraceable_source_count": 0, "invalid_interval_count": 0}
    historical = frame["historical_research_eligible"].fillna(False).astype(bool)
    backfill = historical & frame["announcement_date"].isna() & (pd.to_datetime(frame["effective_from"]) < pd.to_datetime(frame["collected_at"]).dt.normalize())
    invalid_interval = frame["effective_to"].notna() & (pd.to_datetime(frame["effective_from"]) > pd.to_datetime(frame["effective_to"]))
    return {"historical_current_snapshot_backfill_count": int(backfill.sum()), "missing_effective_date_count": int((historical & frame["effective_from"].isna()).sum()), "untraceable_source_count": int(frame["source"].isna().sum() + frame["raw_snapshot_id"].isna().sum()), "invalid_interval_count": int(invalid_interval.sum())}
