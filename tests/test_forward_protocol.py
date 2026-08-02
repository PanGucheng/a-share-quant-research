from __future__ import annotations

import copy

import pytest

from model_research.forward_protocol import load_forward_config


def test_forward_protocol_is_fail_closed() -> None:
    config = load_forward_config(
        "configs/prospective_forward_confirmation_v1.yaml"
    )
    assert config["candidate"]["hyperparameter_search_allowed"] is False
    assert (
        config["governance"][
            "retrospective_extension_prospective_eligible"
        ]
        is False
    )
    assert config["governance"]["production_model_selected"] is False
    assert config["governance"]["forward_data_waiting"] is True
    assert "labels_runtime" not in config["parents"]
    assert config["prediction_freeze"]["label_start_cutoff"] == (
        "next_trading_day_09_25"
    )
    assert config["durable_storage"]["storage_class"] == (
        "git_content_addressed"
    )


def test_forward_protocol_rejects_search_or_overclaim() -> None:
    base = load_forward_config(
        "configs/prospective_forward_confirmation_v1.yaml"
    )
    search = copy.deepcopy(base)
    search["candidate"]["hyperparameter_search_allowed"] = True
    with pytest.raises(ValueError, match="search is forbidden"):
        _validate_payload(search)
    production = copy.deepcopy(base)
    production["governance"]["production_model_selected"] = True
    with pytest.raises(ValueError, match="overclaims"):
        _validate_payload(production)


def _validate_payload(payload: dict) -> None:
    if payload["experiment_class"] != "prospective_research_protocol":
        raise ValueError("forward protocol experiment class mismatch")
    if bool(payload["candidate"]["hyperparameter_search_allowed"]):
        raise ValueError("forward candidate search is forbidden")
    for field in (
        "production_model_selected",
        "live_trading_ready",
        "authoritative_historical_execution_ready",
        "unbiased_historical_estimate",
    ):
        if bool(payload["governance"][field]):
            raise ValueError(f"forward protocol overclaims {field}")
