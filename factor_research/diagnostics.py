from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from factor_research.evaluator import finite_numeric_rows
from factor_research.registry import FactorSpec


CONTROL_BUCKETS = {
    "liquidity_amount_mean_20": "amount_mean_20",
    "volatility_std_20": "std_20",
    "amount_variability_20": "amount_std_20",
}


def direction_adjust(value: float, spec: FactorSpec) -> float:
    sign = spec.direction_sign
    return value * sign if sign is not None and pd.notna(value) else np.nan


def load_tradability_labels(path: Path) -> pd.DataFrame:
    labels_path = path / "tradability_labels.csv"
    if not labels_path.exists():
        raise FileNotFoundError(f"Missing tradability labels: {labels_path}")
    labels = pd.read_csv(labels_path, parse_dates=["datetime"])
    required_columns = ["datetime", "instrument", "can_buy", "liquidity_bucket", "tradability_score"]
    optional_columns = ["can_sell", "data_quality_status", "has_core_missing", "disabled_reason"]
    columns = required_columns + [column for column in optional_columns if column in labels.columns]
    missing = [column for column in required_columns if column not in labels.columns]
    if missing:
        raise ValueError(f"tradability_labels.csv missing required columns: {missing}")
    labels["instrument"] = labels["instrument"].astype(str).str.upper()
    labels["can_buy"] = labels["can_buy"].astype(bool)
    if "can_sell" in labels.columns:
        labels["can_sell"] = labels["can_sell"].astype(bool)
    if "has_core_missing" in labels.columns:
        labels["has_core_missing"] = labels["has_core_missing"].astype(bool)
    labels["liquidity_bucket"] = pd.to_numeric(labels["liquidity_bucket"], errors="coerce")
    labels["tradability_score"] = pd.to_numeric(labels["tradability_score"], errors="coerce")
    return labels[columns]


