from scripts.report_matrix_run_history_v1 import approval_binding_payload


def test_approval_binding_payload_excludes_nonbinding_metadata() -> None:
    approval = {
        "run_id": "run",
        "approved_commit_sha": "a" * 40,
        "approved_resolved_config_sha256": "b" * 64,
        "approved_input_inventory_sha256": "c" * 64,
        "approved_command_sha256": "d" * 64,
        "approved_scope": {"factor_count": 669},
        "approved_scope_sha256": "e" * 64,
        "approval_timestamp": "later",
        "single_use": True,
    }

    payload = approval_binding_payload(approval)

    assert "approval_timestamp" not in payload
    assert "single_use" not in payload
    assert payload["run_id"] == "run"
