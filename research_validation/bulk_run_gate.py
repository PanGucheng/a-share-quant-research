from __future__ import annotations

import json
import os
from datetime import datetime, timezone
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
    if approval.get("single_use") is not True:
        failures.append("single_use_not_true")
    for key, expected in binding.items():
        if approval.get(key) != expected:
            failures.append(f"{key}_mismatch")
    expected_id = approval_id(binding)
    if approval.get("bulk_run_approval_id") != expected_id:
        failures.append("bulk_run_approval_id_mismatch")
    if failures:
        raise BulkRunApprovalError("bulk run approval invalid: " + "; ".join(failures))


def consumption_receipt_path(receipt_dir: Path, bulk_run_approval_id: str) -> Path:
    digest = sha256_text(str(bulk_run_approval_id))
    return receipt_dir / f"{digest}.json"


def reserve_bulk_run_approval(
    approval: Mapping[str, Any],
    binding: Mapping[str, Any],
    *,
    receipt_dir: Path,
) -> Path:
    """Atomically consume a single-use approval before expensive work begins."""

    validate_bulk_run_approval(approval, binding)
    receipt_dir.mkdir(parents=True, exist_ok=True)
    path = consumption_receipt_path(receipt_dir, str(approval["bulk_run_approval_id"]))
    receipt = {
        "schema_version": 1,
        "approval_id": str(approval["bulk_run_approval_id"]),
        "run_id": str(approval["run_id"]),
        "approved_commit_sha": str(approval["approved_commit_sha"]),
        "consumed_at": datetime.now(timezone.utc).isoformat(),
        "status": "reserved",
        "result_artifact_id": None,
    }
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL)
    except FileExistsError as exc:
        raise BulkRunApprovalError(
            f"bulk run approval already consumed: {approval['bulk_run_approval_id']}"
        ) from exc
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(receipt, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
    return path


def finalize_bulk_run_consumption(receipt_path: Path, *, result_artifact_id: str) -> None:
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    if receipt.get("status") != "reserved" or receipt.get("result_artifact_id") is not None:
        raise BulkRunApprovalError(f"invalid reserved consumption receipt: {receipt_path}")
    receipt["status"] = "completed"
    receipt["result_artifact_id"] = str(result_artifact_id)
    temporary = receipt_path.with_suffix(receipt_path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(receipt_path)


def relative_command_path(path: Path, project_root: Path) -> str:
    try:
        return path.resolve().relative_to(project_root.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()
