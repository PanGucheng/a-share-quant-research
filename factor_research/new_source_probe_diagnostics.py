from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from factor_research.evaluator import FactorResearchConfig, load_feature_frame
from factor_research.factor_library import add_basic_factors
from factor_research.report import markdown_table
from scripts.run_factor_score_portfolio import cross_sectional_zscore
from scripts.run_low_frequency_tradability_portfolio import run_low_frequency_portfolio


PROJECT_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class ProbeSelectionConfig:
    max_frame_factors: int
    max_portfolio_factors: int
    per_source_caps: dict[str, int]


@dataclass(frozen=True)
class ProbeDiagnosticsRules:
    min_total_probes: int
    min_frame_factors: int
    min_portfolio_factors: int
    high_abs_corr: float
    high_abs_tradability_exposure: float
    min_horizon_consistency: float


@dataclass(frozen=True)
class ProbePortfolioConfig:
    provider_uri: str
    market: str
    start_time: str
    end_time: str
    label: str
    feature_cache_dir: Path | None
    rebalance_every: int
    topk: int
    cost_bps: float
    score_clip: float
    min_score_components: int
    min_liquidity_bucket: int
    min_tradability_score: float
    min_capacity_multiple: float


@dataclass(frozen=True)
class NewSourceProbeDiagnosticsConfig:
    probe_input: Path
    judgement_board: Path
    factor_frames: dict[str, Path]
    tradability_dir: Path
    output_dir: Path
    selection: ProbeSelectionConfig
    rules: ProbeDiagnosticsRules
    portfolio: ProbePortfolioConfig
    correlation_max_dates: int | None
    exposure_max_dates: int | None
    min_instruments: int
    top_pairs: int


def portable_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def read_csv_required(path: Path) -> pd.DataFrame:
    if not path.exists() or path.stat().st_size <= 0:
        raise FileNotFoundError(f"Missing or empty required input: {path}")
    return pd.read_csv(path)


def numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def sign_value(value: object) -> int:
    number = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    if pd.isna(number) or number == 0:
        return 0
    return 1 if number > 0 else -1


def select_dates(dates: list[pd.Timestamp], max_dates: int | None) -> list[pd.Timestamp]:
    if max_dates is None or max_dates <= 0 or len(dates) <= max_dates:
        return dates
    indexes = np.linspace(0, len(dates) - 1, max_dates).round().astype(int)
    return [dates[index] for index in sorted(set(indexes.tolist()))]


def load_probe_inventory(config: NewSourceProbeDiagnosticsConfig) -> pd.DataFrame:
    probes = read_csv_required(config.probe_input)
    board = read_csv_required(config.judgement_board)
    required = ["factor", "source_family", "judgement_role", "judgement_label"]
    missing = [column for column in required if column not in probes.columns]
    if missing:
        raise ValueError(f"probe input missing required columns: {missing}")
    probes = probes[probes["judgement_role"].eq("new_source_alpha_probe")].copy()
    if probes.empty:
        raise ValueError("new-source alpha probe input is empty")
    board_cols = [
        "factor",
        "source_family",
        "source_project",
        "category",
        "promotion_decision",
        "screening_gate",
        "research_included",
        "downstream_default_included",
    ]
    board_cols = [column for column in board_cols if column in board.columns]
    board_meta = board[board_cols].drop_duplicates("factor")
    suffix_cols = [column for column in board_meta.columns if column != "factor" and column in probes.columns]
    if suffix_cols:
        board_meta = board_meta.drop(columns=suffix_cols)
    probes = probes.merge(board_meta, on="factor", how="left")
    if "downstream_default_included" not in probes.columns:
        probes["downstream_default_included"] = False
    probes["downstream_default_included"] = probes["downstream_default_included"].fillna(False)
    for column in [
        "max_abs_mean_ic",
        "max_abs_qlib_ir",
        "direction_agreement_ratio",
        "coverage",
        "missing_rate",
        "metric_value_count",
    ]:
        if column in probes.columns:
            probes[column] = numeric(probes[column])
    return probes.sort_values(["source_family", "judgement_label", "factor"]).reset_index(drop=True)


