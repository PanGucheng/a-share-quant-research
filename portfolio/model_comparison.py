from __future__ import annotations

import pandas as pd


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
