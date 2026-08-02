from __future__ import annotations

import copy

import pytest

from model_research.forward_hardening import prediction_freeze_schema
from model_research.forward_prediction_contract import (
    validate_forward_admission,
    validate_prediction_freeze_receipt,
)
from model_research.forward_protocol import load_forward_config


FREEZE = "2026-08-02T04:00:00+00:00"


def _valid_receipt() -> dict[str, object]:
    return {
        "decision_date": "2026-08-03",
        "raw_snapshot_first_seen_at": "2026-08-03T07:05:00+08:00",
        "feature_snapshot_created_at": "2026-08-03T15:10:00+08:00",
        "prediction_created_at": "2026-08-03T16:00:00+08:00",
        "prediction_sha256": "a" * 64,
        "prediction_commit_sha": "b" * 40,
        "prediction_commit_timestamp": "2026-08-03T16:10:00+08:00",
        "label_start_date": "2026-08-04",
        "label_start_cutoff": "2026-08-04T09:25:00+08:00",
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


def test_valid_post_freeze_date_and_prediction_receipt_pass() -> None:
    result = validate_prediction_freeze_receipt(
        _valid_receipt(), candidate_freeze_effective_time=FREEZE
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
        (
            "prediction_commit_timestamp",
            "2026-08-04T09:25:00+08:00",
            "committed after",
        ),
        ("label_read_count_at_prediction", 1, "read forward labels"),
    ],
)
def test_prediction_freeze_fails_closed(
    field: str, value: object, message: str
) -> None:
    receipt = copy.deepcopy(_valid_receipt())
    receipt[field] = value
    with pytest.raises(PermissionError, match=message):
        validate_prediction_freeze_receipt(
            receipt, candidate_freeze_effective_time=FREEZE
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
    assert "prediction_created_at" in schema["required_fields"]
    assert "prediction_commit_sha" in schema["required_fields"]
    assert schema["contracts"]["prediction_created_before_label_start_cutoff"]
    assert schema["contracts"]["prediction_commit_before_label_start_cutoff"]
