from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

import pandas as pd


KEY_COLUMNS = ("datetime", "instrument")
MARKET_CAP_COLUMNS = ("total_mv", "circ_mv", "size_quantile", "size_bucket")
INDUSTRY_COLUMNS = (
    "sw_l1_code",
    "sw_l1_name",
    "industry_effective_from",
    "industry_effective_to",
)
PROVENANCE_COLUMNS = ("source", "source_dataset", "source_snapshot_time", "source_hash")
EXTERNAL_STYLE_COLUMNS = KEY_COLUMNS + MARKET_CAP_COLUMNS + INDUSTRY_COLUMNS + PROVENANCE_COLUMNS


def tushare_to_instrument(value: str) -> str:
    match = re.fullmatch(r"(\d{6})\.(SH|SZ)", str(value).upper())
    if match is None:
        raise ValueError(f"unsupported Tushare A-share code: {value}")
    return f"{match.group(2)}{match.group(1)}"


def instrument_to_tushare(value: str) -> str:
    match = re.fullmatch(r"(SH|SZ)(\d{6})", str(value).upper())
    if match is None:
        raise ValueError(f"unsupported project A-share instrument: {value}")
    return f"{match.group(2)}.{match.group(1)}"


def point_effective_industry_join(
    decisions: pd.DataFrame, intervals: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame]:
    required_decisions = {"datetime", "instrument"}
    required_intervals = {
        "instrument",
        "sw_l1_code",
        "sw_l1_name",
        "industry_effective_from",
        "industry_effective_to",
    }
    if missing := required_decisions - set(decisions):
        raise ValueError(f"decision frame missing columns: {sorted(missing)}")
    if missing := required_intervals - set(intervals):
        raise ValueError(f"industry interval frame missing columns: {sorted(missing)}")
    keys = decisions[["datetime", "instrument"]].copy()
    keys["datetime"] = pd.to_datetime(keys["datetime"]).dt.normalize()
    source = intervals[list(required_intervals)].copy()
    source["industry_effective_from"] = pd.to_datetime(source["industry_effective_from"])
    source["industry_effective_to"] = pd.to_datetime(source["industry_effective_to"])
    candidates = keys.merge(source, on="instrument", how="left")
    active = candidates.loc[
        candidates["industry_effective_from"].notna()
        & candidates["datetime"].ge(candidates["industry_effective_from"])
        & (
            candidates["industry_effective_to"].isna()
            | candidates["datetime"].le(candidates["industry_effective_to"])
        )
    ].copy()
    counts = active.groupby(["datetime", "instrument"]).size().rename("active_memberships")
    ambiguous = counts.loc[counts.gt(1)].reset_index()
    if not ambiguous.empty:
        active = active.merge(
            ambiguous[["datetime", "instrument"]].assign(_ambiguous=True),
            on=["datetime", "instrument"],
            how="left",
        )
        active = active.loc[active["_ambiguous"].isna()].drop(columns="_ambiguous")
    selected = active.drop_duplicates(["datetime", "instrument"])
    result = keys.merge(selected, on=["datetime", "instrument"], how="left", validate="one_to_one")
    return result, ambiguous


@dataclass(frozen=True)
class ExternalStyleCapability:
    historical_pit_market_cap_available: bool
    historical_pit_industry_available: bool
    external_style_extension_status: str


def unavailable_capability() -> ExternalStyleCapability:
    return ExternalStyleCapability(False, False, "unavailable_data")


def validate_external_style_frame(frame: pd.DataFrame) -> tuple[pd.DataFrame, ExternalStyleCapability]:
    missing = sorted(set(EXTERNAL_STYLE_COLUMNS) - set(frame.columns))
    if missing:
        raise ValueError(f"external PIT style frame missing columns: {missing}")
    result = frame[list(EXTERNAL_STYLE_COLUMNS)].copy()
    result["datetime"] = pd.to_datetime(result["datetime"], errors="raise").dt.normalize()
    result["instrument"] = result["instrument"].astype(str).str.upper()
    result["industry_effective_from"] = pd.to_datetime(
        result["industry_effective_from"], errors="coerce"
    ).dt.normalize()
    result["industry_effective_to"] = pd.to_datetime(
        result["industry_effective_to"], errors="coerce"
    ).dt.normalize()
    if result.duplicated(list(KEY_COLUMNS)).any():
        raise ValueError("external PIT style frame has duplicate datetime/instrument keys")
    invalid_intervals = (
        result["industry_effective_from"].notna()
        & result["industry_effective_to"].notna()
        & (result["industry_effective_from"] > result["industry_effective_to"])
    )
    if invalid_intervals.any():
        raise ValueError("external PIT style frame has reversed industry effective intervals")
    outside_effective_window = (
        result["industry_effective_from"].notna()
        & (result["datetime"] < result["industry_effective_from"])
    ) | (
        result["industry_effective_to"].notna()
        & (result["datetime"] > result["industry_effective_to"])
    )
    if outside_effective_window.any():
        raise ValueError("external PIT industry values escape their effective intervals")
    market_cap_available = result[["total_mv", "circ_mv"]].notna().any().any()
    industry_available = result[["sw_l1_code", "sw_l1_name"]].notna().any().any()
    if market_cap_available and (result[["total_mv", "circ_mv"]].apply(pd.to_numeric, errors="coerce") < 0).any().any():
        raise ValueError("external PIT market-cap values must be non-negative")
    status = "available" if market_cap_available or industry_available else "unavailable_data"
    return result.sort_values(list(KEY_COLUMNS)).reset_index(drop=True), ExternalStyleCapability(
        bool(market_cap_available), bool(industry_available), status
    )


def audit_external_style_capability(
    config: dict, *, project_root: Path
) -> pd.DataFrame:
    """Audit an optional external PIT input without making it a Core dependency."""
    value = config.get("input_path")
    if not value:
        capability = unavailable_capability()
        input_path = ""
        row_count = 0
    else:
        path = Path(value)
        path = path if path.is_absolute() else project_root / path
        if not path.is_file():
            capability = unavailable_capability()
            input_path = path.as_posix()
            row_count = 0
        else:
            if path.suffix.lower() in {".parquet", ".pq"}:
                frame = pd.read_parquet(path)
            elif path.suffix.lower() == ".csv":
                frame = pd.read_csv(path)
            else:
                raise ValueError("external PIT style input must be CSV or Parquet")
            validated, capability = validate_external_style_frame(frame)
            input_path = path.as_posix()
            row_count = len(validated)
    return pd.DataFrame(
        [
            {
                "historical_pit_market_cap_available": capability.historical_pit_market_cap_available,
                "historical_pit_industry_available": capability.historical_pit_industry_available,
                "external_style_extension_status": capability.external_style_extension_status,
                "required_for_core": bool(config.get("required_for_core", False)),
                "input_path": input_path,
                "row_count": row_count,
            }
        ]
    )
