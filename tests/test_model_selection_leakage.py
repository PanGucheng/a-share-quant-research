from __future__ import annotations

import pandas as pd

from portfolio.model_comparison import prerequisite_status, validate_feature_allowlist


def test_blocked_prerequisite_prevents_ready_status() -> None:
    contracts = {"a": pd.DataFrame([{"check_name": "x", "status": "pass", "severity": "critical"}]), "b": pd.DataFrame([{"check_name": "y", "status": "blocked", "severity": "downstream"}])}
    status = prerequisite_status(contracts)
    assert status.set_index("prerequisite").loc["b", "status"] == "blocked"


def test_feature_allowlist_rejects_non_representatives() -> None:
    stability = pd.DataFrame({"factor": ["a", "b"], "stability_role": ["stable_core", "monitor"]})
    representatives = pd.DataFrame({"factor": ["a"]})
    assert validate_feature_allowlist(["a", "b", "c"], stability, representatives) == ["b", "c"]
