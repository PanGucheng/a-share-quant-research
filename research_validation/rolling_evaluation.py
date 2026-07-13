from __future__ import annotations

import numpy as np
import pandas as pd


SELECTION_COLUMNS = frozenset({"factor", "split_id", "train_mean_ic", "validation_mean_ic", "train_count", "validation_count", "train_coverage", "validation_coverage", "selection_eligible", "fdr_bh_pass", "fdr_bh_q_value"})


def select_factor_window(row: pd.Series, *, min_abs_validation_ic: float, min_dates: int) -> dict:
    forbidden = [column for column in row.index if str(column).startswith("test_")]
    if forbidden:
        raise ValueError(f"selection input contains test metrics: {forbidden}")
    train_mean = float(row["train_mean_ic"])
    validation_mean = float(row["validation_mean_ic"])
    direction = int(np.sign(train_mean)) if np.isfinite(train_mean) else 0
    validation_direction = int(np.sign(validation_mean)) if np.isfinite(validation_mean) else 0
    aligned = direction != 0 and validation_direction == direction
    enough = int(row["train_count"]) >= min_dates and int(row["validation_count"]) >= min_dates
    selection_eligible = bool(row.get("selection_eligible", enough))
    validation_strong = bool(np.isfinite(validation_mean) and abs(validation_mean) >= min_abs_validation_ic)
    selected = bool(aligned and enough and selection_eligible and validation_strong and bool(row["fdr_bh_pass"]))
    reasons = []
    if not aligned: reasons.append("direction_mismatch")
    if not enough: reasons.append("insufficient_dates")
    if not selection_eligible: reasons.append("selection_ineligible")
    if not validation_strong: reasons.append("weak_validation_ic")
    if not bool(row["fdr_bh_pass"]): reasons.append("fdr_not_passed")
    return {"selected": selected, "frozen_direction": direction, "selection_reason": "selected" if selected else ";".join(reasons)}


def stability_board(window_metrics: pd.DataFrame, thresholds: dict | None = None) -> pd.DataFrame:
    thresholds = thresholds or {}
    minimum_eligible_windows = int(thresholds.get("minimum_eligible_windows", 3))
    minimum_selection_frequency = float(thresholds.get("minimum_selection_frequency", 0.60))
    minimum_direction_agreement = float(thresholds.get("minimum_direction_agreement", 0.80))
    minimum_positive_ratio = float(thresholds.get("minimum_direction_adjusted_positive_window_ratio", 0.60))
    maximum_allowed_degradation = float(thresholds.get("maximum_allowed_oos_degradation", 0.03))
    rows = []
    for factor, group in window_metrics.groupby("factor", sort=True):
        eligible = group[group["eligible"]].copy()
        selected = eligible[eligible["selected"]]
        direction_values = eligible.loc[eligible["frozen_direction"] != 0, "frozen_direction"]
        direction_agreement = float(direction_values.value_counts(normalize=True).max()) if len(direction_values) else 0.0
        frequency = float(eligible["selected"].mean()) if len(eligible) else 0.0
        direction_adjusted = eligible["test_mean_ic"] * eligible["frozen_direction"]
        positive_ratio = float((direction_adjusted > 0).mean()) if len(eligible) else 0.0
        degradation = selected["test_mean_ic"].abs() - selected["validation_mean_ic"].abs()
        worst_degradation = float(degradation.min()) if len(degradation) else np.nan
        degradation_ok = bool(len(degradation) and worst_degradation >= -maximum_allowed_degradation)
        if (len(eligible) >= minimum_eligible_windows and frequency >= minimum_selection_frequency
                and direction_agreement >= minimum_direction_agreement and positive_ratio >= minimum_positive_ratio
                and degradation_ok):
            role = "stable_core"
        elif len(eligible) >= minimum_eligible_windows and frequency >= 0.30:
            role = "conditional_signal"
        elif len(eligible) == 0:
            role = "holdout"
        else:
            role = "monitor"
        coverage_min = eligible[["train_coverage", "validation_coverage", "test_coverage"]].min(axis=1).min() if len(eligible) else 0.0
        rows.append(
            {
                "factor": factor,
                "window_count": len(group),
                "eligible_window_count": int(group["eligible"].sum()),
                "selected_window_count": int(group["selected"].sum()),
                "selection_frequency": frequency,
                "direction_adjusted_positive_window_ratio": positive_ratio,
                "direction_agreement_ratio": direction_agreement,
                "median_train_ic": group["train_mean_ic"].median(),
                "median_validation_ic": group["validation_mean_ic"].median(),
                "median_test_ic": group["test_mean_ic"].median(),
                "worst_test_ic": group["test_mean_ic"].min(),
                "median_oos_degradation": degradation.median() if len(degradation) else np.nan,
                "worst_oos_degradation": worst_degradation,
                "fdr_pass_frequency": float(eligible["fdr_bh_pass"].mean()) if len(eligible) else 0.0,
                "coverage_min": coverage_min,
                "coverage_median": eligible[["train_coverage", "validation_coverage", "test_coverage"]].stack().median() if len(eligible) else 0.0,
                "stability_role": role,
                "role_reason": (
                    f"eligible_windows={len(eligible)};selection_frequency={frequency:.3f};"
                    f"direction_agreement={direction_agreement:.3f};direction_adjusted_positive_ratio={positive_ratio:.3f};"
                    f"worst_oos_degradation={worst_degradation}"
                ),
            }
        )
    return pd.DataFrame(rows)
