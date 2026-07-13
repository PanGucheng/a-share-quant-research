from __future__ import annotations

from pathlib import Path

import yaml

from research_validation.profiles import resolve_profile


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_research_data_contract_config_has_required_schemas() -> None:
    path = PROJECT_ROOT / "configs/research_data_contracts_v1.yaml"
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    assert payload["schema_version"] == 1
    assert payload["output_dir"] == "outputs/research_data_contracts_v1/current"
    schemas = {item["schema"] for item in payload["datasets"]}
    assert schemas == {"factor_frame", "tradability_frame", "screening_frame", "judgement_frame"}


def test_baseline_config_keeps_core_and_optional_dependencies_separate() -> None:
    path = PROJECT_ROOT / "configs/factor_validation_baseline_v1.yaml"
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    roles = {item["distribution"]: item["role"] for item in payload["dependencies"]}
    assert roles["pandera"] == "phase_1_required"
    assert roles["mlfinpy"] == "semantic_reference_only"
    assert roles["Riskfolio-Lib"] == "optional_portfolio"


def test_v11_critical_configs_declare_profile_type() -> None:
    names = [
        "point_in_time_universe_smoke_v1.yaml",
        "point_in_time_universe_v1.yaml",
        "purged_walk_forward_v1.yaml",
        "factor_multiple_testing_v1.yaml",
        "factor_rolling_stability_v1.yaml",
        "factor_clustering_v1.yaml",
        "factor_score_construction_v1.yaml",
        "a_share_execution_v1.yaml",
        "external_exposure_data_v1.yaml",
        "final_portfolio_diagnostics_v1.yaml",
        "factor_model_comparison_v1.yaml",
        "legacy_common_scores_v1.yaml",
    ]
    for name in names:
        payload = yaml.safe_load((PROJECT_ROOT / "configs" / name).read_text(encoding="utf-8")) or {}
        assert resolve_profile(payload).type.value == payload["profile_type"]
