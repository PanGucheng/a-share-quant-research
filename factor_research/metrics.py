from __future__ import annotations

import numpy as np
import pandas as pd

from factor_research.diagnostics import assign_daily_bucket
from factor_research.evaluator import finite_numeric_rows
from factor_research.registry import FactorSpec


def coverage_missing(
    frame: pd.DataFrame,
    specs: list[FactorSpec],
    labels: list[str],
    window_name: str,
    sample_name: str,
) -> pd.DataFrame:
    rows = []
    total_rows = len(frame)
    for spec in specs:
        if spec.name not in frame.columns:
            continue
        factor_valid = pd.to_numeric(frame[spec.name], errors="coerce").replace([np.inf, -np.inf], np.nan).notna()
        for label in labels:
            if label not in frame.columns:
                continue
            label_valid = pd.to_numeric(frame[label], errors="coerce").replace([np.inf, -np.inf], np.nan).notna()
            valid_rows = int((factor_valid & label_valid).sum())
            factor_missing_rows = int((~factor_valid).sum())
            label_missing_rows = int((~label_valid).sum())
            rows.append(
                {
                    "window": window_name,
                    "sample": sample_name,
                    "label": label,
                    "factor": spec.name,
                    "category": spec.category,
                    "expected_direction": spec.expected_direction,
                    "total_rows": int(total_rows),
                    "valid_rows": valid_rows,
                    "coverage": valid_rows / total_rows if total_rows else np.nan,
                    "missing_rate": 1 - valid_rows / total_rows if total_rows else np.nan,
                    "factor_missing_rows": factor_missing_rows,
                    "label_missing_rows": label_missing_rows,
                }
            )
    return pd.DataFrame(rows)


def top_quantile_turnover(
    frame: pd.DataFrame,
    specs: list[FactorSpec],
    window_name: str,
    sample_name: str,
    quantiles: int,
    min_count: int,
) -> pd.DataFrame:
    rows = []
    for spec in specs:
        if spec.name not in frame.columns:
            continue
        previous_top: set[str] | None = None
        for dt, group in frame.groupby("datetime", sort=True):
            values = finite_numeric_rows(group, ["instrument", spec.name])
            if len(values) < max(min_count, quantiles):
                continue
            buckets = assign_daily_bucket(values[spec.name], quantiles)
            values = values.assign(quantile=buckets).dropna(subset=["quantile"])
            if values.empty:
                continue
            top = set(values.loc[values["quantile"] == values["quantile"].max(), "instrument"])
            if previous_top:
                rows.append(
                    {
                        "window": window_name,
                        "sample": sample_name,
                        "factor": spec.name,
                        "category": spec.category,
                        "expected_direction": spec.expected_direction,
                        "datetime": dt,
                        "top_count": int(len(top)),
                        "top_quantile_turnover": 1 - len(top & previous_top) / len(previous_top),
                    }
                )
            previous_top = top
    return pd.DataFrame(rows)


def summarize_turnover(turnover: pd.DataFrame) -> pd.DataFrame:
    if turnover.empty:
        return pd.DataFrame()
    return (
        turnover.groupby(["window", "sample", "factor", "category", "expected_direction"])["top_quantile_turnover"]
        .agg(["mean", "median", "max", "count"])
        .reset_index()
        .rename(
            columns={
                "mean": "mean_top_quantile_turnover",
                "median": "median_top_quantile_turnover",
                "max": "max_top_quantile_turnover",
                "count": "turnover_dates",
            }
        )
    )
