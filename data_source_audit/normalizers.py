from __future__ import annotations

import hashlib

import numpy as np
import pandas as pd

from .schemas import CANONICAL_COLUMNS


def _instrument(value: str) -> str:
    text = str(value).upper().replace(".", "")
    if text.startswith(("SH", "SZ")):
        return text
    code = text[-6:]
    return ("SH" if code.startswith(("5", "6", "9")) else "SZ") + code


def _finish(frame: pd.DataFrame) -> pd.DataFrame:
    frame["instrument"] = frame["instrument"].map(_instrument)
    frame["date"] = pd.to_datetime(frame["date"]).dt.normalize()
    for column in CANONICAL_COLUMNS:
        if column not in frame:
            frame[column] = pd.NA
    payload = frame[["source", "instrument", "date"]].astype(str).agg("|".join, axis=1)
    frame["source_row_id"] = payload.map(
        lambda value: hashlib.sha256(value.encode("utf-8")).hexdigest()
    )
    return frame[CANONICAL_COLUMNS].sort_values(
        ["instrument", "date"], kind="stable"
    ).reset_index(drop=True)


def normalize_community(raw: pd.DataFrame) -> pd.DataFrame:
    frame = raw.copy()
    factor = pd.to_numeric(frame["$factor"], errors="coerce")
    for source, target in [
        ("$open", "price_raw_open"),
        ("$high", "price_raw_high"),
        ("$low", "price_raw_low"),
        ("$close", "price_raw_close"),
    ]:
        frame[target] = pd.to_numeric(frame[source], errors="coerce") / factor
    frame["price_raw_preclose"] = frame.groupby("instrument")[
        "price_raw_close"
    ].shift(1)
    # Community provider stores volume in board lots after adjustment and
    # amount in CNY thousands. Both multipliers are independently audited.
    frame["volume_shares"] = (
        pd.to_numeric(frame["$volume"], errors="coerce") * factor * 100.0
    )
    frame["amount_cny"] = pd.to_numeric(frame["$amount"], errors="coerce") * 1000.0
    frame["is_trading"] = (
        frame["price_raw_open"].notna() & frame["volume_shares"].gt(0)
    )
    frame["is_st"] = pd.NA
    frame["suspension_type"] = np.where(
        frame["is_trading"], "none", "source_missing_or_suspended"
    )
    frame["available_before_open"] = "unknown"
    frame["adjustment_mode"] = "raw_reconstructed_from_factor"
    frame["source"] = "community"
    return _finish(frame)


def normalize_baostock(raw: pd.DataFrame) -> pd.DataFrame:
    frame = raw.rename(
        columns={
            "code": "instrument",
            "open": "price_raw_open",
            "high": "price_raw_high",
            "low": "price_raw_low",
            "close": "price_raw_close",
            "preclose": "price_raw_preclose",
            "volume": "volume_shares",
            "amount": "amount_cny",
        }
    ).copy()
    numeric = [
        "price_raw_open",
        "price_raw_high",
        "price_raw_low",
        "price_raw_close",
        "price_raw_preclose",
        "volume_shares",
        "amount_cny",
    ]
    frame[numeric] = frame[numeric].apply(pd.to_numeric, errors="coerce")
    frame["is_trading"] = frame["tradestatus"].astype(str).eq("1")
    frame["is_st"] = frame["isST"].astype(str).map({"1": True, "0": False})
    frame["suspension_type"] = np.where(
        frame["is_trading"], "none", "full_day_or_source_reported"
    )
    frame["available_before_open"] = "unknown"
    frame["adjustment_mode"] = "raw_adjustflag_3"
    frame["source"] = "baostock"
    return _finish(frame)


def normalize_akshare(raw: pd.DataFrame) -> pd.DataFrame:
    frame = raw.rename(
        columns={
            "日期": "date",
            "股票代码": "instrument",
            "开盘": "price_raw_open",
            "最高": "price_raw_high",
            "最低": "price_raw_low",
            "收盘": "price_raw_close",
            "成交量": "volume_lots",
            "成交额": "amount_cny",
        }
    ).copy()
    numeric = [
        "price_raw_open",
        "price_raw_high",
        "price_raw_low",
        "price_raw_close",
        "volume_lots",
        "amount_cny",
    ]
    frame[numeric] = frame[numeric].apply(pd.to_numeric, errors="coerce")
    frame["volume_shares"] = frame["volume_lots"] * 100.0
    frame["price_raw_preclose"] = frame.groupby("instrument")[
        "price_raw_close"
    ].shift(1)
    frame["is_trading"] = frame["price_raw_open"].notna()
    frame["is_st"] = pd.NA
    frame["suspension_type"] = np.where(frame["is_trading"], "none", "source_missing")
    frame["available_before_open"] = "unknown"
    frame["adjustment_mode"] = "raw"
    frame["source"] = "akshare_eastmoney"
    return _finish(frame)
