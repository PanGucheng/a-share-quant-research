from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from model_research.gates import assert_model_scope_allowed  # noqa: E402
from model_research.schemas import (  # noqa: E402
    PREDICTION_COLUMNS,
    prediction_schema_violations,
)
from research_validation.lineage import (  # noqa: E402
    load_artifact_manifest,
    validate_manifest_outputs,
)


REQUIRED_CONTRACTS = {
    "authoritative_selection_closure_consumed",
    "date_split_semantics_authority_consumed",
    "legacy_purged_split_not_direct_parent",
    "date_assignment_payload_hash_equal",
    "matrix_v4_hash_valid",
    "labels_v2_hash_valid",
    "split_dates_exact",
    "split_allowlists_exact",
    "feature_order_exact",
    "target_transform_frozen",
    "metric_registry_frozen",
    "prediction_schema_leakage_free",
    "test_read_count_before_freeze_zero",
    "scope_aware_model_gate_valid",
    "solver_auto_forbidden",
    "fixed_checkpoint_selection_policy",
    "validation_mutation_hash_policy",
}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate compact PR #5A research model protocol evidence."
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("outputs/research_model_protocol_v1/current"),
    )
    args = parser.parse_args()
    output = args.output_dir if args.output_dir.is_absolute() else PROJECT_ROOT / args.output_dir
    manifest = load_artifact_manifest(output / "artifact_manifest.json")
    issues = validate_manifest_outputs(manifest, output)
    assert not issues, issues
    assert manifest["artifact_status"] == "pass"
    assert manifest["lineage_status"] == "complete"
    input_ids = set(manifest["input_artifact_ids"])
    assert any(item.startswith("date_split_semantics_v1:") for item in input_ids)
    assert any(
        item.startswith("research_selection_lineage_closure_v1:")
        for item in input_ids
    )
    assert not any(item.startswith("purged_walk_forward_v1:") for item in input_ids)

    contracts = pd.read_csv(output / "contract_status.csv")
    assert REQUIRED_CONTRACTS <= set(contracts["check_name"])
    critical = contracts.loc[contracts["severity"].astype(str).eq("critical")]
    assert critical["status"].eq("pass").all()

    readiness = pd.read_csv(output / "readiness_summary.csv")
    assert len(readiness) == 1
    row = readiness.iloc[0].to_dict()
    assert_model_scope_allowed(
        row,
        experiment_class="post_observation_research",
        operation="training",
    )
    assert not bool(row["research_model_experiment_started"])
    assert not bool(row["model_training_started"])
    assert bool(row["production_model_hard_stop_active"])
    assert not bool(row["production_model_selected"])
    assert not bool(row["core_model_ready"])
    assert not bool(row["pr5_model_training_ready"])

    schema = json.loads(
        (output / "prediction_schema.json").read_text(encoding="utf-8")
    )
    assert schema["columns"] == list(PREDICTION_COLUMNS)
    assert not prediction_schema_violations(schema["columns"])
    access = pd.read_csv(output / "access_audit.csv")
    test_access = access.loc[access["fold"].astype(str).eq("test")]
    assert int(test_access["read_count"].sum()) == 0
    print("Research model protocol V1 validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
