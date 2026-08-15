from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from research_validation.feature_matrix import canonical_hash, file_sha256

from .inputs import load_split_feature_order


STAGE_ID = "ml_feature_pool_mvp_v1"
POLICY_A = "strict_current_baseline"
POLICY_B = "current_plus_existing_conditional_signal"
POLICY_C = "broad_data_qualified"
POLICY_IDS = (POLICY_A, POLICY_B, POLICY_C)
DIAGNOSTIC_OUTCOMES = frozenset({"strict_favored", "broader_favored", "mixed"})


def _truthy(value: Any) -> bool:
    return value is True or value == 1 or str(value).strip().lower() == "true"


def load_policy_config(path: Path) -> dict[str, Any]:
    config = yaml.safe_load(path.read_text(encoding="utf-8"))
    if config.get("stage_id") != STAGE_ID:
        raise ValueError("unexpected feature-pool policy stage")
    if tuple(config.get("policy_ids", [])) != POLICY_IDS:
        raise ValueError("policy IDs or ordering differ from the MVP V1 contract")
    if config.get("decision_authority") != "diagnostic_only":
        raise ValueError("feature-pool experiment must remain diagnostic_only")
    if config.get("selection_authorized") is not False:
        raise ValueError("policy winner selection is forbidden")
    if config.get("strategy_v2_authorized") is not False:
        raise ValueError("Strategy V2 authorization is forbidden")
    return config


def validate_diagnostic_outcome(payload: dict[str, Any]) -> None:
    outcome = payload.get("diagnostic_outcome")
    if outcome in DIAGNOSTIC_OUTCOMES:
        if payload.get("decision_authority") != "diagnostic_only":
            raise ValueError(f"{outcome} requires decision_authority=diagnostic_only")
        if payload.get("selection_authorized") is not False:
            raise ValueError(f"{outcome} cannot authorize a policy winner")
        if payload.get("strategy_v2_authorized") is not False:
            raise ValueError(f"{outcome} cannot authorize Strategy V2")


def _load_verified_eligibility(
    freeze_path: Path, decisions_path: Path
) -> tuple[dict[str, Any], pd.DataFrame]:
    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
    if freeze.get("stage_id") != "ml_feature_eligibility_mvp_v1":
        raise ValueError("unexpected eligibility freeze")
    if freeze.get("audit_scope") != "feature_only":
        raise ValueError("policy requires a feature-only eligibility freeze")
    if freeze.get("decision_authority") != "diagnostic_only":
        raise ValueError("eligibility freeze is not diagnostic_only")
    if file_sha256(decisions_path) != freeze.get("decisions_sha256"):
        raise ValueError("eligibility decisions hash mismatch")
    return freeze, pd.read_csv(decisions_path)


