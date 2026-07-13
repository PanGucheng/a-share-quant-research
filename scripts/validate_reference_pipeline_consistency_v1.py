from __future__ import annotations

import tempfile
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from portfolio.model_comparison import readiness_flags
from portfolio.score_construction import filter_eligible_representatives
from research_validation.lineage import CodeState, build_artifact_manifest, validate_current_upstream_ids, validate_manifest_outputs
from research_validation.pipeline_consistency import evaluate_semantic_consistency
from research_validation.profiles import Profile, ProfileType


def main() -> int:
    stability = pd.DataFrame([{"factor": "stale", "stability_role": "holdout", "eligible_window_count": 0}])
    history = pd.DataFrame([{"factor": "stale", "selected": False, "selection_eligible": False, "eligible": False, "frozen_direction": 1}])
    reps = pd.DataFrame([{"factor": "stale"}])
    weights = pd.DataFrame([{"factor": "stale"}])
    consistency = evaluate_semantic_consistency(stability, history, reps, weights, score_methods=set(), execution_methods=set(), diagnostic_methods=set())
    assert consistency.unexpected_clustering_factors == {"stale"}
    assert consistency.unexpected_score_factors == {"stale"}
    included, _ = filter_eligible_representatives(history)
    assert included.empty

    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        output = root / "scores.parquet"
        output.write_bytes(b"score")
        parent = build_artifact_manifest(stage_id="stability", profile=Profile("local_reference", ProfileType.REFERENCE), config={"v": 1}, output_files=[output], output_dir=root, code_state=CodeState("abc", False, ""), run_id="parent")
        child = build_artifact_manifest(stage_id="score", profile=Profile("local_reference", ProfileType.REFERENCE), config={"v": 1}, output_files=[output], output_dir=root, code_state=CodeState("abc", False, ""), input_manifests=[parent], run_id="child")
        current_parent = build_artifact_manifest(stage_id="stability", profile=Profile("local_reference", ProfileType.REFERENCE), config={"v": 2}, output_files=[output], output_dir=root, code_state=CodeState("abc", False, ""), run_id="new-parent")
        assert "stale_upstream_artifact" in {item.check_name for item in validate_current_upstream_ids([current_parent, child], {"score": ["stability"]})}
        output.write_bytes(b"tampered")
        assert "output_hash_mismatch" in {item.check_name for item in validate_manifest_outputs(child, root, config={"v": 1})}

    prerequisites = pd.DataFrame([{"status": "pass"}])
    flags = readiness_flags(prerequisites, [Profile("local_reference", ProfileType.REFERENCE)], lineage_status="reference_only", reference_infrastructure_ready=True, reference_lineage_valid=True, semantic_consistency_pass=False, full_research_contracts_pass=False, liquidity_contract_pass=False, historical_exposure_contract_pass=False)
    assert flags["reference_infrastructure_ready"]
    assert not flags["reference_pipeline_ready"]
    print("All reference pipeline consistency synthetic validations passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
