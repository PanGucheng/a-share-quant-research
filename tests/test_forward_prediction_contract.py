from __future__ import annotations

import copy
import hashlib
import os
import subprocess
from pathlib import Path

import pytest

from model_research.forward_hardening import (
    prediction_freeze_schema,
    verify_durable_candidate,
)
from model_research.forward_prediction_contract import (
    derive_label_start_contract,
    load_prediction_entry_contract,
    validate_forward_admission,
    validate_prediction_freeze_receipt,
    verify_prediction_git_binding,
)
from model_research.forward_protocol import load_forward_config


FREEZE = "2026-08-02T04:00:00+00:00"
CALENDAR = ("2026-08-03", "2026-08-04", "2026-08-05", "2026-09-01")


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


@pytest.fixture()
def committed_prediction(tmp_path: Path) -> dict[str, str | Path]:
    repository = tmp_path / "prediction-repository"
    repository.mkdir()
    _git(repository, "init")
    _git(repository, "config", "user.name", "Forward Contract Test")
    _git(repository, "config", "user.email", "forward-contract@example.invalid")
    relative_path = "predictions/2026-08-03/prediction.csv"
    prediction = repository / relative_path
    prediction.parent.mkdir(parents=True)
    payload = b"datetime,instrument,prediction\n2026-08-03,SH600000,0.1\n"
    prediction.write_bytes(payload)
    _git(repository, "add", relative_path)
    commit_env = os.environ.copy()
    commit_env.update(
        {
            "GIT_AUTHOR_DATE": "2026-08-03T16:10:00+08:00",
            "GIT_COMMITTER_DATE": "2026-08-03T16:10:00+08:00",
        }
    )
    _git(repository, "commit", "-m", "freeze prediction", env=commit_env)
    return {
        "repository": repository,
        "repo_path": relative_path,
        "sha256": hashlib.sha256(payload).hexdigest(),
        "commit": _git(repository, "rev-parse", "HEAD"),
    }


def _valid_receipt(committed: dict[str, str | Path]) -> dict[str, object]:
    calendar_contract = derive_label_start_contract(
        decision_date="2026-08-03", trading_calendar=CALENDAR
    )
    return {
        "decision_date": "2026-08-03",
        "raw_snapshot_first_seen_at": "2026-08-03T07:05:00+08:00",
        "feature_snapshot_created_at": "2026-08-03T15:10:00+08:00",
        "prediction_created_at": "2026-08-03T16:00:00+08:00",
        "prediction_sha256": committed["sha256"],
        "prediction_commit_sha": committed["commit"],
        "prediction_repo_path": committed["repo_path"],
        "prediction_commit_timestamp": "2026-08-03T16:10:00+08:00",
        **calendar_contract,
        "label_mature_date": "2026-09-01",
        "label_read_count_at_prediction": 0,
        "candidate_freeze_id": "forward-candidate-freeze:" + "c" * 64,
        "model_sha256": "d" * 64,
        "preprocessing_sha256": "e" * 64,
    }


def test_downloaded_after_freeze_does_not_make_old_date_prospective() -> None:
    with pytest.raises(PermissionError, match="decision_date"):
        validate_forward_admission(
            decision_date="2026-06-10",
            raw_snapshot_first_seen_at="2026-08-03T08:00:00+08:00",
            candidate_freeze_effective_time=FREEZE,
        )


def test_first_seen_must_be_strictly_after_candidate_freeze() -> None:
    with pytest.raises(PermissionError, match="first seen"):
        validate_forward_admission(
            decision_date="2026-08-03",
            raw_snapshot_first_seen_at=FREEZE,
            candidate_freeze_effective_time=FREEZE,
        )


def test_calendar_derives_next_trading_day_and_shanghai_cutoff() -> None:
    result = derive_label_start_contract(
        decision_date="2026-08-03", trading_calendar=CALENDAR
    )
    assert result["label_start_date"] == "2026-08-04"
    assert result["label_start_cutoff"] == "2026-08-04T09:25:00+08:00"