def _policy_rows(
    *,
    split_id: str,
    a_order: list[str],
    eligibility: pd.DataFrame,
    stability: pd.DataFrame,
) -> list[dict[str, Any]]:
    split_eligibility = eligibility.loc[
        eligibility["outer_split_id"].astype(str).eq(split_id)
    ].copy()
    if split_eligibility["factor"].duplicated().any():
        raise ValueError(f"duplicate eligibility factors for {split_id}")
    by_factor = split_eligibility.set_index("factor", drop=False)
    missing_a = sorted(set(a_order).difference(by_factor.index))
    if missing_a:
        raise ValueError(f"Policy A factors absent from eligibility audit: {missing_a}")
    incorrect_a = [
        factor
        for factor in a_order
        if not _truthy(by_factor.at[factor, "correctness_pass"])
    ]
    if incorrect_a:
        raise ValueError(
            f"Policy A correctness failed closed for {split_id}: {incorrect_a}"
        )

    split_stability = stability.loc[
        stability["outer_split_id"].astype(str).eq(split_id),
        ["factor", "stability_role"],
    ].copy()
    if split_stability["factor"].duplicated().any():
        raise ValueError(f"duplicate stability roles for {split_id}")
    roles = split_stability.set_index("factor")["stability_role"].astype(str).to_dict()
    qualified = set(
        split_eligibility.loc[
            split_eligibility["data_qualified"].map(_truthy), "factor"
        ].astype(str)
    )
    a_set = set(a_order)
    b_additions = sorted(
        factor
        for factor in qualified.difference(a_set)
        if roles.get(factor) == "conditional_signal"
    )
    c_additions = sorted(
        qualified.difference(a_set),
        key=lambda factor: (
            str(by_factor.at[factor, "source_family"]),
            factor,
        ),
    )
    orders = {
        POLICY_A: a_order,
        POLICY_B: a_order + sorted(
            b_additions,
            key=lambda factor: (str(by_factor.at[factor, "source_family"]), factor),
        ),
        POLICY_C: a_order + c_additions,
    }
    if not set(orders[POLICY_A]).issubset(orders[POLICY_B]) or not set(
        orders[POLICY_B]
    ).issubset(orders[POLICY_C]):
        raise AssertionError(f"A subset B subset C contract failed for {split_id}")

    rows: list[dict[str, Any]] = []
    for policy_id, factors in orders.items():
        for feature_order, factor in enumerate(factors):
            if factor in a_set:
                reason = "strict_current_baseline_member"
            elif policy_id == POLICY_B:
                reason = "data_qualified_existing_conditional_signal"
            else:
                reason = "broad_data_qualified_member"
            rows.append(
                {
                    "outer_split_id": split_id,
                    "policy_id": policy_id,
                    "factor": factor,
                    "feature_order": feature_order,
                    "source_family": by_factor.at[factor, "source_family"],
                    "stability_role": roles.get(factor, "not_applicable"),
                    "correctness_pass": _truthy(
                        by_factor.at[factor, "correctness_pass"]
                    ),
                    "data_qualified": _truthy(by_factor.at[factor, "data_qualified"]),
                    "inclusion_reason": reason,
                    "decision_authority": "diagnostic_only",
                    "selection_authorized": False,
                    "strategy_v2_authorized": False,
                }
            )
    return rows


def build_policy_manifests(
    *,
    split_ids: list[str],
    weights_path: Path,
    allowlist_path: Path,
    eligibility_freeze_path: Path,
    eligibility_decisions_path: Path,
    stability_path: Path,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    freeze, eligibility = _load_verified_eligibility(
        eligibility_freeze_path, eligibility_decisions_path
    )
    stability = pd.read_csv(stability_path)
    all_rows: list[dict[str, Any]] = []
    manifest_rows: list[dict[str, Any]] = []
    for split_id in split_ids:
        ordered, receipt = load_split_feature_order(
            weights_path, allowlist_path, outer_split_id=split_id
        )
        a_order = ordered["factor"].astype(str).tolist()
        rows = _policy_rows(
            split_id=split_id,
            a_order=a_order,
            eligibility=eligibility,
            stability=stability,
        )
        all_rows.extend(rows)
        split_rows = pd.DataFrame(rows)
        for policy_id in POLICY_IDS:
            factors = split_rows.loc[
                split_rows["policy_id"].eq(policy_id)
            ].sort_values("feature_order")["factor"].tolist()
            manifest_rows.append(
                {
                    "outer_split_id": split_id,
                    "policy_id": policy_id,
                    "factor_count": len(factors),
                    "feature_order_sha256": canonical_hash(factors),
                    "policy_a_correctness_pass": True,
                    "policy_a_allowlist_sha256": str(receipt["allowlist_sha256"]),
                    "eligibility_freeze_sha256": file_sha256(eligibility_freeze_path),
                    "eligibility_decisions_sha256": freeze["decisions_sha256"],
                    "decision_authority": "diagnostic_only",
                    "selection_authorized": False,
                    "strategy_v2_authorized": False,
                }
            )
    features = pd.DataFrame(all_rows)
    policies = pd.DataFrame(manifest_rows)
    for split_id in split_ids:
        counts = policies.loc[policies["outer_split_id"].eq(split_id)].set_index(
            "policy_id"
        )["factor_count"]
        if not counts[POLICY_A] <= counts[POLICY_B] <= counts[POLICY_C]:
            raise AssertionError(f"policy counts are not nested for {split_id}")
    return features, policies


def write_policy_manifests(
    *, output_dir: Path, features: pd.DataFrame, policies: pd.DataFrame
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    targets = [output_dir / "feature_pool_manifest.csv", output_dir / "policy_manifest.csv"]
    if any(path.exists() for path in targets):
        raise FileExistsError("policy manifests are immutable; refusing overwrite")
    features.to_csv(targets[0], index=False, encoding="utf-8-sig")
    policies.to_csv(targets[1], index=False, encoding="utf-8-sig")
