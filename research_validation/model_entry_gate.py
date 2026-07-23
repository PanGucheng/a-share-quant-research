from __future__ import annotations

from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ACCURACY_CORRECTION_READINESS = (
    PROJECT_ROOT / "outputs" / "accuracy_correction_v1" / "current" / "readiness_summary.csv"
)


class ModelEntryBlockedError(RuntimeError):
    """Raised when machine-readable selection integrity does not authorize training."""


def _as_bool(value: object, *, field: str) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"true", "1", "yes"}:
        return True
    if text in {"false", "0", "no"}:
        return False
    raise ValueError(f"{field} must be boolean, got {value!r}")


def model_entry_blockers(
    readiness: pd.DataFrame,
    selections: pd.DataFrame,
    *,
    selection_name: str,
    accuracy_correction: pd.DataFrame | None = None,
) -> list[str]:
    if accuracy_correction is None:
        if not ACCURACY_CORRECTION_READINESS.is_file():
            return [
                "missing repository accuracy-correction readiness: "
                f"{ACCURACY_CORRECTION_READINESS}"
            ]
        accuracy_correction = pd.read_csv(ACCURACY_CORRECTION_READINESS)
    if len(accuracy_correction) != 1:
        return [
            "accuracy-correction readiness must contain exactly one row, "
            f"got {len(accuracy_correction)}"
        ]

    required_accuracy_fields = {
        "selection_holdout_integrity_ready",
        "universe_lifecycle_v2_ready",
        "research_formula_accuracy_ready",
        "matrix_v4_lifecycle_clean",
        "pairwise_ic_ready",
        "model_research_ready",
        "execution_semantics_accuracy_ready",
        "market_cache_v2_ready",
        "future_market_field_count",
        "stale_policy_valid",
        "authoritative_oos_execution_ready",
        "core_model_ready",
        "pr5_model_training_ready",
        "model_training_started",
        "model_entry_hard_stop_active",
        "accuracy_correction_status",
    }
    missing_accuracy = sorted(required_accuracy_fields - set(accuracy_correction.columns))
    if missing_accuracy:
        return [f"accuracy-correction readiness missing fields: {missing_accuracy}"]

    accuracy = accuracy_correction.iloc[0]
    accuracy_blockers: list[str] = []
    if str(accuracy["accuracy_correction_status"]).strip().lower() != "complete":
        accuracy_blockers.append(
            f"accuracy_correction_status={accuracy['accuracy_correction_status']!r}"
        )
    for field in [
        "selection_holdout_integrity_ready",
        "universe_lifecycle_v2_ready",
        "research_formula_accuracy_ready",
        "matrix_v4_lifecycle_clean",
        "pairwise_ic_ready",
        "model_research_ready",
        "execution_semantics_accuracy_ready",
        "market_cache_v2_ready",
        "stale_policy_valid",
        "authoritative_oos_execution_ready",
        "core_model_ready",
        "pr5_model_training_ready",
    ]:
        if not _as_bool(accuracy[field], field=field):
            accuracy_blockers.append(f"{field}=false")
    try:
        future_market_field_count = int(accuracy["future_market_field_count"])
    except (TypeError, ValueError):
        accuracy_blockers.append(
            "future_market_field_count must be an integer, "
            f"got {accuracy['future_market_field_count']!r}"
        )
    else:
        if future_market_field_count != 0:
            accuracy_blockers.append(
                f"future_market_field_count={future_market_field_count}"
            )
    if _as_bool(
        accuracy["model_entry_hard_stop_active"],
        field="model_entry_hard_stop_active",
    ):
        accuracy_blockers.append("model_entry_hard_stop_active=true")
    if _as_bool(accuracy["model_training_started"], field="model_training_started"):
        accuracy_blockers.append("model_training_started=true")
    if accuracy_blockers:
        return accuracy_blockers

    if len(readiness) != 1:
        return [f"readiness_summary must contain exactly one row, got {len(readiness)}"]

    required_readiness = {
        "selection_integrity_status",
        "model_entry_hard_stop_active",
        "feature_selection_holdout_clean",
        "clustering_holdout_clean",
        "fdr_family_semantics_valid",
        "fdr_artifact_consumed",
        "raw_input_provenance_complete",
        "split_allowlists_frozen",
        "core_model_ready",
        "pr5_model_training_ready",
        "model_training_started",
    }
    missing = sorted(required_readiness - set(readiness.columns))
    if missing:
        return [f"readiness_summary missing fields: {missing}"]

    row = readiness.iloc[0]
    blockers: list[str] = []
    if str(row["selection_integrity_status"]).strip().lower() != "ready":
        blockers.append(f"selection_integrity_status={row['selection_integrity_status']!r}")
    if _as_bool(row["model_entry_hard_stop_active"], field="model_entry_hard_stop_active"):
        blockers.append("model_entry_hard_stop_active=true")
    for field in [
        "feature_selection_holdout_clean",
        "clustering_holdout_clean",
        "fdr_family_semantics_valid",
        "fdr_artifact_consumed",
        "raw_input_provenance_complete",
        "split_allowlists_frozen",
        "core_model_ready",
        "pr5_model_training_ready",
    ]:
        if not _as_bool(row[field], field=field):
            blockers.append(f"{field}=false")
    if _as_bool(row["model_training_started"], field="model_training_started"):
        blockers.append("model_training_started=true")

    required_selection = {"selection_name", "selection_status", "model_input_allowed"}
    missing_selection = sorted(required_selection - set(selections.columns))
    if missing_selection:
        blockers.append(f"selection registry missing fields: {missing_selection}")
        return blockers
    matched = selections.loc[selections["selection_name"].astype(str).eq(selection_name)]
    if len(matched) != 1:
        blockers.append(f"selection_name={selection_name!r} matched {len(matched)} rows")
        return blockers
    selection = matched.iloc[0]
    if str(selection["selection_status"]).strip().lower() != "holdout_clean":
        blockers.append(f"selection_status={selection['selection_status']!r}")
    if not _as_bool(selection["model_input_allowed"], field="model_input_allowed"):
        blockers.append("model_input_allowed=false")
    return blockers


def assert_model_entry_allowed(
    readiness: pd.DataFrame,
    selections: pd.DataFrame,
    *,
    selection_name: str,
    accuracy_correction: pd.DataFrame | None = None,
) -> None:
    blockers = model_entry_blockers(
        readiness,
        selections,
        selection_name=selection_name,
        accuracy_correction=accuracy_correction,
    )
    if blockers:
        raise ModelEntryBlockedError("model entry blocked: " + "; ".join(blockers))


def assert_model_entry_files(
    readiness_path: Path,
    selection_status_path: Path,
    *,
    selection_name: str,
    accuracy_correction_path: Path = ACCURACY_CORRECTION_READINESS,
) -> None:
    if not readiness_path.is_file():
        raise ModelEntryBlockedError(f"model entry blocked: missing readiness summary: {readiness_path}")
    if not selection_status_path.is_file():
        raise ModelEntryBlockedError(f"model entry blocked: missing selection registry: {selection_status_path}")
    if not accuracy_correction_path.is_file():
        raise ModelEntryBlockedError(
            "model entry blocked: missing accuracy-correction readiness: "
            f"{accuracy_correction_path}"
        )
    assert_model_entry_allowed(
        pd.read_csv(readiness_path),
        pd.read_csv(selection_status_path),
        selection_name=selection_name,
        accuracy_correction=pd.read_csv(accuracy_correction_path),
    )
