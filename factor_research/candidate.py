from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from factor_research.registry import FactorSpec, spec_map


MAIN_WINDOW = "main_research_2021_2023"
OOS_WINDOW = "recent_oos_2024_2026"
RAW_SAMPLE = "raw"
TRADABLE_SAMPLE = "tradable_only"


@dataclass(frozen=True)
class CandidateSelectionRules:
    min_coverage: float = 0.90
    max_missing_rate: float = 0.10
    min_main_directional_rank_ic: float = 0.03
    min_oos_directional_rank_ic: float = 0.0
    min_rank_ic_win_rate: float = 0.52
    min_positive_slices: int = 3
    min_directional_spread: float = 0.0
    min_monotonicity_score: float = 0.0
    max_correlation: float = 0.80
    max_top_quantile_turnover: float = 1.0


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
    turnover_summary: pd.DataFrame | None = None,
    rules: CandidateSelectionRules | None = None,
) -> pd.DataFrame:
    rules = rules or CandidateSelectionRules()
    turnover_summary = turnover_summary if turnover_summary is not None else pd.DataFrame()
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
            main_missing = _metric(main, "missing_rate")
            main_rank_ic = _metric(main, "mean_rank_ic")
            main_directional = _metric(main, "directional_mean_rank_ic")
            main_win_rate = _metric(main, "ic_win_rate")
            oos_rank_ic = _metric(oos, "mean_rank_ic")
            oos_directional = _metric(oos, "directional_mean_rank_ic")
            mono_score = _metric(mono, "monotonicity_score")
            directional_spread = _metric(mono, "directional_spread")
            turnover = _first_row(
                turnover_summary[
                    (turnover_summary["window"] == MAIN_WINDOW)
                    & (turnover_summary["sample"] == TRADABLE_SAMPLE)
                    & (turnover_summary["factor"] == factor)
                ]
            )
            mean_turnover = _metric(turnover, "mean_top_quantile_turnover")
            directional_slices = raw_slices["directional_mean_rank_ic"].dropna()
            positive_slices = int((directional_slices > 0).sum())
            slice_count = int(len(raw_slices))
            stability_score = positive_slices / slice_count if slice_count else np.nan

            reasons = []
            decision = "watch"
            if spec.direction_sign is None:
                reasons.append("watch_direction")
            if pd.isna(main_coverage) or main_coverage < rules.min_coverage:
                decision = "reject"
                reasons.append("low_coverage")
            if pd.notna(main_missing) and main_missing > rules.max_missing_rate:
                decision = "reject"
                reasons.append("high_missing")
            if pd.notna(oos_directional) and oos_directional < rules.min_oos_directional_rank_ic:
                decision = "reject"
                reasons.append("negative_oos")
            if pd.notna(main_directional) and main_directional < 0 and pd.notna(oos_directional) and oos_directional < 0:
                decision = "reject"
                reasons.append("opposite_direction")
            if pd.notna(mean_turnover) and mean_turnover > rules.max_top_quantile_turnover:
                decision = "reject"
                reasons.append("high_turnover")

            promote_ready = (
                spec.direction_sign is not None
                and pd.notna(main_coverage)
                and main_coverage >= rules.min_coverage
                and (pd.isna(main_missing) or main_missing <= rules.max_missing_rate)
                and pd.notna(main_directional)
                and main_directional > rules.min_main_directional_rank_ic
                and pd.notna(oos_directional)
                and oos_directional > rules.min_oos_directional_rank_ic
                and (pd.isna(main_win_rate) or main_win_rate >= rules.min_rank_ic_win_rate)
                and positive_slices >= rules.min_positive_slices
                and pd.notna(directional_spread)
                and directional_spread > rules.min_directional_spread
                and pd.notna(mono_score)
                and mono_score > rules.min_monotonicity_score
                and (pd.isna(mean_turnover) or mean_turnover <= rules.max_top_quantile_turnover)
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
                    "main_missing_rate": main_missing,
                    "main_rank_ic": main_rank_ic,
                    "main_directional_rank_ic": main_directional,
                    "main_ic_win_rate": main_win_rate,
                    "oos_rank_ic": oos_rank_ic,
                    "oos_directional_rank_ic": oos_directional,
                    "mean_top_quantile_turnover": mean_turnover,
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
    return apply_redundancy(decisions, correlation, rules.max_correlation)


def apply_redundancy(decisions: pd.DataFrame, correlation: pd.DataFrame, max_correlation: float = 0.80) -> pd.DataFrame:
    result = decisions.copy()
    for label, group in result[result["decision"] == "promote"].groupby("label"):
        accepted: list[str] = []
        ordered = group.sort_values("main_directional_rank_ic", ascending=False)
        for row in ordered.itertuples(index=False):
            redundant_with = []
            for accepted_factor in accepted:
                corr = _correlation_lookup(correlation, row.factor, accepted_factor, label)
                if pd.notna(corr) and abs(corr) >= max_correlation:
                    redundant_with.append(accepted_factor)
            if redundant_with:
                mask = (result["label"] == label) & (result["factor"] == row.factor)
                result.loc[mask, "decision"] = "reject"
                result.loc[mask, "reason"] = result.loc[mask, "reason"] + "|redundant_weak"
                result.loc[mask, "redundancy_group"] = ",".join(redundant_with)
            else:
                accepted.append(row.factor)
    return result.sort_values(["label", "decision", "main_directional_rank_ic"], ascending=[True, True, False])
