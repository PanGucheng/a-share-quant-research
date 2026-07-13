from __future__ import annotations

import pandas as pd

from portfolio.model_comparison import readiness_flags
from research_validation.profiles import Profile, ProfileType


def passing_prerequisites() -> pd.DataFrame:
    return pd.DataFrame([{"prerequisite": "pre_model_diagnostics", "status": "pass"}])


def test_reference_outputs_cannot_pass_full_or_core_gate() -> None:
    flags = readiness_flags(passing_prerequisites(), [Profile("local_reference", ProfileType.REFERENCE)], lineage_status="reference_only", full_research_contracts_pass=True, liquidity_contract_pass=True, historical_exposure_contract_pass=True)
    assert flags["reference_ready"]
    assert not flags["full_research_ready"]
    assert not flags["core_model_ready"]


def test_external_exposure_does_not_block_reference_or_core_contract_shape() -> None:
    flags = readiness_flags(passing_prerequisites(), [Profile("full_research", ProfileType.FULL_RESEARCH)], lineage_status="complete", full_research_contracts_pass=True, liquidity_contract_pass=True, historical_exposure_contract_pass=False)
    assert flags["core_model_ready"]
    assert not flags["historical_exposure_model_ready"]


def test_pre_model_gate_has_no_trained_method_dependency() -> None:
    import yaml
    from pathlib import Path

    config = yaml.safe_load(Path("configs/pre_model_diagnostics_v1.yaml").read_text(encoding="utf-8"))
    assert "regularized_linear" not in config["required_methods"]
    assert "lightgbm" not in config["required_methods"]
