from __future__ import annotations

import json
import uuid
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Mapping

import pandas as pd

from .forward_prediction_contract import derive_label_start_contract


RAW_COLUMNS = (
    "datetime",
    "instrument",
    "$open",
    "$high",
    "$low",
    "$close",
    "$volume",
    "$amount",
)
KEY_COLUMNS = ("datetime", "instrument")
LABEL_COLUMN = "label_20d_t1"
EVIDENCE_GRADE = "personal_research_grade"


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _atomic_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex[:8]}.tmp")
    temporary.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
            default=str,
        )
        + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _atomic_csv(path: Path, frame: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex[:8]}.tmp")
    frame.to_csv(temporary, index=False, lineterminator="\n")
    temporary.replace(path)


def load_trading_calendar(path: str | Path) -> tuple[date, ...]:
    values = tuple(
        date.fromisoformat(line.strip())
        for line in Path(path).read_text(encoding="utf-8-sig").splitlines()
        if line.strip()
    )
    if not values or values != tuple(sorted(set(values))):
        raise ValueError("trading calendar must be nonempty, unique, and sorted")
    return values


def derive_label_window(
    decision_date: object,
    trading_calendar: tuple[date, ...],
    *,
    holding_days: int = 20,
) -> dict[str, str]:
    start = derive_label_start_contract(
        decision_date=decision_date,
        trading_calendar=trading_calendar,
    )
    decision = date.fromisoformat(str(decision_date))
    try:
        position = trading_calendar.index(decision)
    except ValueError as exc:
        raise PermissionError(
            "decision_date is not in authoritative trading calendar"
        ) from exc
    mature_position = position + 1 + int(holding_days)
    if mature_position >= len(trading_calendar):
        raise PermissionError(
            "trading calendar does not cover the full label maturity window"
        )
    return {
        **start,
        "label_mature_date": trading_calendar[mature_position].isoformat(),
    }


def initial_forward_state(freeze: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "evidence_grade": EVIDENCE_GRADE,
        "candidate_freeze_id": freeze["forward_candidate_freeze_id"],
        "model_sha256": freeze["model_binary_sha256"],
        "preprocessing_sha256": freeze["preprocessing_sha256"],
        "feature_order_sha256": freeze["feature_order_sha256"],
        "last_raw_date": None,
        "last_feature_date": None,
        "last_prediction_date": None,
        "prediction_dates": [],
        "pending_commit_dates": [],
        "pending_label_dates": [],
        "mature_label_dates": [],
        "dry_run_dates": [],
        "failed_dates": [],
        "official_forward_prediction_count": 0,
        "forward_pipeline_code_ready": True,
        "single_day_feature_pipeline_ready": True,
        "single_day_prediction_pipeline_ready": True,
        "label_maturity_tracker_ready": True,
        "duplicate_prediction_protection_ready": True,
        "frozen_model_hash_valid": True,
        "frozen_feature_order_valid": True,
        "prediction_stage_label_read_count": 0,
        "forward_data_waiting": True,
        "primary_confirmation_complete": False,
        "production_model_selected": False,
        "live_trading_ready": False,
    }


def load_forward_state(path: str | Path, freeze: Mapping[str, Any]) -> dict[str, Any]:
    target = Path(path)
    state = _read_json(target) if target.is_file() else initial_forward_state(freeze)
    for field, expected in (
        ("candidate_freeze_id", freeze["forward_candidate_freeze_id"]),
        ("model_sha256", freeze["model_binary_sha256"]),
        ("preprocessing_sha256", freeze["preprocessing_sha256"]),
        ("feature_order_sha256", freeze["feature_order_sha256"]),
    ):
        if state.get(field) != expected:
            raise ValueError(f"forward state {field} differs from candidate freeze")
    return state


def record_forward_failure(
    *,
    decision_date: str,
    error: Exception,
    dry_run: bool,
    freeze_path: str | Path,
    state_path: str | Path,
) -> None:
    """Record an operational failure without touching any prediction payload."""

    freeze = _read_json(Path(freeze_path))
    state = load_forward_state(state_path, freeze)
    previous = [
        item
        for item in state["failed_dates"]
        if str(item.get("decision_date")) != decision_date
    ]
    previous.append(
        {
            "decision_date": decision_date,
            "mode": "dry_run" if dry_run else "official",
            "error_type": type(error).__name__,
            "error": str(error),
            "failed_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    state["failed_dates"] = sorted(
        previous, key=lambda item: str(item["decision_date"])
    )
    _atomic_json(Path(state_path), state)


def _record_date(state: dict[str, Any], field: str, value: str) -> None:
    values = sorted(set(str(item) for item in state[field]) | {value})
    state[field] = values
