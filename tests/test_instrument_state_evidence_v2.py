from __future__ import annotations

import pandas as pd
import pytest

from qlib_integration.instrument_state_evidence import (
    classify_available_phase,
    detect_authoritative_conflicts,
    evidence_cache_key,
    executable_disposition,
    trading_permissions,
    validate_evidence_frame,
)


def evidence(**overrides: object) -> pd.DataFrame:
    row: dict[str, object] = {
        "instrument": "SZ000413",
        "state_type": "suspension",
        "state_value": "full_day",
        "effective_from": "2024-08-15",
        "published_at": "2024-08-14",
        "publication_precision": "date",
        "source_id": "szse_announcement",
        "source_tier": "tier_0",
        "evidence_id": "event-1",
        "authoritative": True,
    }
    row.update(overrides)
    return pd.DataFrame([row])


def test_previous_date_publication_is_before_open() -> None:
    assert (
        classify_available_phase(
            published_at="2024-08-14",
            effective_date="2024-08-15",
            publication_precision="date",
        )
        == "before_open"
    )


def test_same_date_without_time_is_unknown() -> None:
    assert (
        classify_available_phase(
            published_at="2024-08-15",
            effective_date="2024-08-15",
            publication_precision="date",
        )
        == "unknown"
    )


def test_timestamp_after_conservative_cutoff_is_after_open() -> None:
    assert (
        classify_available_phase(
            published_at="2024-08-15 09:05:00+08:00",
            effective_date="2024-08-15",
            publication_precision="timestamp",
        )
        == "after_open"
    )


def test_tier_one_cannot_be_authoritative() -> None:
    issues = validate_evidence_frame(evidence(source_tier="tier_1"))
    assert "non_tier_0_marked_authoritative" in issues


def test_conflicting_tier_zero_events_are_detected() -> None:
    frame = pd.concat(
        [
            evidence(),
            evidence(
                state_value="none",
                evidence_id="event-2",
            ),
        ],
        ignore_index=True,
    )
    conflicts = detect_authoritative_conflicts(frame)
    assert len(conflicts) == 1
    assert int(conflicts.iloc[0]["value_count"]) == 2


@pytest.mark.parametrize("state_type", ["suspension", "listing_termination"])
def test_suspension_or_termination_never_creates_synthetic_fill(
    state_type: str,
) -> None:
    state_value = "full_day" if state_type == "suspension" else "terminated"
    result = trading_permissions(state_type=state_type, state_value=state_value)
    assert not result["can_buy"]
    assert not result["can_sell"]
    assert not result["synthetic_fill_allowed"]


def test_listing_termination_is_not_executable_disposition() -> None:
    assert not executable_disposition(
        {
            "state_type": "listing_termination",
            "source_tier": "tier_0",
            "available_phase": "before_open",
            "cash_per_share": 0.37,
            "evidence_id": "termination",
        }
    )


def test_only_tier_zero_before_open_cash_disposition_is_executable() -> None:
    payload = {
        "state_type": "asset_disposition",
        "source_tier": "tier_0",
        "available_phase": "before_open",
        "cash_per_share": 0.12,
        "evidence_id": "cash-event",
    }
    assert executable_disposition(payload)
    assert not executable_disposition({**payload, "source_tier": "tier_1"})
    assert not executable_disposition({**payload, "available_phase": "unknown"})


def test_raw_snapshot_hash_is_part_of_evidence_cache_key() -> None:
    event = evidence().iloc[0].to_dict()
    assert evidence_cache_key(event, "a" * 64) != evidence_cache_key(event, "b" * 64)
