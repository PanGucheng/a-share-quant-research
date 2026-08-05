from __future__ import annotations

import hashlib
import json
import os
import subprocess
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from model_research.forward_pipeline import (
    finalize_prediction_commit,
    load_candidate_bundle,
    record_forward_failure,
    run_single_day_prediction,
    update_mature_forward_labels,
)
from research_validation.feature_matrix import canonical_hash, file_sha256


class FakePredictor:
    def __init__(self, factors: tuple[str, ...]) -> None:
        self.factors = factors

    def feature_name(self) -> list[str]:
        return list(self.factors)

    def predict(self, values: np.ndarray) -> np.ndarray:
        return np.asarray(values, dtype=float).sum(axis=1)


def _git(repository: Path, *args: str, env: dict[str, str] | None = None) -> str:
    result = subprocess.run(
        ["git", "-C", str(repository), *args],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
    )
    return result.stdout.strip()


def _write_csv(path: Path, frame: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, lineterminator="\n")


@pytest.fixture()
def forward_fixture(tmp_path: Path) -> dict[str, object]:
    repository = tmp_path / "repo"
    repository.mkdir()
    _git(repository, "init")
    _git(repository, "config", "user.name", "Forward Test")
    _git(repository, "config", "user.email", "forward@example.invalid")
    factors = tuple(f"factor_{index:02d}" for index in range(52))
    asset_dir = repository / "artifacts/candidate"
    asset_dir.mkdir(parents=True)
    model_path = asset_dir / "model.txt"
    model_path.write_bytes(b"frozen-model")
    preprocessing_path = asset_dir / "preprocessing.json"
    preprocessing = {
        "algorithm": "stable_daily_equal_weighted_preprocessing_v1",
        "feature_names": list(factors),
        "medians": [0.0] * 52,
        "means": [0.0] * 52,
        "variances": [1.0] * 52,
        "preprocessing_artifact_id": "weighted-preprocessing:test",
    }
    preprocessing_path.write_text(json.dumps(preprocessing), encoding="utf-8")
    freeze = {
        "candidate_status": "provisional_research_only",
        "factor_count": 52,
        "feature_order_sha256": canonical_hash(list(factors)),
        "forward_candidate_freeze_id": "forward-candidate-freeze:" + "a" * 64,
        "candidate_freeze_effective_time_utc": "2026-08-02T14:33:38.772344+00:00",
        "model_binary_sha256": file_sha256(model_path),
        "model_size_bytes": model_path.stat().st_size,
        "model_storage_uri": "repo://artifacts/candidate/model.txt",
        "preprocessing_sha256": file_sha256(preprocessing_path),
        "preprocessing_size_bytes": preprocessing_path.stat().st_size,
        "preprocessing_storage_uri": "repo://artifacts/candidate/preprocessing.json",
        "production_model_selected": False,
        "live_trading_ready": False,
    }
    freeze_path = repository / "freeze.json"
    freeze_path.write_text(json.dumps(freeze), encoding="utf-8")
    calendar = pd.bdate_range("2026-08-03", periods=35)
    calendar_path = repository / "calendar.txt"
    calendar_path.write_text(
        "\n".join(value.date().isoformat() for value in calendar) + "\n",
        encoding="utf-8",
    )
    instruments = ["SH600000", "SZ000001", "SH600519"]
    raw = pd.DataFrame(
        {
            "datetime": ["2026-08-03"] * 3,
            "instrument": instruments,
            "$open": [10.0, 20.0, 30.0],
            "$high": [10.5, 20.5, 30.5],
            "$low": [9.5, 19.5, 29.5],
            "$close": [10.2, 20.2, 30.2],
            "$volume": [1000.0, 2000.0, 3000.0],
            "$amount": [10000.0, 40000.0, 90000.0],
        }
    )
    raw_path = repository / "input/raw.csv"
    _write_csv(raw_path, raw)
    features = pd.DataFrame(
        {
            "datetime": ["2026-08-03"] * 3,
            "instrument": instruments,
            **{
                factor: [index + 0.1, index + 0.2, index + 0.3]
                for index, factor in enumerate(factors)
            },
        }
    )
    feature_path = repository / "input/features.csv"
    _write_csv(feature_path, features)
    output_root = repository / "outputs/forward"
    return {
        "repository": repository,
        "factors": factors,
        "freeze": freeze,
        "freeze_path": freeze_path,
        "calendar": calendar,
        "calendar_path": calendar_path,
        "raw_path": raw_path,
        "feature_path": feature_path,
        "output_root": output_root,
        "state_path": output_root / "status.json",
    }


def _loader(factors: tuple[str, ...]):
    return lambda _path: FakePredictor(factors)