def attach_tradability(frame: pd.DataFrame, labels: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    result["instrument"] = result["instrument"].astype(str).str.upper()
    result = result.merge(labels, on=["datetime", "instrument"], how="left")
    result["can_buy"] = result["can_buy"].fillna(False).astype(bool)
    if "can_sell" in result.columns:
        result["can_sell"] = result["can_sell"].fillna(False).astype(bool)
    if "has_core_missing" in result.columns:
        result["has_core_missing"] = result["has_core_missing"].fillna(True).astype(bool)
    if "data_quality_status" in result.columns:
        result["data_quality_status"] = result["data_quality_status"].fillna("missing_tradability")
    if "disabled_reason" in result.columns:
        result["disabled_reason"] = result["disabled_reason"].fillna("missing_tradability")
    result["liquidity_bucket"] = pd.to_numeric(result["liquidity_bucket"], errors="coerce")
    result["tradability_score"] = pd.to_numeric(result["tradability_score"], errors="coerce")
    return result


def tradable_only(frame: pd.DataFrame, min_liquidity_bucket: int, min_tradability_score: float) -> pd.DataFrame:
    if "can_buy" not in frame.columns:
        return frame.iloc[0:0].copy()
    return frame[
        frame["can_buy"]
        & frame["liquidity_bucket"].ge(min_liquidity_bucket)
        & frame["tradability_score"].ge(min_tradability_score)
    ].copy()


def information_coefficient(frame: pd.DataFrame, specs: list[FactorSpec], label: str, min_count: int) -> pd.DataFrame:
    rows = []
    for spec in specs:
        if spec.name not in frame.columns:
            continue
        for dt, group in frame.groupby("datetime", sort=True):
            values = finite_numeric_rows(group, [spec.name, label])
            if len(values) < min_count:
                continue
            rows.append(
                {
                    "datetime": dt,
                    "factor": spec.name,
                    "count": int(len(values)),
                    "ic": values[spec.name].corr(values[label], method="pearson"),
                    "rank_ic": values[spec.name].corr(values[label], method="spearman"),
                }
            )
    return pd.DataFrame(rows)


def summarize_factors(
    frame: pd.DataFrame,
    ic_series: pd.DataFrame,
    specs: list[FactorSpec],
    label: str,
    window_name: str,
    sample_name: str,
) -> pd.DataFrame:
    rows = []
    total_rows = len(frame)
    for spec in specs:
        if spec.name not in frame.columns:
            continue
        valid = finite_numeric_rows(frame, [spec.name, label])
        factor_ic = ic_series[ic_series["factor"] == spec.name] if not ic_series.empty else pd.DataFrame()
        ic = factor_ic["ic"].dropna() if not factor_ic.empty else pd.Series(dtype=float)
        rank_ic = factor_ic["rank_ic"].dropna() if not factor_ic.empty else pd.Series(dtype=float)
        mean_rank_ic = rank_ic.mean() if not rank_ic.empty else np.nan
        sign = spec.direction_sign
        directional_rank_ic = rank_ic * sign if sign is not None else pd.Series(dtype=float)
        directional_rank_ic_std = directional_rank_ic.std() if len(directional_rank_ic) > 1 else np.nan
        rows.append(
            {
                "window": window_name,
                "sample": sample_name,
                "label": label,
                "factor": spec.name,
                "category": spec.category,
                "expected_direction": spec.expected_direction,
                "coverage": len(valid) / total_rows if total_rows else np.nan,
                "missing_rate": 1 - len(valid) / total_rows if total_rows else np.nan,
                "mean_ic": ic.mean() if not ic.empty else np.nan,
                "icir": ic.mean() / ic.std() if len(ic) > 1 and ic.std() else np.nan,
                "mean_rank_ic": mean_rank_ic,
                "directional_mean_rank_ic": direction_adjust(mean_rank_ic, spec),
                "rank_icir": rank_ic.mean() / rank_ic.std() if len(rank_ic) > 1 and rank_ic.std() else np.nan,
                "directional_rank_icir": (
                    directional_rank_ic.mean() / directional_rank_ic_std
                    if len(directional_rank_ic) > 1 and directional_rank_ic_std
                    else np.nan
                ),
                "ic_win_rate": (directional_rank_ic > 0).mean() if not directional_rank_ic.empty else np.nan,
                "ic_dates": int(len(rank_ic)),
                "valid_rows": int(len(valid)),
            }
        )
    return pd.DataFrame(rows)


def assign_daily_bucket(values: pd.Series, quantiles: int) -> pd.Series:
    if values.notna().sum() < quantiles:
        return pd.Series(np.nan, index=values.index)
    try:
        return pd.qcut(values, quantiles, labels=False, duplicates="drop") + 1
    except ValueError:
        return pd.Series(np.nan, index=values.index)


def group_monotonicity(
    frame: pd.DataFrame,
    specs: list[FactorSpec],
    label: str,
    window_name: str,
    sample_name: str,
    quantiles: int,
    min_count: int,
) -> pd.DataFrame:
    rows = []
    for spec in specs:
        if spec.name not in frame.columns:
            continue
        group_rows = []
        for dt, group in frame.groupby("datetime", sort=True):
            values = finite_numeric_rows(group, [spec.name, label])
            if len(values) < max(min_count, quantiles):
                continue
            buckets = assign_daily_bucket(values[spec.name], quantiles)
            values = values.assign(quantile=buckets).dropna(subset=["quantile"])
            if values.empty:
                continue
            for quantile, q_group in values.groupby("quantile"):
                group_rows.append({"datetime": dt, "quantile": int(quantile), "mean_label": q_group[label].mean()})
        if not group_rows:
            continue
        groups = pd.DataFrame(group_rows)
        avg = groups.groupby("quantile")["mean_label"].mean().sort_index()
        if len(avg) < 2:
            continue
        spread = avg.iloc[-1] - avg.iloc[0]
        corr = pd.Series(avg.index.astype(float)).corr(avg, method="spearman")
        rows.append(
            {
                "window": window_name,
                "sample": sample_name,
                "label": label,
                "factor": spec.name,
                "category": spec.category,
                "expected_direction": spec.expected_direction,
                "quantile_count": int(len(avg)),
                "bottom_mean_label": float(avg.iloc[0]),
                "top_mean_label": float(avg.iloc[-1]),
                "top_bottom_spread": float(spread),
                "directional_spread": direction_adjust(float(spread), spec),
                "monotonicity_score": direction_adjust(float(corr), spec),
            }
        )
    return pd.DataFrame(rows)


def bucket_ic(
    frame: pd.DataFrame,
    specs: list[FactorSpec],
    label: str,
    window_name: str,
    sample_name: str,
    quantiles: int,
    min_count: int,
) -> pd.DataFrame:
    rows = []
    for bucket_name, control in CONTROL_BUCKETS.items():
        if control not in frame.columns:
            continue
        bucketed = frame.copy()
        bucketed["control_bucket"] = bucketed.groupby("datetime")[control].transform(
            lambda values: assign_daily_bucket(values, quantiles)
        )
        for spec in specs:
            if spec.name not in bucketed.columns:
                continue
            bucket_ic_rows = []
            for (dt, bucket), group in bucketed.dropna(subset=["control_bucket"]).groupby(
                ["datetime", "control_bucket"], sort=True
            ):
                values = finite_numeric_rows(group, [spec.name, label])
                if len(values) < min_count:
                    continue
                bucket_ic_rows.append(
                    {
                        "datetime": dt,
                        "bucket": int(bucket),
                        "rank_ic": values[spec.name].corr(values[label], method="spearman"),
                    }
                )
            if not bucket_ic_rows:
                continue
            result = pd.DataFrame(bucket_ic_rows)
            for bucket, group in result.groupby("bucket"):
                mean_rank_ic = group["rank_ic"].mean()
                rows.append(
                    {
                        "window": window_name,
                        "sample": sample_name,
                        "label": label,
                        "factor": spec.name,
                        "bucket_name": bucket_name,
                        "bucket": int(bucket),
                        "mean_rank_ic": mean_rank_ic,
                        "directional_mean_rank_ic": direction_adjust(mean_rank_ic, spec),
                        "ic_dates": int(group["rank_ic"].notna().sum()),
                    }
                )
    return pd.DataFrame(rows)


def factor_correlation(
    frame: pd.DataFrame,
    specs: list[FactorSpec],
    window_name: str,
    sample_name: str,
    label: str,
) -> pd.DataFrame:
    columns = [spec.name for spec in specs if spec.name in frame.columns]
    values = frame[columns].apply(pd.to_numeric, errors="coerce")
    values = values.where(np.isfinite(values), np.nan)
    corr = values.corr(method="spearman")
    rows = []
    for left in columns:
        for right in columns:
            if left >= right:
                continue
            rows.append(
                {
                    "window": window_name,
                    "sample": sample_name,
                    "label": label,
                    "factor_a": left,
                    "factor_b": right,
                    "spearman_corr": corr.loc[left, right],
                }
            )
    return pd.DataFrame(rows)
