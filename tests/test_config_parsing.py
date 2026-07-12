from __future__ import annotations

from pathlib import Path

import yaml


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
    assert roles["mlfinpy"] == "phase_3_required"
    assert roles["Riskfolio-Lib"] == "optional_portfolio"