def _run(fixture: dict[str, object], **overrides: object) -> dict[str, object]:
    arguments = {
        "decision_date": "2026-08-03",
        "raw_path": fixture["raw_path"],
        "feature_path": fixture["feature_path"],
        "raw_snapshot_first_seen_at": "2026-08-03T07:05:00+08:00",
        "feature_snapshot_created_at": "2026-08-03T15:30:00+08:00",
        "prediction_created_at": "2026-08-03T16:00:00+08:00",
        "trading_calendar_path": fixture["calendar_path"],
        "freeze_path": fixture["freeze_path"],
        "repository_root": fixture["repository"],
        "output_root": fixture["output_root"],
        "state_path": fixture["state_path"],
        "dry_run": False,
        "predictor_loader": _loader(fixture["factors"]),
    }
    arguments.update(overrides)
    return run_single_day_prediction(**arguments)


def _commit_prediction(fixture: dict[str, object]) -> str:
    repository = Path(fixture["repository"])
    relative = "outputs/forward/predictions/2026-08-03/prediction.csv"
    _git(repository, "add", relative)
    env = os.environ.copy()
    env.update(
        {
            "GIT_AUTHOR_DATE": "2026-08-03T16:10:00+08:00",
            "GIT_COMMITTER_DATE": "2026-08-03T16:10:00+08:00",
        }
    )
    _git(repository, "commit", "-m", "freeze forward prediction", env=env)
    return _git(repository, "rev-parse", "HEAD")


def _finalize(fixture: dict[str, object], commit: str) -> dict[str, object]:
    return finalize_prediction_commit(
        decision_date="2026-08-03",
        prediction_commit_sha=commit,
        trading_calendar_path=fixture["calendar_path"],
        freeze_path=fixture["freeze_path"],
        repository_root=fixture["repository"],
        output_root=fixture["output_root"],
        state_path=fixture["state_path"],
    )


def test_legal_single_day_prediction_and_state_update(forward_fixture) -> None:
    result = _run(forward_fixture)
    assert result["status"] == "pending_commit"
    assert result["label_read_count_at_prediction"] == 0
    state = json.loads(Path(forward_fixture["state_path"]).read_text())
    assert state["pending_commit_dates"] == ["2026-08-03"]
    assert state["official_forward_prediction_count"] == 0


def test_raw_market_snapshot_may_cover_more_than_feature_universe(
    forward_fixture,
) -> None:
    raw = pd.read_csv(forward_fixture["raw_path"])
    extra = raw.iloc[[0]].copy()
    extra["instrument"] = "SH699999"
    _write_csv(forward_fixture["raw_path"], pd.concat([raw, extra], ignore_index=True))
    result = _run(forward_fixture)
    assert result["status"] == "pending_commit"


def test_old_date_and_pre_freeze_first_seen_are_rejected(forward_fixture) -> None:
    with pytest.raises(PermissionError, match="decision_date"):
        _run(forward_fixture, decision_date="2026-08-02")
    with pytest.raises(PermissionError, match="first seen"):
        _run(
            forward_fixture,
            raw_snapshot_first_seen_at="2026-08-02T14:33:38.772344+00:00",
        )


@pytest.mark.parametrize("mutation", ["missing", "reordered"])
def test_frozen_factor_set_and_order_are_exact(forward_fixture, mutation) -> None:
    features = pd.read_csv(forward_fixture["feature_path"])
    if mutation == "missing":
        features = features.drop(columns=[forward_fixture["factors"][-1]])
    else:
        columns = features.columns.tolist()
        columns[-1], columns[-2] = columns[-2], columns[-1]
        features = features[columns]
    path = Path(forward_fixture["repository"]) / f"input/{mutation}.csv"
    _write_csv(path, features)
    with pytest.raises(ValueError, match="exact frozen factor order"):
        _run(forward_fixture, feature_path=path)


@pytest.mark.parametrize("asset", ["model", "preprocessing"])
def test_frozen_asset_hash_mismatch_is_rejected(forward_fixture, asset) -> None:
    path = Path(forward_fixture["repository"]) / f"artifacts/candidate/{asset}.txt"
    if asset == "preprocessing":
        path = path.with_name("preprocessing.json")
    path.write_bytes(path.read_bytes() + b"tamper")
    with pytest.raises(ValueError, match="hash mismatch"):
        load_candidate_bundle(
            forward_fixture["freeze_path"],
            repository_root=forward_fixture["repository"],
            predictor_loader=_loader(forward_fixture["factors"]),
        )


def test_duplicate_prediction_is_rejected_and_force_is_dev_only(forward_fixture) -> None:
    _run(forward_fixture)
    with pytest.raises(FileExistsError, match="already exists"):
        _run(forward_fixture)
    with pytest.raises(PermissionError, match="forbidden"):
        _run(forward_fixture, force_dev=True)


