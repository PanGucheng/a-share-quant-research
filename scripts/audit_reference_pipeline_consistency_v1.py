from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from research_validation.lineage import capture_code_state, write_stage_artifact_manifest  # noqa: E402
from research_validation.pipeline_consistency import evaluate_semantic_consistency  # noqa: E402


def _read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path) if path.is_file() else pd.DataFrame()


def _set(frame: pd.DataFrame, column: str) -> set[str]:
    if frame.empty or column not in frame:
        return set()
    return set(frame[column].dropna().astype(str))


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit reference pipeline semantic consistency without mutating upstream stages.")
    parser.add_argument("--config", type=Path, default=Path("configs/reference_pipeline_consistency_v1.yaml"))
    args = parser.parse_args()
    config_path = args.config if args.config.is_absolute() else PROJECT_ROOT / args.config
    config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    code_state = capture_code_state(PROJECT_ROOT)

    stability = _read_csv(PROJECT_ROOT / config["stability_board"])
    history = _read_csv(PROJECT_ROOT / config["selection_history"])
    representatives = _read_csv(PROJECT_ROOT / config["cluster_representatives"])
    weights = _read_csv(PROJECT_ROOT / config["factor_weights"])
    diagnostics = _read_csv(PROJECT_ROOT / config["diagnostic_comparison"])
    score_path = PROJECT_ROOT / config["scores"]
    scores = pd.read_parquet(score_path, columns=["method"]) if score_path.is_file() else pd.DataFrame(columns=["method"])

    eligible_roles = {"stable_core", "conditional_signal", "risk_control"}
    eligible = stability.loc[
        stability.get("stability_role", pd.Series(index=stability.index, dtype=object)).isin(eligible_roles)
        & stability.get("eligible_window_count", pd.Series(0, index=stability.index)).gt(0)
    ]
    selected = history.loc[history.get("selected", pd.Series(False, index=history.index)).fillna(False).astype(bool)]
    eligible_factors = _set(eligible, "factor")
    selected_factors = _set(selected, "factor")
    representative_factors = _set(representatives, "factor")
    weight_factors = _set(weights, "factor")
    score_methods = _set(scores, "method")
    diagnostic_methods = _set(diagnostics, "method") & set(config["current_diagnostic_methods"])
    execution_contract = _read_csv(PROJECT_ROOT / config["execution_contract"])
    execution_ready = not execution_contract.empty and execution_contract.loc[
        execution_contract.status.isin(["fail", "blocked"]) & execution_contract.severity.eq("critical")
    ].empty
    execution_methods = {str(config["execution_method"])} if execution_ready else set()

    normalized_execution = {"stable_equal" if value == "equal_directional_zscore" else value for value in execution_methods} | execution_methods
    semantic = evaluate_semantic_consistency(
        stability, history, representatives, weights, score_methods=score_methods,
        execution_methods=execution_methods, diagnostic_methods=diagnostic_methods,
    )
    unexpected_clustering = set(semantic.unexpected_clustering_factors)
    unexpected_score = set(semantic.unexpected_score_factors)
    unexpected_execution = set(semantic.unexpected_execution_methods)
    unexpected_diagnostics = diagnostic_methods - (normalized_execution | score_methods)

    inventory = pd.DataFrame([
        {"check_name": "stability_factor_count", "observed_value": len(stability), "expected_value": "reported", "status": "pass"},
        {"check_name": "stability_eligible_factor_count", "observed_value": len(eligible_factors), "expected_value": ">=1 for pipeline", "status": "blocked" if not eligible_factors else "pass"},
        {"check_name": "selection_selected_row_count", "observed_value": len(selected), "expected_value": ">=1 for pipeline", "status": "blocked" if selected.empty else "pass"},
        {"check_name": "cluster_representative_count", "observed_value": len(representative_factors), "expected_value": "subset of eligible", "status": "fail" if unexpected_clustering else "pass"},
        {"check_name": "score_weight_factor_count", "observed_value": len(weight_factors), "expected_value": "subset of selected representatives", "status": "fail" if unexpected_score else "pass"},
        {"check_name": "score_row_count", "observed_value": len(scores), "expected_value": "0 when upstream blocked", "status": "fail" if not eligible_factors and len(scores) else "pass"},
    ])
    stale = pd.DataFrame([
        {"stage_id": "factor_clustering_v1", "stale": bool(unexpected_clustering), "reason": "representatives_not_in_current_eligible_stability" if unexpected_clustering else ""},
        {"stage_id": "factor_score_construction_v1", "stale": bool(unexpected_score or (not eligible_factors and len(scores))), "reason": "weights_or_runtime_not_supported_by_current_selection" if unexpected_score or (not eligible_factors and len(scores)) else ""},
        {"stage_id": "a_share_execution_v1", "stale": bool(not eligible_factors and len(scores)), "reason": "execution_consumes_stale_score" if not eligible_factors and len(scores) else ""},
        {"stage_id": "pre_model_diagnostics_v1", "stale": bool(not eligible_factors and diagnostic_methods), "reason": "diagnostics_consume_stale_current_methods" if not eligible_factors and diagnostic_methods else ""},
    ])
    consistency = pd.DataFrame([
        {"check_name": "clustering_factors_subset_stability", "status": "fail" if unexpected_clustering else "pass", "observed_value": len(unexpected_clustering), "required_value": 0, "severity": "critical"},
        {"check_name": "score_factors_subset_selected_representatives", "status": "fail" if unexpected_score else "pass", "observed_value": len(unexpected_score), "required_value": 0, "severity": "critical"},
        {"check_name": "execution_methods_subset_score_methods", "status": "fail" if unexpected_execution else "pass", "observed_value": len(unexpected_execution), "required_value": 0, "severity": "critical"},
        {"check_name": "diagnostic_methods_subset_execution_methods", "status": "fail" if unexpected_diagnostics else "pass", "observed_value": len(unexpected_diagnostics), "required_value": 0, "severity": "critical"},
        {"check_name": "current_reference_pipeline", "status": "blocked" if not eligible_factors else "pass", "observed_value": len(eligible_factors), "required_value": ">=1", "severity": "critical"},
    ])
    contract = consistency.copy()
    contract["reason"] = [
        "Clustering inputs must be current eligible stability factors.",
        "Score factors must be selected, eligible representatives.",
        "Execution methods must exist in the current score artifact.",
        "Current diagnostic methods must have current execution evidence.",
        "No factor passes the hardened reference eligibility contract.",
    ]

    output = PROJECT_ROOT / config["output_dir"]
    output.mkdir(parents=True, exist_ok=True)
    inventory.to_csv(output / "inconsistency_inventory.csv", index=False, encoding="utf-8-sig")
    stale.to_csv(output / "stale_artifact_inventory.csv", index=False, encoding="utf-8-sig")
    consistency.to_csv(output / "stage_consistency_status.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame({"factor": sorted(unexpected_clustering)}).to_csv(output / "unexpected_clustering_factors.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame({"factor": sorted(unexpected_score)}).to_csv(output / "unexpected_score_factors.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame({"method": sorted(unexpected_execution | unexpected_diagnostics)}).to_csv(output / "unexpected_execution_methods.csv", index=False, encoding="utf-8-sig")
    contract.to_csv(output / "contract_status.csv", index=False, encoding="utf-8-sig")
    (output / "consistency_audit_report.md").write_text(
        "# Reference Pipeline Consistency Audit V1\n\n"
        f"- Stability factors: `{len(stability)}`; eligible: `{len(eligible_factors)}`\n"
        f"- Selected history rows: `{len(selected)}`\n"
        f"- Active representatives: `{len(representative_factors)}`\n"
        f"- Active score factors: `{len(weight_factors)}`; score rows: `{len(scores)}`\n"
        f"- Stale downstream stages: `{int(stale.stale.sum())}`\n"
        "- Audit conclusion: `reference_pipeline_ready=false`\n",
        encoding="utf-8",
    )
    output_files = [item for item in output.iterdir() if item.is_file() and item.name != "artifact_manifest.json"]
    write_stage_artifact_manifest(
        project_root=PROJECT_ROOT, stage_id="reference_pipeline_consistency_v1", config=config,
        output_dir=output, output_files=output_files, code_state=code_state,
        input_manifest_paths=[PROJECT_ROOT / item for item in config.get("input_manifests", [])],
        missing_lineage_fields=["v1_1_consistency_gap"], lineage_status="reference_only",
    )
    print(contract.to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
