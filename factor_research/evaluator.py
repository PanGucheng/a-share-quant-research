from dataclasses import dataclass
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from factor_research.factor_library import BASE_FIELDS, FACTOR_COLUMNS, FACTOR_METADATA, LABEL_COLUMNS, add_basic_factors
from factor_research.report import write_markdown_report


@dataclass(frozen=True)
class FactorResearchConfig:
    provider_uri: str
    market: str
    start_time: str
    end_time: str
    output_dir: Path
    label: str = "label_1d_t1"
    quantiles: int = 5
    min_count: int = 50
    feature_cache_dir: Path | None = None
    refresh_feature_cache: bool = False


def feature_cache_path(config: FactorResearchConfig) -> Path | None:
    if config.feature_cache_dir is None:
        return None
    key = {
        "provider_uri": str(config.provider_uri).replace("\\", "/"),
        "market": config.market,
        "start_time": config.start_time,
        "end_time": config.end_time,
        "fields": BASE_FIELDS,
        "version": 1,
    }
    digest = hashlib.sha256(json.dumps(key, sort_keys=True).encode("utf-8")).hexdigest()[:16]
    return Path(config.feature_cache_dir) / f"features_{digest}.pkl"


def load_feature_frame(config: FactorResearchConfig) -> pd.DataFrame:
    cache_path = feature_cache_path(config)
    if cache_path is not None and cache_path.exists() and not config.refresh_feature_cache:
        print(f"Loading cached features: {cache_path}", flush=True)
        return pd.read_pickle(cache_path)

    import qlib
    from qlib.config import C, REG_CN
    from qlib.data import D

    qlib.init(provider_uri=config.provider_uri, region=REG_CN)
    C.kernels = 1
    C.joblib_backend = "sequential"
    data = D.features(
        D.instruments(config.market),
        BASE_FIELDS,
        start_time=config.start_time,
        end_time=config.end_time,
        freq="day",
    )
    frame = data.reset_index().sort_values(["instrument", "datetime"])
    if cache_path is not None:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        frame.to_pickle(cache_path)
        print(f"Cached features: {cache_path}", flush=True)
    return frame


