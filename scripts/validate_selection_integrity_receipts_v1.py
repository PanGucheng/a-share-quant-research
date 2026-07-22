from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from research_validation.lineage import load_artifact_manifest, validate_manifest_outputs  # noqa: E402


def resolve(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else (PROJECT_ROOT / path).resolve()


def assert_compact_artifact(config_path: str, manifest_path: str, contract_path: str) -> dict[str, object]:
    config = yaml.safe_load(resolve(config_path).read_text(encoding="utf-8")) or {}
    path = resolve(manifest_path)
    manifest = load_artifact_manifest(path)
    assert not validate_manifest_outputs(manifest, path.parent, config=config)
    assert manifest["artifact_status"] == "pass"
    contract = pd.read_csv(resolve(contract_path))
    assert contract["status"].eq("pass").all()
    return manifest


def main() -> int:
    raw = assert_compact_artifact(
        "configs/raw_market_data_snapshot_v1.yaml",
        "outputs/raw_market_data_snapshot_v1/full_research_669/artifact_manifest.json",
        "outputs/raw_market_data_snapshot_v1/full_research_669/contract_status.csv",
    )
    source = assert_compact_artifact(
        "configs/factor_source_provenance_v1.yaml",
        "outputs/factor_source_provenance_v1/current/artifact_manifest.json",
        "outputs/factor_source_provenance_v1/current/contract_status.csv",
    )
    matrix = assert_compact_artifact(
        "configs/full_research_feature_matrix_669_v1.yaml",
        "outputs/full_research_feature_matrix_669_v1/current/artifact_manifest.json",
        "outputs/full_research_feature_matrix_669_v1/current/contract_status.csv",
    )
    reproducibility = assert_compact_artifact(
        "configs/full_research_feature_matrix_669_reproducibility_v3.yaml",
        "outputs/full_research_feature_matrix_669_v1/reproducibility_v3/artifact_manifest.json",
        "outputs/full_research_feature_matrix_669_v1/reproducibility_v3/contract_status.csv",
    )
    history = assert_compact_artifact(
        "configs/matrix_run_history_669_v1.yaml",
        "outputs/full_research_feature_matrix_669_v1/run_history_v1/artifact_manifest.json",
        "outputs/full_research_feature_matrix_669_v1/run_history_v1/contract_status.csv",
    )

    matrix_inputs = set(map(str, matrix["input_artifact_ids"]))
    assert str(raw["artifact_id"]) in matrix_inputs
    assert str(source["artifact_id"]) in matrix_inputs
    assert str(matrix["artifact_id"]) in set(map(str, reproducibility["input_artifact_ids"]))
    history_inputs = set(map(str, history["input_artifact_ids"]))
    assert str(matrix["artifact_id"]) in history_inputs
    assert str(reproducibility["artifact_id"]) in history_inputs
    assert sum(value.startswith("bulk_run_review_v1:") for value in history_inputs) == 2

    batch = pd.read_csv(resolve("outputs/full_research_feature_matrix_669_v1/current/batch_manifest.csv"))
    assert len(batch) == 30
    assert batch["status"].eq("pass").all()
    assert int(batch["factor_count"].sum()) == 669
    assert batch["key_schema_version"].eq(3).all()
    assert not batch["reindexed_from_cache"].astype(bool).any()
    assert batch["market_data_snapshot_artifact_id"].eq(raw["artifact_id"]).all()
    assert batch["source_provenance_artifact_id"].eq(source["artifact_id"]).all()

    reproduction_contract = pd.read_csv(resolve("outputs/full_research_feature_matrix_669_v1/reproducibility_v3/contract_status.csv"))
    assert reproduction_contract["status"].eq("pass").all()
    run_history = pd.read_csv(resolve("outputs/full_research_feature_matrix_669_v1/run_history_v1/matrix_run_history.csv"))
    assert set(run_history["operation"]) == {"materialize", "cache_verify"}
    assert run_history["result_artifact_id"].eq(matrix["artifact_id"]).all()

    readiness_config = yaml.safe_load(resolve("configs/full_research_669_readiness_v1.yaml").read_text(encoding="utf-8")) or {}
    readiness_path = resolve("outputs/full_research_669_readiness_v1/current/artifact_manifest.json")
    readiness = load_artifact_manifest(readiness_path)
    assert not validate_manifest_outputs(readiness, readiness_path.parent, config=readiness_config)
    assert readiness["artifact_status"] == "blocked"
    readiness_inputs = set(map(str, readiness["input_artifact_ids"]))
    assert {str(raw["artifact_id"]), str(source["artifact_id"]), str(matrix["artifact_id"]), str(reproducibility["artifact_id"]), str(history["artifact_id"])}.issubset(readiness_inputs)
    flags = pd.read_csv(readiness_path.parent / "readiness_summary.csv").iloc[0]
    assert bool(flags["matrix_v3_provenance_ready"])
    assert bool(flags["purged_exact_assignments_ready"])
    assert bool(flags["labels_current_lineage"])
    assert bool(flags["daily_ic_current_lineage"])
    for field in ("fdr_current_lineage", "selection_chain_current", "core_model_ready", "pr5_model_training_ready", "model_training_started"):
        assert not bool(flags[field])
    assert flags["selection_integrity_status"] == "blocked"
    assert bool(flags["model_entry_hard_stop_active"])
    print("Compact provenance, matrix reproducibility, run history, and blocked readiness receipts passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
