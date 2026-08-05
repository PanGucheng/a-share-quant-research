from __future__ import annotations

import json
import shutil
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from research_validation.feature_matrix import canonical_hash, file_sha256

from .forward_hardening import verify_durable_candidate
from .forward_prediction_contract import (
    derive_label_start_contract,
    validate_forward_admission,
    validate_prediction_freeze_receipt,
    verify_prediction_git_binding,
)
from .preprocessing import WeightedPreprocessingFit


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


@dataclass(frozen=True)
class CandidateBundle:
    freeze: dict[str, Any]
    factors: tuple[str, ...]
    preprocessing: WeightedPreprocessingFit
    predictor: Any


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


def _default_predictor(model_path: Path) -> Any:
    import lightgbm as lgb

    return lgb.Booster(model_file=str(model_path))


def load_candidate_bundle(
    freeze_path: str | Path,
    *,
    repository_root: str | Path,
    predictor_loader: Callable[[Path], Any] = _default_predictor,
) -> CandidateBundle:
    freeze = _read_json(Path(freeze_path))
    if (
        freeze.get("candidate_status") != "provisional_research_only"
        or int(freeze.get("factor_count", 0)) != 52
        or freeze.get("production_model_selected") is not False
        or freeze.get("live_trading_ready") is not False
    ):
        raise ValueError("candidate freeze is not the frozen research-only candidate")
    model_path, preprocessing_path = verify_durable_candidate(
        freeze,
        repository_root=repository_root,
    )
    payload = _read_json(preprocessing_path)
    factors = tuple(str(value) for value in payload["feature_names"])
    if (
        len(factors) != 52
        or len(set(factors)) != 52
        or canonical_hash(list(factors)) != freeze["feature_order_sha256"]
    ):
        raise ValueError("frozen 52-factor order is invalid")
    preprocessing = WeightedPreprocessingFit(
        feature_names=factors,
        medians=np.asarray(payload["medians"], dtype=float),
        means=np.asarray(payload["means"], dtype=float),
        variances=np.asarray(payload["variances"], dtype=float),
    )
    if any(len(values) != 52 for values in (
        preprocessing.medians,
        preprocessing.means,
        preprocessing.variances,
    )):
        raise ValueError("frozen preprocessing width is not 52")
    predictor = predictor_loader(model_path)
    if hasattr(predictor, "feature_name"):
        model_features = tuple(str(value) for value in predictor.feature_name())
        if model_features != factors:
            raise ValueError("LightGBM model feature order differs from freeze")
    return CandidateBundle(
        freeze=freeze,
        factors=factors,
        preprocessing=preprocessing,
        predictor=predictor,
    )


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


def _record_date(state: dict[str, Any], field: str, value: str) -> None:
    values = sorted(set(str(item) for item in state[field]) | {value})
    state[field] = values


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


def finalize_prediction_commit(
    *,
    decision_date: str,
    prediction_commit_sha: str,
    trading_calendar_path: str | Path,
    freeze_path: str | Path,
    repository_root: str | Path,
    output_root: str | Path,
    state_path: str | Path,
) -> dict[str, Any]:
    repository = Path(repository_root).resolve()
    root = Path(output_root).resolve()
    target = root / "predictions" / decision_date
    receipt_path = target / "prediction_receipt.json"
    if receipt_path.exists():
        raise FileExistsError(f"prediction receipt already finalized for {decision_date}")
    pending = _read_json(target / "prediction_pending_receipt.json")
    freeze = _read_json(Path(freeze_path))
    state = load_forward_state(state_path, freeze)
    prediction_path = target / "prediction.csv"
    if file_sha256(prediction_path) != pending["prediction_sha256"]:
        raise ValueError("working prediction file differs from pending receipt")
    try:
        repo_path = prediction_path.resolve().relative_to(repository).as_posix()
    except ValueError as exc:
        raise ValueError("prediction path is outside the Git repository") from exc
    binding = verify_prediction_git_binding(
        repository=repository,
        prediction_commit_sha=prediction_commit_sha,
        prediction_repo_path=repo_path,
        prediction_sha256=pending["prediction_sha256"],
    )
    receipt = {
        **pending,
        "status": "pending_label",
        "prediction_repo_path": repo_path,
        "prediction_commit_sha": prediction_commit_sha,
        "prediction_commit_timestamp": binding["prediction_commit_timestamp"],
    }
    calendar = load_trading_calendar(trading_calendar_path)
    validated = validate_prediction_freeze_receipt(
        receipt,
        candidate_freeze_effective_time=freeze[
            "candidate_freeze_effective_time_utc"
        ],
        trading_calendar=calendar,
        repository=repository,
    )
    _atomic_json(receipt_path, receipt)
    state["pending_commit_dates"] = [
        value for value in state["pending_commit_dates"] if value != decision_date
    ]
    _record_date(state, "prediction_dates", decision_date)
    _record_date(state, "pending_label_dates", decision_date)
    state["last_prediction_date"] = decision_date
    state["official_forward_prediction_count"] = len(state["prediction_dates"])
    state["forward_data_waiting"] = False
    _atomic_json(Path(state_path), state)
    return {**validated, "status": "pending_label"}


