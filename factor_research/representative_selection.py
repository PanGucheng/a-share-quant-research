from __future__ import annotations

import pandas as pd


def select_representatives(clusters: pd.DataFrame, stability: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    merged = clusters.merge(stability, on="factor", how="left", validate="one_to_one")
    if "fdr_pass_frequency" in merged:
        fdr_score = merged["fdr_pass_frequency"].fillna(0)
    else:
        fdr_score = merged["upstream_fdr_pass"].fillna(False).astype(float)
    merged["representative_score"] = (
        merged["selection_frequency"].fillna(0) * 0.40
        + merged["direction_agreement_ratio"].fillna(0) * 0.25
        + fdr_score * 0.20
        + merged["coverage_median"].fillna(0) * 0.15
    )
    ordered = merged.sort_values(["cluster_id", "representative_score", "factor"], ascending=[True, False, True])
    representatives = ordered.groupby("cluster_id", as_index=False).first()
    representatives["is_representative"] = True
    selected = set(representatives["factor"])
    excluded = ordered.loc[~ordered["factor"].isin(selected)].copy()
    excluded["exclusion_reason"] = "redundant_with_cluster_representative"
    return representatives, excluded
