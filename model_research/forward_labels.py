from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import pandas as pd

from research_validation.feature_matrix import file_sha256

from .forward_prediction_contract import validate_prediction_freeze_receipt
from .forward_state import (
    EVIDENCE_GRADE,
    KEY_COLUMNS,
    LABEL_COLUMN,
    _atomic_csv,
    _atomic_json,
    _read_json,
    _record_date,
    load_forward_state,
    load_trading_calendar,
)


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
