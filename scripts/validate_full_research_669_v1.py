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
    assert manifest["artifact_status"] == "blocked"
    assert manifest["blocked_reason"] == "blocked_selection_integrity_not_revalidated"
    lineage_issues = pd.read_csv(output_dir / "lineage_issues.csv")
    assert not lineage_issues.empty
    assert set(lineage_issues["check_name"]) == {"stale_upstream_artifact"}
    flags = pd.read_csv(output_dir / "readiness_summary.csv").iloc[0]
    assert bool(flags["full_research_669_infrastructure_ready"])
    assert bool(flags["full_research_669_matrix_content_ready"])
    assert bool(flags["matrix_v3_provenance_ready"])
    assert bool(flags["purged_exact_assignments_ready"])
    assert not bool(flags["full_research_669_validation_chain_ready"])
    assert bool(flags["full_research_669_qlib_execution_operational"])
    assert not bool(flags["full_research_authoritative_tradability_ready"])
    assert bool(flags["historical_selection_evidence_valid"])
    for name in [
        "feature_selection_holdout_clean",
        "clustering_holdout_clean",
        "fdr_family_semantics_valid",
        "fdr_artifact_consumed",
        "raw_input_provenance_complete",
        "split_allowlists_frozen",
        "feature_allowlist_frozen",
        "bulk_run_execution_authorized",
        "core_model_ready",
        "pr5_model_training_ready",
        "labels_current_lineage",
        "daily_ic_current_lineage",
        "fdr_current_lineage",
        "selection_chain_current",
    ]:
        assert not bool(flags[name])
    assert flags["selection_integrity_status"] == "blocked"
    assert bool(flags["model_entry_hard_stop_active"])
    assert flags["bulk_run_user_review_status"] == "not_requested"
    assert not bool(flags["model_training_started"])
    selection = pd.read_csv(output_dir / "selection_status.csv").iloc[0]
    assert selection["selection_name"] == "exploratory_global_representatives_v1"
    assert selection["selection_status"] == "test_influenced"
    assert not bool(selection["model_input_allowed"])
    print("Full-research 669 engineering evidence passed; selection integrity is honestly blocked.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