def test_failed_retry_does_not_damage_existing_dry_run(forward_fixture) -> None:
    first = _run(forward_fixture, dry_run=True)
    prediction = Path(first["prediction_path"])
    original_hash = file_sha256(prediction)
    bad = pd.read_csv(forward_fixture["feature_path"]).drop(
        columns=[forward_fixture["factors"][-1]]
    )
    bad_path = Path(forward_fixture["repository"]) / "input/bad.csv"
    _write_csv(bad_path, bad)
    with pytest.raises(ValueError, match="exact frozen factor order"):
        _run(
            forward_fixture,
            dry_run=True,
            force_dev=True,
            feature_path=bad_path,
        )
    assert prediction.is_file()
    assert file_sha256(prediction) == original_hash

    error = ValueError("invalid feature snapshot")
    record_forward_failure(
        decision_date="2026-08-03",
        error=error,
        dry_run=True,
        freeze_path=forward_fixture["freeze_path"],
        state_path=forward_fixture["state_path"],
    )
    state = json.loads(Path(forward_fixture["state_path"]).read_text())
    assert state["failed_dates"][0]["error_type"] == "ValueError"
    assert file_sha256(prediction) == original_hash


def test_finalize_commit_binds_prediction_and_marks_pending_label(forward_fixture) -> None:
    _run(forward_fixture)
    result = _finalize(forward_fixture, _commit_prediction(forward_fixture))
    assert result["status"] == "pending_label"
    state = json.loads(Path(forward_fixture["state_path"]).read_text())
    assert state["prediction_dates"] == ["2026-08-03"]
    assert state["pending_label_dates"] == ["2026-08-03"]
    assert state["official_forward_prediction_count"] == 1


def test_labels_are_not_opened_before_maturity(forward_fixture) -> None:
    _run(forward_fixture)
    _finalize(forward_fixture, _commit_prediction(forward_fixture))
    result = update_mature_forward_labels(
        as_of_date="2026-08-28",
        label_dir=Path(forward_fixture["repository"]) / "missing-label-dir",
        trading_calendar_path=forward_fixture["calendar_path"],
        freeze_path=forward_fixture["freeze_path"],
        repository_root=forward_fixture["repository"],
        output_root=forward_fixture["output_root"],
        state_path=forward_fixture["state_path"],
        current_date=date(2026, 8, 28),
    )
    assert result["matured_dates"] == []
    assert result["pending_label_dates"] == ["2026-08-03"]


def test_label_update_rejects_future_as_of_date(forward_fixture) -> None:
    with pytest.raises(PermissionError, match="system date"):
        update_mature_forward_labels(
            as_of_date="2026-08-06",
            label_dir=Path(forward_fixture["repository"]) / "labels",
            trading_calendar_path=forward_fixture["calendar_path"],
            freeze_path=forward_fixture["freeze_path"],
            repository_root=forward_fixture["repository"],
            output_root=forward_fixture["output_root"],
            state_path=forward_fixture["state_path"],
            current_date=date(2026, 8, 5),
        )


def test_label_update_rejects_prediction_file_drift(forward_fixture) -> None:
    _run(forward_fixture)
    _finalize(forward_fixture, _commit_prediction(forward_fixture))
    prediction = (
        Path(forward_fixture["output_root"])
        / "predictions/2026-08-03/prediction.csv"
    )
    prediction.write_bytes(prediction.read_bytes() + b"\n")
    mature_date = forward_fixture["calendar"][21].date().isoformat()
    with pytest.raises(ValueError, match="committed receipt"):
        update_mature_forward_labels(
            as_of_date=mature_date,
            label_dir=Path(forward_fixture["repository"]) / "labels",
            trading_calendar_path=forward_fixture["calendar_path"],
            freeze_path=forward_fixture["freeze_path"],
            repository_root=forward_fixture["repository"],
            output_root=forward_fixture["output_root"],
            state_path=forward_fixture["state_path"],
            current_date=date.fromisoformat(mature_date),
        )


def test_mature_label_computes_daily_rank_ic_and_updates_state(forward_fixture) -> None:
    _run(forward_fixture)
    _finalize(forward_fixture, _commit_prediction(forward_fixture))
    label_dir = Path(forward_fixture["repository"]) / "labels"
    labels = pd.DataFrame(
        {
            "datetime": ["2026-08-03"] * 3,
            "instrument": ["SH600000", "SZ000001", "SH600519"],
            "label_20d_t1": [0.1, 0.2, 0.3],
        }
    )
    _write_csv(label_dir / "2026-08-03.csv", labels)
    mature_date = forward_fixture["calendar"][21].date().isoformat()
    result = update_mature_forward_labels(
        as_of_date=mature_date,
        label_dir=label_dir,
        trading_calendar_path=forward_fixture["calendar_path"],
        freeze_path=forward_fixture["freeze_path"],
        repository_root=forward_fixture["repository"],
        output_root=forward_fixture["output_root"],
        state_path=forward_fixture["state_path"],
        current_date=date.fromisoformat(mature_date),
    )
    assert result["matured_dates"] == ["2026-08-03"]
    metrics = pd.read_csv(
        Path(forward_fixture["output_root"]) / "metrics/daily_metrics.csv"
    )
    assert metrics.loc[0, "valid_pair_count"] == 3
    assert metrics.loc[0, "daily_rank_ic"] == pytest.approx(1.0)
    assert not bool(metrics.loc[0, "primary_confirmation_authority"])
    state = json.loads(Path(forward_fixture["state_path"]).read_text())
    assert state["mature_label_dates"] == ["2026-08-03"]
    assert state["primary_confirmation_complete"] is False
