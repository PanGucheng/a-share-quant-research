from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from factor_research.preprocess import (
    add_log_amount_proxy,
    cross_sectional_rank_norm,
    cross_sectional_zscore,
    groupwise_zscore,
    residual_neutralize_daily,
    winsorize_mad,
)
from factor_research.registry import FactorSpec


@dataclass(frozen=True)
class NeutralizationMethod:
    name: str
    description: str
    required_columns: tuple[str, ...] = ()


DEFAULT_METHODS = [
    NeutralizationMethod("raw", "Original factor value after tradability/data-quality filtering."),
    NeutralizationMethod("cs_rank", "Daily cross-sectional rank normalization, Qlib CSRankNorm style."),
    NeutralizationMethod("cs_zscore", "Daily robust z-score after MAD winsorization."),
    NeutralizationMethod(
        "liquidity_bucket_zscore",
        "Daily robust z-score inside each tradability liquidity bucket.",
        ("liquidity_bucket",),
    ),
    NeutralizationMethod(
        "volatility_bucket_zscore",
        "Daily robust z-score inside each amplitude_20 volatility bucket.",
        ("volatility_bucket",),
    ),
    NeutralizationMethod(
        "amount_proxy_residual",
        "Daily residual after controlling log(amount_mean_20).",
        ("log_amount_mean_20",),
    ),
    NeutralizationMethod(
        "liquidity_volatility_residual",
        "Daily residual after controlling liquidity bucket, volatility bucket, and log amount proxy.",
        ("liquidity_bucket", "volatility_bucket", "log_amount_mean_20"),
    ),
]


def available_methods(frame: pd.DataFrame, methods: list[NeutralizationMethod] | None = None) -> list[NeutralizationMethod]:
    result = []
    for method in methods or DEFAULT_METHODS:
        if all(column in frame.columns for column in method.required_columns):
            result.append(method)
    return result


def add_neutralized_factors(
    frame: pd.DataFrame,
    specs: list[FactorSpec],
    methods: list[NeutralizationMethod] | None = None,
    min_count: int = 50,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    result = add_log_amount_proxy(frame)
    rows = []
    active_methods = available_methods(result, methods)
    for spec in specs:
        if spec.name not in result.columns:
            continue
        for method in active_methods:
            column = f"{spec.name}__{method.name}"
            if method.name == "raw":
                result[column] = result[spec.name]
            elif method.name == "cs_rank":
                result[column] = result.groupby("datetime", group_keys=False)[spec.name].transform(cross_sectional_rank_norm)
            elif method.name == "cs_zscore":
                clean_col = f"__{spec.name}_mad"
                result[clean_col] = result.groupby("datetime", group_keys=False)[spec.name].transform(winsorize_mad)
                result[column] = result.groupby("datetime", group_keys=False)[clean_col].transform(cross_sectional_zscore)
                result = result.drop(columns=[clean_col])
            elif method.name == "liquidity_bucket_zscore":
                result[column] = groupwise_zscore(result, spec.name, "liquidity_bucket")
            elif method.name == "volatility_bucket_zscore":
                result[column] = groupwise_zscore(result, spec.name, "volatility_bucket")
            elif method.name == "amount_proxy_residual":
                result[column] = residual_neutralize_daily(
                    result,
                    spec.name,
                    ["log_amount_mean_20"],
                    min_count=min_count,
                )
            elif method.name == "liquidity_volatility_residual":
                result[column] = residual_neutralize_daily(
                    result,
                    spec.name,
                    ["liquidity_bucket", "volatility_bucket", "log_amount_mean_20"],
                    min_count=min_count,
                )
            else:
                continue
            rows.append(
                {
                    "factor": spec.name,
                    "neutralization": method.name,
                    "neutralized_factor": column,
                    "description": method.description,
                    "required_columns": ",".join(method.required_columns),
                    "non_null_rows": int(pd.to_numeric(result[column], errors="coerce").notna().sum()),
                }
            )
    return result, pd.DataFrame(rows)
