from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from research_validation.feature_matrix import canonical_hash, file_sha256

from .feature_pool_policy import POLICY_A, _load_verified_eligibility
from .protocol import resolve


STAGE_ID = "ml_clustering_ablation_v1"
POLICY_D = "all_existing_stable_core"
POLICY_IDS = (POLICY_A, POLICY_D)


def _truthy(value: Any) -> bool:
    return value is True or value == 1 or str(value).strip().lower() == "true"


def load_clustering_ablation_config(path: Path) -> dict[str, Any]:
    config = yaml.safe_load(path.read_text(encoding="utf-8"))
    if config.get("stage_id") != STAGE_ID:
        raise ValueError("unexpected clustering-ablation stage")
    if tuple(config.get("policy_ids", [])) != POLICY_IDS:
        raise ValueError("clustering-ablation policy IDs or order changed")
    required_false = (
        "authoritative_execution",
        "unbiased_final_estimate",
        "selection_authorized",
        "strategy_v2_authorized",
    )
    if any(config.get(field) is not False for field in required_false):
        raise ValueError("clustering ablation must remain non-authoritative diagnostic research")
    if config.get("decision_authority") != "diagnostic_only":
        raise ValueError("clustering ablation must remain diagnostic_only")
    if config.get("historical_test_already_observed") is not True:
        raise ValueError("clustering ablation must declare the observed historical test")
    baseline = yaml.safe_load(
        resolve(config["parents"]["baseline_policy_config"]).read_text(encoding="utf-8")
    )
    if config.get("canary") != baseline.get("canary"):
        raise ValueError("clustering-ablation canary must equal the frozen MVP canary")
    if config["parents"]["lightgbm_config"] != baseline["parents"]["lightgbm_config"]:
        raise ValueError("clustering ablation must reuse the frozen LightGBM config")
    return config


def _verified_csv(path: Path, manifest: dict[str, Any]) -> pd.DataFrame:
    expected = manifest.get("output_file_hashes", {}).get(path.name)
    if not expected or file_sha256(path) != expected:
        raise ValueError(f"frozen parent hash mismatch: {path}")
    return pd.read_csv(path)


def _cluster_annotations(config: dict[str, Any]) -> pd.DataFrame:
    parents = config["parents"]
    manifest_path = resolve(parents["clustering_artifact_manifest"])
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("stage_id") != "factor_clustering_v2" or manifest.get(
        "artifact_status"
    ) != "pass":
        raise ValueError("unexpected clustering parent artifact")
    membership = _verified_csv(resolve(parents["cluster_membership"]), manifest)
    representatives = _verified_csv(
        resolve(parents["cluster_representatives"]), manifest
    )
    exclusions = _verified_csv(resolve(parents["cluster_exclusions"]), manifest)
    scores = pd.concat(
        [
            representatives[["outer_split_id", "factor", "representative_score"]].assign(
                is_representative=True
            ),
            exclusions[["outer_split_id", "factor", "representative_score"]].assign(
                is_representative=False
            ),
        ],
        ignore_index=True,
    )
    if scores.duplicated(["outer_split_id", "factor"]).any():
        raise ValueError("duplicate clustering annotations")
    annotations = membership.merge(
        scores,
        on=["outer_split_id", "factor"],
        how="left",
        validate="one_to_one",
    )
    if annotations[["representative_score", "is_representative"]].isna().any().any():
        raise ValueError("incomplete clustering annotations")
    return annotations