def quality_sort_frame(frame: pd.DataFrame) -> pd.DataFrame:
    label_rank = {
        "strong_signal_probe": 0,
        "consistent_signal_probe": 1,
    }
    result = frame.copy()
    result["_label_rank"] = result["judgement_label"].map(label_rank).fillna(9)
    for column in ["max_abs_mean_ic", "max_abs_qlib_ir", "direction_agreement_ratio", "coverage"]:
        if column not in result.columns:
            result[column] = np.nan
    result = result.sort_values(
        ["_label_rank", "max_abs_mean_ic", "max_abs_qlib_ir", "direction_agreement_ratio", "coverage", "factor"],
        ascending=[True, False, False, False, False, True],
    )
    return result.drop(columns=["_label_rank"])


def select_probe_subset(probes: pd.DataFrame, config: ProbeSelectionConfig, count_key: str) -> pd.DataFrame:
    selected = []
    for source, group in probes.groupby("source_family", sort=True):
        cap = int(config.per_source_caps.get(str(source), len(group)))
        if cap <= 0:
            continue
        selected.append(quality_sort_frame(group).head(cap))
    if not selected:
        return pd.DataFrame(columns=probes.columns)
    result = quality_sort_frame(pd.concat(selected, ignore_index=True))
    max_count = getattr(config, count_key)
    if max_count > 0:
        result = result.head(max_count)
    return result.reset_index(drop=True)


