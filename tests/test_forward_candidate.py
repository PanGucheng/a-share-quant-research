from __future__ import annotations

from model_research.forward_candidate import (
    _selected_candidate,
)
from model_research.forward_protocol import load_forward_config


def test_forward_candidate_is_exact_frozen_split_003_spec() -> None:
    config = load_forward_config(
        "configs/prospective_forward_confirmation_v1.yaml"
    )
    candidate = _selected_candidate(config)
    assert candidate["structural_row_id"] == "structure_04"
    assert candidate["num_boost_round"] == 200
    assert candidate["candidate_sha256"] == (
        "28cd65e113ad52527ff34ec9268ee4a5cbd286d9a81c838fda2e8d86b897980a"
    )


def test_forward_candidate_training_dates_stop_before_snapshot() -> None:
    config = load_forward_config(
        "configs/prospective_forward_confirmation_v1.yaml"
    )
    assert config["training"]["start_date"].isoformat() == "2021-02-01"
    assert config["training"]["end_date"].isoformat() == "2026-05-11"
    assert (
        config["training"]["end_date"]
        < config["temporal_boundary"]["current_snapshot_end"]
    )
