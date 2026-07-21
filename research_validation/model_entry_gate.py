from __future__ import annotations

from pathlib import Path

import pandas as pd


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
) -> list[str]:
    if len(readiness) != 1:
        return [f"readiness_summary must contain exactly one row, got {len(readiness)}"]

    required_readiness = {
        "selection_integrity_status",
        "model_entry_hard_stop_active",
        "feature_selection_holdout_clean",
        "clustering_holdout_clean",
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
) -> None:
    blockers = model_entry_blockers(readiness, selections, selection_name=selection_name)
    if blockers:
        raise ModelEntryBlockedError("model entry blocked: " + "; ".join(blockers))


def assert_model_entry_files(
    readiness_path: Path,
    selection_status_path: Path,
    *,
    selection_name: str,
) -> None:
    if not readiness_path.is_file():
        raise ModelEntryBlockedError(f"model entry blocked: missing readiness summary: {readiness_path}")
    if not selection_status_path.is_file():
        raise ModelEntryBlockedError(f"model entry blocked: missing selection registry: {selection_status_path}")
    assert_model_entry_allowed(
        pd.read_csv(readiness_path),
        pd.read_csv(selection_status_path),
        selection_name=selection_name,
    )
