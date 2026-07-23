from __future__ import annotations

import pandas as pd
import pytest

from portfolio.model_comparison import prerequisite_status, validate_feature_allowlist
from research_validation.model_entry_gate import ModelEntryBlockedError, assert_model_entry_allowed


def test_blocked_prerequisite_prevents_ready_status() -> None:
    contracts = {"a": pd.DataFrame([{"check_name": "x", "status": "pass", "severity": "critical"}]), "b": pd.DataFrame([{"check_name": "y", "status": "blocked", "severity": "downstream"}])}
    status = prerequisite_status(contracts)
    assert status.set_index("prerequisite").loc["b", "status"] == "blocked"


def test_feature_allowlist_rejects_non_representatives() -> None:
    stability = pd.DataFrame({"factor": ["a", "b"], "stability_role": ["stable_core", "monitor"]})
    representatives = pd.DataFrame({"factor": ["a"]})
    assert validate_feature_allowlist(["a", "b", "c"], stability, representatives) == ["b", "c"]


def ready_row(**overrides: object) -> pd.DataFrame:
    values: dict[str, object] = {
        "selection_integrity_status": "ready",
        "model_entry_hard_stop_active": False,
        "feature_selection_holdout_clean": True,
        "clustering_holdout_clean": True,
        "fdr_family_semantics_valid": True,
        "fdr_artifact_consumed": True,
        "raw_input_provenance_complete": True,
        "split_allowlists_frozen": True,
        "core_model_ready": True,
        "pr5_model_training_ready": True,
        "model_training_started": False,
    }
    values.update(overrides)
    return pd.DataFrame([values])


def selection_row(**overrides: object) -> pd.DataFrame:
    values: dict[str, object] = {
        "selection_name": "split_specific_holdout_clean_allowlists_v1",
        "selection_status": "holdout_clean",
        "model_input_allowed": True,
    }
    values.update(overrides)
    return pd.DataFrame([values])


def accuracy_ready_row(**overrides: object) -> pd.DataFrame:
    values: dict[str, object] = {
        "selection_holdout_integrity_ready": True,
        "universe_lifecycle_v2_ready": True,
        "research_formula_accuracy_ready": True,
        "matrix_v4_lifecycle_clean": True,
        "pairwise_ic_ready": True,
        "model_research_ready": True,
        "execution_semantics_accuracy_ready": True,
        "market_cache_v2_ready": True,
        "future_market_field_count": 0,
        "stale_policy_valid": True,
        "authoritative_oos_execution_ready": True,
        "core_model_ready": True,
        "pr5_model_training_ready": True,
        "model_training_started": False,
        "model_entry_hard_stop_active": False,
        "accuracy_correction_status": "complete",
    }
    values.update(overrides)
    return pd.DataFrame([values])


def test_model_entry_rejects_exploratory_selection_even_if_old_readiness_is_true() -> None:
    with pytest.raises(ModelEntryBlockedError, match="selection_status='test_influenced'"):
        assert_model_entry_allowed(
            ready_row(),
            selection_row(
                selection_name="exploratory_global_representatives_v1",
                selection_status="test_influenced",
                model_input_allowed=False,
            ),
            selection_name="exploratory_global_representatives_v1",
            accuracy_correction=accuracy_ready_row(),
        )


def test_model_entry_rejects_machine_hard_stop() -> None:
    with pytest.raises(ModelEntryBlockedError, match="selection_integrity_status='blocked'"):
        assert_model_entry_allowed(
            ready_row(
                selection_integrity_status="blocked",
                model_entry_hard_stop_active=True,
                core_model_ready=False,
                pr5_model_training_ready=False,
            ),
            selection_row(),
            selection_name="split_specific_holdout_clean_allowlists_v1",
            accuracy_correction=accuracy_ready_row(),
        )


def test_model_entry_rejects_invalid_fdr_family_semantics() -> None:
    with pytest.raises(ModelEntryBlockedError, match="fdr_family_semantics_valid=false"):
        assert_model_entry_allowed(
            ready_row(fdr_family_semantics_valid=False),
            selection_row(),
            selection_name="split_specific_holdout_clean_allowlists_v1",
            accuracy_correction=accuracy_ready_row(),
        )


def test_model_entry_accepts_only_holdout_clean_ready_selection() -> None:
    assert_model_entry_allowed(
        ready_row(),
        selection_row(),
        selection_name="split_specific_holdout_clean_allowlists_v1",
        accuracy_correction=accuracy_ready_row(),
    )


def test_repository_accuracy_correction_policy_blocks_current_selection() -> None:
    with pytest.raises(
        ModelEntryBlockedError,
        match="accuracy_correction_status='blocked_research_and_execution_accuracy'",
    ):
        assert_model_entry_allowed(
            ready_row(),
            selection_row(),
            selection_name="split_specific_holdout_clean_allowlists_v1",
        )


def test_model_entry_requires_full_research_and_execution_accuracy() -> None:
    with pytest.raises(ModelEntryBlockedError, match="pairwise_ic_ready=false"):
        assert_model_entry_allowed(
            ready_row(),
            selection_row(),
            selection_name="split_specific_holdout_clean_allowlists_v1",
            accuracy_correction=accuracy_ready_row(
                accuracy_correction_status="blocked_research_accuracy",
                pairwise_ic_ready=False,
                model_research_ready=False,
                authoritative_oos_execution_ready=False,
                core_model_ready=False,
                pr5_model_training_ready=False,
                model_entry_hard_stop_active=True,
            ),
        )


def test_linear_model_runner_calls_machine_entry_gate() -> None:
    from pathlib import Path

    source = Path("scripts/run_linear_factor_model.py").read_text(encoding="utf-8")
    assert "assert_model_entry_files(" in source
