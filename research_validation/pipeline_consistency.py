from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class ConsistencyResult:
    eligible_factors: frozenset[str]
    selected_factors: frozenset[str]
    representative_factors: frozenset[str]
    weight_factors: frozenset[str]
    unexpected_clustering_factors: frozenset[str]
    unexpected_score_factors: frozenset[str]
    unexpected_execution_methods: frozenset[str]
    unexpected_diagnostic_methods: frozenset[str]

    @property
    def pipeline_consistent(self) -> bool:
        return not any((self.unexpected_clustering_factors, self.unexpected_score_factors, self.unexpected_execution_methods, self.unexpected_diagnostic_methods))


def _values(frame: pd.DataFrame, column: str) -> frozenset[str]:
    if frame.empty or column not in frame:
        return frozenset()
    return frozenset(frame[column].dropna().astype(str))


def evaluate_semantic_consistency(
    stability: pd.DataFrame,
    history: pd.DataFrame,
    representatives: pd.DataFrame,
    weights: pd.DataFrame,
    *,
    score_methods: set[str],
    execution_methods: set[str],
    diagnostic_methods: set[str],
) -> ConsistencyResult:
    eligible_roles = {"stable_core", "conditional_signal", "risk_control"}
    role = stability.get("stability_role", pd.Series(index=stability.index, dtype=object)).isin(eligible_roles)
    windows = stability.get("eligible_window_count", pd.Series(0, index=stability.index)).gt(0)
    eligible = _values(stability.loc[role & windows], "factor")
    selected_mask = history.get("selected", pd.Series(False, index=history.index)).fillna(False).astype(bool)
    if "selection_eligible" in history:
        selected_mask &= history.selection_eligible.fillna(False).astype(bool)
    if "eligible" in history:
        selected_mask &= history.eligible.fillna(False).astype(bool)
    selected = _values(history.loc[selected_mask], "factor")
    reps = _values(representatives, "factor")
    weight_factors = _values(weights, "factor")
    return ConsistencyResult(
        eligible_factors=eligible,
        selected_factors=selected,
        representative_factors=reps,
        weight_factors=weight_factors,
        unexpected_clustering_factors=frozenset(reps - eligible),
        unexpected_score_factors=frozenset(weight_factors - (reps & selected & eligible)),
        unexpected_execution_methods=frozenset(execution_methods - score_methods),
        unexpected_diagnostic_methods=frozenset(diagnostic_methods - execution_methods),
    )