def load_factor_frames(config: NewSourceProbeDiagnosticsConfig, selected: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    pieces = []
    coverage_rows = []
    for source, group in selected.groupby("source_family", sort=True):
        path = config.factor_frames.get(str(source))
        factors = group["factor"].astype(str).tolist()
        if path is None or not path.exists():
            for factor in factors:
                coverage_rows.append(
                    {
                        "factor": factor,
                        "source_family": source,
                        "frame_status": "missing_factor_frame",
                        "valid_rows": 0,
                        "total_rows": 0,
                        "coverage": np.nan,
                        "missing_rate": np.nan,
                    }
                )
            continue
        frame = pd.read_pickle(path)
        required = ["datetime", "instrument"]
        missing_required = [column for column in required if column not in frame.columns]
        if missing_required:
            raise ValueError(f"{path} missing required columns: {missing_required}")
        available = [factor for factor in factors if factor in frame.columns]
        missing = sorted(set(factors) - set(available))
        for factor in missing:
            coverage_rows.append(
                {
                    "factor": factor,
                    "source_family": source,
                    "frame_status": "missing_factor_column",
                    "valid_rows": 0,
                    "total_rows": int(len(frame)),
                    "coverage": 0.0,
                    "missing_rate": 1.0,
                }
            )
        if not available:
            continue
        subset = frame[["datetime", "instrument", *available]].copy()
        subset["datetime"] = pd.to_datetime(subset["datetime"])
        subset["instrument"] = subset["instrument"].astype(str).str.upper()
        for factor in available:
            valid = int(subset[factor].notna().sum())
            total = int(len(subset))
            coverage_rows.append(
                {
                    "factor": factor,
                    "source_family": source,
                    "frame_status": "available",
                    "valid_rows": valid,
                    "total_rows": total,
                    "coverage": float(valid / total) if total else np.nan,
                    "missing_rate": float(1 - valid / total) if total else np.nan,
                }
            )
        pieces.append(subset)
    if not pieces:
        return pd.DataFrame(), pd.DataFrame(coverage_rows)
    merged = pieces[0]
    for piece in pieces[1:]:
        merged = merged.merge(piece, on=["datetime", "instrument"], how="inner")
    return merged.sort_values(["datetime", "instrument"]).reset_index(drop=True), pd.DataFrame(coverage_rows)


def daily_cross_section_spearman_frame(
    frame: pd.DataFrame,
    factors: list[str],
    *,
    max_dates: int | None,
    min_instruments: int,
    top_pairs: int,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    available = [factor for factor in factors if factor in frame.columns]
    if len(available) < 2 or frame.empty:
        return pd.DataFrame(), pd.DataFrame(), {"enabled": False, "reason": "not_enough_factors"}
    dates = select_dates(sorted(frame["datetime"].dropna().unique().tolist()), max_dates)
    work = frame[frame["datetime"].isin(dates)][["datetime", *available]].copy()
    n = len(available)
    corr_sum = np.zeros((n, n), dtype="float64")
    corr_count = np.zeros((n, n), dtype="int32")
    used_dates = 0
    for _, group in work.groupby("datetime", sort=True):
        if len(group) < min_instruments:
            continue
        corr = group[available].corr(method="spearman", min_periods=min_instruments)
        arr = corr.to_numpy(dtype="float64")
        mask = ~np.isnan(arr)
        corr_sum[mask] += arr[mask]
        corr_count[mask] += 1
        used_dates += 1
    with np.errstate(invalid="ignore", divide="ignore"):
        mean_corr = corr_sum / corr_count
    np.fill_diagonal(mean_corr, np.nan)

    factor_rows = []
    pair_rows = []
    for i, factor in enumerate(available):
        row = mean_corr[i, :]
        valid = np.where(~np.isnan(row))[0]
        if len(valid) == 0:
            factor_rows.append(
                {
                    "factor": factor,
                    "strongest_corr_factor": "",
                    "strongest_corr": np.nan,
                    "strongest_abs_corr": np.nan,
                }
            )
            continue
        strongest_index = valid[np.argmax(np.abs(row[valid]))]
        factor_rows.append(
            {
                "factor": factor,
                "strongest_corr_factor": available[strongest_index],
                "strongest_corr": float(row[strongest_index]),
                "strongest_abs_corr": float(abs(row[strongest_index])),
            }
        )
    for i in range(n):
        for j in range(i + 1, n):
            value = mean_corr[i, j]
            if np.isnan(value):
                continue
            pair_rows.append(
                {
                    "factor_a": available[i],
                    "factor_b": available[j],
                    "mean_daily_spearman_corr": float(value),
                    "abs_mean_daily_spearman_corr": float(abs(value)),
                    "date_count": int(corr_count[i, j]),
                }
            )
    pair_summary = pd.DataFrame(pair_rows)
    if not pair_summary.empty:
        pair_summary = pair_summary.sort_values("abs_mean_daily_spearman_corr", ascending=False).head(top_pairs)
    meta = {
        "enabled": True,
        "method": "daily_cross_section_spearman_mean",
        "available_factor_count": len(available),
        "candidate_date_count": len(dates),
        "used_date_count": used_dates,
        "min_instruments": min_instruments,
    }
    return pd.DataFrame(factor_rows), pair_summary, meta


def load_tradability_subset(tradability_dir: Path, dates: list[pd.Timestamp]) -> pd.DataFrame:
    path = tradability_dir / "tradability_labels.csv"
    if not path.exists():
        raise FileNotFoundError(f"Missing tradability labels: {path}")
    labels = pd.read_csv(
        path,
        usecols=["datetime", "instrument", "liquidity_value", "liquidity_bucket", "tradability_score", "can_buy", "can_sell"],
        parse_dates=["datetime"],
    )
    labels["instrument"] = labels["instrument"].astype(str).str.upper()
    if dates:
        labels = labels[labels["datetime"].isin(dates)].copy()
    return labels


def tradability_exposure(
    frame: pd.DataFrame,
    factors: list[str],
    config: NewSourceProbeDiagnosticsConfig,
) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame()
    available = [factor for factor in factors if factor in frame.columns]
    dates = select_dates(sorted(frame["datetime"].dropna().unique().tolist()), config.exposure_max_dates)
    work = frame[frame["datetime"].isin(dates)][["datetime", "instrument", *available]].copy()
    labels = load_tradability_subset(config.tradability_dir, dates)
    work = work.merge(labels, on=["datetime", "instrument"], how="inner")
    proxy_cols = ["liquidity_value", "liquidity_bucket", "tradability_score"]
    rows = []
    for factor in available:
        corr_sums = {proxy: 0.0 for proxy in proxy_cols}
        corr_counts = {proxy: 0 for proxy in proxy_cols}
        high_bucket_mean = []
        low_bucket_mean = []
        for _, group in work.groupby("datetime", sort=True):
            if len(group) < config.min_instruments:
                continue
            factor_values = pd.to_numeric(group[factor], errors="coerce")
            for proxy in proxy_cols:
                proxy_values = pd.to_numeric(group[proxy], errors="coerce")
                corr = factor_values.corr(proxy_values, method="spearman")
                if pd.notna(corr):
                    corr_sums[proxy] += float(corr)
                    corr_counts[proxy] += 1
            zscore = cross_sectional_zscore(factor_values, 3.0)
            high = zscore[group["liquidity_bucket"].ge(4)].dropna()
            low = zscore[group["liquidity_bucket"].le(2)].dropna()
            if not high.empty:
                high_bucket_mean.append(float(high.mean()))
            if not low.empty:
                low_bucket_mean.append(float(low.mean()))
        row = {"factor": factor}
        abs_values = []
        for proxy in proxy_cols:
            value = corr_sums[proxy] / corr_counts[proxy] if corr_counts[proxy] else np.nan
            row[f"mean_spearman_{proxy}"] = value
            row[f"{proxy}_date_count"] = corr_counts[proxy]
            if pd.notna(value):
                abs_values.append(abs(value))
        row["high_liquidity_z_mean"] = float(np.mean(high_bucket_mean)) if high_bucket_mean else np.nan
        row["low_liquidity_z_mean"] = float(np.mean(low_bucket_mean)) if low_bucket_mean else np.nan
        row["high_minus_low_liquidity_z"] = (
            row["high_liquidity_z_mean"] - row["low_liquidity_z_mean"]
            if pd.notna(row["high_liquidity_z_mean"]) and pd.notna(row["low_liquidity_z_mean"])
            else np.nan
        )
        row["max_abs_tradability_exposure"] = max(abs_values) if abs_values else np.nan
        rows.append(row)
    return pd.DataFrame(rows)


def horizon_consistency(row: pd.Series) -> dict[str, Any]:
    pairs = [
        ("alphalens_mean_ic_10d", "alphalens_mean_ic_20d"),
        ("jqfactor_mean_ic_10d", "jqfactor_mean_ic_20d"),
        ("qlib_information_ratio_10d", "qlib_information_ratio_20d"),
    ]
    observed = 0
    consistent = 0
    for left, right in pairs:
        left_sign = sign_value(row.get(left))
        right_sign = sign_value(row.get(right))
        if left_sign == 0 or right_sign == 0:
            continue
        observed += 1
        if left_sign == right_sign:
            consistent += 1
    return {
        "horizon_pair_count": observed,
        "horizon_consistent_count": consistent,
        "horizon_consistency_ratio": float(consistent / observed) if observed else np.nan,
    }


def build_diagnostic_board(
    probes: pd.DataFrame,
    selected_frame: pd.DataFrame,
    selected_portfolio: pd.DataFrame,
    coverage: pd.DataFrame,
    corr_summary: pd.DataFrame,
    exposure: pd.DataFrame,
    rules: ProbeDiagnosticsRules,
) -> pd.DataFrame:
    board = probes.copy()
    board["frame_diagnostic_selected"] = board["factor"].isin(set(selected_frame["factor"]))
    board["portfolio_smoke_selected"] = board["factor"].isin(set(selected_portfolio["factor"]))
    stability_rows = pd.DataFrame([horizon_consistency(row) for _, row in board.iterrows()])
    board = pd.concat([board.reset_index(drop=True), stability_rows], axis=1)
    if not coverage.empty:
        board = board.merge(coverage, on=["factor", "source_family"], how="left", suffixes=("", "_frame"))
    if not corr_summary.empty:
        board = board.merge(corr_summary, on="factor", how="left")
    if not exposure.empty:
        board = board.merge(exposure, on="factor", how="left")
    board["high_redundancy_watch"] = numeric(board.get("strongest_abs_corr", pd.Series(np.nan, index=board.index))).ge(
        rules.high_abs_corr
    )
    board["high_tradability_exposure_watch"] = numeric(
        board.get("max_abs_tradability_exposure", pd.Series(np.nan, index=board.index))
    ).ge(rules.high_abs_tradability_exposure)
    board["horizon_unstable_watch"] = numeric(board["horizon_consistency_ratio"]).lt(rules.min_horizon_consistency)
    board["diagnostic_label"] = np.select(
        [
            board["portfolio_smoke_selected"],
            board["high_redundancy_watch"],
            board["high_tradability_exposure_watch"],
            board["horizon_unstable_watch"],
            board["frame_diagnostic_selected"],
        ],
        [
            "portfolio_smoke_probe",
            "redundancy_watch",
            "tradability_exposure_watch",
            "horizon_stability_watch",
            "frame_diagnostic_probe",
        ],
        default="metric_only_probe",
    )
    return board.sort_values(["diagnostic_label", "source_family", "factor"]).reset_index(drop=True)


def direction_weight(row: pd.Series) -> float:
    direction = str(row.get("consensus_direction", "")).lower()
    if direction == "positive":
        return 1.0
    if direction == "negative":
        return -1.0
    sign = sign_value(row.get("consensus_direction_sign"))
    return float(sign) if sign else np.nan


def score_portfolio_candidates(
    factor_frame: pd.DataFrame,
    weights: pd.DataFrame,
    portfolio: ProbePortfolioConfig,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    if factor_frame.empty or weights.empty:
        return pd.DataFrame(), pd.DataFrame()
    start = pd.Timestamp(portfolio.start_time)
    end = pd.Timestamp(portfolio.end_time)
    factors = weights["factor"].astype(str).tolist()
    frame = factor_frame[factor_frame["datetime"].between(start, end)][["datetime", "instrument", *factors]].copy()
    score = pd.Series(0.0, index=frame.index)
    total_abs_weight = pd.Series(0.0, index=frame.index)
    component_count = pd.Series(0, index=frame.index, dtype="int64")
    component_rows = []
    for row in weights.itertuples(index=False):
        zscore = frame.groupby("datetime", group_keys=False)[row.factor].transform(
            lambda values: cross_sectional_zscore(values, portfolio.score_clip)
        )
        valid = zscore.notna()
        score.loc[valid] += zscore.loc[valid] * float(row.weight)
        total_abs_weight.loc[valid] += abs(float(row.weight))
        component_count.loc[valid] += 1
        component_rows.append(
            {
                "factor": row.factor,
                "weight": row.weight,
                "valid_rows": int(valid.sum()),
                "coverage": float(valid.mean()),
            }
        )
    frame["score_component_count"] = component_count
    frame["score"] = np.where(total_abs_weight > 0, score / total_abs_weight, np.nan)
    frame = frame[frame["score_component_count"].ge(portfolio.min_score_components)].copy()
    return frame[["datetime", "instrument", "score", "score_component_count"]], pd.DataFrame(component_rows)


def load_label_frame(portfolio: ProbePortfolioConfig, output_dir: Path) -> pd.DataFrame:
    feature_config = FactorResearchConfig(
        provider_uri=portfolio.provider_uri,
        market=portfolio.market,
        start_time=portfolio.start_time,
        end_time=portfolio.end_time,
        label=portfolio.label,
        output_dir=output_dir,
        feature_cache_dir=portfolio.feature_cache_dir,
    )
    raw = load_feature_frame(feature_config)
    features = add_basic_factors(raw)
    features["instrument"] = features["instrument"].astype(str).str.upper()
    features["datetime"] = pd.to_datetime(features["datetime"])
    features["daily_return"] = features.groupby("instrument")["$close"].pct_change(fill_method=None)
    return features[["datetime", "instrument", portfolio.label, "daily_return"]].copy()


def run_portfolio_smoke(
    factor_frame: pd.DataFrame,
    selected: pd.DataFrame,
    config: NewSourceProbeDiagnosticsConfig,
) -> dict[str, pd.DataFrame | dict[str, Any]]:
    weights = selected.copy()
    weights["weight"] = weights.apply(direction_weight, axis=1)
    weights = weights.dropna(subset=["weight"])
    if weights.empty:
        empty_summary = {"status": "skipped_no_directional_weights", "candidate_count": 0}
        return {
            "summary": empty_summary,
            "weights": pd.DataFrame(),
            "component_summary": pd.DataFrame(),
            "daily": pd.DataFrame(),
            "rebalances": pd.DataFrame(),
            "positions": pd.DataFrame(),
            "liquidity_exposure": pd.DataFrame(),
        }
    score_frame, component_summary = score_portfolio_candidates(factor_frame, weights[["factor", "weight"]], config.portfolio)
    if score_frame.empty:
        empty_summary = {"status": "skipped_empty_score_frame", "candidate_count": int(len(weights))}
        return {
            "summary": empty_summary,
            "weights": weights[["factor", "source_family", "judgement_label", "consensus_direction", "weight"]],
            "component_summary": component_summary,
            "daily": pd.DataFrame(),
            "rebalances": pd.DataFrame(),
            "positions": pd.DataFrame(),
            "liquidity_exposure": pd.DataFrame(),
        }
    labels = load_label_frame(config.portfolio, config.output_dir)
    frame = score_frame.merge(labels, on=["datetime", "instrument"], how="inner")
    tradability = load_tradability_subset(config.tradability_dir, [])
    frame = frame.merge(tradability, on=["datetime", "instrument"], how="left")
    frame["can_buy"] = frame["can_buy"].fillna(False).astype(bool)
    frame["can_sell"] = frame["can_sell"].fillna(False).astype(bool)
    frame["liquidity_bucket"] = pd.to_numeric(frame["liquidity_bucket"], errors="coerce")
    frame["tradability_score"] = pd.to_numeric(frame["tradability_score"], errors="coerce")
    daily, rebalances, positions, summary = run_low_frequency_portfolio(
        frame.sort_values(["datetime", "instrument"]).reset_index(drop=True),
        config.portfolio.label,
        config.portfolio.topk,
        config.portfolio.rebalance_every,
        config.portfolio.cost_bps,
        config.portfolio.min_liquidity_bucket,
        config.portfolio.min_tradability_score,
        config.portfolio.min_capacity_multiple,
    )
    summary.update(
        {
            "status": "pass" if summary.get("executed_rebalances", 0) else "partial_no_executed_rebalances",
            "candidate_count": int(len(weights)),
            "score_policy": "equal_directional_zscore_from_probe_consensus",
            "score_clip": config.portfolio.score_clip,
            "min_score_components": config.portfolio.min_score_components,
        }
    )
    if positions.empty:
        liquidity = pd.DataFrame()
    else:
        liquidity = (
            positions.groupby("liquidity_bucket")
            .size()
            .reset_index(name="position_count")
            .sort_values("liquidity_bucket")
        )
        total = liquidity["position_count"].sum()
        liquidity["position_share"] = liquidity["position_count"] / total if total else 0.0
    return {
        "summary": summary,
        "weights": weights[["factor", "source_family", "judgement_label", "consensus_direction", "weight"]],
        "component_summary": component_summary,
        "daily": daily,
        "rebalances": rebalances,
        "positions": positions,
        "liquidity_exposure": liquidity,
    }


def build_contract_status(
    probes: pd.DataFrame,
    frame_selected: pd.DataFrame,
    portfolio_selected: pd.DataFrame,
    corr_pairs: pd.DataFrame,
    portfolio_summary: dict[str, Any],
    board: pd.DataFrame,
    rules: ProbeDiagnosticsRules,
) -> pd.DataFrame:
    rows = [
        {
            "check_id": "probe_count",
            "status": "pass" if len(probes) >= rules.min_total_probes else "blocked",
            "detail": f"probes={len(probes)}",
        },
        {
            "check_id": "frame_selection_count",
            "status": "pass" if len(frame_selected) >= rules.min_frame_factors else "blocked",
            "detail": f"selected={len(frame_selected)}",
        },
        {
            "check_id": "portfolio_selection_count",
            "status": "pass" if len(portfolio_selected) >= rules.min_portfolio_factors else "blocked",
            "detail": f"selected={len(portfolio_selected)}",
        },
        {
            "check_id": "correlation_pairs",
            "status": "pass" if len(corr_pairs) > 0 else "partial",
            "detail": f"pairs={len(corr_pairs)}",
        },
        {
            "check_id": "portfolio_smoke_executed",
            "status": "pass" if int(portfolio_summary.get("executed_rebalances", 0) or 0) > 0 else "partial",
            "detail": f"executed_rebalances={portfolio_summary.get('executed_rebalances', 0)}",
        },
        {
            "check_id": "new_source_not_downstream_default",
            "status": "pass" if not board.get("downstream_default_included", pd.Series(False, index=board.index)).astype(bool).any() else "blocked",
            "detail": f"downstream_default={int(board.get('downstream_default_included', pd.Series(False, index=board.index)).astype(bool).sum())}",
        },
    ]
    return pd.DataFrame(rows)


def source_summary(probes: pd.DataFrame, board: pd.DataFrame) -> pd.DataFrame:
    base = probes.groupby("source_family").size().reset_index(name="probe_count")
    label_counts = (
        probes.pivot_table(index="source_family", columns="judgement_label", values="factor", aggfunc="count", fill_value=0)
        .add_prefix("label_")
        .reset_index()
    )
    if board.empty:
        return base.merge(label_counts, on="source_family", how="left")
    diagnostic_counts = (
        board.pivot_table(index="source_family", columns="diagnostic_label", values="factor", aggfunc="count", fill_value=0)
        .add_prefix("diagnostic_")
        .reset_index()
    )
    selected_counts = (
        board.groupby("source_family")
        .agg(
            frame_diagnostic_selected=("frame_diagnostic_selected", "sum"),
            portfolio_smoke_selected=("portfolio_smoke_selected", "sum"),
        )
        .reset_index()
    )
    return (
        base.merge(label_counts, on="source_family", how="left")
        .merge(diagnostic_counts, on="source_family", how="left")
        .merge(selected_counts, on="source_family", how="left")
        .fillna(0)
    )


def write_report(
    config: NewSourceProbeDiagnosticsConfig,
    probes: pd.DataFrame,
    frame_selected: pd.DataFrame,
    portfolio_selected: pd.DataFrame,
    board: pd.DataFrame,
    corr_pairs: pd.DataFrame,
    exposure: pd.DataFrame,
    portfolio_summary: dict[str, Any],
    contract: pd.DataFrame,
    corr_meta: dict[str, Any],
) -> None:
    source_counts = probes.groupby(["source_family", "judgement_label"]).size().reset_index(name="count")
    diagnostic_counts = board.groupby(["source_family", "diagnostic_label"]).size().reset_index(name="count")
    top_corr = corr_pairs.head(20) if not corr_pairs.empty else pd.DataFrame()
    top_exposure = (
        exposure.sort_values("max_abs_tradability_exposure", ascending=False).head(20)
        if not exposure.empty and "max_abs_tradability_exposure" in exposure.columns
        else exposure
    )
    lines = [
        "# New-Source Probe Diagnostics V1",
        "",
        f"- Probe input: `{portable_path(config.probe_input)}`",
        f"- Output dir: `{portable_path(config.output_dir)}`",
        "- Scope: diagnostics only; no model training, no strategy optimization, no evaluator definition changes.",
        "- New-source probes remain research queue entries, not downstream defaults.",
        "",
        "## Contract Status",
        "",
        markdown_table(contract),
        "",
        "## Source Counts",
        "",
        markdown_table(source_counts),
        "",
        "## Diagnostic Counts",
        "",
        markdown_table(diagnostic_counts),
        "",
        "## Selection",
        "",
        f"- Frame diagnostics selected: `{len(frame_selected)}`",
        f"- Portfolio smoke selected: `{len(portfolio_selected)}`",
        f"- Correlation meta: `{corr_meta}`",
        "",
        "## Portfolio Smoke Summary",
        "",
        markdown_table(pd.DataFrame([portfolio_summary])),
        "",
        "## Top Correlation Pairs",
        "",
        markdown_table(top_corr),
        "",
        "## Top Tradability Exposure",
        "",
        markdown_table(top_exposure),
        "",
        "## Output Files",
        "",
        "- `new_source_probe_inventory.csv`",
        "- `new_source_probe_diagnostic_board.csv`",
        "- `selected_probe_factor_coverage.csv`",
        "- `selected_probe_correlation_summary.csv`",
        "- `selected_probe_correlation_top_pairs.csv`",
        "- `selected_probe_tradability_exposure.csv`",
        "- `portfolio_smoke_summary.csv`",
        "- `portfolio_smoke_weights.csv`",
        "- `portfolio_smoke_liquidity_exposure.csv`",
        "- `new_source_probe_diagnostics_contract_status.csv`",
    ]
    (config.output_dir / "new_source_probe_diagnostics_report.md").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )


def write_outputs(
    config: NewSourceProbeDiagnosticsConfig,
    outputs: dict[str, Any],
) -> None:
    config.output_dir.mkdir(parents=True, exist_ok=True)
    outputs["probes"].to_csv(config.output_dir / "new_source_probe_inventory.csv", index=False, encoding="utf-8-sig")
    outputs["board"].to_csv(config.output_dir / "new_source_probe_diagnostic_board.csv", index=False, encoding="utf-8-sig")
    outputs["frame_selected"].to_csv(config.output_dir / "selected_probe_frame_factors.csv", index=False, encoding="utf-8-sig")
    outputs["portfolio_selected"].to_csv(config.output_dir / "selected_probe_portfolio_factors.csv", index=False, encoding="utf-8-sig")
    outputs["coverage"].to_csv(config.output_dir / "selected_probe_factor_coverage.csv", index=False, encoding="utf-8-sig")
    outputs["corr_summary"].to_csv(config.output_dir / "selected_probe_correlation_summary.csv", index=False, encoding="utf-8-sig")
    outputs["corr_pairs"].to_csv(config.output_dir / "selected_probe_correlation_top_pairs.csv", index=False, encoding="utf-8-sig")
    outputs["exposure"].to_csv(config.output_dir / "selected_probe_tradability_exposure.csv", index=False, encoding="utf-8-sig")
    outputs["source_summary"].to_csv(config.output_dir / "new_source_probe_source_summary.csv", index=False, encoding="utf-8-sig")
    outputs["contract"].to_csv(config.output_dir / "new_source_probe_diagnostics_contract_status.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame([outputs["corr_meta"]]).to_csv(config.output_dir / "selected_probe_correlation_meta.csv", index=False, encoding="utf-8-sig")

    portfolio = outputs["portfolio"]
    pd.DataFrame([portfolio["summary"]]).to_csv(config.output_dir / "portfolio_smoke_summary.csv", index=False, encoding="utf-8-sig")
    portfolio["weights"].to_csv(config.output_dir / "portfolio_smoke_weights.csv", index=False, encoding="utf-8-sig")
    portfolio["component_summary"].to_csv(config.output_dir / "portfolio_smoke_component_summary.csv", index=False, encoding="utf-8-sig")
    portfolio["liquidity_exposure"].to_csv(config.output_dir / "portfolio_smoke_liquidity_exposure.csv", index=False, encoding="utf-8-sig")
    portfolio["daily"].head(200).to_csv(config.output_dir / "portfolio_smoke_daily_sample.csv", index=False, encoding="utf-8-sig")
    portfolio["rebalances"].head(200).to_csv(config.output_dir / "portfolio_smoke_rebalance_sample.csv", index=False, encoding="utf-8-sig")

    write_report(
        config,
        outputs["probes"],
        outputs["frame_selected"],
        outputs["portfolio_selected"],
        outputs["board"],
        outputs["corr_pairs"],
        outputs["exposure"],
        portfolio["summary"],
        outputs["contract"],
        outputs["corr_meta"],
    )


def run_new_source_probe_diagnostics(config: NewSourceProbeDiagnosticsConfig) -> dict[str, Any]:
    config.output_dir.mkdir(parents=True, exist_ok=True)
    probes = load_probe_inventory(config)
    frame_selected = select_probe_subset(probes, config.selection, "max_frame_factors")
    portfolio_selected = select_probe_subset(probes, config.selection, "max_portfolio_factors")
    factor_frame, coverage = load_factor_frames(config, frame_selected)
    selected_factors = frame_selected["factor"].astype(str).tolist()
    corr_summary, corr_pairs, corr_meta = daily_cross_section_spearman_frame(
        factor_frame,
        selected_factors,
        max_dates=config.correlation_max_dates,
        min_instruments=config.min_instruments,
        top_pairs=config.top_pairs,
    )
    exposure = tradability_exposure(factor_frame, selected_factors, config)
    portfolio = run_portfolio_smoke(factor_frame, portfolio_selected, config)
    board = build_diagnostic_board(
        probes,
        frame_selected,
        portfolio_selected,
        coverage,
        corr_summary,
        exposure,
        config.rules,
    )
    contract = build_contract_status(
        probes,
        frame_selected,
        portfolio_selected,
        corr_pairs,
        portfolio["summary"],
        board,
        config.rules,
    )
    outputs = {
        "probes": probes,
        "frame_selected": frame_selected,
        "portfolio_selected": portfolio_selected,
        "factor_frame": factor_frame,
        "coverage": coverage,
        "corr_summary": corr_summary,
        "corr_pairs": corr_pairs,
        "corr_meta": corr_meta,
        "exposure": exposure,
        "portfolio": portfolio,
        "board": board,
        "source_summary": source_summary(probes, board),
        "contract": contract,
    }
    write_outputs(config, outputs)
    return outputs