def _daily_metrics(prediction: pd.DataFrame, labels: pd.DataFrame) -> dict[str, Any]:
    merged = prediction[["datetime", "instrument", "score"]].merge(
        labels[["datetime", "instrument", LABEL_COLUMN]],
        on=list(KEY_COLUMNS),
        how="left",
        validate="one_to_one",
    )
    valid = merged[["score", LABEL_COLUMN]].notna().all(axis=1)
    pairs = merged.loc[valid, ["score", LABEL_COLUMN]]
    rank_ic = float(pairs["score"].corr(pairs[LABEL_COLUMN], method="spearman"))
    pearson_ic = float(pairs["score"].corr(pairs[LABEL_COLUMN], method="pearson"))
    return {
        "datetime": str(merged["datetime"].iloc[0]),
        "daily_rank_ic": rank_ic,
        "daily_pearson_ic": pearson_ic,
        "coverage": float(valid.mean()),
        "valid_pair_count": int(valid.sum()),
        "positive_ic_indicator": bool(rank_ic > 0),
    }


def update_mature_forward_labels(
    *,
    as_of_date: str,
    label_dir: str | Path,
    trading_calendar_path: str | Path,
    freeze_path: str | Path,
    repository_root: str | Path,
    output_root: str | Path,
    state_path: str | Path,
    current_date: date | None = None,
) -> dict[str, Any]:
    as_of = date.fromisoformat(as_of_date)
    observed_today = current_date or datetime.now(ZoneInfo("Asia/Shanghai")).date()
    if as_of > observed_today:
        raise PermissionError("as_of_date cannot be later than the system date")
    freeze = _read_json(Path(freeze_path))
    state = load_forward_state(state_path, freeze)
    calendar = load_trading_calendar(trading_calendar_path)
    root = Path(output_root).resolve()
    metrics_path = root / "metrics" / "daily_metrics.csv"
    metrics = pd.read_csv(metrics_path) if metrics_path.is_file() else pd.DataFrame()
    matured: list[str] = []
    for decision_date in list(state["pending_label_dates"]):
        target = root / "predictions" / decision_date
        receipt = _read_json(target / "prediction_receipt.json")
        mature_date = date.fromisoformat(receipt["label_mature_date"])
        if as_of < mature_date:
            continue
        validate_prediction_freeze_receipt(
            receipt,
            candidate_freeze_effective_time=freeze[
                "candidate_freeze_effective_time_utc"
            ],
            trading_calendar=calendar,
            repository=repository_root,
        )
        prediction_path = target / "prediction.csv"
        if file_sha256(prediction_path) != receipt["prediction_sha256"]:
            raise ValueError(
                f"working prediction differs from committed receipt: {decision_date}"
            )
        label_path = Path(label_dir) / f"{decision_date}.csv"
        labels = pd.read_csv(label_path)
        if tuple(labels.columns) != (*KEY_COLUMNS, LABEL_COLUMN):
            raise ValueError(f"label schema is invalid for {decision_date}")
        labels["datetime"] = pd.to_datetime(
            labels["datetime"], errors="raise"
        ).dt.date.astype(str)
        labels["instrument"] = labels["instrument"].astype(str).str.upper()
        if labels.empty or not labels["datetime"].eq(decision_date).all():
            raise ValueError(f"label file has wrong decision date: {decision_date}")
        if labels.duplicated(list(KEY_COLUMNS)).any():
            raise ValueError(f"duplicate label keys: {decision_date}")
        labels[LABEL_COLUMN] = pd.to_numeric(labels[LABEL_COLUMN], errors="coerce")
        prediction = pd.read_csv(prediction_path)
        row = _daily_metrics(prediction, labels)
        row.update(
            {
                "candidate_freeze_id": freeze["forward_candidate_freeze_id"],
                "primary_confirmation_authority": False,
                "evidence_grade": EVIDENCE_GRADE,
            }
        )
        if metrics.empty:
            metrics = pd.DataFrame([row])
        elif decision_date not in metrics["datetime"].astype(str).tolist():
            metrics = pd.concat([metrics, pd.DataFrame([row])], ignore_index=True)
        matured.append(decision_date)
    if matured:
        metrics = metrics.sort_values("datetime", kind="stable").reset_index(drop=True)
        _atomic_csv(metrics_path, metrics)
        state["pending_label_dates"] = [
            value for value in state["pending_label_dates"] if value not in matured
        ]
        for value in matured:
            _record_date(state, "mature_label_dates", value)
        _atomic_json(Path(state_path), state)
    return {
        "as_of_date": as_of_date,
        "matured_dates": matured,
        "pending_label_dates": state["pending_label_dates"],
        "primary_confirmation_complete": False,
    }
