from __future__ import annotations

import shutil
import uuid
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Callable

import numpy as np
import pandas as pd

from research_validation.feature_matrix import file_sha256

from .forward_binding import (
    _default_predictor,
    load_candidate_bundle,
)
from .forward_prediction_contract import validate_forward_admission
from .forward_state import (
    EVIDENCE_GRADE,
    KEY_COLUMNS,
    RAW_COLUMNS,
    _atomic_csv,
    _atomic_json,
    _record_date,
    derive_label_window,
    load_forward_state,
    load_trading_calendar,
)


def _normalize_raw(path: Path, decision: date) -> pd.DataFrame:
    raw = pd.read_csv(path)
    if tuple(raw.columns) != RAW_COLUMNS:
        raise ValueError("raw input schema/order is invalid")
    raw["datetime"] = pd.to_datetime(raw["datetime"], errors="raise").dt.date
    raw["instrument"] = raw["instrument"].astype(str).str.upper()
    if raw.empty or not raw["datetime"].eq(decision).all():
        raise ValueError("raw input must contain exactly the requested decision date")
    if raw.duplicated(list(KEY_COLUMNS)).any():
        raise ValueError("raw input contains duplicate date-instrument keys")
    numeric = list(RAW_COLUMNS[2:])
    raw[numeric] = raw[numeric].apply(pd.to_numeric, errors="coerce")
    if raw[numeric].isna().any().any():
        raise ValueError("raw input has incomplete required OHLCVA values")
    return raw.sort_values(list(KEY_COLUMNS), kind="stable").reset_index(drop=True)


def _normalize_features(
    path: Path,
    decision: date,
    factors: tuple[str, ...],
) -> pd.DataFrame:
    frame = pd.read_csv(path)
    if tuple(frame.columns) != (*KEY_COLUMNS, *factors):
        raise ValueError("feature snapshot does not match exact frozen factor order")
    frame["datetime"] = pd.to_datetime(frame["datetime"], errors="raise").dt.date
    frame["instrument"] = frame["instrument"].astype(str).str.upper()
    if frame.empty or not frame["datetime"].eq(decision).all():
        raise ValueError("feature snapshot must contain exactly the requested date")
    if frame.duplicated(list(KEY_COLUMNS)).any():
        raise ValueError("feature snapshot contains duplicate keys")
    frame[list(factors)] = frame[list(factors)].apply(pd.to_numeric, errors="coerce")
    values = frame[list(factors)].replace([np.inf, -np.inf], np.nan)
    if values.isna().all(axis=1).any():
        raise ValueError("feature snapshot contains all-NaN rows")
    frame[list(factors)] = values
    return frame.sort_values(list(KEY_COLUMNS), kind="stable").reset_index(drop=True)