def finite_numeric_rows(frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    values = frame[columns].copy()
    for column in columns:
        if column != "instrument":
            values[column] = pd.to_numeric(values[column], errors="coerce")
    numeric_columns = [column for column in columns if column != "instrument"]
    mask = np.isfinite(values[numeric_columns]).all(axis=1)
    return values.loc[mask]


def information_coefficient(frame: pd.DataFrame, label: str) -> pd.DataFrame:
    rows = []
    for factor in FACTOR_COLUMNS:
        for dt, group in frame.groupby("datetime", sort=True):
            values = finite_numeric_rows(group, [factor, label])
            if len(values) < 2:
                continue
            rows.append(
                {
                    "datetime": dt,
                    "factor": factor,
                    "count": int(len(values)),
                    "ic": values[factor].corr(values[label], method="pearson"),
                    "rank_ic": values[factor].corr(values[label], method="spearman"),
                }
            )
    return pd.DataFrame(rows)


def factor_summary(frame: pd.DataFrame, ic_series: pd.DataFrame, label: str) -> pd.DataFrame:
    rows = []
    total_rows = len(frame)
    for factor in FACTOR_COLUMNS:
        valid = finite_numeric_rows(frame, [factor, label])
        factor_ic = ic_series[ic_series["factor"] == factor]
        ic = factor_ic["ic"].dropna()
        rank_ic = factor_ic["rank_ic"].dropna()
        metadata = FACTOR_METADATA.get(factor, {})
        expected_direction = metadata.get("expected_direction", "watch")
        direction_sign = {"positive": 1, "negative": -1}.get(expected_direction)
        mean_rank_ic = rank_ic.mean() if not rank_ic.empty else np.nan
        rows.append(
            {
                "factor": factor,
                "category": metadata.get("category", "unknown"),
                "expected_direction": expected_direction,
                "coverage": len(valid) / total_rows if total_rows else np.nan,
                "mean_ic": ic.mean() if not ic.empty else np.nan,
                "icir": ic.mean() / ic.std() if len(ic) > 1 and ic.std() else np.nan,
                "mean_rank_ic": mean_rank_ic,
                "directional_mean_rank_ic": mean_rank_ic * direction_sign if direction_sign is not None else np.nan,
                "rank_icir": rank_ic.mean() / rank_ic.std() if len(rank_ic) > 1 and rank_ic.std() else np.nan,
                "valid_rows": int(len(valid)),
            }
        )
    return pd.DataFrame(rows).sort_values("mean_rank_ic", key=lambda s: s.abs(), ascending=False)


def group_returns(frame: pd.DataFrame, label: str, quantiles: int, min_count: int) -> pd.DataFrame:
    rows = []
    for factor in FACTOR_COLUMNS:
        for dt, group in frame.groupby("datetime", sort=True):
            values = finite_numeric_rows(group, [factor, label])
            if len(values) < max(min_count, quantiles):
                continue
            try:
                buckets = pd.qcut(values[factor], quantiles, labels=False, duplicates="drop")
            except ValueError:
                continue
            values = values.assign(quantile=buckets + 1)
            for quantile, q_group in values.groupby("quantile"):
                rows.append(
                    {
                        "datetime": dt,
                        "factor": factor,
                        "quantile": int(quantile),
                        "mean_label": q_group[label].mean(),
                        "count": int(len(q_group)),
                    }
                )
    return pd.DataFrame(rows)


def turnover(frame: pd.DataFrame, quantiles: int, min_count: int) -> pd.DataFrame:
    rows = []
    for factor in FACTOR_COLUMNS:
        previous_top: set[str] | None = None
        for dt, group in frame.groupby("datetime", sort=True):
            values = finite_numeric_rows(group, ["instrument", factor]).dropna()
            if len(values) < max(min_count, quantiles):
                continue
            try:
                buckets = pd.qcut(values[factor], quantiles, labels=False, duplicates="drop")
            except ValueError:
                continue
            values = values.assign(quantile=buckets + 1)
            top = set(values.loc[values["quantile"] == values["quantile"].max(), "instrument"])
            if previous_top is not None and previous_top:
                rows.append(
                    {
                        "datetime": dt,
                        "factor": factor,
                        "top_count": int(len(top)),
                        "turnover": 1 - len(top & previous_top) / len(previous_top),
                    }
                )
            previous_top = top
    return pd.DataFrame(rows)


def factor_correlation(frame: pd.DataFrame) -> pd.DataFrame:
    values = frame[FACTOR_COLUMNS].apply(pd.to_numeric, errors="coerce")
    values = values.where(np.isfinite(values), np.nan)
    return values.corr(method="spearman").reset_index().rename(columns={"index": "factor"})


def run_factor_research(config: FactorResearchConfig) -> Path:
    config.output_dir.mkdir(parents=True, exist_ok=True)
    raw = load_feature_frame(config)
    factors = add_basic_factors(raw)
    ic = information_coefficient(factors, config.label)
    summary = factor_summary(factors, ic, config.label)
    groups = group_returns(factors, config.label, config.quantiles, config.min_count)
    turns = turnover(factors, config.quantiles, config.min_count)
    corr = factor_correlation(factors)

    summary.to_csv(config.output_dir / "factor_summary.csv", index=False, encoding="utf-8-sig")
    ic.to_csv(config.output_dir / "ic_series.csv", index=False, encoding="utf-8-sig")
    groups.to_csv(config.output_dir / "group_return.csv", index=False, encoding="utf-8-sig")
    turns.to_csv(config.output_dir / "turnover.csv", index=False, encoding="utf-8-sig")
    corr.to_csv(config.output_dir / "correlation.csv", index=False, encoding="utf-8-sig")
    write_markdown_report(config, summary, ic, groups, turns, config.output_dir / "factor_research_report.md")
    return config.output_dir
