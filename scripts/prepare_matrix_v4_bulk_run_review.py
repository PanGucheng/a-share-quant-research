from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from research_validation.bulk_run_gate import approval_id, build_bulk_run_binding  # noqa: E402
from research_validation.lineage import (  # noqa: E402
    capture_code_state,
    load_artifact_manifest,
    write_stage_artifact_manifest,
)
from research_validation.stage_output import StageOutputPublisher  # noqa: E402
from scripts.run_full_research_feature_matrix_v4 import (  # noqa: E402
    batch_specs,
    matrix_v4_exact_command,
    matrix_v4_input_inventory,
    matrix_v4_scope,
)


CONTROLLED = [
    "artifact_manifest.json",
    "bulk_run_review.md",
    "exact_command.txt",
    "input_inventory.csv",
    "preflight_contract_status.csv",
    "resolved_config.json",
    "resource_estimate.json",
    "user_approval.json",
]


def resolve(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else (PROJECT_ROOT / path).resolve()


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare exact Matrix v4 session-waiver binding.")
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/full_research_feature_matrix_v4_bulk_review.yaml"),
    )
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    review = yaml.safe_load(resolve(args.config).read_text(encoding="utf-8")) or {}
    matrix_config_path = resolve(review["matrix_config"])
    config = yaml.safe_load(matrix_config_path.read_text(encoding="utf-8")) or {}
    specs = batch_specs(config)
    code_state = capture_code_state(PROJECT_ROOT)
    if code_state.dirty:
        raise ValueError("Matrix v4 review bundle requires a clean committed worktree")
    canary = pd.read_csv(resolve(config["matrix_v4_canary_contract"]))
    dependency = pd.read_csv(resolve(config["factor_dependency_inventory"]))
    v3 = pd.read_csv(resolve(config["matrix_v3_batch_manifest"]))
    estimated_write = int(pd.to_numeric(v3["output_size_bytes"], errors="coerce").sum())
    runtime_parent = resolve(config["runtime_dir"]).parent
    runtime_parent.mkdir(parents=True, exist_ok=True)
    free_disk = shutil.disk_usage(runtime_parent).free
    required_disk = int(estimated_write * float(review["minimum_free_disk_multiplier"]))
    checks = [
        ("canary_all_pass", canary["status"].eq("pass").all(), int(canary["status"].ne("pass").sum())),
        ("factor_count_669", len(dependency) == 669, len(dependency)),
        ("batch_count_30", len(specs) == 30, len(specs)),
        ("filter_only_candidates_605", int(dependency["filter_only_reuse_allowed"].astype(bool).sum()) == 605, int(dependency["filter_only_reuse_allowed"].astype(bool).sum())),
        ("alpha101_mandatory_64", int((dependency["source_family"].eq("alpha101") & ~dependency["filter_only_reuse_allowed"].astype(bool)).sum()) == 64, 64),
        ("free_disk_sufficient", free_disk >= required_disk, f"{free_disk}>={required_disk}"),
    ]
    contracts = pd.DataFrame(
        [
            {
                "check": name,
                "status": "pass" if passed else "fail",
                "severity": "critical",
                "detail": detail,
            }
            for name, passed, detail in checks
        ]
    )
    ready = contracts["status"].eq("pass").all()
    output = resolve(review["output_root"]) / args.run_id
    approval_path = output / "user_approval.json"
    exact_command = matrix_v4_exact_command(matrix_config_path, approval_path)
    inventory = matrix_v4_input_inventory(config, specs)
    scope = matrix_v4_scope(config, specs)
    binding = build_bulk_run_binding(
        run_id=args.run_id,
        commit_sha=code_state.commit_sha,
        config=config,
        input_inventory=inventory,
        exact_command=exact_command,
        scope=scope,
    )
    approval = {
        **binding,
        "bulk_run_approval_id": approval_id(binding),
        "status": "approved" if ready else "pending_review",
        "approval_mode": review["approval_mode"],
        "approved_by": review["approved_by"],
        "approval_source": review["approval_source"],
        "approval_timestamp": datetime.now(timezone.utc).isoformat(),
        "single_use": True,
    }
    resource = {
        "estimated_matrix_v3_output_bytes": estimated_write,
        "minimum_free_disk_multiplier": review["minimum_free_disk_multiplier"],
        "required_free_disk_bytes": required_disk,
        "free_disk_bytes": free_disk,
        "estimated_peak_memory_bytes": review["estimated_peak_memory_bytes"],
        "resume_policy": "per-batch hash-addressed partition and comparison sidecar",
        "failure_policy": "retain valid partitions; changed code/config/input requires a new single-use binding",
    }
    with StageOutputPublisher(output, CONTROLLED) as publisher:
        pd.DataFrame(inventory).to_csv(
            publisher.path("input_inventory.csv"), index=False, encoding="utf-8-sig"
        )
        contracts.to_csv(
            publisher.path("preflight_contract_status.csv"),
            index=False,
            encoding="utf-8-sig",
        )
        publisher.path("resolved_config.json").write_text(
            json.dumps(config, ensure_ascii=False, indent=2, default=str) + "\n",
            encoding="utf-8",
        )
        publisher.path("resource_estimate.json").write_text(
            json.dumps(resource, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        publisher.path("exact_command.txt").write_text(exact_command + "\n", encoding="utf-8")
        publisher.path("user_approval.json").write_text(
            json.dumps(approval, ensure_ascii=False, indent=2, sort_keys=True, default=str) + "\n",
            encoding="utf-8",
        )
        publisher.path("bulk_run_review.md").write_text(
            "\n".join(
                [
                    "# Matrix V4 Bulk-Run Review",
                    "",
                    f"- Status: `{'approved_by_session_waiver' if ready else 'blocked'}`",
                    f"- Commit: `{code_state.commit_sha}`",
                    f"- Scope: `{scope['batch_count']}` batches / `{scope['factor_count']}` factors",
                    f"- Reuse / recompute: `{scope['reused_factor_count']}` / `{scope['recomputed_factor_count']}`",
                    f"- Free / required disk: `{free_disk}` / `{required_disk}`",
                    f"- Approval: `{approval['bulk_run_approval_id']}`",
                    "- The five-source Top2000 canary is pass and no outer-test outcome is read.",
                    "- Any code, config, input, command, or scope change invalidates this binding.",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        files = [publisher.path(name) for name in CONTROLLED if name != "artifact_manifest.json"]
        write_stage_artifact_manifest(
            project_root=PROJECT_ROOT,
            stage_id="matrix_v4_bulk_run_review",
            config={**review, "run_id": args.run_id, "matrix_config": config},
            output_dir=publisher.staging_dir,
            output_files=files,
            code_state=code_state,
            input_manifest_paths=[
                resolve(config[key])
                for key in (
                    "factor_catalog_manifest",
                    "factor_dependency_manifest",
                    "universe_manifest",
                    "matrix_v3_manifest",
                    "matrix_v4_canary_manifest",
                    "raw_market_data_snapshot_manifest",
                )
            ],
            start_date=config["start_date"],
            end_date=config["end_date"],
            artifact_status="pass" if ready else "blocked",
            blocked_reason="" if ready else "blocked_matrix_v4_bulk_preflight",
        )
        publisher.publish()
    print(contracts.to_string(index=False))
    print(exact_command)
    return 0 if ready else 2


if __name__ == "__main__":
    raise SystemExit(main())
