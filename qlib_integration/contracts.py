from __future__ import annotations

import re
from collections.abc import Iterable

import numpy as np
import pandas as pd


SIGNAL_COLUMNS = [
    "datetime",
    "instrument",
    "score",
    "method",
    "signal_artifact_id",
    "profile_name",
    "profile_type",
    "research_run_family_id",
]

MARKET_COLUMNS = [
    "datetime",
    "instrument",
    "open",
    "close",
    "volume",
    "amount",
    "can_buy",
    "can_sell",
    "limit_up",
    "limit_down",
    "suspended",
    "factor",
    "change",
    "execution_price",
]


def _require_columns(frame: pd.DataFrame, columns: Iterable[str], name: str) -> None:
    missing = sorted(set(columns) - set(frame.columns))
    if missing:
        raise ValueError(f"{name} missing columns: {missing}")


def normalize_instrument(value: str) -> str:
    text = str(value).strip().upper()
    if re.fullmatch(r"(?:SH|SZ)\d{6}", text):
        return text
    match = re.fullmatch(r"(\d{6})\.(SH|SZ)", text)
    if match:
        return f"{match.group(2)}{match.group(1)}"
    match = re.fullmatch(r"(SH|SZ)\.(\d{6})", text)
    if match:
        return f"{match.group(1)}{match.group(2)}"
    if re.fullmatch(r"\d{6}", text):
        raise ValueError(f"ambiguous instrument without exchange: {text}")
    raise ValueError(f"unsupported instrument format: {value}")


def _normalize_common(frame: pd.DataFrame, name: str) -> pd.DataFrame:
    result = frame.copy()
    result["datetime"] = pd.to_datetime(result["datetime"], errors="raise")
    if result["datetime"].dt.tz is not None:
        result["datetime"] = result["datetime"].dt.tz_localize(None)
    result["datetime"] = result["datetime"].dt.normalize()
    result["instrument"] = result["instrument"].map(normalize_instrument)
    if result[["datetime", "instrument"]].isna().any().any():
        raise ValueError(f"{name} has null datetime or instrument")
    return result


def validate_signal_frame(frame: pd.DataFrame) -> pd.DataFrame:
    _require_columns(frame, SIGNAL_COLUMNS, "signal")
    result = _normalize_common(frame[SIGNAL_COLUMNS], "signal")
    result["score"] = pd.to_numeric(result["score"], errors="coerce")
    if not np.isfinite(result["score"]).all():
        raise ValueError("signal score must be finite")
    text_columns = [
        "method",
        "signal_artifact_id",
        "profile_name",
        "profile_type",
        "research_run_family_id",
    ]
    for column in text_columns:
        result[column] = result[column].astype(str).str.strip()
        if result[column].eq("").any():
            raise ValueError(f"signal {column} must be non-empty")
    if result.duplicated(["datetime", "instrument", "method"]).any():
        raise ValueError("signal has duplicate datetime/instrument/method rows")
    for column in ["profile_name", "profile_type", "research_run_family_id"]:
        if result[column].nunique(dropna=False) != 1:
            raise ValueError(f"signal mixes {column}")
    return result.sort_values(["datetime", "method", "instrument"], kind="stable").reset_index(drop=True)


def validate_market_frame(frame: pd.DataFrame) -> pd.DataFrame:
    _require_columns(frame, MARKET_COLUMNS, "market")
    result = _normalize_common(frame, "market")
    if result.duplicated(["datetime", "instrument"]).any():
        raise ValueError("market has duplicate datetime/instrument rows")

    numeric = ["open", "close", "volume", "amount", "factor", "change", "execution_price"]
    for column in numeric:
        result[column] = pd.to_numeric(result[column], errors="coerce")
    boolean = ["can_buy", "can_sell", "limit_up", "limit_down", "suspended"]
    for column in boolean:
        if result[column].isna().any():
            raise ValueError(f"market {column} must not be null")
        result[column] = result[column].astype(bool)

    if (result["volume"].fillna(0) < 0).any() or (result["amount"].fillna(0) < 0).any():
        raise ValueError("market volume and amount must be non-negative")
    if (result["factor"].dropna() <= 0).any():
        raise ValueError("market factor must be positive")

    order_eligible = result["can_buy"] | result["can_sell"]
    valuation_eligible = ~result["suspended"]
    for column in ["open", "volume", "execution_price"]:
        invalid = order_eligible & (~np.isfinite(result[column]) | result[column].le(0))
        if invalid.any():
            raise ValueError(f"tradable market rows require positive finite {column}")
    for column in ["close", "factor"]:
        invalid = valuation_eligible & (~np.isfinite(result[column]) | result[column].le(0))
        if invalid.any():
            raise ValueError(f"tradable market rows require positive finite {column}")

    if (result["suspended"] & (result["can_buy"] | result["can_sell"])).any():
        raise ValueError("suspended rows cannot be buyable or sellable")
    if (result["limit_up"] & result["can_buy"]).any():
        raise ValueError("limit-up rows cannot be buyable")
    if (result["limit_down"] & result["can_sell"]).any():
        raise ValueError("limit-down rows cannot be sellable")

    return result.sort_values(["datetime", "instrument"], kind="stable").reset_index(drop=True)


def contract_row(
    check_name: str,
    passed: bool,
    observed_value: object,
    required_value: object,
    reason: str = "",
    severity: str = "critical",
) -> dict[str, object]:
    return {
        "check_name": check_name,
        "status": "pass" if passed else "blocked",
        "observed_value": observed_value,
        "required_value": required_value,
        "severity": severity,
        "reason": reason,
    }
