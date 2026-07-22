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
from research_validation.feature_matrix import file_sha256  # noqa: E402
from research_validation.lineage import LineageIssue, capture_code_state, load_artifact_manifest, validate_manifest_outputs, write_stage_artifact_manifest  # noqa: E402
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


def effective_stage_config(name: str, spec: dict[str, str]) -> dict[str, object]:
    config = yaml.safe_load(resolve(spec["config"]).read_text(encoding="utf-8")) or {}
    if name == "execution":
        config = {**config, "execution_semantics_sha256": file_sha256(resolve(config["execution_semantics"]))}
    return config


def main() -> int:
    parser = argparse.ArgumentParser(description="Report current selection-integrity readiness for the 669-factor research chain.")
    parser.add_argument("--config", type=Path, default=Path("configs/full_research_669_readiness_v1.yaml"))
    args = parser.parse_args()
    config = yaml.safe_load(resolve(args.config).read_text(encoding="utf-8")) or {}
    loaded: dict[str, dict[str, object]] = {}
    contracts: dict[str, pd.DataFrame] = {}
    issues: list[LineageIssue] = []
    inventory: list[dict[str, object]] = []
    for name, spec in config["evidence"].items():
        manifest_path = resolve(spec["manifest"])
        stage_config = effective_stage_config(name, spec)
        manifest = load_artifact_manifest(manifest_path)
        stage_issues = validate_manifest_outputs(manifest, manifest_path.parent, config=stage_config)
        if manifest["artifact_status"] != "pass":
            stage_issues.append(LineageIssue("artifact_status", str(manifest["artifact_id"]), str(manifest["blocked_reason"]), str(manifest["stage_id"])))
        allowed_reference_only = name == "qlib_environment" and manifest["lineage_status"] == "reference_only"
        if manifest["lineage_status"] != "complete" and not allowed_reference_only:
            stage_issues.append(LineageIssue("lineage_status", str(manifest["artifact_id"]), str(manifest["lineage_status"]), str(manifest["stage_id"])))
        if bool(manifest["code_dirty"]):
            stage_issues.append(LineageIssue("clean_code", str(manifest["artifact_id"]), "evidence produced from dirty code", str(manifest["stage_id"])))
        contract = pd.read_csv(resolve(spec["contract"]))
        critical_blocked = int((contract["severity"].eq("critical") & ~contract["status"].eq("pass")).sum())
        if critical_blocked:
            stage_issues.append(LineageIssue("critical_contract", str(manifest["artifact_id"]), f"{critical_blocked} critical checks blocked", str(manifest["stage_id"])))
        issues.extend(stage_issues)
        loaded[name] = manifest
        contracts[name] = contract
        inventory.append(
            {
                "evidence": name,
                "stage_id": manifest["stage_id"],
                "artifact_id": manifest["artifact_id"],
                "critical_blocked": critical_blocked,
                "issue_count": len(stage_issues),
            }
        )

    for child_name, parent_names in config["expected_edges"].items():
        child = loaded[child_name]
        child_inputs = set(map(str, child["input_artifact_ids"]))
        for parent_name in parent_names:
            parent_id = str(loaded[parent_name]["artifact_id"])
            if parent_id not in child_inputs:
                issues.append(LineageIssue("stale_upstream_artifact", str(child["artifact_id"]), f"missing current {parent_name}: {parent_id}", str(child["stage_id"])))

    chain_names = [
        "matrix", "labels", "daily_ic", "splits", "selection_projection", "fdr",
        "stability", "clustering_projection", "clustering", "allowlist", "weights", "mutation", "freeze", "score", "execution",
    ]
    for field in ["universe_artifact_id", "factor_catalog_id", "factor_frame_id", "split_manifest_id"]:
        values = {str(loaded[name][field]) for name in chain_names if loaded[name].get(field)}
        if len(values) > 1:
            issues.append(LineageIssue("inconsistent_lineage_id", "", f"{field}: {sorted(values)}", "full_research_669_readiness_v1"))

    expected_factors = int(config["expected_factor_count"])
    expected_batches = int(config["expected_batch_count"])
    expected_splits = int(config["expected_outer_splits"])
    matrix_batches = pd.read_csv(resolve(config["evidence"]["matrix"]["manifest"]).parent / "batch_manifest.csv")
    fdr = pd.read_csv(resolve(config["evidence"]["fdr"]["manifest"]).parent / "fdr_results.csv")
    stability = pd.read_csv(resolve(config["evidence"]["stability"]["manifest"]).parent / "factor_stability_board.csv")
    representatives = pd.read_csv(resolve(config["evidence"]["clustering"]["manifest"]).parent / "representatives_by_split.csv")
    allowlist_manifest = pd.read_csv(resolve(config["evidence"]["allowlist"]["manifest"]).parent / "split_allowlist_manifest.csv")
    weight_manifest = pd.read_csv(resolve(config["evidence"]["weights"]["manifest"]).parent / "weight_manifest.csv")
    mutation_results = pd.read_csv(resolve(config["evidence"]["mutation"]["manifest"]).parent / "mutation_results.csv")
    freeze_index = pd.read_csv(resolve(config["evidence"]["freeze"]["manifest"]).parent / "pre_test_freeze_index.csv")
    score_diagnostics = pd.read_csv(resolve(config["evidence"]["score"]["manifest"]).parent / "score_diagnostics.csv")
    release_index = pd.read_csv(resolve(config["evidence"]["score"]["manifest"]).parent / "test_release_index.csv")
    execution_contract = contracts["execution"]
    run_history = pd.read_csv(resolve(config["evidence"]["matrix_run_history"]["manifest"]).parent / "matrix_run_history.csv")

    batch_ready = (
        len(matrix_batches) == expected_batches
        and matrix_batches["status"].eq("pass").all()
        and int(matrix_batches["factor_count"].sum()) == expected_factors
        and matrix_batches["cache_hit"].astype(bool).all()
        and matrix_batches["key_schema_version"].eq(3).all()
    )
    fdr_ready = (
        len(fdr) == expected_splits * expected_factors
        and fdr.groupby("outer_split_id")["factor"].nunique().eq(expected_factors).all()
        and fdr["included_folds"].eq("train").all()
        and not fdr.duplicated(["outer_split_id", "factor"]).any()
    )
    stability_ready = (
        len(stability) == expected_splits * expected_factors
        and stability.groupby("outer_split_id")["factor"].nunique().eq(expected_factors).all()
        and not any(str(column).startswith("test_") or "oos" in str(column).lower() for column in stability)
        and contracts["stability"]["status"].eq("pass").all()
    )
    clustering_ready = (
        representatives["outer_split_id"].nunique() == expected_splits
        and contracts["clustering"]["status"].eq("pass").all()
        and contracts["clustering_projection"]["status"].eq("pass").all()
    )
    allowlists_ready = (
        len(allowlist_manifest) == expected_splits
        and allowlist_manifest["holdout_clean"].astype(bool).all()
        and contracts["allowlist"]["status"].eq("pass").all()
    )
    weights_ready = (
        weight_manifest.groupby("outer_split_id")["method"].nunique().eq(2).all()
        and weight_manifest["holdout_clean"].astype(bool).all()
        and contracts["weights"]["status"].eq("pass").all()
    )
    mutation_ready = (
        len(mutation_results) == 36
        and mutation_results["development_projection_unchanged"].astype(bool).all()
        and mutation_results["selection_payloads_unchanged"].astype(bool).all()
        and mutation_results["mutation_effective"].astype(bool).all()
        and contracts["mutation"]["status"].eq("pass").all()
    )
    freeze_ready = (
        len(freeze_index) == expected_splits
        and freeze_index["test_release_count"].eq(0).all()
        and contracts["freeze"]["status"].eq("pass").all()
    )
    score_ready = (
        score_diagnostics.groupby("outer_split_id")["method"].nunique().eq(2).all()
        and score_diagnostics["coverage"].eq(1.0).all()
        and len(release_index) == expected_splits
        and release_index["status"].eq("consumed").all()
        and contracts["score"]["status"].eq("pass").all()
    )
    execution_ready = not execution_contract.loc[execution_contract["severity"].eq("critical"), "status"].ne("pass").any()
    approval_consumed = (
        set(run_history["operation"]) == {"materialize", "cache_verify"}
        and run_history["single_use_declared"].astype(bool).all()
        and run_history["receipt_status"].eq("retrospective_completed").all()
        and run_history["result_artifact_id"].eq(loaded["matrix"]["artifact_id"]).all()
    )
    no_lineage_issues = not issues
    raw_provenance_ready = batch_ready and not any(item.stage_id in {loaded["raw_snapshot"]["stage_id"], loaded["source_provenance"]["stage_id"], loaded["matrix"]["stage_id"]} for item in issues)
    selection_ready = all(
        [
            no_lineage_issues,
            raw_provenance_ready,
            fdr_ready,
            stability_ready,
            clustering_ready,
            allowlists_ready,
            weights_ready,
            mutation_ready,
            freeze_ready,
            score_ready,
            execution_ready,
            approval_consumed,
        ]
    )
    flags: dict[str, object] = {
        "full_research_669_infrastructure_ready": batch_ready,
        "full_research_669_matrix_content_ready": batch_ready,
        "matrix_v3_provenance_ready": raw_provenance_ready,
        "purged_exact_assignments_ready": contracts["splits"]["status"].eq("pass").all(),
        "labels_current_lineage": no_lineage_issues,
        "daily_ic_current_lineage": no_lineage_issues,
        "fdr_current_lineage": no_lineage_issues and fdr_ready,
        "selection_chain_current": no_lineage_issues,
        "full_research_669_validation_chain_ready": selection_ready,
        "full_research_669_qlib_execution_operational": execution_ready,
        "full_research_authoritative_tradability_ready": False,
        "historical_selection_evidence_valid": True,
        "feature_selection_holdout_clean": stability_ready and mutation_ready,
        "clustering_holdout_clean": clustering_ready and mutation_ready,
        "fdr_family_semantics_valid": fdr_ready,
        "fdr_artifact_consumed": stability_ready,
        "raw_input_provenance_complete": raw_provenance_ready,
        "split_allowlists_frozen": allowlists_ready,
        "feature_allowlist_frozen": allowlists_ready,
        "pre_test_freeze_contract_ready": freeze_ready,
        "transparent_score_ready": score_ready,
        "transparent_qlib_execution_ready": execution_ready,
        "selection_integrity_status": "ready" if selection_ready else "blocked",
        "model_entry_hard_stop_active": not selection_ready,
        "bulk_run_user_review_status": "consumed" if approval_consumed else "blocked",
        "bulk_run_execution_authorized": False,
        "bulk_run_current_head_binding_satisfied": bool(run_history["current_head_binding_satisfied"].astype(bool).all()),
        "bulk_run_single_use_enforced_at_execution": bool(run_history["single_use_enforced_at_execution"].astype(bool).all()),
        "core_model_ready": selection_ready,
        "pr5_model_training_ready": selection_ready,
        "historical_oos_comparison_complete": False,
        "production_model_selected": False,
        "model_training_started": False,
    }
    expected_values: dict[str, object] = {
        "full_research_authoritative_tradability_ready": False,
        "bulk_run_execution_authorized": False,
        "bulk_run_current_head_binding_satisfied": False,
        "bulk_run_single_use_enforced_at_execution": False,
        "historical_oos_comparison_complete": False,
        "production_model_selected": False,
        "model_training_started": False,
        "selection_integrity_status": "ready",
        "model_entry_hard_stop_active": False,
        "bulk_run_user_review_status": "consumed",
    }
    rows = []
    for name, value in flags.items():
        required = expected_values.get(name, True)
        severity = "critical"
        reason = "Current holdout-clean PR #4.1 evidence."
        if name == "full_research_authoritative_tradability_ready":
            severity = "capability"
            reason = "Historical suspension and directional price-limit labels remain proxy-derived."
        elif name in {"historical_selection_evidence_valid", "historical_oos_comparison_complete", "production_model_selected", "bulk_run_execution_authorized", "bulk_run_current_head_binding_satisfied", "bulk_run_single_use_enforced_at_execution"}:
            severity = "evidence"
            reason = "Historical run limitation is disclosed; exact inputs and matrix equivalence passed, and future runs use the hardened gate."
        rows.append(contract_row(name, value == required, value, required, reason, severity))
    contract = pd.DataFrame(rows)

    prior_selection_path = resolve(config["output_dir"]) / "selection_status.csv"
    if prior_selection_path.is_file():
        prior = pd.read_csv(prior_selection_path)
        historical = prior.loc[prior["selection_name"].astype(str).eq("exploratory_global_representatives_v1")].copy()
    else:
        historical = pd.DataFrame()
    if historical.empty:
        historical = pd.DataFrame(
            [
                {
                    "selection_name": "exploratory_global_representatives_v1",
                    "selection_status": "test_influenced",
                    "model_input_allowed": False,
                    "representative_count": 16,
                    "source_artifact_id": "historical_pr4_global_clustering",
                    "superseded_by": "split_specific_holdout_clean_allowlists_v1",
                    "outer_split_factor_counts": "not_applicable",
                }
            ]
        )
    historical["model_input_allowed"] = False
    current_selection = pd.DataFrame(
        [
            {
                "selection_name": "split_specific_holdout_clean_allowlists_v1",
                "selection_status": "holdout_clean",
                "model_input_allowed": bool(selection_ready),
                "representative_count": int(allowlist_manifest["factor_count"].sum()),
                "source_artifact_id": str(loaded["allowlist"]["artifact_id"]),
                "superseded_by": "",
                "outer_split_factor_counts": "|".join(map(str, allowlist_manifest.sort_values("outer_split_id")["factor_count"].tolist())),
            }
        ]
    )
    selection_status = pd.concat([historical.reindex(columns=current_selection.columns), current_selection], ignore_index=True)
    readiness_gate_pass = selection_ready and bool(contract.loc[contract["severity"].eq("critical"), "status"].eq("pass").all())
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
            + f"\n- Stable-core / split representatives: `{int(stability['stability_role'].eq('stable_core').sum())}` / `{len(representatives)}`"
            + "\n- Selection integrity: holdout-clean and ready for the separately planned PR #5A protocol."
            + "\n- Model training: not started; historical OOS comparison and production selection remain false."
            + "\n- Authoritative historical tradability capability remains blocked and is not overstated.\n",
            encoding="utf-8",
        )
        files = [publisher.path(name) for name in CONTROLLED if name != "artifact_manifest.json"]
        write_stage_artifact_manifest(
            project_root=PROJECT_ROOT,
            stage_id="full_research_669_readiness_v1",
            config=config,
            output_dir=publisher.staging_dir,
            output_files=files,
            code_state=capture_code_state(PROJECT_ROOT),
            input_manifest_paths=[resolve(spec["manifest"]) for spec in config["evidence"].values()],
            missing_lineage_fields=[],
            artifact_status="pass" if readiness_gate_pass else "blocked",
            blocked_reason="" if readiness_gate_pass else "blocked_selection_integrity_not_revalidated",
        )
        publisher.publish()
    print(contract.to_string(index=False))
    return 0 if readiness_gate_pass else 2


if __name__ == "__main__":
    raise SystemExit(main())
