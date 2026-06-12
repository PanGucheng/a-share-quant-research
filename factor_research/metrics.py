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
                new_names = top - previous_top
                rows.append(
                    {
                        "window": window_name,
                        "sample": sample_name,
                        "factor": spec.name,
                        "category": spec.category,
                        "expected_direction": spec.expected_direction,
                        "datetime": dt,
                        "top_count": int(len(top)),
                        "previous_top_count": int(len(previous_top)),
                        "new_top_count": int(len(new_names)),
                        "top_quantile_turnover": len(new_names) / len(top) if top else np.nan,
                    }
                )
            previous_top = top
    return pd.DataFrame(rows)


def group_returns(
    frame: pd.DataFrame,
    specs: list[FactorSpec],
    labels: list[str],
    window_name: str,
    sample_name: str,
    quantiles: int,
    min_count: int,
) -> pd.DataFrame:
    rows = []
    active_specs = [spec for spec in specs if spec.name in frame.columns]
    active_labels = [label for label in labels if label in frame.columns]
    if not active_specs or not active_labels:
        return pd.DataFrame()
    for dt, group in frame.groupby("datetime", sort=True):
        label_values = {
            label: pd.to_numeric(group[label], errors="coerce").replace([np.inf, -np.inf], np.nan)
            for label in active_labels
        }
        for spec in active_specs:
            factor_values = pd.to_numeric(group[spec.name], errors="coerce").replace([np.inf, -np.inf], np.nan)
            factor_valid = factor_values.notna()
            if int(factor_valid.sum()) < max(min_count, quantiles):
                continue
            buckets = assign_daily_bucket(factor_values, quantiles)
            for label, y in label_values.items():
                valid = factor_valid & y.notna() & buckets.notna()
                if int(valid.sum()) < max(min_count, quantiles):
                    continue
                values = pd.DataFrame({"quantile": buckets.loc[valid], label: y.loc[valid]})
                for quantile, quantile_frame in values.groupby("quantile", sort=True):
                    rows.append(
                        {
                            "window": window_name,
                            "sample": sample_name,
                            "label": label,
                            "factor": spec.name,
                            "category": spec.category,
                            "expected_direction": spec.expected_direction,
                            "datetime": dt,
                            "quantile": int(quantile),
                            "mean_label": float(quantile_frame[label].mean()),
                            "count": int(len(quantile_frame)),
                        }
                    )
    return pd.DataFrame(rows)


def summarize_group_returns(group_return: pd.DataFrame) -> pd.DataFrame:
    if group_return.empty:
        return pd.DataFrame()
    return (
        group_return.groupby(["window", "sample", "label", "factor", "category", "expected_direction", "quantile"])[
            "mean_label"
        ]
        .agg(["mean", "std", "count"])
        .reset_index()
        .rename(
            columns={
                "mean": "mean_group_return",
                "std": "std_group_return",
                "count": "group_return_dates",
            }
        )
    )


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
