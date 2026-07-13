from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from portfolio.model_comparison import prerequisite_status, readiness_flags  # noqa: E402
from research_validation.lineage import (  # noqa: E402
    LineageIssue,
    capture_code_state,
    load_input_manifests,
    validate_current_upstream_ids,
    validate_lineage_chain,
    validate_manifest_outputs,
    write_stage_artifact_manifest,
)
from research_validation.profiles import Profile, ProfileType  # noqa: E402


def contract_pass(path: Path) -> bool:
    if not path.is_file():
        return False
    frame = pd.read_csv(path)
    blocking = frame.loc[frame.status.isin(["fail", "blocked"]) & frame.severity.isin(["critical", "downstream"])]
    return blocking.empty


def main() -> int:
    parser = argparse.ArgumentParser(description="Report model readiness without starting training.")
    parser.add_argument("--config", type=Path, default=Path("configs/factor_model_comparison_v1.yaml"))
    args = parser.parse_args()
    path = args.config if args.config.is_absolute() else PROJECT_ROOT / args.config
    config = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    code_state = capture_code_state(PROJECT_ROOT)

    contracts = {name: pd.read_csv(PROJECT_ROOT / value) for name, value in config["prerequisites"].items()}
    status = prerequisite_status(contracts)
    input_paths = [PROJECT_ROOT / item for item in config.get("input_manifests", [])]
    manifests, missing_manifests = load_input_manifests(input_paths)
    profiles = [Profile(str(item["profile_name"]), ProfileType(str(item["profile_type"]))) for item in manifests]
    lineage_status = "reference_only" if missing_manifests or any(item["lineage_status"] != "complete" for item in manifests) else "complete"

    reference_issues: list[LineageIssue] = validate_lineage_chain(
        manifests, profile_gate="reference", require_complete=False,
        require_known_inputs=True, require_consistent_ids=True, require_clean_code=False,
    )
    reference_issues.extend(validate_current_upstream_ids(manifests, config.get("lineage_edges", {})))
    manifest_by_stage = {str(item["stage_id"]): item for item in manifests}
    for stage_id, config_name in config.get("manifest_configs", {}).items():
        manifest = manifest_by_stage.get(stage_id)
        if manifest is None:
            continue
        stage_config = yaml.safe_load((PROJECT_ROOT / config_name).read_text(encoding="utf-8")) or {}
        reference_issues.extend(
            validate_manifest_outputs(manifest, PROJECT_ROOT / stage_config["output_dir"], config=stage_config)
        )
    reference_issues.extend(LineageIssue("manifest_missing", "", value) for value in missing_manifests)
    full_issues = validate_lineage_chain(
        manifests, profile_gate="full_research", require_complete=True,
        require_known_inputs=True, require_consistent_ids=True, require_clean_code=True,
    )

    consistency_path = PROJECT_ROOT / config["consistency_contract"]
    consistency = pd.read_csv(consistency_path) if consistency_path.is_file() else pd.DataFrame()
    if consistency.empty:
        consistency_blocking = pd.DataFrame([{"check_name": "consistency_contract_missing"}])
    else:
        consistency_blocking = consistency.loc[
            consistency.status.isin(["fail", "blocked"]) & consistency.severity.eq("critical")
        ]
    infrastructure_ready = bool(manifests) and not missing_manifests
    reference_lineage_valid = not reference_issues
    full_lineage_valid = not full_issues
    flags = readiness_flags(
        status, profiles, lineage_status=lineage_status,
        reference_infrastructure_ready=infrastructure_ready,
        reference_lineage_valid=reference_lineage_valid,
        semantic_consistency_pass=consistency_blocking.empty,
        full_research_contracts_pass=all(contract_pass(PROJECT_ROOT / item) for item in config.get("full_research_prerequisites", [])),
        liquidity_contract_pass=contract_pass(PROJECT_ROOT / config["capability_prerequisites"]["liquidity_residualized"]),
        historical_exposure_contract_pass=contract_pass(PROJECT_ROOT / config["capability_prerequisites"]["historical_exposure"]),
    )

    output = PROJECT_ROOT / config["output_dir"]
    output.mkdir(parents=True, exist_ok=True)
    status.to_csv(output / "prerequisite_status.csv", index=False, encoding="utf-8-sig")
    reasons = {
        "reference_infrastructure_ready": "Module, profile, manifest, and synthetic-contract infrastructure is available.",
        "reference_pipeline_ready": "Requires current real-data contracts, lineage freshness, and semantic consistency.",
        "reference_ready": "Deprecated compatibility alias of reference_pipeline_ready.",
        "full_research_ready": "Requires homogeneous full_research artifacts and complete lineage.",
        "core_model_ready": "Core training inherits the full-research and complete-lineage requirements.",
        "liquidity_residualized_model_ready": "Adds the liquidity residualization capability contract.",
        "historical_exposure_model_ready": "Adds genuine historical PIT industry and market-cap exposure data.",
        "model_training_started": "Training remains outside this infrastructure PR.",
    }
    critical_names = {"reference_infrastructure_ready", "reference_pipeline_ready", "reference_ready", "model_training_started"}
    contract = pd.DataFrame([
        {
            "check_name": name,
            "status": "pass" if value or name == "model_training_started" else "blocked",
            "observed_value": value,
            "required_value": False if name == "model_training_started" else True,
            "severity": "critical" if name in critical_names else "capability",
            "reason": reasons[name],
        }
        for name, value in flags.items()
    ])
    contract.to_csv(output / "contract_status.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame([item.__dict__ for item in reference_issues], columns=["check_name", "artifact_id", "reason", "stage_id", "severity"]).to_csv(output / "lineage_issues.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame([
        {"gate": "reference", "lineage_valid": reference_lineage_valid, "issue_count": len(reference_issues), "critical_issue_count": sum(item.severity == "critical" for item in reference_issues)},
        {"gate": "full_research", "lineage_valid": full_lineage_valid, "issue_count": len(full_issues), "critical_issue_count": sum(item.severity == "critical" for item in full_issues)},
    ]).to_csv(output / "lineage_validation_summary.csv", index=False, encoding="utf-8-sig")
    summary = flags | {
        "reference_ready_deprecated": True,
        "reference_lineage_valid": reference_lineage_valid,
        "full_research_lineage_valid": full_lineage_valid,
        "lineage_status": lineage_status,
        "missing_manifest_count": len(missing_manifests),
        "lineage_issue_count": len(reference_issues),
        "critical_lineage_issue_count": sum(item.severity == "critical" for item in reference_issues),
    }
    pd.DataFrame([summary]).to_csv(output / "readiness_summary.csv", index=False, encoding="utf-8-sig")
    (output / "model_comparison_report.md").write_text(
        "# Factor Model Comparison V1\n\n"
        + "\n".join(f"- {name}: `{str(value).lower()}`" for name, value in flags.items())
        + f"\n- Reference lineage valid: `{str(reference_lineage_valid).lower()}`\n"
        + "- Training remains outside this PR.\n",
        encoding="utf-8",
    )
    output_files = [item for item in output.iterdir() if item.is_file() and item.name != "artifact_manifest.json"]
    write_stage_artifact_manifest(
        project_root=PROJECT_ROOT, stage_id="factor_model_comparison_v1", config=config,
        output_dir=output, output_files=output_files, code_state=code_state,
        input_manifest_paths=input_paths,
        missing_lineage_fields=[f"input_manifest:{item}" for item in missing_manifests],
        lineage_status=lineage_status,
    )
    print(contract.to_string(index=False))
    return 0 if flags["reference_infrastructure_ready"] and not flags["model_training_started"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