def test_prediction_entry_contract_is_fail_closed() -> None:
    contract = load_prediction_entry_contract(
        "configs/forward_prediction_entry_contract_v1.yaml"
    )
    assert contract["calendar"]["receipt_values_are_non_authoritative"]
    assert contract["git_binding"]["prediction_blob_sha256_must_match"]
    assert contract["governance"]["forward_data_waiting"]
    assert contract["governance"]["generate_forward_prediction"] is False


def test_calendar_rejects_non_trading_decision_date() -> None:
    with pytest.raises(PermissionError, match="not in authoritative"):
        derive_label_start_contract(
            decision_date="2026-08-02", trading_calendar=CALENDAR
        )


def test_valid_post_freeze_date_and_prediction_receipt_pass(
    committed_prediction: dict[str, str | Path],
) -> None:
    result = validate_prediction_freeze_receipt(
        _valid_receipt(committed_prediction),
        candidate_freeze_effective_time=FREEZE,
        trading_calendar=CALENDAR,
        repository=committed_prediction["repository"],
    )
    assert result["admission_status"] == "prospective_eligible"
    assert result["prediction_freeze_status"] == (
        "immutable_before_label_start"
    )


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        (
            "prediction_created_at",
            "2026-08-04T09:25:00+08:00",
            "created after",
        ),
        ("label_read_count_at_prediction", 1, "read forward labels"),
    ],
)
def test_prediction_freeze_fails_closed(
    field: str,
    value: object,
    message: str,
    committed_prediction: dict[str, str | Path],
) -> None:
    receipt = copy.deepcopy(_valid_receipt(committed_prediction))
    receipt[field] = value
    with pytest.raises(PermissionError, match=message):
        validate_prediction_freeze_receipt(
            receipt,
            candidate_freeze_effective_time=FREEZE,
            trading_calendar=CALENDAR,
            repository=committed_prediction["repository"],
        )


def test_git_committer_timestamp_must_precede_derived_cutoff(
    committed_prediction: dict[str, str | Path],
) -> None:
    repository = Path(committed_prediction["repository"])
    commit_env = os.environ.copy()
    commit_env.update(
        {
            "GIT_AUTHOR_DATE": "2026-08-04T09:25:00+08:00",
            "GIT_COMMITTER_DATE": "2026-08-04T09:25:00+08:00",
        }
    )
    _git(repository, "commit", "--allow-empty", "-m", "late receipt", env=commit_env)
    receipt = _valid_receipt(committed_prediction)
    receipt["prediction_commit_sha"] = _git(repository, "rev-parse", "HEAD")
    receipt["prediction_commit_timestamp"] = "2026-08-04T09:25:00+08:00"
    with pytest.raises(PermissionError, match="committed after"):
        validate_prediction_freeze_receipt(
            receipt,
            candidate_freeze_effective_time=FREEZE,
            trading_calendar=CALENDAR,
            repository=repository,
        )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("label_start_date", "2026-08-05"),
        ("label_start_cutoff", "2026-08-04T10:25:00+08:00"),
        ("trading_calendar_sha256", "f" * 64),
    ],
)
def test_receipt_cannot_override_calendar_derived_values(
    field: str,
    value: str,
    committed_prediction: dict[str, str | Path],
) -> None:
    receipt = _valid_receipt(committed_prediction)
    receipt[field] = value
    with pytest.raises(PermissionError, match="calendar-derived"):
        validate_prediction_freeze_receipt(
            receipt,
            candidate_freeze_effective_time=FREEZE,
            trading_calendar=CALENDAR,
            repository=committed_prediction["repository"],
        )


