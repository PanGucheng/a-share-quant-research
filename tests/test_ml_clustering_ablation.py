from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from model_research.clustering_ablation import (
    POLICY_D,
    build_clustering_ablation_manifests,
    freeze_metadata_for_split,
    load_clustering_ablation_config,
)
from model_research.feature_pool_experiment import run_coordinated_historical_replay
from model_research.feature_pool_policy import POLICY_A
from research_validation.feature_matrix import canonical_hash, file_sha256


def _write_csv(path: Path, rows: list[dict]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(path, index=False)
    return path


def _artifact_manifest(path: Path, stage_id: str, files: list[Path]) -> Path:
    payload = {
        "stage_id": stage_id,
        "artifact_status": "pass",
        "artifact_id": f"{stage_id}:frozen",
        "output_file_hashes": {file.name: file_sha256(file) for file in files},
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_policy_d_is_only_qualified_existing_stable_core_and_keeps_a_order(
    tmp_path: Path,
) -> None:
    baseline_features = _write_csv(
        tmp_path / "baseline_features.csv",
        [
            {
                "outer_split_id": "split_001",
                "policy_id": POLICY_A,
                "factor": factor,
                "feature_order": order,
            }
            for order, factor in enumerate(("rep_z", "rep_a"))
        ],
    )
    baseline_policies = _write_csv(
        tmp_path / "baseline_policies.csv",
        [
            {
                "outer_split_id": "split_001",
                "policy_id": POLICY_A,
                "factor_count": 2,
                "feature_order_sha256": canonical_hash(["rep_z", "rep_a"]),
                "policy_a_allowlist_sha256": "frozen-a",
            }
        ],
    )
    eligibility = _write_csv(
        tmp_path / "eligibility.csv",
        [
            {
                "outer_split_id": "split_001",
                "factor": factor,
                "source_family": family,
                "correctness_pass": True,
                "data_qualified": qualified,
                "eligibility_reason": "pass" if qualified else "quality_duplicate_pass",
            }
            for factor, family, qualified in (
                ("rep_z", "z", True),
                ("rep_a", "a", True),
                ("nonrep_b", "b", True),
                ("nonrep_a", "a", True),
                ("blocked", "c", False),
                ("conditional", "a", True),
            )
        ],
    )
    eligibility_freeze = tmp_path / "eligibility_freeze.json"
    eligibility_freeze.write_text(
        json.dumps(
            {
                "stage_id": "ml_feature_eligibility_mvp_v1",
                "audit_scope": "feature_only",
                "decision_authority": "diagnostic_only",
                "decisions_sha256": file_sha256(eligibility),
            }
        ),
        encoding="utf-8",
    )
    stability = _write_csv(
        tmp_path / "stability.csv",
        [
            {
                "outer_split_id": "split_001",
                "factor": factor,
                "stability_role": role,
            }
            for factor, role in (
                ("rep_z", "stable_core"),
                ("rep_a", "stable_core"),
                ("nonrep_b", "stable_core"),
                ("nonrep_a", "stable_core"),
                ("blocked", "stable_core"),
                ("conditional", "conditional_signal"),
            )
        ],
    )
    stability_manifest = _artifact_manifest(
        tmp_path / "stability_manifest.json", "factor_rolling_stability_v2", [stability]
    )
    clusters = _write_csv(
        tmp_path / "clusters.csv",
        [
            {"outer_split_id": "split_001", "factor": factor, "cluster_id": cluster}
            for factor, cluster in (
                ("rep_z", "c1"),
                ("rep_a", "c2"),
                ("nonrep_b", "c1"),
                ("nonrep_a", "c2"),
                ("blocked", "c1"),
            )
        ],
    )
    representatives = _write_csv(
        tmp_path / "representatives.csv",
        [
            {
                "outer_split_id": "split_001",
                "factor": factor,
                "representative_score": 1.0,
            }
            for factor in ("rep_z", "rep_a")
        ],
    )
    exclusions = _write_csv(
        tmp_path / "cluster_exclusions.csv",
        [
            {
                "outer_split_id": "split_001",
                "factor": factor,
                "representative_score": score,
            }
            for factor, score in (("nonrep_b", 0.8), ("nonrep_a", 0.7), ("blocked", 0.6))
        ],
    )
    clustering_manifest = _artifact_manifest(
        tmp_path / "clustering_manifest.json",
        "factor_clustering_v2",
        [clusters, representatives, exclusions],
    )
    config = {
        "split_ids": ["split_001"],
        "parents": {
            "baseline_feature_manifest": str(baseline_features),
            "baseline_policy_manifest": str(baseline_policies),
            "eligibility_freeze": str(eligibility_freeze),
            "eligibility_decisions": str(eligibility),
            "stability_board": str(stability),
            "stability_artifact_manifest": str(stability_manifest),
            "cluster_membership": str(clusters),
            "cluster_representatives": str(representatives),
            "cluster_exclusions": str(exclusions),
            "clustering_artifact_manifest": str(clustering_manifest),
        },
    }
    features, policies, rejected = build_clustering_ablation_manifests(config)
    repeated = build_clustering_ablation_manifests(config)
    pd.testing.assert_frame_equal(features, repeated[0])
    pd.testing.assert_frame_equal(policies, repeated[1])
    d = features.loc[features["policy_id"].eq(POLICY_D)].sort_values("feature_order")
    assert d["factor"].tolist() == ["rep_z", "rep_a", "nonrep_a", "nonrep_b"]
    assert d["stability_role"].eq("stable_core").all()
    assert d["data_qualified"].all()
    assert (~d["is_representative"]).sum() == 2
    assert "conditional" not in set(d["factor"])
    assert rejected["factor"].tolist() == ["blocked"]
    a = features.loc[features["policy_id"].eq(POLICY_A)].sort_values("feature_order")
    assert a["factor"].tolist() == ["rep_z", "rep_a"]
    assert policies.loc[policies["policy_id"].eq(POLICY_D), "factor_count"].item() == 4

    manifest_path = tmp_path / "policy_manifest.csv"
    policies.to_csv(manifest_path, index=False)
    metadata = freeze_metadata_for_split(
        config=config, policy_manifest_path=manifest_path, split_id="split_001"
    )
    assert metadata["cluster_representative_gate_applied"] is False
    assert metadata["stable_core_definition_recomputed"] is False


def test_clustering_ablation_config_keeps_observed_history_diagnostic_only() -> None:
    config = load_clustering_ablation_config(
        Path("configs/ml_clustering_ablation_v1.yaml")
    )
    assert config["historical_test_already_observed"] is True
    assert config["authoritative_execution"] is False
    assert config["unbiased_final_estimate"] is False
    assert config["decision_authority"] == "diagnostic_only"
    assert config["selection_authorized"] is False
    assert config["strategy_v2_authorized"] is False


def test_coordinated_replay_is_single_release_fail_closed(tmp_path: Path) -> None:
    replay_root = tmp_path / "historical_replay"
    replay_root.mkdir()
    try:
        run_coordinated_historical_replay(
            policy_config_path=tmp_path / "unused.yaml",
            feature_manifest_path=tmp_path / "unused.csv",
            development_root=tmp_path / "development",
            replay_root=replay_root,
        )
    except PermissionError as error:
        assert "single-release" in str(error)
    else:
        raise AssertionError("repeated coordinated release did not fail closed")
