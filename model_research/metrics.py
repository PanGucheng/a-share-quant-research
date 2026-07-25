from __future__ import annotations

from typing import Any


def frozen_metric_registry(config: dict[str, Any]) -> dict[str, Any]:
    validation = dict(config["validation"])
    required = {
        "primary_metric": "mean_daily_rank_ic",
        "tie_break_1": "daily_rank_ic_ir",
        "tie_break_2": "prediction_coverage",
        "tie_break_3": "lower_model_complexity",
        "final_tie_break": "canonical_candidate_sha256",
        "final_fit_scope": "outer_train_plus_validation",
    }
    mismatches = {
        field: (validation.get(field), expected)
        for field, expected in required.items()
        if validation.get(field) != expected
    }
    if mismatches:
        raise ValueError(f"metric registry is not frozen: {mismatches}")
    return {
        **validation,
        "candidate_selection_scope": "outer_validation_only",
        "test_metric_authority": "evaluation_only",
        "registry_status": "frozen",
    }
