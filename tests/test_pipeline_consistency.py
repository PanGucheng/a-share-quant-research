from __future__ import annotations

import pandas as pd

from research_validation.pipeline_consistency import evaluate_semantic_consistency


def test_old_representative_and_unselected_weight_are_inconsistent() -> None:
    stability = pd.DataFrame([{"factor": "old", "stability_role": "holdout", "eligible_window_count": 0}])
    history = pd.DataFrame([{"factor": "old", "selected": False, "selection_eligible": False, "eligible": False}])
    representatives = pd.DataFrame([{"factor": "old"}])
    weights = pd.DataFrame([{"factor": "old"}])
    result = evaluate_semantic_consistency(stability, history, representatives, weights, score_methods=set(), execution_methods=set(), diagnostic_methods=set())
    assert result.unexpected_clustering_factors == {"old"}
    assert result.unexpected_score_factors == {"old"}
    assert not result.pipeline_consistent


def test_empty_blocked_chain_is_semantically_consistent_but_not_available() -> None:
    stability = pd.DataFrame([{"factor": "old", "stability_role": "holdout", "eligible_window_count": 0}])
    result = evaluate_semantic_consistency(stability, pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), score_methods=set(), execution_methods=set(), diagnostic_methods=set())
    assert result.pipeline_consistent
    assert not result.eligible_factors
