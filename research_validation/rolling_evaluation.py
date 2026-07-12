from __future__ import annotations

import numpy as np
import pandas as pd


SELECTION_COLUMNS = frozenset({"factor", "split_id", "train_mean_ic", "validation_mean_ic", "train_count", "validation_count", "fdr_bh_pass", "fdr_bh_q_value"})


def select_factor_window(row: pd.Series, *, min_abs_validation_ic: float, min_dates: int) -> dict:
    forbidden = [column for column in row.index if str(column).startswith("test_")]
    if forbidden:
        raise ValueError(f"selection input contains test metrics: {forbidden}")
    direction = int(np.sign(float(row["train_mean_ic"])))
    aligned = direction != 0 and int(np.sign(float(row["validation_mean_ic"]))) == direction
    enough = int(row["train_count"]) >= min_dates and int(row["validation_count"]) >= min_dates
    selected = bool(aligned and enough and abs(float(row["validation_mean_ic"])) >= min_abs_validation_ic and bool(row["fdr_bh_pass"]))
    reasons = []
    if not aligned: reasons.append("direction_mismatch")
    if not enough: reasons.append("insufficient_dates")
    if abs(float(row["validation_mean_ic"])) < min_abs_validation_ic: reasons.append("weak_validation_ic")
    if not bool(row["fdr_bh_pass"]): reasons.append("fdr_not_passed")
    return {"selected": selected, "frozen_direction": direction, "selection_reason": "selected" if selected else ";".join(reasons)}


def stability_board(window_metrics: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for factor, group in window_metrics.groupby("factor", sort=True):
        selected = group[group["selected"]]
        direction_values = group.loc[group["frozen_direction"] != 0, "frozen_direction"]
        direction_agreement = float(direction_values.value_counts(normalize=True).max()) if len(direction_values) else 0.0
        frequency = float(group["selected"].mean())
        if frequency >= 0.60 and direction_agreement >= 0.80 and len(group) >= 3:
            role = "stable_core"
        elif frequency >= 0.30:
            role = "conditional_signal"
        elif len(group) == 0:
            role = "holdout"
        else:
            role = "monitor"
        degradation = selected["test_mean_ic"].abs() - selected["validation_mean_ic"].abs()
        rows.append(
            {
                "factor": factor,
                "window_count": len(group),
                "eligible_window_count": int(group["eligible"].sum()),
                "selected_window_count": int(group["selected"].sum()),
                "selection_frequency": frequency,
                "positive_ic_window_ratio": float((group["test_mean_ic"] > 0).mean()),
                "direction_agreement_ratio": direction_agreement,
                "median_train_ic": group["train_mean_ic"].median(),
                "median_validation_ic": group["validation_mean_ic"].median(),
                "median_test_ic": group["test_mean_ic"].median(),
                "worst_test_ic": group["test_mean_ic"].min(),
                "median_oos_degradation": degradation.median() if len(degradation) else np.nan,
                "maximum_oos_degradation": degradation.min() if len(degradation) else np.nan,
                "fdr_pass_frequency": float(group["fdr_bh_pass"].mean()),
                "coverage_min": group[["train_coverage", "validation_coverage", "test_coverage"]].min(axis=1).min(),
                "coverage_median": group[["train_coverage", "validation_coverage", "test_coverage"]].stack().median(),
                "stability_role": role,
                "role_reason": f"selection_frequency={frequency:.3f};direction_agreement={direction_agreement:.3f}",
            }
        )
    return pd.DataFrame(rows)
