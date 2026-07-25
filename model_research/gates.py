from __future__ import annotations

import csv
from collections.abc import Mapping
from pathlib import Path


RESEARCH_EXPERIMENT_CLASS = "post_observation_research"
BLOCKED_EXPERIMENT_CLASSES = frozenset(
    {"authoritative_oos", "production", "paper", "live"}
)
PROJECT_ROOT = Path(__file__).resolve().parents[1]
RESEARCH_MODEL_PROTOCOL_READINESS = (
    PROJECT_ROOT
    / "outputs"
    / "research_model_protocol_v1"
    / "current"
    / "readiness_summary.csv"
)


class ModelScopeBlockedError(RuntimeError):
    """Raised when the scoped model protocol does not authorize an action."""


def _as_bool(value: object, *, field: str) -> bool:
    if isinstance(value, bool):
        return value
    normalized = str(value).strip().lower()
    if normalized in {"true", "1", "yes"}:
        return True
    if normalized in {"false", "0", "no"}:
        return False
    raise ValueError(f"{field} must be boolean, got {value!r}")


def model_scope_blockers(
    readiness: Mapping[str, object],
    *,
    experiment_class: str | None,
    operation: str = "training",
) -> list[str]:
    normalized_class = str(experiment_class or "").strip().lower()
    if not normalized_class:
        return ["experiment_class_unspecified"]
    if normalized_class in BLOCKED_EXPERIMENT_CLASSES:
        return [f"experiment_class_blocked:{normalized_class}"]
    if normalized_class != RESEARCH_EXPERIMENT_CLASS:
        return [f"experiment_class_unknown:{normalized_class}"]

    required = {
        "research_model_protocol_ready",
        "research_model_input_ready",
        "research_model_training_ready",
        "research_model_hard_stop_active",
        "production_model_hard_stop_active",
        "production_model_selected",
    }
    missing = sorted(required - set(readiness))
    if missing:
        return [f"research_model_readiness_missing:{','.join(missing)}"]

    blockers: list[str] = []
    for field in (
        "research_model_protocol_ready",
        "research_model_input_ready",
        "research_model_training_ready",
    ):
        if not _as_bool(readiness[field], field=field):
            blockers.append(f"{field}=false")
    if _as_bool(
        readiness["research_model_hard_stop_active"],
        field="research_model_hard_stop_active",
    ):
        blockers.append("research_model_hard_stop_active=true")
    if not _as_bool(
        readiness["production_model_hard_stop_active"],
        field="production_model_hard_stop_active",
    ):
        blockers.append("production_model_hard_stop_active=false")
    if _as_bool(
        readiness["production_model_selected"],
        field="production_model_selected",
    ):
        blockers.append("production_model_selected=true")
    if operation not in {"input_audit", "canary", "training", "prediction"}:
        blockers.append(f"operation_unknown:{operation}")
    return blockers


def assert_model_scope_allowed(
    readiness: Mapping[str, object],
    *,
    experiment_class: str | None,
    operation: str = "training",
) -> None:
    blockers = model_scope_blockers(
        readiness,
        experiment_class=experiment_class,
        operation=operation,
    )
    if blockers:
        raise ModelScopeBlockedError(
            "model scope blocked: " + "; ".join(blockers)
        )


def assert_research_model_entry_file(
    readiness_path: Path = RESEARCH_MODEL_PROTOCOL_READINESS,
    *,
    experiment_class: str | None,
    operation: str = "training",
) -> None:
    if not readiness_path.is_file():
        raise ModelScopeBlockedError(
            f"model scope blocked: missing scoped readiness: {readiness_path}"
        )
    with readiness_path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != 1:
        raise ModelScopeBlockedError(
            f"model scope blocked: scoped readiness rows={len(rows)}"
        )
    assert_model_scope_allowed(
        rows[0],
        experiment_class=experiment_class,
        operation=operation,
    )
