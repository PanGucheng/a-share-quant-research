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


def test_infrastructure_can_pass_while_reference_pipeline_is_blocked() -> None:
    flags = readiness_flags(
        passing_prerequisites(), [Profile("local_reference", ProfileType.REFERENCE)],
        lineage_status="reference_only", reference_infrastructure_ready=True,
        reference_lineage_valid=True, semantic_consistency_pass=False,
        full_research_contracts_pass=False, liquidity_contract_pass=False,
        historical_exposure_contract_pass=False,
    )
    assert flags["reference_infrastructure_ready"]
    assert not flags["reference_pipeline_ready"]
    assert not flags["reference_ready"]


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


def test_diagnostics_runner_has_no_hardcoded_reference_weight_path() -> None:
    from pathlib import Path

    source = Path("scripts/run_final_portfolio_diagnostics_v1.py").read_text(encoding="utf-8")
    assert "outputs/factor_score_construction_v1/local_reference/factor_weights_by_window.csv" not in source
    assert 'config["factor_weights"]' in source


def test_model_gate_calls_lineage_validator() -> None:
    from pathlib import Path

    source = Path("scripts/run_factor_model_comparison_v1.py").read_text(encoding="utf-8")
    assert "validate_lineage_chain(" in source
    assert "validate_manifest_outputs(" in source
