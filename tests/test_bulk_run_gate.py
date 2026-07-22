from __future__ import annotations

import pytest

from research_validation.bulk_run_gate import (
    BulkRunApprovalError,
    approval_id,
    build_bulk_run_binding,
    finalize_bulk_run_consumption,
    reserve_bulk_run_approval,
    validate_bulk_run_approval,
)
from scripts.run_full_research_feature_matrix_v1 import matrix_exact_command


def binding() -> dict[str, object]:
    return build_bulk_run_binding(
        run_id="matrix-v3-test",
        commit_sha="a" * 40,
        config={"cache_key_schema_version": 3},
        input_inventory=[{"name": "raw", "sha256": "b" * 64}],
        exact_command="python run.py --config config.yaml",
        scope={"batch_count": 30, "factor_count": 669},
    )


def test_session_waiver_must_match_every_exact_binding_field() -> None:
    expected = binding()
    approval = {
        **expected,
        "status": "approved",
        "approval_mode": "user_session_waiver",
        "bulk_run_approval_id": approval_id(expected),
        "single_use": True,
    }
    validate_bulk_run_approval(approval, expected)

    approval["approved_scope"] = {"batch_count": 29, "factor_count": 669}
    with pytest.raises(BulkRunApprovalError, match="approved_scope_mismatch"):
        validate_bulk_run_approval(approval, expected)


def test_consumed_or_unapproved_approval_is_rejected() -> None:
    expected = binding()
    approval = {
        **expected,
        "status": "consumed",
        "approval_mode": "user_session_waiver",
        "bulk_run_approval_id": approval_id(expected),
        "single_use": True,
    }
    with pytest.raises(BulkRunApprovalError, match="status=consumed"):
        validate_bulk_run_approval(approval, expected)


def test_single_use_approval_writes_and_enforces_consumption_receipt(tmp_path) -> None:
    expected = binding()
    approval = {
        **expected,
        "status": "approved",
        "approval_mode": "user_session_waiver",
        "bulk_run_approval_id": approval_id(expected),
        "single_use": True,
    }

    receipt = reserve_bulk_run_approval(approval, expected, receipt_dir=tmp_path)
    finalize_bulk_run_consumption(receipt, result_artifact_id="matrix:abc")

    assert '"status": "completed"' in receipt.read_text(encoding="utf-8")
    assert '"result_artifact_id": "matrix:abc"' in receipt.read_text(encoding="utf-8")
    with pytest.raises(BulkRunApprovalError, match="already consumed"):
        reserve_bulk_run_approval(approval, expected, receipt_dir=tmp_path)


def test_approval_must_explicitly_be_single_use() -> None:
    expected = binding()
    approval = {
        **expected,
        "status": "approved",
        "approval_mode": "user_session_waiver",
        "bulk_run_approval_id": approval_id(expected),
    }
    with pytest.raises(BulkRunApprovalError, match="single_use_not_true"):
        validate_bulk_run_approval(approval, expected)


def test_exact_command_binds_approval_path_and_purpose(tmp_path) -> None:
    command = matrix_exact_command(tmp_path / "matrix.yaml", tmp_path / "approval.json", "cache_verify")

    assert "--config" in command
    assert "--approval" in command
    assert "--run-purpose cache_verify" in command
