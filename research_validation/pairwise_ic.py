from __future__ import annotations

import numpy as np
import pandas as pd


def pairwise_daily_spearman(
    frame: pd.DataFrame,
    factors: list[str],
    *,
    label_column: str,
    minimum_cross_section: int,
    tie_method: str = "average",
) -> pd.DataFrame:
    """Compute factor-specific pairwise Spearman IC for one date."""

    if tie_method != "average":
        raise ValueError("only the frozen average tie policy is supported")
    factor_values = frame[factors].apply(pd.to_numeric, errors="coerce")
    label = pd.to_numeric(frame[label_column], errors="coerce")
    pair_valid = factor_values.notna().mul(label.notna(), axis=0)
    factor_rank = factor_values.where(pair_valid).rank(method=tie_method)
    label_matrix = pd.DataFrame(
        np.broadcast_to(label.to_numpy()[:, None], factor_values.shape),
        index=factor_values.index,
        columns=factors,
    )
    label_rank = label_matrix.where(pair_valid).rank(method=tie_method)
    correlations = factor_rank.corrwith(label_rank)
    pair_count = pair_valid.sum().astype(int)
    factor_missing = factor_values.isna().sum().astype(int)
    label_missing = int(label.isna().sum())
    rows = []
    for factor in factors:
        count = int(pair_count[factor])
        value = correlations[factor]
        rows.append(
            {
                "factor": factor,
                "rank_ic": (
                    float(value)
                    if count >= minimum_cross_section and pd.notna(value)
                    else np.nan
                ),
                "pair_count": count,
                "factor_missing_count": int(factor_missing[factor]),
                "label_missing_count": label_missing,
                "tie_method": tie_method,
            }
        )
    return pd.DataFrame(rows)
