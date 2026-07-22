from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from research_validation.lineage import load_artifact_manifest, validate_manifest_outputs  # noqa: E402


def main() -> int:
    config_path = PROJECT_ROOT / "configs/full_research_669_readiness_v1.yaml"
    config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    output_dir = PROJECT_ROOT / config["output_dir"]
    manifest = load_artifact_manifest(output_dir / "artifact_manifest.json")
    assert not validate_manifest_outputs(manifest, output_dir, config=config)
    assert manifest["artifact_status"] == "pass"
    assert manifest["blocked_reason"] == ""
    lineage_issues = pd.read_csv(output_dir / "lineage_issues.csv")
    assert lineage_issues.empty
    flags = pd.read_csv(output_dir / "readiness_summary.csv").iloc[0]
    for name in [
        "full_research_669_infrastructure_ready",
        "full_research_669_matrix_content_ready",
        "matrix_v3_provenance_ready",
        "purged_exact_assignments_ready",
        "labels_current_lineage",
        "daily_ic_current_lineage",
        "fdr_current_lineage",
        "selection_chain_current",
        "full_research_669_validation_chain_ready",
        "full_research_669_qlib_execution_operational",
        "feature_selection_holdout_clean",
        "clustering_holdout_clean",
        "fdr_family_semantics_valid",
        "fdr_artifact_consumed",
        "raw_input_provenance_complete",
        "split_allowlists_frozen",
        "feature_allowlist_frozen",
        "pre_test_freeze_contract_ready",
        "transparent_score_ready",
        "transparent_qlib_execution_ready",
        "core_model_ready",
        "pr5_model_training_ready",
    ]:
        assert bool(flags[name]), name
    for name in [
        "full_research_authoritative_tradability_ready",
        "model_entry_hard_stop_active",
        "bulk_run_execution_authorized",
        "bulk_run_current_head_binding_satisfied",
        "bulk_run_single_use_enforced_at_execution",
        "historical_oos_comparison_complete",
        "production_model_selected",
        "model_training_started",
    ]:
        assert not bool(flags[name]), name
    assert flags["selection_integrity_status"] == "ready"
    assert flags["bulk_run_user_review_status"] == "consumed"
    selections = pd.read_csv(output_dir / "selection_status.csv").set_index("selection_name")
    historical = selections.loc["exploratory_global_representatives_v1"]
    current = selections.loc["split_specific_holdout_clean_allowlists_v1"]
    assert historical["selection_status"] == "test_influenced"
    assert not bool(historical["model_input_allowed"])
    assert current["selection_status"] == "holdout_clean"
    assert bool(current["model_input_allowed"])
    assert int(current["representative_count"]) == 148
    assert current["outer_split_factor_counts"] == "48|46|54"
    print("Full-research 669 selection integrity is ready; model training remains unstarted.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
