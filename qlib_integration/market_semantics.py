from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml


@dataclass(frozen=True)
class ResolvedFee:
    schedule_id: str
    effective_from: pd.Timestamp
    effective_to: pd.Timestamp | None
    buy_commission_rate: float
    sell_commission_rate: float
    minimum_commission: float
    sell_stamp_tax_rate: float
    transfer_fee_rate: float
    slippage_bps: float


def load_yaml(path: str | Path) -> dict[str, Any]:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}


def resolve_fee(schedule: dict[str, Any], trading_date: object, security_type: str = "a_share") -> ResolvedFee:
    date = pd.Timestamp(trading_date).normalize()
    matches: list[tuple[pd.Timestamp, dict[str, Any]]] = []
    for row in schedule.get("schedules", []):
        if row.get("security_type") != security_type:
            continue
        start = pd.Timestamp(row["effective_from"]).normalize()
        end = pd.Timestamp(row["effective_to"]).normalize() if row.get("effective_to") else None
        if start <= date and (end is None or date <= end):
            matches.append((start, row))
    if len(matches) != 1:
        raise ValueError(f"fee schedule must resolve exactly once for {security_type} on {date.date()}; got {len(matches)}")
    start, row = matches[0]
    return ResolvedFee(
        schedule_id=str(row["schedule_id"]),
        effective_from=start,
        effective_to=pd.Timestamp(row["effective_to"]).normalize() if row.get("effective_to") else None,
        buy_commission_rate=float(row["buy_commission_rate"]),
        sell_commission_rate=float(row["sell_commission_rate"]),
        minimum_commission=float(row["minimum_commission"]),
        sell_stamp_tax_rate=float(row["sell_stamp_tax_rate"]),
        transfer_fee_rate=float(row["transfer_fee_rate"]),
        slippage_bps=float(row["slippage_bps"]),
    )


def infer_board(instrument: str) -> str:
    code = str(instrument).upper().replace("SH", "").replace("SZ", "")
    if code.startswith(("688", "689")):
        return "star"
    if code.startswith(("300", "301")):
        return "chinext"
    if code.startswith(("600", "601", "603", "605", "000", "001", "002", "003")):
        return "main"
    return "unknown"


def resolve_price_limit_rule(
    rules: dict[str, Any],
    *,
    board: str,
    st_flag: bool | None,
    ipo_age: int | None,
    trading_date: object,
) -> dict[str, Any]:
    if board == "unknown" or st_flag is None or ipo_age is None:
        raise ValueError("price-limit rule inputs are incomplete")
    date = pd.Timestamp(trading_date).normalize()
    candidates = []
    for row in rules.get("price_limit_rules", []):
        if row["board"] not in {board, "all"}:
            continue
        if row.get("st_flag") is not None and bool(row["st_flag"]) != bool(st_flag):
            continue
        start = pd.Timestamp(row["effective_from"]).normalize()
        end = pd.Timestamp(row["effective_to"]).normalize() if row.get("effective_to") else None
        if start <= date and (end is None or date <= end):
            candidates.append(row)
    if len(candidates) != 1:
        raise ValueError(f"price-limit rule must resolve exactly once; got {len(candidates)}")
    result = dict(candidates[0])
    no_limit_days = int(result.get("ipo_no_limit_trading_days", 0))
    result["limit_ratio"] = None if int(ipo_age) <= no_limit_days else float(result["limit_ratio"])
    return result


def resolve_lot_rule(rules: dict[str, Any], *, board: str, side: str) -> dict[str, Any]:
    if side not in {"buy", "sell"}:
        raise ValueError(f"unsupported side: {side}")
    matches = [row for row in rules.get("lot_rules", []) if row["board"] == board and row["side"] == side]
    if len(matches) != 1:
        raise ValueError(f"lot rule must resolve exactly once for {board}/{side}; got {len(matches)}")
    return dict(matches[0])


def validate_field_timing(frame: pd.DataFrame) -> pd.DataFrame:
    required = {
        "field_name",
        "observation_timestamp",
        "available_at",
        "execution_timestamp",
        "source_artifact_id",
    }
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"field timing frame missing columns: {missing}")
    result = frame.copy()
    for column in ["observation_timestamp", "available_at", "execution_timestamp"]:
        result[column] = pd.to_datetime(result[column], errors="raise")
    result["future_field"] = result["available_at"] > result["execution_timestamp"]
    return result


def stale_valuation(
    close: pd.Series,
    *,
    maximum_stale_trading_days: int,
) -> pd.DataFrame:
    numeric = pd.to_numeric(close, errors="coerce")
    valid = np.isfinite(numeric) & numeric.gt(0)
    values: list[float] = []
    ages: list[int | None] = []
    last_value = np.nan
    age: int | None = None
    for value, is_valid in zip(numeric, valid):
        if bool(is_valid):
            last_value = float(value)
            age = 0
        elif age is not None:
            age += 1
        values.append(last_value if age is not None and age <= maximum_stale_trading_days else np.nan)
        ages.append(age)
    return pd.DataFrame(
        {
            "valuation_price": values,
            "valuation_price_age_trading_days": pd.Series(ages, dtype="Int64"),
            "valuation_stale_blocked": [
                age is None or age > maximum_stale_trading_days for age in ages
            ],
        },
        index=close.index,
    )
