from __future__ import annotations

import pandas as pd

from factor_research.candidate import CandidateSelectionRules, decide_candidates
from factor_research.registry import FactorSpec


def select_factor_candidates(
    summary: pd.DataFrame,
    monotonicity: pd.DataFrame,
    correlation: pd.DataFrame,
    specs: list[FactorSpec],
    turnover_summary: pd.DataFrame | None = None,
    rules: CandidateSelectionRules | None = None,
) -> pd.DataFrame:
    return decide_candidates(
        summary=summary,
        monotonicity=monotonicity,
        correlation=correlation,
        specs=specs,
        turnover_summary=turnover_summary,
        rules=rules,
    )
