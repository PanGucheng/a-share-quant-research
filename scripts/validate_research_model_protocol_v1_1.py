from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from model_research.gates import (  # noqa: E402
    REQUIRED_ENTRY_CONTRACTS,
    assert_research_model_entry_artifact,
)
from research_validation.lineage import (  # noqa: E402
    load_artifact_manifest,
    validate_manifest_outputs,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate PR #5A.1 artifact-bound model protocol closure."
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("outputs/research_model_protocol_v1_1/current"),
    )
    args = parser.parse_args()
    output = (
        args.output_dir
        if args.output_dir.is_absolute()
        else PROJECT_ROOT / args.output_dir
    )
    manifest_path = output / "artifact_manifest.json"
    manifest = load_artifact_manifest(manifest_path)
    issues = validate_manifest_outputs(manifest, output)
    assert not issues, issues
    assert manifest["stage_id"] == "research_model_protocol_v1_1"
    assert manifest["artifact_status"] == "pass"
    assert manifest["lineage_status"] == "complete"
    assert not bool(manifest["code_dirty"])
    assert_research_model_entry_artifact(
        manifest_path,
        experiment_class="post_observation_research",
        operation="training",
    )

    contracts = pd.read_csv(output / "contract_status.csv")
    assert REQUIRED_ENTRY_CONTRACTS <= set(contracts["check_name"].astype(str))
    assert contracts.loc[
        contracts["severity"].astype(str).eq("critical"), "status"
    ].astype(str).eq("pass").all()
    readiness = pd.read_csv(output / "readiness_summary.csv")
    assert len(readiness) == 1
    row = readiness.iloc[0]
    assert str(row["protocol_closure_version"]) == "1.1"
    for field in (
        "research_model_protocol_ready",
        "research_model_input_protocol_ready",
        "research_model_input_ready",
        "research_model_training_ready",
        "development_dry_run_ready",
    ):
        assert bool(row[field])
    assert not bool(row["research_model_hard_stop_active"])
    assert bool(row["production_model_hard_stop_active"])
    assert not bool(row["production_model_selected"])
    assert not bool(row["model_training_started"])
    assert not bool(row["authoritative_execution"])
    assert not bool(row["unbiased_final_estimate"])
    assert int(row["test_read_count_before_freeze"]) == 0

    access = pd.read_csv(output / "access_audit.csv")
    assert int(
        pd.to_numeric(
            access.loc[access["fold"].astype(str).eq("test"), "read_count"]
        ).sum()
    ) == 0
    validation = pd.read_csv(output / "validation_transform_receipt.csv")
    assert len(validation) == 3
    assert validation["status"].astype(str).eq("pass").all()
    eligibility = pd.read_csv(output / "sample_eligibility_receipt.csv")
    assert len(eligibility) == 2659
    assert eligibility["status"].astype(str).eq("pass").all()
    superseded = pd.read_csv(output / "superseded_artifacts.csv")
    assert len(superseded) == 1
    assert (
        superseded.iloc[0]["disposition"]
        == "superseded_for_model_entry"
    )
    print("Research model protocol V1.1 closure validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
