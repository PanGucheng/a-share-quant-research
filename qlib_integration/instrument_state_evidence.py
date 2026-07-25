from __future__ import annotations

from datetime import datetime, time
import hashlib
import json
from typing import Any
from zoneinfo import ZoneInfo

import pandas as pd


REQUIRED_EVIDENCE_COLUMNS = {
    "instrument",
    "state_type",
    "state_value",
    "effective_from",
    "published_at",
    "publication_precision",
    "source_id",
    "source_tier",
    "evidence_id",
}
VALID_SOURCE_TIERS = {"tier_0", "tier_1", "tier_2", "tier_3"}
VALID_PUBLICATION_PRECISIONS = {"timestamp", "date", "unknown"}
VALID_STATE_TYPES = {
    "st",
    "suspension",
    "resumption",
    "listing_termination",
    "asset_disposition",
}


def evidence_cache_key(
    normalized_event: dict[str, Any], raw_snapshot_sha256: str
) -> str:
    """Bind a normalized event to the exact raw evidence payload."""

    payload = {
        "normalized_event": normalized_event,
        "raw_snapshot_sha256": str(raw_snapshot_sha256),
        "cache_schema": "historical_instrument_state_evidence_v2",
    }
    return hashlib.sha256(
        json.dumps(
            payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str
        ).encode("utf-8")
    ).hexdigest()


def classify_available_phase(
    *,
    published_at: Any,
    effective_date: Any,
    publication_precision: str,
    timezone: str = "Asia/Shanghai",
    before_open_cutoff: str = "09:00:00",
) -> str:
    """Classify historical availability without inventing an intraday timestamp."""

    precision = str(publication_precision).strip().lower()
    if precision not in VALID_PUBLICATION_PRECISIONS:
        raise ValueError(f"invalid publication_precision: {publication_precision!r}")
    if precision == "unknown" or pd.isna(published_at):
        return "unknown"

    published = pd.Timestamp(published_at)
    effective = pd.Timestamp(effective_date).normalize()
    if precision == "date":
        if published.normalize() < effective:
            return "before_open"
        return "unknown"

    zone = ZoneInfo(timezone)
    if published.tzinfo is None:
        published = published.tz_localize(zone)
    else:
        published = published.tz_convert(zone)
    cutoff_parts = [int(item) for item in before_open_cutoff.split(":")]
    cutoff = pd.Timestamp(
        datetime.combine(effective.date(), time(*cutoff_parts), tzinfo=zone)
    )
    return "before_open" if published <= cutoff else "after_open"


def validate_evidence_frame(frame: pd.DataFrame) -> list[str]:
    issues: list[str] = []
    missing = sorted(REQUIRED_EVIDENCE_COLUMNS - set(frame.columns))
    if missing:
        return [f"missing_columns:{'|'.join(missing)}"]
    if frame.empty:
        return ["empty_evidence"]
    invalid_tiers = sorted(set(frame["source_tier"].astype(str)) - VALID_SOURCE_TIERS)
    if invalid_tiers:
        issues.append(f"invalid_source_tiers:{'|'.join(invalid_tiers)}")
    invalid_types = sorted(set(frame["state_type"].astype(str)) - VALID_STATE_TYPES)
    if invalid_types:
        issues.append(f"invalid_state_types:{'|'.join(invalid_types)}")
    invalid_precision = sorted(
        set(frame["publication_precision"].astype(str))
        - VALID_PUBLICATION_PRECISIONS
    )
    if invalid_precision:
        issues.append(f"invalid_publication_precision:{'|'.join(invalid_precision)}")
    if frame["evidence_id"].astype(str).duplicated().any():
        issues.append("duplicate_evidence_id")
    authoritative = frame.get(
        "authoritative", pd.Series(False, index=frame.index, dtype=bool)
    ).astype(bool)
    if (authoritative & ~frame["source_tier"].eq("tier_0")).any():
        issues.append("non_tier_0_marked_authoritative")
    return issues


def detect_authoritative_conflicts(frame: pd.DataFrame) -> pd.DataFrame:
    issues = validate_evidence_frame(frame)
    if issues:
        raise ValueError(";".join(issues))
    tier_zero = frame.loc[frame["source_tier"].eq("tier_0")].copy()
    if tier_zero.empty:
        return pd.DataFrame(
            columns=["instrument", "state_type", "effective_from", "value_count"]
        )
    conflicts = (
        tier_zero.groupby(
            ["instrument", "state_type", "effective_from"], as_index=False
        )["state_value"]
        .nunique()
        .rename(columns={"state_value": "value_count"})
    )
    return conflicts.loc[conflicts["value_count"].gt(1)].reset_index(drop=True)


def trading_permissions(
    *, state_type: str, state_value: Any
) -> dict[str, object]:
    state_type = str(state_type)
    if state_type == "suspension" and str(state_value) == "full_day":
        return {
            "can_buy": False,
            "can_sell": False,
            "synthetic_fill_allowed": False,
        }
    if state_type == "listing_termination":
        return {
            "can_buy": False,
            "can_sell": False,
            "synthetic_fill_allowed": False,
        }
    return {
        "can_buy": True,
        "can_sell": True,
        "synthetic_fill_allowed": False,
    }


def executable_disposition(evidence: dict[str, Any]) -> bool:
    """Only a Tier-0, before-open asset disposition can authorize cash action."""

    required = {
        "state_type",
        "source_tier",
        "available_phase",
        "cash_per_share",
        "evidence_id",
    }
    if required - set(evidence):
        return False
    if evidence["state_type"] != "asset_disposition":
        return False
    if evidence["source_tier"] != "tier_0":
        return False
    if evidence["available_phase"] != "before_open":
        return False
    cash_per_share = pd.to_numeric(evidence["cash_per_share"], errors="coerce")
    return bool(pd.notna(cash_per_share) and float(cash_per_share) >= 0)
