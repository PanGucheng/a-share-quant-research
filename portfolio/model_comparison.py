from __future__ import annotations

import pandas as pd

from research_validation.profiles import Profile, assert_profiles_compatible


def prerequisite_status(contracts: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows = []
    for stage, frame in contracts.items():
        blocking = frame.loc[frame["status"].isin(["fail", "blocked"]) & frame["severity"].isin(["critical", "downstream"])]
        rows.append({"prerequisite": stage, "status": "pass" if blocking.empty else "blocked", "blocking_checks": ";".join(blocking["check_name"].astype(str)), "blocking_count": len(blocking)})
    return pd.DataFrame(rows)


def validate_feature_allowlist(features: list[str], stability: pd.DataFrame, representatives: pd.DataFrame) -> list[str]:
    allowed_roles = {"stable_core", "conditional_signal", "risk_control"}
    allowed = set(stability.loc[stability.stability_role.isin(allowed_roles), "factor"]) & set(representatives["factor"])
    return sorted(set(features) - allowed)


def readiness_flags(
    prerequisite_table: pd.DataFrame,
    profiles: list[Profile],
    *,
    lineage_status: str,
    reference_infrastructure_ready: bool = True,
    reference_lineage_valid: bool = True,
    semantic_consistency_pass: bool = True,
    full_research_contracts_pass: bool,
    liquidity_contract_pass: bool,
    historical_exposure_contract_pass: bool,
) -> dict[str, bool]:
    reference_contracts_pass = bool((prerequisite_table["status"] == "pass").all())
    try:
        assert_profiles_compatible(profiles, "reference")
        reference_profiles_pass = True
    except ValueError:
        reference_profiles_pass = False
    reference_pipeline_ready = (
        reference_infrastructure_ready
        and reference_contracts_pass
        and reference_profiles_pass
        and reference_lineage_valid
        and semantic_consistency_pass
        and lineage_status in {"complete", "reference_only"}
    )
    try:
        assert_profiles_compatible(profiles, "full_research")
        full_profiles_pass = True
    except ValueError:
        full_profiles_pass = False
    full_research_ready = full_research_contracts_pass and full_profiles_pass and lineage_status == "complete"
    return {
        "reference_infrastructure_ready": reference_infrastructure_ready,
        "reference_pipeline_ready": reference_pipeline_ready,
        "reference_ready": reference_pipeline_ready,
        "full_research_ready": full_research_ready,
        "core_model_ready": full_research_ready,
        "liquidity_residualized_model_ready": full_research_ready and liquidity_contract_pass,
        "historical_exposure_model_ready": full_research_ready and historical_exposure_contract_pass,
        "model_training_started": False,
    }
