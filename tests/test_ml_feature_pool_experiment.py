from __future__ import annotations

from pathlib import Path

from model_research.feature_pool_experiment import canary_candidates
from model_research.lightgbm_models import load_lightgbm_config


def test_canary_uses_same_two_rows_from_frozen_candidate_table() -> None:
    project_root = Path(__file__).resolve().parents[1]
    config = load_lightgbm_config(project_root / "configs/research_lightgbm_v1.yaml")
    canary = {
        "structural_row_ids": ["structure_01", "structure_02"],
        "checkpoint": 100,
    }
    candidates = canary_candidates(config, canary)
    assert [row["structural_row_id"] for row in candidates] == [
        "structure_01",
        "structure_02",
    ]
    assert {row["num_boost_round"] for row in candidates} == {100}
    assert all(row["candidate_sha256"] for row in candidates)
