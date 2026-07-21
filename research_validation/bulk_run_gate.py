from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Sequence

from .lineage import canonical_json, config_sha256, sha256_text


class BulkRunApprovalError(RuntimeError):
    pass


def input_inventory_sha256(rows: Sequence[Mapping[str, Any]]) -> str:
    normalized = sorted((dict(row) for row in rows), key=lambda row: canonical_json(row))
    return sha256_text(canonical_json(normalized))


def command_sha256(command: str) -> str:
    return sha256_text(command.strip())


def build_bulk_run_binding(
    *,
    run_id: str,
    commit_sha: str,
    config: Mapping[str, Any],
    input_inventory: Sequence[Mapping[str, Any]],
    exact_command: str,
    scope: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "run_id": run_id,
        "approved_commit_sha": commit_sha,
        "approved_resolved_config_sha256": config_sha256(config),
        "approved_input_inventory_sha256": input_inventory_sha256(input_inventory),
        "approved_command_sha256": command_sha256(exact_command),
        "approved_scope": dict(scope),
        "approved_scope_sha256": sha256_text(canonical_json(dict(scope))),
    }


def approval_id(binding: Mapping[str, Any]) -> str:
    return "bulk-run-approval:" + sha256_text(canonical_json(dict(binding)))


def validate_bulk_run_approval(
    approval: Mapping[str, Any],
    binding: Mapping[str, Any],
    *,
    allowed_modes: Sequence[str] = ("explicit_user_approval", "user_session_waiver"),
) -> None:
    failures = []
    if approval.get("status") != "approved":
        failures.append(f"status={approval.get('status')}")
    if approval.get("approval_mode") not in set(allowed_modes):
        failures.append(f"approval_mode={approval.get('approval_mode')}")
    for key, expected in binding.items():
        if approval.get(key) != expected:
            failures.append(f"{key}_mismatch")
    expected_id = approval_id(binding)
    if approval.get("bulk_run_approval_id") != expected_id:
        failures.append("bulk_run_approval_id_mismatch")
    if failures:
        raise BulkRunApprovalError("bulk run approval invalid: " + "; ".join(failures))


def relative_command_path(path: Path, project_root: Path) -> str:
    try:
        return path.resolve().relative_to(project_root.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()
