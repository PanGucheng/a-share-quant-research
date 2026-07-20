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
from research_validation.lineage import LineageIssue, capture_code_state, load_artifact_manifest, validate_manifest_outputs, write_stage_artifact_manifest  # noqa: E402
from research_validation.stage_output import StageOutputPublisher  # noqa: E402

CONTROLLED = ["artifact_manifest.json", "contract_status.csv", "evidence_inventory.csv", "lineage_issues.csv", "readiness_summary.csv", "full_research_trial_readiness_report.md"]


def resolve(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else (PROJECT_ROOT / path).resolve()


def main() -> int:
    parser = argparse.ArgumentParser(description="Report compact evidence readiness for the 80-factor full-research trial.")
    parser.add_argument("--config", type=Path, default=Path("configs/full_research_trial_readiness_v1.yaml"))
    args = parser.parse_args()
    config = yaml.safe_load(resolve(args.config).read_text(encoding="utf-8")) or {}
    loaded: dict[str, dict[str, object]] = {}
    issues: list[LineageIssue] = []
    inventory: list[dict[str, object]] = []
    for name, spec in config["evidence"].items():
        manifest_path = resolve(spec["manifest"])
        stage_config = yaml.safe_load(resolve(spec["config"]).read_text(encoding="utf-8")) or {}
        manifest = load_artifact_manifest(manifest_path)
        output_dir = resolve(stage_config["output_dir"])
        stage_issues = validate_manifest_outputs(manifest, output_dir, config=stage_config)
        if manifest["artifact_status"] != "pass":
            stage_issues.append(LineageIssue("artifact_status", str(manifest["artifact_id"]), str(manifest["blocked_reason"]), str(manifest["stage_id"])))
        if manifest["lineage_status"] != "complete":
            stage_issues.append(LineageIssue("lineage_status", str(manifest["artifact_id"]), str(manifest["lineage_status"]), str(manifest["stage_id"])))
        if bool(manifest["code_dirty"]):
            stage_issues.append(LineageIssue("clean_code", str(manifest["artifact_id"]), "evidence produced from dirty code", str(manifest["stage_id"])))
        contract = pd.read_csv(resolve(spec["contract"]))
        critical_blocked = int((contract["severity"].eq("critical") & contract["status"].isin(["blocked", "fail"])).sum())
        if critical_blocked:
            stage_issues.append(LineageIssue("critical_contract", str(manifest["artifact_id"]), f"{critical_blocked} critical checks blocked", str(manifest["stage_id"])))
        issues.extend(stage_issues)
        loaded[name] = manifest
        inventory.append({"evidence": name, "stage_id": manifest["stage_id"], "artifact_id": manifest["artifact_id"], "critical_blocked": critical_blocked, "issue_count": len(stage_issues)})

    for child_name, parent_names in config["expected_edges"].items():
        child = loaded[child_name]
        inputs = set(map(str, child["input_artifact_ids"]))
        for parent_name in parent_names:
            parent_id = str(loaded[parent_name]["artifact_id"])
            if parent_id not in inputs:
                issues.append(LineageIssue("stale_upstream_artifact", str(child["artifact_id"]), f"missing current {parent_name}: {parent_id}", str(child["stage_id"])))

    lineage_ids = {
        field: {str(value[field]) for value in loaded.values() if value.get(field)}
        for field in ["universe_artifact_id", "factor_catalog_id", "factor_frame_id", "split_manifest_id"]
    }
    for field, values in lineage_ids.items():
        if len(values) > 1:
            issues.append(LineageIssue("inconsistent_lineage_id", "", f"{field}: {sorted(values)}", "full_research_trial_readiness_v1"))

    matrix_batches = pd.read_csv(resolve(config["evidence"]["matrix"]["manifest"]).parent / "batch_manifest.csv")
    stability = pd.read_csv(resolve(config["evidence"]["stability"]["manifest"]).parent / "factor_stability_board.csv")
    representatives = pd.read_csv(resolve(config["evidence"]["clustering"]["manifest"]).parent / "cluster_representatives.csv")
    score_availability = pd.read_csv(resolve(config["evidence"]["score"]["manifest"]).parent / "score_availability.csv")
    execution_contract = pd.read_csv(resolve(config["evidence"]["execution"]["contract"]))
    evidence_valid = not issues
    batch_ready = len(matrix_batches) == 5 and matrix_batches["status"].eq("pass").all() and int(matrix_batches["factor_count"].sum()) == 80 and matrix_batches["cache_hit"].astype(bool).all()
    validation_ready = len(stability) == 80 and not representatives.empty and score_availability["status"].eq("pass").all()
    execution_ready = not execution_contract.loc[execution_contract["severity"].eq("critical"), "status"].isin(["blocked", "fail"]).any()
    flags = {
        "full_research_trial_infrastructure_ready": evidence_valid and batch_ready,
        "full_research_validation_chain_ready": evidence_valid and validation_ready,
        "full_research_qlib_execution_operational": evidence_valid and execution_ready,
        "full_research_authoritative_tradability_ready": False,
        "full_research_trial_ready": evidence_valid and batch_ready and validation_ready and execution_ready,
        "pr4_scale_up_ready": evidence_valid and batch_ready and validation_ready and execution_ready,
        "model_training_started": False,
    }
    rows = [
        contract_row(name, value if name != "model_training_started" else not value, value, False if name == "model_training_started" else True,
                     "Historical suspension and directional price-limit labels remain proxy-derived." if name == "full_research_authoritative_tradability_ready" else "Evidence-backed PR #3 gate.",
                     "capability" if name == "full_research_authoritative_tradability_ready" else "critical")
        for name, value in flags.items()
    ]
    contract = pd.DataFrame(rows)
    output_dir = resolve(config["output_dir"])
    code_state = capture_code_state(PROJECT_ROOT)
    with StageOutputPublisher(output_dir, CONTROLLED) as publisher:
        contract.to_csv(publisher.path("contract_status.csv"), index=False, encoding="utf-8-sig")
        pd.DataFrame(inventory).to_csv(publisher.path("evidence_inventory.csv"), index=False, encoding="utf-8-sig")
        pd.DataFrame([item.__dict__ for item in issues], columns=["check_name", "artifact_id", "reason", "stage_id", "severity"]).to_csv(publisher.path("lineage_issues.csv"), index=False, encoding="utf-8-sig")
        pd.DataFrame([flags]).to_csv(publisher.path("readiness_summary.csv"), index=False, encoding="utf-8-sig")
        publisher.path("full_research_trial_readiness_report.md").write_text(
            "# Full-Research 80-Factor Trial Readiness V1\n\n" + "\n".join(f"- {name}: `{str(value).lower()}`" for name, value in flags.items())
            + f"\n\n- Evidence stages: `{len(loaded)}`\n- Lineage issues: `{len(issues)}`\n- Stable core / representatives: `{int(stability['stability_role'].eq('stable_core').sum())}` / `{len(representatives)}`\n"
            + "- Scope: 80-factor pipeline trial only; 669-factor run and model training have not started.\n",
            encoding="utf-8",
        )
        files = [publisher.path(name) for name in CONTROLLED if name != "artifact_manifest.json"]
        write_stage_artifact_manifest(
            project_root=PROJECT_ROOT, stage_id="full_research_trial_readiness_v1", config=config,
            output_dir=publisher.staging_dir, output_files=files, code_state=code_state,
            input_manifest_paths=[resolve(spec["manifest"]) for spec in config["evidence"].values()],
            missing_lineage_fields=[], artifact_status="pass" if flags["full_research_trial_ready"] else "blocked",
            blocked_reason="" if flags["full_research_trial_ready"] else "blocked_full_research_trial_readiness",
        )
        publisher.publish()
    print(contract.to_string(index=False))
    return 0 if flags["full_research_trial_ready"] and not flags["model_training_started"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
