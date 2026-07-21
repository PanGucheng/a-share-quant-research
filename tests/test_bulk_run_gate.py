from __future__ import annotations

import pytest

from research_validation.bulk_run_gate import (
    BulkRunApprovalError,
    approval_id,
    build_bulk_run_binding,
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
    }
    with pytest.raises(BulkRunApprovalError, match="status=consumed"):
        validate_bulk_run_approval(approval, expected)


def test_exact_command_binds_approval_path_and_purpose(tmp_path) -> None:
    command = matrix_exact_command(tmp_path / "matrix.yaml", tmp_path / "approval.json", "cache_verify")

    assert "--config" in command
    assert "--approval" in command
    assert "--run-purpose cache_verify" in command
