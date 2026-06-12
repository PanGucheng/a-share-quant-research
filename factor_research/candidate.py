from __future__ import annotations

import numpy as np
import pandas as pd

from factor_research.registry import FactorSpec, spec_map


MAIN_WINDOW = "main_research_2021_2023"
OOS_WINDOW = "recent_oos_2024_2026"
RAW_SAMPLE = "raw"
TRADABLE_SAMPLE = "tradable_only"


def _first_row(frame: pd.DataFrame) -> pd.Series | None:
    if frame.empty:
        return None
    return frame.iloc[0]


def _metric(row: pd.Series | None, name: str) -> float:
    if row is None or name not in row:
        return np.nan
    return pd.to_numeric(row[name], errors="coerce")


def _correlation_lookup(correlation: pd.DataFrame, factor_a: str, factor_b: str, label: str) -> float:
    if correlation.empty:
        return np.nan
    direct = correlation[
        (correlation["window"] == MAIN_WINDOW)
        & (correlation["sample"] == TRADABLE_SAMPLE)
        & (correlation["label"] == label)
        & (correlation["factor_a"] == factor_a)
        & (correlation["factor_b"] == factor_b)
    ]
    reverse = correlation[
        (correlation["window"] == MAIN_WINDOW)
        & (correlation["sample"] == TRADABLE_SAMPLE)
        & (correlation["label"] == label)
        & (correlation["factor_a"] == factor_b)
        & (correlation["factor_b"] == factor_a)
    ]
    row = _first_row(direct if not direct.empty else reverse)
    return _metric(row, "spearman_corr")


def decide_candidates(
    summary: pd.DataFrame,
    monotonicity: pd.DataFrame,
    correlation: pd.DataFrame,
    specs: list[FactorSpec],
) -> pd.DataFrame:
    spec_by_name = spec_map(specs)
    rows = []
    labels = sorted(summary["label"].dropna().unique())
    for label in labels:
        for factor, spec in spec_by_name.items():
            factor_summary = summary[(summary["label"] == label) & (summary["factor"] == factor)]
            main = _first_row(
                factor_summary[
                    (factor_summary["window"] == MAIN_WINDOW) & (factor_summary["sample"] == TRADABLE_SAMPLE)
                ]
            )
            oos = _first_row(
                factor_summary[
                    (factor_summary["window"] == OOS_WINDOW) & (factor_summary["sample"] == TRADABLE_SAMPLE)
                ]
            )
            raw_slices = factor_summary[factor_summary["sample"] == RAW_SAMPLE]
            mono = _first_row(
                monotonicity[
                    (monotonicity["label"] == label)
                    & (monotonicity["factor"] == factor)
                    & (monotonicity["window"] == MAIN_WINDOW)
                    & (monotonicity["sample"] == TRADABLE_SAMPLE)
                ]
            )

            main_coverage = _metric(main, "coverage")
            main_rank_ic = _metric(main, "mean_rank_ic")
            main_directional = _metric(main, "directional_mean_rank_ic")
            oos_rank_ic = _metric(oos, "mean_rank_ic")
            oos_directional = _metric(oos, "directional_mean_rank_ic")
            mono_score = _metric(mono, "monotonicity_score")
            directional_spread = _metric(mono, "directional_spread")
            directional_slices = raw_slices["directional_mean_rank_ic"].dropna()
            positive_slices = int((directional_slices > 0).sum())
            slice_count = int(len(raw_slices))
            stability_score = positive_slices / slice_count if slice_count else np.nan

            reasons = []
            decision = "watch"
            if spec.direction_sign is None:
                reasons.append("watch_direction")
            if pd.isna(main_coverage) or main_coverage < 0.80:
                decision = "reject"
                reasons.append("low_coverage")
            if pd.notna(oos_directional) and oos_directional < 0:
                decision = "reject"
                reasons.append("negative_oos")
            if pd.notna(main_directional) and main_directional < 0 and pd.notna(oos_directional) and oos_directional < 0:
                decision = "reject"
                reasons.append("opposite_direction")

            promote_ready = (
                spec.direction_sign is not None
                and pd.notna(main_coverage)
                and main_coverage >= 0.90
                and pd.notna(main_directional)
                and main_directional > 0.03
                and pd.notna(oos_directional)
                and oos_directional > 0
                and positive_slices >= 3
                and pd.notna(directional_spread)
                and directional_spread > 0
                and pd.notna(mono_score)
                and mono_score > 0
            )
            if promote_ready and decision != "reject":
                decision = "promote"
                reasons.append("passes_rules")
            elif decision == "watch" and not reasons:
                reasons.append("insufficient_evidence")

            rows.append(
                {
                    "label": label,
                    "factor": factor,
                    "category": spec.category,
                    "expected_direction": spec.expected_direction,
                    "decision": decision,
                    "reason": "|".join(dict.fromkeys(reasons)),
                    "main_coverage": main_coverage,
                    "main_rank_ic": main_rank_ic,
                    "main_directional_rank_ic": main_directional,
                    "oos_rank_ic": oos_rank_ic,
                    "oos_directional_rank_ic": oos_directional,
                    "positive_directional_slices": positive_slices,
                    "slice_count": slice_count,
                    "stability_score": stability_score,
                    "monotonicity_score": mono_score,
                    "directional_spread": directional_spread,
                    "redundancy_group": "",
                }
            )

    decisions = pd.DataFrame(rows)
    if decisions.empty:
        return decisions
    return apply_redundancy(decisions, correlation)


def apply_redundancy(decisions: pd.DataFrame, correlation: pd.DataFrame) -> pd.DataFrame:
    result = decisions.copy()
    for label, group in result[result["decision"] == "promote"].groupby("label"):
        accepted: list[str] = []
        ordered = group.sort_values("main_directional_rank_ic", ascending=False)
        for row in ordered.itertuples(index=False):
            redundant_with = []
            for accepted_factor in accepted:
                corr = _correlation_lookup(correlation, row.factor, accepted_factor, label)
                if pd.notna(corr) and abs(corr) >= 0.80:
                    redundant_with.append(accepted_factor)
            if redundant_with:
                mask = (result["label"] == label) & (result["factor"] == row.factor)
                result.loc[mask, "decision"] = "reject"
                result.loc[mask, "reason"] = result.loc[mask, "reason"] + "|redundant_weak"
                result.loc[mask, "redundancy_group"] = ",".join(redundant_with)
            else:
                accepted.append(row.factor)
    return result.sort_values(["label", "decision", "main_directional_rank_ic"], ascending=[True, True, False])
