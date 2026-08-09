from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

import numpy as np

from research_validation.feature_matrix import canonical_hash, file_sha256

from .forward_hardening import verify_durable_candidate
from .forward_prediction_contract import (
    validate_prediction_freeze_receipt,
    verify_prediction_git_binding,
)
from .forward_state import (
    _atomic_json,
    _read_json,
    _record_date,
    load_forward_state,
    load_trading_calendar,
)
from .preprocessing import WeightedPreprocessingFit


@dataclass(frozen=True)
class CandidateBundle:
    freeze: dict[str, Any]
    factors: tuple[str, ...]
    preprocessing: WeightedPreprocessingFit
    predictor: Any


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
    if any(
        len(values) != 52
        for values in (
            preprocessing.medians,
            preprocessing.means,
            preprocessing.variances,
        )
    ):
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
