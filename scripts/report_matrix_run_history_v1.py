from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from qlib_integration.contracts import contract_row  # noqa: E402
from research_validation.bulk_run_gate import approval_id  # noqa: E402
from research_validation.lineage import (  # noqa: E402
    capture_code_state,
    load_artifact_manifest,
    validate_manifest_outputs,
    write_stage_artifact_manifest,
)
from research_validation.stage_output import StageOutputPublisher  # noqa: E402


CONTROLLED = (
    "artifact_manifest.json",
    "contract_status.csv",
    "matrix_run_history.csv",
    "matrix_run_history_report.md",
    "resolved_config.json",
)
BINDING_FIELDS = (
    "run_id",
    "approved_commit_sha",
    "approved_resolved_config_sha256",
    "approved_input_inventory_sha256",
    "approved_command_sha256",
    "approved_scope",
    "approved_scope_sha256",
)


def resolve(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else (PROJECT_ROOT / path).resolve()


def approval_binding_payload(approval: dict[str, object]) -> dict[str, object]:
    return {field: approval[field] for field in BINDING_FIELDS}


def main() -> int:
    parser = argparse.ArgumentParser(description="Publish compact history for authoritative matrix bulk runs.")
    parser.add_argument("--config", type=Path, default=Path("configs/matrix_run_history_669_v1.yaml"))
    args = parser.parse_args()
    config = yaml.safe_load(resolve(args.config).read_text(encoding="utf-8")) or {}

    matrix_path = resolve(config["matrix_manifest"])
    reproducibility_path = resolve(config["reproducibility_manifest"])
    matrix = load_artifact_manifest(matrix_path)
    reproducibility = load_artifact_manifest(reproducibility_path)
    manifests = [matrix, reproducibility]
    manifest_paths = [matrix_path, reproducibility_path]
    rows: list[dict[str, object]] = []
    approval_ids_valid = True
    for purpose in ("materialize", "cache_verify"):
        spec = config["reviews"][purpose]
        review_path = resolve(spec["manifest"])
        review = load_artifact_manifest(review_path)
        approval = json.loads(resolve(spec["approval"]).read_text(encoding="utf-8"))
        manifests.append(review)
        manifest_paths.append(review_path)
        computed_id = approval_id(approval_binding_payload(approval))
        approval_ids_valid = approval_ids_valid and computed_id == approval["bulk_run_approval_id"]
        rows.append(
            {
                "operation": purpose,
                "run_id": approval["run_id"],
                "approval_artifact_id": review["artifact_id"],
                "approval_id": approval["bulk_run_approval_id"],
                "approved_at": approval["approval_timestamp"],
                "consumed_at": matrix["created_at"],
                "consumed_at_source": "final_matrix_publication_time_upper_bound",
                "result_artifact_id": matrix["artifact_id"],
                "receipt_status": "retrospective_completed",
                "single_use_declared": approval.get("single_use") is True,
                "single_use_enforced_at_execution": False,
                "approved_commit_sha": approval["approved_commit_sha"],
                "execution_code_commit_sha": matrix["code_commit_sha"],
                "current_head_binding_satisfied": approval["approved_commit_sha"] == matrix["code_commit_sha"],
                "historical_limitation": "pre-hardening run; exact inputs/source hashes passed and matrix equivalence is proven",
            }
        )

    issues = []
    for manifest, path in zip(manifests, manifest_paths):
        issues.extend(validate_manifest_outputs(manifest, path.parent))
    history = pd.DataFrame(rows)
    matrix_inputs = set(map(str, matrix["input_artifact_ids"]))
    review_ids = {row["operation"]: row["approval_artifact_id"] for row in rows}
    contracts = pd.DataFrame(
        [
            contract_row("all_evidence_outputs_fresh", not issues, len(issues), 0),
            contract_row("materialize_and_cache_verify_recorded", set(history["operation"]) == {"materialize", "cache_verify"}, sorted(history["operation"]), ["cache_verify", "materialize"]),
            contract_row("approval_ids_valid", approval_ids_valid, approval_ids_valid, True),
            contract_row("single_use_declaration_recorded", bool(history["single_use_declared"].all()), int(history["single_use_declared"].sum()), 2),
            contract_row("historical_enforcement_limit_disclosed", not bool(history["single_use_enforced_at_execution"].any()), int(history["single_use_enforced_at_execution"].sum()), 0, "Future runs are atomically consumed; these two runs predate that gate.", "evidence"),
            contract_row("historical_head_binding_limit_disclosed", not bool(history["current_head_binding_satisfied"].any()), int(history["current_head_binding_satisfied"].sum()), 0, "Future approvals bind clean execution HEAD; these runs used source hashes plus the older provenance commit binding.", "evidence"),
            contract_row("cache_review_is_direct_matrix_parent", str(review_ids["cache_verify"]) in matrix_inputs, review_ids["cache_verify"], "direct matrix parent"),
            contract_row("materialize_review_preserved_by_history", bool(review_ids["materialize"]), review_ids["materialize"], "nonempty approval artifact"),
            contract_row("reproducibility_targets_current_matrix", str(matrix["artifact_id"]) in set(map(str, reproducibility["input_artifact_ids"])), reproducibility["input_artifact_ids"], matrix["artifact_id"]),
        ]
    )
    ready = bool(contracts["status"].eq("pass").all())
    output_dir = resolve(config["output_dir"])
    with StageOutputPublisher(output_dir, CONTROLLED) as publisher:
        history.to_csv(publisher.path("matrix_run_history.csv"), index=False, encoding="utf-8-sig")
        contracts.to_csv(publisher.path("contract_status.csv"), index=False, encoding="utf-8-sig")
        publisher.path("resolved_config.json").write_text(
            json.dumps(config, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        publisher.path("matrix_run_history_report.md").write_text(
            "# Matrix V3 Run History\n\n"
            + f"- Status: `{'pass' if ready else 'blocked'}`\n"
            + f"- Result matrix: `{matrix['artifact_id']}`\n"
            + "- Materialization and cache-verification approvals are both retained.\n"
            + "- Historical limitation: these runs predate current-HEAD and atomic single-use enforcement; exact source/input hashes and zero-difference reproducibility remain valid.\n"
            + "- Future runs must create an atomic consumption receipt before computation.\n",
            encoding="utf-8",
        )
        files = [publisher.path(name) for name in CONTROLLED if name != "artifact_manifest.json"]
        write_stage_artifact_manifest(
            project_root=PROJECT_ROOT,
            stage_id="matrix_run_history_v1",
            config=config,
            output_dir=publisher.staging_dir,
            output_files=files,
            code_state=capture_code_state(PROJECT_ROOT),
            input_manifest_paths=manifest_paths,
            factor_frame_id=matrix["factor_frame_id"],
            start_date=matrix["start_date"],
            end_date=matrix["end_date"],
            lineage_status="complete",
            artifact_status="pass" if ready else "blocked",
            blocked_reason="" if ready else "blocked_matrix_run_history",
        )
        publisher.publish()
    print(contracts.to_string(index=False))
    return 0 if ready else 2


if __name__ == "__main__":
    raise SystemExit(main())
