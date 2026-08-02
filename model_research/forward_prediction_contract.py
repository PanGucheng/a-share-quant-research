from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any, Mapping
from zoneinfo import ZoneInfo


SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
COMMIT_PATTERN = re.compile(r"^[0-9a-f]{40}$")
SHANGHAI = ZoneInfo("Asia/Shanghai")


def _aware_timestamp(value: object, *, field: str) -> datetime:
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field} must be timezone-aware")
    return parsed


def _date(value: object, *, field: str) -> date:
    try:
        return date.fromisoformat(str(value))
    except ValueError as exc:
        raise ValueError(f"{field} must be an ISO date") from exc


def validate_forward_admission(
    *,
    decision_date: object,
    raw_snapshot_first_seen_at: object,
    candidate_freeze_effective_time: object,
) -> dict[str, object]:
    """Fail closed against post-freeze downloads of already-historical dates."""

    decision = _date(decision_date, field="decision_date")
    first_seen = _aware_timestamp(
        raw_snapshot_first_seen_at, field="raw_snapshot_first_seen_at"
    )
    freeze = _aware_timestamp(
        candidate_freeze_effective_time,
        field="candidate_freeze_effective_time",
    )
    effective_local_date = freeze.astimezone(SHANGHAI).date()
    if decision <= effective_local_date:
        raise PermissionError(
            "decision_date is not after candidate freeze effective local date"
        )
    if first_seen <= freeze:
        raise PermissionError(
            "raw snapshot was not first seen after candidate freeze timestamp"
        )
    return {
        "decision_date": decision.isoformat(),
        "candidate_freeze_effective_date_asia_shanghai": (
            effective_local_date.isoformat()
        ),
        "raw_snapshot_first_seen_at": first_seen.isoformat(),
        "admission_status": "prospective_eligible",
    }


def validate_prediction_freeze_receipt(
    receipt: Mapping[str, Any],
    *,
    candidate_freeze_effective_time: object,
) -> dict[str, object]:
    """Validate immutable prediction creation and publication before t+1."""

    required = {
        "decision_date",
        "raw_snapshot_first_seen_at",
        "feature_snapshot_created_at",
        "prediction_created_at",
        "prediction_sha256",
        "prediction_commit_sha",
        "prediction_commit_timestamp",
        "label_start_date",
        "label_start_cutoff",
        "label_mature_date",
        "label_read_count_at_prediction",
        "candidate_freeze_id",
        "model_sha256",
        "preprocessing_sha256",
    }
    missing = sorted(required - set(receipt))
    if missing:
        raise ValueError(f"prediction freeze receipt missing fields: {missing}")
    admission = validate_forward_admission(
        decision_date=receipt["decision_date"],
        raw_snapshot_first_seen_at=receipt["raw_snapshot_first_seen_at"],
        candidate_freeze_effective_time=candidate_freeze_effective_time,
    )
    decision = _date(receipt["decision_date"], field="decision_date")
    label_start = _date(receipt["label_start_date"], field="label_start_date")
    label_mature = _date(receipt["label_mature_date"], field="label_mature_date")
    first_seen = _aware_timestamp(
        receipt["raw_snapshot_first_seen_at"],
        field="raw_snapshot_first_seen_at",
    )
    feature_created = _aware_timestamp(
        receipt["feature_snapshot_created_at"],
        field="feature_snapshot_created_at",
    )
    prediction_created = _aware_timestamp(
        receipt["prediction_created_at"], field="prediction_created_at"
    )
    commit_timestamp = _aware_timestamp(
        receipt["prediction_commit_timestamp"],
        field="prediction_commit_timestamp",
    )
    cutoff = _aware_timestamp(
        receipt["label_start_cutoff"], field="label_start_cutoff"
    )
    if not decision < label_start < label_mature:
        raise ValueError("label dates do not follow t < t+1 < t+21 ordering")
    if feature_created < first_seen:
        raise PermissionError("feature snapshot predates raw first-seen receipt")
    if prediction_created < feature_created:
        raise PermissionError("prediction predates feature snapshot")
    if prediction_created >= cutoff:
        raise PermissionError("prediction was created after label-start cutoff")
    if commit_timestamp >= cutoff:
        raise PermissionError("prediction was committed after label-start cutoff")
    if commit_timestamp < prediction_created:
        raise PermissionError("prediction commit predates prediction payload")
    if int(receipt["label_read_count_at_prediction"]) != 0:
        raise PermissionError("prediction stage read forward labels")
    if not SHA256_PATTERN.fullmatch(str(receipt["prediction_sha256"])):
        raise ValueError("prediction_sha256 is invalid")
    if not COMMIT_PATTERN.fullmatch(str(receipt["prediction_commit_sha"])):
        raise ValueError("prediction_commit_sha is invalid")
    for field in ("model_sha256", "preprocessing_sha256"):
        if not SHA256_PATTERN.fullmatch(str(receipt[field])):
            raise ValueError(f"{field} is invalid")
    if not str(receipt["candidate_freeze_id"]).startswith(
        "forward-candidate-freeze:"
    ):
        raise ValueError("candidate_freeze_id is invalid")
    return {
        **admission,
        "prediction_created_at": prediction_created.isoformat(),
        "prediction_commit_timestamp": commit_timestamp.isoformat(),
        "label_start_cutoff": cutoff.isoformat(),
        "prediction_freeze_status": "immutable_before_label_start",
    }
