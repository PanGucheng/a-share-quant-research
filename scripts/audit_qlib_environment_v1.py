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
from qlib_integration.environment import audit_qlib_environment, environment_ready  # noqa: E402
from research_validation.lineage import capture_code_state, write_stage_artifact_manifest  # noqa: E402
from research_validation.stage_output import StageOutputPublisher  # noqa: E402


CONTROLLED = [
    "artifact_manifest.json",
    "contract_status.csv",
    "environment_audit.json",
    "environment_report.md",
    "environment_status.csv",
    "resolved_config.json",
]


def resolve(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else (PROJECT_ROOT / path).resolve()


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit the pinned Qlib execution environment.")
    parser.add_argument("--config", type=Path, default=Path("configs/qlib_environment_v1.yaml"))
    args = parser.parse_args()
    config = yaml.safe_load(resolve(args.config).read_text(encoding="utf-8")) or {}
    payload = audit_qlib_environment(
        resolve(config["qlib_source"]), resolve(config["qlib_provider"]), str(config["expected_qlib_commit"])
    )
    ready = environment_ready(payload)
    rows = [
        contract_row("python_3_10", bool(payload["python_3_10"]), payload["python_version"], "3.10.x"),
        contract_row("qlib_commit_matches", bool(payload["qlib_commit_matches"]), payload["qlib_source_commit"], payload["expected_qlib_commit"]),
        contract_row("qlib_runtime_code_clean", not bool(payload["runtime_code_dirty"]), payload["runtime_dirty_files"], []),
        contract_row("provider_calendar_present", bool(payload["provider_calendar_exists"]), payload["provider_calendar_exists"], True),
        contract_row("provider_instruments_present", bool(payload["provider_instruments_exists"]), payload["provider_instruments_exists"], True),
        contract_row("provider_features_present", bool(payload["provider_features_exists"]), payload["provider_features_exists"], True),
        contract_row("qlib_environment_resolved", ready, ready, True),
    ]
    status = pd.DataFrame(rows)
    output_dir = resolve(config["output_dir"])
    code_state = capture_code_state(PROJECT_ROOT)
    with StageOutputPublisher(output_dir, CONTROLLED) as publisher:
        publisher.path("environment_audit.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        status.to_csv(publisher.path("contract_status.csv"), index=False, encoding="utf-8-sig")
        pd.DataFrame([payload]).to_csv(publisher.path("environment_status.csv"), index=False, encoding="utf-8-sig")
        publisher.path("resolved_config.json").write_text(
            json.dumps(config, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8"
        )
        publisher.path("environment_report.md").write_text(
            "# Qlib Environment V1\n\n"
            f"- Status: `{'pass' if ready else 'blocked'}`\n"
            f"- Python: `{payload['python_version']}`\n"
            f"- Qlib commit: `{payload['qlib_source_commit']}`\n"
            f"- Runtime code dirty: `{str(payload['runtime_code_dirty']).lower()}`\n"
            f"- Source worktree dirty warning: `{str(payload['source_worktree_dirty']).lower()}`\n",
            encoding="utf-8",
        )
        files = [publisher.path(name) for name in CONTROLLED if name != "artifact_manifest.json"]
        write_stage_artifact_manifest(
            project_root=PROJECT_ROOT,
            stage_id="qlib_environment_v1",
            config=config,
            output_dir=publisher.staging_dir,
            output_files=files,
            code_state=code_state,
            lineage_status="reference_only",
            artifact_status="pass" if ready else "blocked",
            blocked_reason="" if ready else "blocked_qlib_environment_unresolved",
        )
        publisher.publish()
    print(status.to_string(index=False))
    return 0 if ready else 2


if __name__ == "__main__":
    raise SystemExit(main())