def build_clustering_ablation_manifests(
    config: dict[str, Any],
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    parents = config["parents"]
    baseline_features_path = resolve(parents["baseline_feature_manifest"])
    baseline_policies_path = resolve(parents["baseline_policy_manifest"])
    baseline_features = pd.read_csv(baseline_features_path)
    baseline_policies = pd.read_csv(baseline_policies_path)
    eligibility_freeze_path = resolve(parents["eligibility_freeze"])
    eligibility_decisions_path = resolve(parents["eligibility_decisions"])
    eligibility_freeze, eligibility = _load_verified_eligibility(
        eligibility_freeze_path, eligibility_decisions_path
    )

    stability_manifest_path = resolve(parents["stability_artifact_manifest"])
    stability_manifest = json.loads(stability_manifest_path.read_text(encoding="utf-8"))
    if stability_manifest.get("stage_id") != "factor_rolling_stability_v2" or stability_manifest.get(
        "artifact_status"
    ) != "pass":
        raise ValueError("unexpected stability parent artifact")
    stability = _verified_csv(resolve(parents["stability_board"]), stability_manifest)
    annotations = _cluster_annotations(config)
    clustering_manifest_path = resolve(parents["clustering_artifact_manifest"])
    clustering_manifest = json.loads(clustering_manifest_path.read_text(encoding="utf-8"))

    rows: list[dict[str, Any]] = []
    policy_rows: list[dict[str, Any]] = []
    exclusion_rows: list[dict[str, Any]] = []
    for split_id in [str(value) for value in config["split_ids"]]:
        baseline_a = baseline_features.loc[
            baseline_features["outer_split_id"].astype(str).eq(split_id)
            & baseline_features["policy_id"].astype(str).eq(POLICY_A)
        ].sort_values("feature_order", kind="stable")
        baseline_policy = baseline_policies.loc[
            baseline_policies["outer_split_id"].astype(str).eq(split_id)
            & baseline_policies["policy_id"].astype(str).eq(POLICY_A)
        ]
        if len(baseline_policy) != 1 or baseline_a.empty:
            raise ValueError(f"missing frozen Policy A: {split_id}")
        a_factors = baseline_a["factor"].astype(str).tolist()
        if canonical_hash(a_factors) != str(baseline_policy.iloc[0]["feature_order_sha256"]):
            raise ValueError(f"frozen Policy A order mismatch: {split_id}")

        split_stability = stability.loc[
            stability["outer_split_id"].astype(str).eq(split_id),
            ["factor", "stability_role"],
        ].copy()
        split_eligibility = eligibility.loc[
            eligibility["outer_split_id"].astype(str).eq(split_id),
            [
                "factor",
                "source_family",
                "correctness_pass",
                "data_qualified",
                "eligibility_reason",
            ],
        ].copy()
        if split_stability["factor"].duplicated().any() or split_eligibility[
            "factor"
        ].duplicated().any():
            raise ValueError(f"duplicate parent membership: {split_id}")
        stable = split_stability.loc[
            split_stability["stability_role"].astype(str).eq("stable_core")
        ].merge(split_eligibility, on="factor", how="left", validate="one_to_one")
        if stable["correctness_pass"].isna().any():
            raise ValueError(f"stable_core absent from eligibility freeze: {split_id}")
        incorrect = stable.loc[~stable["correctness_pass"].map(_truthy)]
        if not incorrect.empty:
            raise ValueError(
                f"stable_core correctness failed closed for {split_id}: "
                f"{incorrect['factor'].astype(str).tolist()}"
            )
        excluded = stable.loc[~stable["data_qualified"].map(_truthy)].copy()
        for row in excluded.itertuples(index=False):
            exclusion_rows.append(
                {
                    "outer_split_id": split_id,
                    "factor": str(row.factor),
                    "stability_role": "stable_core",
                    "correctness_pass": True,
                    "data_qualified": False,
                    "eligibility_reason": str(row.eligibility_reason),
                    "exclusion_semantics": "frozen_data_eligibility",
                }
            )
        qualified = stable.loc[stable["data_qualified"].map(_truthy)].merge(
            annotations.loc[annotations["outer_split_id"].astype(str).eq(split_id)],
            on="factor",
            how="left",
            validate="one_to_one",
        )
        if qualified[["cluster_id", "representative_score", "is_representative"]].isna().any().any():
            raise ValueError(f"qualified stable_core lacks cluster annotation: {split_id}")
        d_set = set(qualified["factor"].astype(str))
        if not set(a_factors).issubset(d_set):
            raise ValueError(f"frozen Policy A is not a subset of D: {split_id}")
        additions = qualified.loc[~qualified["factor"].astype(str).isin(a_factors)].sort_values(
            ["source_family", "factor"], kind="stable"
        )["factor"].astype(str).tolist()
        d_factors = a_factors + additions
        qualified_by_factor = qualified.set_index("factor", drop=False)
        for policy_id, factors in ((POLICY_A, a_factors), (POLICY_D, d_factors)):
            for order, factor in enumerate(factors):
                annotation = qualified_by_factor.loc[factor]
                rows.append(
                    {
                        "outer_split_id": split_id,
                        "policy_id": policy_id,
                        "factor": factor,
                        "feature_order": order,
                        "source_family": str(annotation["source_family"]),
                        "stability_role": "stable_core",
                        "correctness_pass": True,
                        "data_qualified": True,
                        "cluster_id": str(annotation["cluster_id"]),
                        "is_representative": _truthy(annotation["is_representative"]),
                        "representative_score": float(annotation["representative_score"]),
                        "inclusion_reason": (
                            "frozen_strict_current_baseline_member"
                            if policy_id == POLICY_A
                            else "existing_stable_core_and_frozen_data_qualified"
                        ),
                        "decision_authority": "diagnostic_only",
                        "selection_authorized": False,
                        "strategy_v2_authorized": False,
                    }
                )
            feature_pool_hash = canonical_hash(sorted(factors))
            feature_order_hash = canonical_hash(factors)
            if policy_id == POLICY_A and feature_order_hash != str(
                baseline_policy.iloc[0]["feature_order_sha256"]
            ):
                raise AssertionError(f"Policy A changed: {split_id}")
            policy_rows.append(
                {
                    "outer_split_id": split_id,
                    "policy_id": policy_id,
                    "factor_count": len(factors),
                    "feature_pool_sha256": feature_pool_hash,
                    "feature_order_sha256": feature_order_hash,
                    "policy_a_unchanged": True,
                    "policy_a_allowlist_sha256": str(
                        baseline_policy.iloc[0]["policy_a_allowlist_sha256"]
                    ),
                    "baseline_feature_manifest_sha256": file_sha256(
                        baseline_features_path
                    ),
                    "baseline_policy_manifest_sha256": file_sha256(
                        baseline_policies_path
                    ),
                    "eligibility_freeze_sha256": file_sha256(eligibility_freeze_path),
                    "eligibility_decisions_sha256": eligibility_freeze["decisions_sha256"],
                    "stable_core_parent_artifact_id": stability_manifest["artifact_id"],
                    "stability_board_sha256": file_sha256(resolve(parents["stability_board"])),
                    "clustering_parent_artifact_id": clustering_manifest["artifact_id"],
                    "clustering_manifest_sha256": file_sha256(clustering_manifest_path),
                    "decision_authority": "diagnostic_only",
                    "selection_authorized": False,
                    "strategy_v2_authorized": False,
                }
            )
    features = pd.DataFrame(rows)
    policies = pd.DataFrame(policy_rows)
    exclusions = pd.DataFrame(exclusion_rows)
    return features, policies, exclusions


def write_clustering_ablation_manifests(
    *, output_dir: Path, features: pd.DataFrame, policies: pd.DataFrame, exclusions: pd.DataFrame
) -> None:
    targets = {
        "feature_pool_manifest.csv": features,
        "policy_manifest.csv": policies,
        "stable_core_eligibility_exclusions.csv": exclusions,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    if any((output_dir / name).exists() for name in targets):
        raise FileExistsError("clustering-ablation manifests are immutable")
    for name, frame in targets.items():
        frame.to_csv(output_dir / name, index=False, encoding="utf-8-sig")


def freeze_metadata_for_split(
    *, config: dict[str, Any], policy_manifest_path: Path, split_id: str
) -> dict[str, Any]:
    policies = pd.read_csv(policy_manifest_path)
    row = policies.loc[
        policies["outer_split_id"].astype(str).eq(split_id)
        & policies["policy_id"].astype(str).eq(POLICY_D)
    ]
    if len(row) != 1:
        raise ValueError(f"missing unique Policy D manifest row: {split_id}")
    values = row.iloc[0]
    return {
        "feature_pool_sha256": str(values["feature_pool_sha256"]),
        "policy_manifest_sha256": file_sha256(policy_manifest_path),
        "stable_core_parent_artifact_id": str(
            values["stable_core_parent_artifact_id"]
        ),
        "stability_board_sha256": str(values["stability_board_sha256"]),
        "clustering_parent_artifact_id": str(
            values["clustering_parent_artifact_id"]
        ),
        "clustering_manifest_sha256": str(values["clustering_manifest_sha256"]),
        "eligibility_freeze_sha256": str(values["eligibility_freeze_sha256"]),
        "eligibility_decisions_sha256": str(values["eligibility_decisions_sha256"]),
        "cluster_representative_gate_applied": False,
        "stable_core_definition_recomputed": False,
    }


def build_ablation_freeze_index(
    *,
    config: dict[str, Any],
    baseline_development_root: Path,
    ablation_development_root: Path,
) -> pd.DataFrame:
    from .feature_pool_experiment import _development_arm_complete

    rows: list[dict[str, Any]] = []
    candidate_hashes: set[str] = set()
    for split_id in [str(value) for value in config["split_ids"]]:
        for policy_id, root in (
            (POLICY_A, baseline_development_root),
            (POLICY_D, ablation_development_root),
        ):
            arm_dir = root / split_id / policy_id
            if not _development_arm_complete(arm_dir):
                raise PermissionError(f"freeze index blocked by incomplete arm: {arm_dir}")
            receipt = json.loads((arm_dir / "arm_receipt.json").read_text(encoding="utf-8"))
            freeze_path = arm_dir / "freeze.json"
            if int(receipt.get("test_read_count", -1)) != 0:
                raise PermissionError(f"pre-freeze test access reported: {split_id}/{policy_id}")
            candidate_hashes.add(str(receipt["candidate_table_sha256"]))
            rows.append(
                {
                    "outer_split_id": split_id,
                    "policy_id": policy_id,
                    "freeze_path": str(freeze_path.resolve()),
                    "freeze_sha256": file_sha256(freeze_path),
                    "candidate_count": int(receipt["candidate_count"]),
                    "candidate_table_sha256": str(receipt["candidate_table_sha256"]),
                    "test_read_count": 0,
                    "decision_authority": "diagnostic_only",
                    "selection_authorized": False,
                    "strategy_v2_authorized": False,
                }
            )
    index = pd.DataFrame(rows)
    if len(index) != len(config["split_ids"]) * len(POLICY_IDS):
        raise AssertionError("clustering-ablation freeze index is incomplete")
    if len(candidate_hashes) != 1:
        raise AssertionError("A and D did not share the frozen candidate table")
    target = ablation_development_root / "freeze_index.csv"
    if target.exists():
        observed = pd.read_csv(target)
        if canonical_hash(observed.to_dict("records")) != canonical_hash(
            index.to_dict("records")
        ):
            raise FileExistsError("existing clustering-ablation freeze index differs")
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        index.to_csv(target, index=False, encoding="utf-8-sig")
    return index
