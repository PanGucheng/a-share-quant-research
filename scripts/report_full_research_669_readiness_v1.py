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
from research_validation.lineage import (  # noqa: E402
    LineageIssue,
    capture_code_state,
    load_artifact_manifest,
    validate_manifest_outputs,
    write_stage_artifact_manifest,
)
from research_validation.stage_output import StageOutputPublisher  # noqa: E402

CONTROLLED = [
    "artifact_manifest.json",
    "contract_status.csv",
    "evidence_inventory.csv",
    "lineage_issues.csv",
    "readiness_summary.csv",
    "selection_status.csv",
    "full_research_669_readiness_report.md",
]


def resolve(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else (PROJECT_ROOT / path).resolve()


def main() -> int:
    parser = argparse.ArgumentParser(description="Report evidence readiness for the frozen 669-factor research run.")
    parser.add_argument("--config", type=Path, default=Path("configs/full_research_669_readiness_v1.yaml"))
    args = parser.parse_args()
    config = yaml.safe_load(resolve(args.config).read_text(encoding="utf-8")) or {}
    loaded: dict[str, dict[str, object]] = {}
    issues: list[LineageIssue] = []
    inventory: list[dict[str, object]] = []
    for name, spec in config["evidence"].items():
        manifest_path = resolve(spec["manifest"])
        stage_config = yaml.safe_load(resolve(spec["config"]).read_text(encoding="utf-8")) or {}
        manifest = load_artifact_manifest(manifest_path)
        stage_issues = validate_manifest_outputs(manifest, resolve(stage_config["output_dir"]), config=stage_config)
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

    chain_evidence = {
        name: value
        for name, value in loaded.items()
        if name not in {"raw_snapshot", "source_provenance", "matrix_reproducibility", "matrix_run_history"}
    }
    for field in ["universe_artifact_id", "factor_catalog_id", "factor_frame_id", "split_manifest_id"]:
        values = {str(value[field]) for value in chain_evidence.values() if value.get(field)}
        if len(values) > 1:
            issues.append(LineageIssue("inconsistent_lineage_id", "", f"{field}: {sorted(values)}", "full_research_669_readiness_v1"))

    expected_factors = int(config["expected_factor_count"])
    expected_batches = int(config["expected_batch_count"])
    matrix_batches = pd.read_csv(resolve(config["evidence"]["matrix"]["manifest"]).parent / "batch_manifest.csv")
    stability = pd.read_csv(resolve(config["evidence"]["stability"]["manifest"]).parent / "factor_stability_board.csv")
    representatives = pd.read_csv(resolve(config["evidence"]["clustering"]["manifest"]).parent / "cluster_representatives.csv")
    score_availability = pd.read_csv(resolve(config["evidence"]["score"]["manifest"]).parent / "score_availability.csv")
    execution_contract = pd.read_csv(resolve(config["evidence"]["execution"]["contract"]))
    issue_names_by_stage = {}
    for issue in issues:
        issue_names_by_stage.setdefault(issue.stage_id, set()).add(issue.check_name)
    matrix_support_names = {"catalog", "universe", "raw_snapshot", "source_provenance", "matrix", "matrix_reproducibility", "matrix_run_history"}
    matrix_support_stages = {str(loaded[name]["stage_id"]) for name in matrix_support_names}
    matrix_support_valid = not any(issue.stage_id in matrix_support_stages for issue in issues)
    batch_ready = (
        len(matrix_batches) == expected_batches
        and matrix_batches["status"].eq("pass").all()
        and int(matrix_batches["factor_count"].sum()) == expected_factors
        and matrix_batches["cache_hit"].astype(bool).all()
    )
    validation_ready = len(stability) == expected_factors and not representatives.empty and score_availability["status"].eq("pass").all()
    execution_ready = not execution_contract.loc[execution_contract["severity"].eq("critical"), "status"].isin(["blocked", "fail"]).any()
    historical_selection_evidence_valid = validation_ready
    matrix_v3_provenance_ready = matrix_support_valid and batch_ready
    split_output_dir = resolve(config["evidence"]["splits"]["manifest"]).parent
    purged_exact_assignments_ready = (
        not issue_names_by_stage.get(str(loaded["splits"]["stage_id"]), set()).difference({"stale_upstream_artifact"})
        and (split_output_dir / "date_assignments.csv").is_file()
        and (split_output_dir / "label_intervals.csv").is_file()
    )
    current_edge_issues = [item for item in issues if item.check_name == "stale_upstream_artifact"]
    stale_stages = {item.stage_id for item in current_edge_issues}
    labels_current_lineage = str(loaded["labels"]["stage_id"]) not in stale_stages
    daily_ic_current_lineage = labels_current_lineage and str(loaded["daily_ic"]["stage_id"]) not in stale_stages
    fdr_current_lineage = daily_ic_current_lineage and str(loaded["fdr"]["stage_id"]) not in stale_stages
    selection_chain_current = not current_edge_issues
    flags: dict[str, object] = {
        "full_research_669_infrastructure_ready": matrix_v3_provenance_ready,
        "full_research_669_matrix_content_ready": matrix_v3_provenance_ready,
        "matrix_v3_provenance_ready": matrix_v3_provenance_ready,
        "purged_exact_assignments_ready": purged_exact_assignments_ready,
        "labels_current_lineage": labels_current_lineage,
        "daily_ic_current_lineage": daily_ic_current_lineage,
        "fdr_current_lineage": fdr_current_lineage,
        "selection_chain_current": selection_chain_current,
        "full_research_669_validation_chain_ready": False,
        "full_research_669_qlib_execution_operational": execution_ready,
        "full_research_authoritative_tradability_ready": False,
        "historical_selection_evidence_valid": historical_selection_evidence_valid,
        "feature_selection_holdout_clean": False,
        "clustering_holdout_clean": False,
        "fdr_family_semantics_valid": False,
        "fdr_artifact_consumed": False,
        "raw_input_provenance_complete": False,
        "split_allowlists_frozen": False,
        "feature_allowlist_frozen": False,
        "selection_integrity_status": "blocked",
        "model_entry_hard_stop_active": True,
        "bulk_run_user_review_status": "not_requested",
        "bulk_run_execution_authorized": False,
        "core_model_ready": False,
        "pr5_model_training_ready": False,
        "model_training_started": False,
    }
    expected_false = {
        "fdr_current_lineage",
        "selection_chain_current",
        "feature_allowlist_frozen",
        "bulk_run_execution_authorized",
        "core_model_ready",
        "pr5_model_training_ready",
        "model_training_started",
    }
    expected_values: dict[str, object] = {
        **{name: False for name in expected_false},
        "selection_integrity_status": "blocked",
        "model_entry_hard_stop_active": True,
        "bulk_run_user_review_status": "not_requested",
    }
    rows = []
    for name, value in flags.items():
        required = expected_values.get(name, True)
        passed = value == required
        reason = "Evidence-backed PR #4 engineering capability."
        severity = "critical"
        if name == "full_research_authoritative_tradability_ready":
            reason = "Historical suspension and directional price-limit labels remain proxy-derived."
            severity = "capability"
        elif name in {"historical_selection_evidence_valid"}:
            reason = "Historical PR #4 selection evidence is preserved but cannot authorize model input."
            severity = "evidence"
        elif name in expected_values:
            reason = "Selection-integrity hard stop required before PR #4.1 revalidation."
        elif not passed:
            reason = "Selection-integrity capability has not been revalidated."
        rows.append(contract_row(name, passed, value, required, reason, severity))
    contract = pd.DataFrame(rows)
    selection_status = pd.DataFrame(
        [
            {
                "selection_name": "exploratory_global_representatives_v1",
                "selection_status": "test_influenced",
                "model_input_allowed": False,
                "representative_count": int(len(representatives)),
                "source_artifact_id": str(loaded["clustering"]["artifact_id"]),
                "superseded_by": "split_specific_holdout_clean_allowlists_v1",
            }
        ]
    )
    output_dir = resolve(config["output_dir"])
    with StageOutputPublisher(output_dir, CONTROLLED) as publisher:
        contract.to_csv(publisher.path("contract_status.csv"), index=False, encoding="utf-8-sig")
        pd.DataFrame(inventory).to_csv(publisher.path("evidence_inventory.csv"), index=False, encoding="utf-8-sig")
        pd.DataFrame([item.__dict__ for item in issues], columns=["check_name", "artifact_id", "reason", "stage_id", "severity"]).to_csv(publisher.path("lineage_issues.csv"), index=False, encoding="utf-8-sig")
        pd.DataFrame([flags]).to_csv(publisher.path("readiness_summary.csv"), index=False, encoding="utf-8-sig")
        selection_status.to_csv(publisher.path("selection_status.csv"), index=False, encoding="utf-8-sig")
        publisher.path("full_research_669_readiness_report.md").write_text(
            "# Full-Research 669-Factor Readiness V1\n\n"
            + "\n".join(f"- {name}: `{str(value).lower()}`" for name, value in flags.items())
            + f"\n\n- Evidence stages: `{len(loaded)}`\n- Lineage issues: `{len(issues)}`"
            + f"\n- Current-lineage stale edges: `{len(current_edge_issues)}`"
            + f"\n- Historical stable core / exploratory representatives: `{int(stability['stability_role'].eq('stable_core').sum())}` / `{len(representatives)}`"
            + "\n- Selection integrity: blocked; historical representatives are test-influenced and forbidden as model input."
            + "\n- Scope: PR #4 engineering evidence remains available; PR #4.1 selection revalidation and model training have not started.\n",
            encoding="utf-8",
        )
        files = [publisher.path(name) for name in CONTROLLED if name != "artifact_manifest.json"]
        safety_gate_pass = (
            flags["selection_integrity_status"] == "blocked"
            and bool(flags["model_entry_hard_stop_active"])
            and not bool(flags["feature_allowlist_frozen"])
            and not bool(flags["core_model_ready"])
            and not bool(flags["pr5_model_training_ready"])
            and not bool(flags["model_training_started"])
            and not bool(selection_status["model_input_allowed"].iloc[0])
        )
        write_stage_artifact_manifest(
            project_root=PROJECT_ROOT,
            stage_id="full_research_669_readiness_v1",
            config=config,
            output_dir=publisher.staging_dir,
            output_files=files,
            code_state=capture_code_state(PROJECT_ROOT),
            input_manifest_paths=[resolve(spec["manifest"]) for spec in config["evidence"].values()],
            missing_lineage_fields=[],
            artifact_status="blocked",
            blocked_reason="blocked_selection_integrity_not_revalidated",
        )
        publisher.publish()
    print(contract.to_string(index=False))
    return 0 if safety_gate_pass else 2


if __name__ == "__main__":
    raise SystemExit(main())