def test_git_binding_reads_commit_blob_and_timestamp(
    committed_prediction: dict[str, str | Path],
) -> None:
    result = verify_prediction_git_binding(
        repository=committed_prediction["repository"],
        prediction_commit_sha=committed_prediction["commit"],
        prediction_repo_path=committed_prediction["repo_path"],
        prediction_sha256=committed_prediction["sha256"],
    )
    assert result["prediction_sha256"] == committed_prediction["sha256"]
    assert result["prediction_commit_timestamp"] == "2026-08-03T16:10:00+08:00"


def test_git_binding_rejects_wrong_blob_hash(
    committed_prediction: dict[str, str | Path],
) -> None:
    with pytest.raises(ValueError, match="blob SHA256"):
        verify_prediction_git_binding(
            repository=committed_prediction["repository"],
            prediction_commit_sha=committed_prediction["commit"],
            prediction_repo_path=committed_prediction["repo_path"],
            prediction_sha256="f" * 64,
        )


def test_git_binding_rejects_missing_commit(
    committed_prediction: dict[str, str | Path],
) -> None:
    with pytest.raises(ValueError, match="Git prediction receipt"):
        verify_prediction_git_binding(
            repository=committed_prediction["repository"],
            prediction_commit_sha="f" * 40,
            prediction_repo_path=committed_prediction["repo_path"],
            prediction_sha256=committed_prediction["sha256"],
        )


def test_git_binding_rejects_path_absent_from_commit_tree(
    committed_prediction: dict[str, str | Path],
) -> None:
    with pytest.raises(ValueError, match="absent from the receipt commit tree"):
        verify_prediction_git_binding(
            repository=committed_prediction["repository"],
            prediction_commit_sha=committed_prediction["commit"],
            prediction_repo_path="predictions/2026-08-03/missing.csv",
            prediction_sha256=committed_prediction["sha256"],
        )


def test_receipt_timestamp_must_equal_git_committer_timestamp(
    committed_prediction: dict[str, str | Path],
) -> None:
    receipt = _valid_receipt(committed_prediction)
    receipt["prediction_commit_timestamp"] = "2026-08-03T16:11:00+08:00"
    with pytest.raises(PermissionError, match="Git committer timestamp"):
        validate_prediction_freeze_receipt(
            receipt,
            candidate_freeze_effective_time=FREEZE,
            trading_calendar=CALENDAR,
            repository=committed_prediction["repository"],
        )


def test_forward_config_uses_v1_1_and_manifest_resolved_labels() -> None:
    config = load_forward_config(
        "configs/prospective_forward_confirmation_v1.yaml"
    )
    assert "labels_runtime" not in config["parents"]
    assert config["parents"]["feature_order"].startswith(
        "outputs/research_model_protocol_v1_1/"
    )
    assert config["parents"]["protocol_manifest"].startswith(
        "outputs/research_model_protocol_v1_1/"
    )
    assert len(config["training"]["labels_runtime_sha256"]) == 64


def test_prediction_freeze_schema_requires_payload_and_commit_receipts() -> None:
    schema = prediction_freeze_schema()
    assert schema["schema_version"] == 2
    assert "prediction_created_at" in schema["required_fields"]
    assert "prediction_commit_sha" in schema["required_fields"]
    assert "prediction_repo_path" in schema["required_fields"]
    assert "trading_calendar_sha256" in schema["required_fields"]
    assert schema["contracts"]["prediction_created_before_label_start_cutoff"]
    assert schema["contracts"]["prediction_commit_before_label_start_cutoff"]
    assert schema["contracts"]["label_start_derived_from_authoritative_calendar"]
    assert schema["contracts"]["prediction_blob_loaded_from_commit_tree"]
    assert schema["contracts"]["prediction_commit_timestamp_loaded_from_git"]


def test_committed_candidate_assets_are_hash_valid() -> None:
    model, preprocessing = verify_durable_candidate(
        "outputs/prospective_forward_hardening_v1/current/"
        "forward_candidate_freeze.json"
    )
    assert model.stat().st_size == 688235
    assert preprocessing.stat().st_size == 5639
