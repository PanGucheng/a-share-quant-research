from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd
import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from qlib_integration.contracts import contract_row  # noqa: E402
from qlib_integration.readiness import contract_ready, validate_execution_evidence  # noqa: E402
from research_validation.lineage import capture_code_state, write_stage_artifact_manifest  # noqa: E402
from research_validation.stage_output import StageOutputPublisher  # noqa: E402


CONTROLLED = [
    "artifact_manifest.json",
    "contract_status.csv",
    "lineage_issues.csv",
    "qlib_exchange_readiness_report.md",
    "readiness_summary.csv",
]


def resolve(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else (PROJECT_ROOT / path).resolve()


def main() -> int:
    parser = argparse.ArgumentParser(description="Report Qlib Exchange V1 evidence-backed readiness.")
    parser.add_argument("--config", type=Path, default=Path("configs/qlib_exchange_readiness_v1.yaml"))
    args = parser.parse_args()
    config = yaml.safe_load(resolve(args.config).read_text(encoding="utf-8")) or {}
    evidence = config["evidence"]
    loaded, issues = validate_execution_evidence(PROJECT_ROOT, evidence)
    issue_stages = {item.stage_id for item in issues}

    environment_ready = "environment" in loaded and contract_ready(PROJECT_ROOT / evidence["environment"]["contract"], {"critical"}) and str(loaded["environment"]["stage_id"]) not in issue_stages
    infrastructure_ready = environment_ready and all(name in loaded for name in evidence) and not issues
    synthetic_ready = infrastructure_ready and contract_ready(PROJECT_ROOT / evidence["synthetic"]["contract"], {"critical"}) and str(loaded["synthetic"]["stage_id"]) not in issue_stages
    reconciliation_ready = synthetic_ready and contract_ready(PROJECT_ROOT / evidence["reconciliation"]["contract"], {"critical"}) and str(loaded["reconciliation"]["stage_id"]) not in issue_stages
    reference_ready = infrastructure_ready and contract_ready(PROJECT_ROOT / evidence["reference"]["contract"], {"critical", "capability"}) and str(loaded["reference"]["stage_id"]) not in issue_stages
    flags = {
        "qlib_exchange_infrastructure_ready": infrastructure_ready,
        "qlib_exchange_synthetic_ready": synthetic_ready,
        "execution_reconciliation_ready": reconciliation_ready,
        "qlib_exchange_reference_ready": reference_ready,
        "model_training_started": False,
    }
    reasons = {
        "qlib_exchange_infrastructure_ready": "Pinned environment and all four evidence manifests are present, current and hash-valid.",
        "qlib_exchange_synthetic_ready": "Synthetic Qlib execution critical contracts pass.",
        "execution_reconciliation_ready": "Reference/Qlib exact-parity scenario passes with zero unknown differences.",
        "qlib_exchange_reference_ready": "Requires authoritative PIT universe and historical directional tradability labels; current local sample uses disclosed proxies.",
        "model_training_started": "Model training remains outside PR #2.",
    }
    contract = pd.DataFrame(
        [
            contract_row(
                name,
                value if name != "model_training_started" else not value,
                value,
                False if name == "model_training_started" else True,
                reasons[name],
                "capability" if name == "qlib_exchange_reference_ready" else "critical",
            )
            for name, value in flags.items()
        ]
    )
    output_dir = resolve(config["output_dir"])
    code_state = capture_code_state(PROJECT_ROOT)
    with StageOutputPublisher(output_dir, CONTROLLED) as publisher:
        contract.to_csv(publisher.path("contract_status.csv"), index=False, encoding="utf-8-sig")
        pd.DataFrame([flags]).to_csv(publisher.path("readiness_summary.csv"), index=False, encoding="utf-8-sig")
        pd.DataFrame(
            [item.__dict__ for item in issues],
            columns=["check_name", "artifact_id", "reason", "stage_id", "severity"],
        ).to_csv(publisher.path("lineage_issues.csv"), index=False, encoding="utf-8-sig")
        publisher.path("qlib_exchange_readiness_report.md").write_text(
            "# Qlib Exchange Readiness V1\n\n"
            + "\n".join(f"- {name}: `{str(value).lower()}`" for name, value in flags.items())
            + "\n\nThe local-reference execution is operational but remains capability-blocked by non-authoritative historical tradability labels and a non-PIT sample universe.\n",
            encoding="utf-8",
        )
        files = [publisher.path(name) for name in CONTROLLED if name != "artifact_manifest.json"]
        write_stage_artifact_manifest(
            project_root=PROJECT_ROOT,
            stage_id="qlib_exchange_readiness_v1",
            config=config,
            output_dir=publisher.staging_dir,
            output_files=files,
            code_state=code_state,
            input_manifest_paths=[PROJECT_ROOT / spec["manifest"] for spec in evidence.values()],
            factor_frame_id="execution-readiness:mixed-evidence",
            missing_lineage_fields=["pit_universe_artifact", "authoritative_historical_tradability"],
            lineage_status="reference_only",
            artifact_status="pass" if infrastructure_ready and synthetic_ready and reconciliation_ready else "blocked",
            blocked_reason="" if infrastructure_ready and synthetic_ready and reconciliation_ready else "blocked_qlib_exchange_core_readiness",
        )
        publisher.publish()
    print(contract.to_string(index=False))
    return 0 if infrastructure_ready and synthetic_ready and reconciliation_ready and not flags["model_training_started"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
