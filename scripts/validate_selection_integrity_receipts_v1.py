from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from research_validation.feature_matrix import file_sha256  # noqa: E402
from research_validation.lineage import load_artifact_manifest, validate_manifest_outputs  # noqa: E402


def resolve(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else (PROJECT_ROOT / path).resolve()


def effective_config(name: str, spec: dict[str, str]) -> dict[str, object]:
    config = yaml.safe_load(resolve(spec["config"]).read_text(encoding="utf-8")) or {}
    if name == "execution":
        config = {**config, "execution_semantics_sha256": file_sha256(resolve(config["execution_semantics"]))}
    return config


def main() -> int:
    readiness_config = yaml.safe_load(resolve("configs/full_research_669_readiness_v1.yaml").read_text(encoding="utf-8")) or {}
    manifests: dict[str, dict[str, object]] = {}
    for name, spec in readiness_config["evidence"].items():
        manifest_path = resolve(spec["manifest"])
        manifest = load_artifact_manifest(manifest_path)
        assert not validate_manifest_outputs(manifest, manifest_path.parent, config=effective_config(name, spec)), name
        assert manifest["artifact_status"] == "pass", name
        assert manifest["lineage_status"] == "complete" or (name == "qlib_environment" and manifest["lineage_status"] == "reference_only"), name
        assert not bool(manifest["code_dirty"]), name
        contract = pd.read_csv(resolve(spec["contract"]))
        assert contract.loc[contract["severity"].eq("critical"), "status"].eq("pass").all(), name
        manifests[name] = manifest

    for child_name, parent_names in readiness_config["expected_edges"].items():
        child_inputs = set(map(str, manifests[child_name]["input_artifact_ids"]))
        for parent_name in parent_names:
            assert str(manifests[parent_name]["artifact_id"]) in child_inputs, f"{child_name} missing {parent_name}"

    batch = pd.read_csv(resolve("outputs/full_research_feature_matrix_669_v1/current/batch_manifest.csv"))
    assert len(batch) == 30
    assert batch["status"].eq("pass").all()
    assert int(batch["factor_count"].sum()) == 669
    assert batch["key_schema_version"].eq(3).all()
    assert not batch["reindexed_from_cache"].astype(bool).any()
    assert batch["market_data_snapshot_artifact_id"].eq(manifests["raw_snapshot"]["artifact_id"]).all()
    assert batch["source_provenance_artifact_id"].eq(manifests["source_provenance"]["artifact_id"]).all()

    fdr = pd.read_csv(resolve("outputs/factor_multiple_testing_v1/full_research_669/fdr_results.csv"))
    assert len(fdr) == 3 * 669
    assert fdr.groupby("outer_split_id")["factor"].nunique().eq(669).all()
    assert fdr["included_folds"].eq("train").all()
    stability_receipts = pd.read_csv(resolve("outputs/factor_rolling_stability_v1/full_research_669/input_receipts.csv"))
    assert manifests["fdr"]["artifact_id"] in set(stability_receipts["artifact_id"])
    stability_contract = pd.read_csv(resolve("outputs/factor_rolling_stability_v1/full_research_669/contract_status.csv")).set_index("check_name")
    assert stability_contract.loc["internally_recomputed_fdr", "status"] == "pass"

    mutation = pd.read_csv(resolve("outputs/selection_mutation_contract_v1/full_research_669/mutation_results.csv"))
    assert len(mutation) == 36
    assert mutation[["development_projection_unchanged", "selection_payloads_unchanged", "mutation_effective"]].astype(bool).all().all()
    payload_hashes = pd.read_csv(resolve("outputs/selection_mutation_contract_v1/full_research_669/business_payload_hashes.csv"))
    assert "weights_sha256" in payload_hashes.columns

    freeze_index = pd.read_csv(resolve("outputs/pre_test_freeze_v1/full_research_669/pre_test_freeze_index.csv"))
    assert len(freeze_index) == 3
    assert freeze_index["test_release_count"].eq(0).all()
    for row in freeze_index.itertuples(index=False):
        path = resolve("outputs/pre_test_freeze_v1/full_research_669") / row.freeze_path
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert file_sha256(path) == row.freeze_sha256
        assert payload["freeze_id"] == row.freeze_id
        assert payload["model_binary_sha256"] == "not_applicable_transparent_baseline"

    score_receipt = pd.read_csv(resolve("outputs/split_transparent_score_v1/full_research_669/score_artifact.csv")).iloc[0]
    release_index = pd.read_csv(resolve("outputs/split_transparent_score_v1/full_research_669/test_release_index.csv"))
    assert len(release_index) == 3
    assert release_index["status"].eq("consumed").all()
    for row in release_index.itertuples(index=False):
        path = resolve("outputs/split_transparent_score_v1/full_research_669") / row.receipt_path
        receipt = json.loads(path.read_text(encoding="utf-8"))
        assert file_sha256(path) == row.receipt_sha256
        assert receipt["status"] == "consumed"
        assert receipt["score_artifact_sha256"] == score_receipt["sha256"]

    readiness_path = resolve("outputs/full_research_669_readiness_v1/current/artifact_manifest.json")
    readiness = load_artifact_manifest(readiness_path)
    assert not validate_manifest_outputs(readiness, readiness_path.parent)
    assert readiness["artifact_status"] == "pass"
    flags = pd.read_csv(readiness_path.parent / "readiness_summary.csv").iloc[0]
    for field in (
        "matrix_v3_provenance_ready", "purged_exact_assignments_ready", "labels_current_lineage", "daily_ic_current_lineage",
        "fdr_current_lineage", "selection_chain_current", "feature_selection_holdout_clean", "clustering_holdout_clean",
        "fdr_family_semantics_valid", "fdr_artifact_consumed", "raw_input_provenance_complete", "split_allowlists_frozen",
        "pre_test_freeze_contract_ready", "transparent_score_ready", "transparent_qlib_execution_ready", "core_model_ready", "pr5_model_training_ready",
    ):
        assert bool(flags[field]), field
    assert flags["selection_integrity_status"] == "ready"
    assert not bool(flags["model_entry_hard_stop_active"])
    assert not bool(flags["model_training_started"])
    assert not bool(flags["historical_oos_comparison_complete"])
    assert not bool(flags["production_model_selected"])
    correction = pd.read_csv(
        resolve(
            "outputs/accuracy_correction_v1/current/readiness_summary.csv"
        )
    ).iloc[0]
    assert bool(correction["selection_holdout_integrity_ready"])
    assert bool(correction["model_entry_hard_stop_active"])
    assert not bool(correction["model_research_ready"])
    assert not bool(correction["authoritative_oos_execution_ready"])
    assert not bool(correction["core_model_ready"])
    assert not bool(correction["pr5_model_training_ready"])
    print(
        "Historical selection lineage receipts passed; Accuracy Correction V1 "
        "supersedes their model-input and OOS authority."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
