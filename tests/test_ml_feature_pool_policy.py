from __future__ import annotations

import pandas as pd
import pytest

from model_research.feature_pool_policy import (
    POLICY_A,
    POLICY_B,
    POLICY_C,
    _policy_rows,
    validate_diagnostic_outcome,
)


def _eligibility(a_correct: object = True) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "outer_split_id": ["split_001"] * 4,
            "factor": ["a", "conditional", "broad", "blocked"],
            "source_family": ["z", "a", "b", "c"],
            "correctness_pass": [a_correct, True, True, True],
            "data_qualified": [True, True, True, False],
        }
    )


def _stability() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "outer_split_id": ["split_001"] * 4,
            "factor": ["a", "conditional", "broad", "blocked"],
            "stability_role": ["stable_core", "conditional_signal", "holdout", "conditional_signal"],
        }
    )


def test_policy_sets_are_nested_and_b_uses_full_semantic_id() -> None:
    rows = pd.DataFrame(
        _policy_rows(
            split_id="split_001",
            a_order=["a"],
            eligibility=_eligibility(),
            stability=_stability(),
        )
    )
    factors = {
        policy: set(rows.loc[rows["policy_id"].eq(policy), "factor"])
        for policy in (POLICY_A, POLICY_B, POLICY_C)
    }
    assert factors[POLICY_A] == {"a"}
    assert factors[POLICY_B] == {"a", "conditional"}
    assert factors[POLICY_C] == {"a", "conditional", "broad"}
    assert factors[POLICY_A] <= factors[POLICY_B] <= factors[POLICY_C]
    assert POLICY_B == "current_plus_existing_conditional_signal"
    assert rows["decision_authority"].eq("diagnostic_only").all()


def test_policy_a_correctness_fails_closed_even_for_string_false() -> None:
    with pytest.raises(ValueError, match="failed closed"):
        _policy_rows(
            split_id="split_001",
            a_order=["a"],
            eligibility=_eligibility("False"),
            stability=_stability(),
        )


@pytest.mark.parametrize("outcome", ["strict_favored", "broader_favored", "mixed"])
def test_diagnostic_language_never_authorizes_a_winner(outcome: str) -> None:
    payload = {
        "diagnostic_outcome": outcome,
        "decision_authority": "diagnostic_only",
        "selection_authorized": False,
        "strategy_v2_authorized": False,
    }
    validate_diagnostic_outcome(payload)
    payload["selection_authorized"] = True
    with pytest.raises(ValueError, match="cannot authorize"):
        validate_diagnostic_outcome(payload)