def run_single_day_prediction(
    *,
    decision_date: str,
    raw_path: str | Path,
    feature_path: str | Path,
    raw_snapshot_first_seen_at: str,
    trading_calendar_path: str | Path,
    freeze_path: str | Path,
    repository_root: str | Path,
    output_root: str | Path,
    state_path: str | Path,
    dry_run: bool,
    force_dev: bool = False,
    feature_snapshot_created_at: str | None = None,
    prediction_created_at: str | None = None,
    predictor_loader: Callable[[Path], Any] = _default_predictor,
) -> dict[str, Any]:
    decision = date.fromisoformat(decision_date)
    bundle = load_candidate_bundle(
        freeze_path,
        repository_root=repository_root,
        predictor_loader=predictor_loader,
    )
    state = load_forward_state(state_path, bundle.freeze)
    if force_dev and not dry_run:
        raise PermissionError("--force-dev is forbidden for official forward runs")
    calendar = load_trading_calendar(trading_calendar_path)
    label_window = derive_label_window(decision_date, calendar)
    first_seen = datetime.fromisoformat(
        raw_snapshot_first_seen_at.replace("Z", "+00:00")
    )
    if first_seen.tzinfo is None:
        raise ValueError("raw_snapshot_first_seen_at must be timezone-aware")
    if not dry_run:
        validate_forward_admission(
            decision_date=decision_date,
            raw_snapshot_first_seen_at=raw_snapshot_first_seen_at,
            candidate_freeze_effective_time=bundle.freeze[
                "candidate_freeze_effective_time_utc"
            ],
        )
    raw = _normalize_raw(Path(raw_path), decision)
    features = _normalize_features(Path(feature_path), decision, bundle.factors)
    raw_instruments = set(raw["instrument"])
    feature_instruments = set(features["instrument"])
    missing_raw = sorted(feature_instruments - raw_instruments)
    if missing_raw:
        raise ValueError(
            "raw snapshot is missing frozen feature instruments: "
            f"{missing_raw[:10]}"
        )
    created = datetime.fromisoformat(
        (prediction_created_at or datetime.now(timezone.utc).isoformat()).replace(
            "Z", "+00:00"
        )
    )
    feature_created = datetime.fromisoformat(
        (feature_snapshot_created_at or created.isoformat()).replace("Z", "+00:00")
    )
    if created.tzinfo is None or feature_created.tzinfo is None:
        raise ValueError("feature and prediction timestamps must be timezone-aware")
    if feature_created < first_seen or created < feature_created:
        raise PermissionError("feature/prediction timestamp ordering is invalid")
    cutoff = datetime.fromisoformat(label_window["label_start_cutoff"])
    if not dry_run and created >= cutoff:
        raise PermissionError("prediction was created after label-start cutoff")
    transformed = bundle.preprocessing.transform(
        features[list(bundle.factors)].to_numpy(dtype=float)
    )
    scores = np.asarray(bundle.predictor.predict(transformed), dtype=float)
    if scores.shape != (len(features),) or not np.isfinite(scores).all():
        raise ValueError("model returned invalid single-day predictions")
    prediction = pd.DataFrame(
        {
            "datetime": [decision_date] * len(features),
            "instrument": features["instrument"],
            "score": scores,
            "model_sha256": bundle.freeze["model_binary_sha256"],
            "feature_order_sha256": bundle.freeze["feature_order_sha256"],
            "candidate_freeze_id": bundle.freeze["forward_candidate_freeze_id"],
            "prediction_created_at": created.isoformat(),
        }
    )
    root = Path(output_root).resolve()
    if not dry_run:
        try:
            root.relative_to(Path(repository_root).resolve())
        except ValueError as exc:
            raise ValueError(
                "official prediction output must be inside the Git repository"
            ) from exc
    category = "dry_run" if dry_run else "predictions"
    target = root / category / decision_date
    if target.exists() and not (dry_run and force_dev):
        raise FileExistsError(f"prediction already exists for {decision_date}")
    if target.exists():
        shutil.rmtree(target)
    staging = target.parent / f".{decision_date}.staging-{uuid.uuid4().hex[:8]}"
    staging.mkdir(parents=True, exist_ok=False)
    try:
        prediction_path = staging / "prediction.csv"
        _atomic_csv(prediction_path, prediction)
        shutil.copy2(raw_path, staging / "raw.csv")
        shutil.copy2(feature_path, staging / "features.csv")
        pending = {
            "schema_version": 1,
            "evidence_grade": EVIDENCE_GRADE,
            "evidence_eligible": not dry_run,
            "status": "dry_run_complete" if dry_run else "pending_commit",
            "decision_date": decision_date,
            "raw_data_path": (target / "raw.csv").as_posix(),
            "raw_snapshot_first_seen_at": first_seen.isoformat(),
            "raw_data_sha256": file_sha256(Path(raw_path)),
            "data_completeness_status": "pass",
            "feature_snapshot_created_at": feature_created.isoformat(),
            "feature_snapshot_sha256": file_sha256(Path(feature_path)),
            "factor_count": 52,
            "feature_order_sha256": bundle.freeze["feature_order_sha256"],
            "prediction_created_at": created.isoformat(),
            "prediction_sha256": file_sha256(prediction_path),
            "label_start_date": label_window["label_start_date"],
            "label_start_cutoff": label_window["label_start_cutoff"],
            "label_mature_date": label_window["label_mature_date"],
            "trading_calendar_sha256": label_window[
                "trading_calendar_sha256"
            ],
            "label_read_count_at_prediction": 0,
            "candidate_freeze_id": bundle.freeze["forward_candidate_freeze_id"],
            "model_sha256": bundle.freeze["model_binary_sha256"],
            "preprocessing_sha256": bundle.freeze["preprocessing_sha256"],
            "production_model_selected": False,
            "live_trading_ready": False,
        }
        _atomic_json(staging / "prediction_pending_receipt.json", pending)
        target.parent.mkdir(parents=True, exist_ok=True)
        staging.replace(target)
    except Exception:
        if staging.exists():
            shutil.rmtree(staging)
        raise
    state["last_raw_date"] = decision_date
    state["last_feature_date"] = decision_date
    if dry_run:
        _record_date(state, "dry_run_dates", decision_date)
    else:
        _record_date(state, "pending_commit_dates", decision_date)
    _atomic_json(Path(state_path), state)
    return {
        "status": "dry_run_complete" if dry_run else "pending_commit",
        "decision_date": decision_date,
        "prediction_path": (target / "prediction.csv").as_posix(),
        "prediction_sha256": pending["prediction_sha256"],
        "label_read_count_at_prediction": 0,
        "evidence_eligible": not dry_run,
    }
