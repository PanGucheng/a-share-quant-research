from __future__ import annotations

import json
import math
import shutil
from pathlib import Path
from typing import Any, Mapping

import numpy as np
import pandas as pd
import yaml

from research_validation.feature_matrix import canonical_hash, file_sha256
from research_validation.lineage import (
    capture_code_state,
    load_artifact_manifest,
    validate_manifest_outputs,
    write_stage_artifact_manifest,
)

from .contracts import validate_market_frame, validate_signal_frame
from .runner import run_qlib_execution
from .strategy_adapter import rebalance_execution_dates


PROJECT_ROOT = Path(__file__).resolve().parents[1]
STAGE_ID = "historical_portfolio_backtest_v1"
SPLITS = ("split_001", "split_002", "split_003")
DEVELOPMENT_SPLITS = ("split_001", "split_002")
HOLDOUT_SPLIT = "split_003"
PREDICTION_COLUMNS = (
    "outer_split_id",
    "datetime",
    "instrument",
    "method",
    "prediction",
    "prediction_artifact_id",
    "allowlist_sha256",
    "feature_order_sha256",
    "model_freeze_id",
    "experiment_class",
)
RUNTIME_TABLES = (
    "orders",
    "fills",
    "rejected_orders",
    "partial_fills",
    "transaction_costs",
    "daily_accounting",
    "positions",
    "execution_summary",
)
COMPACT_FILES = (
    "resolved_config.json",
    "prediction_input_receipts.csv",
    "development_results.csv",
    "selected_portfolio_rule.json",
    "holdout_result.csv",
    "performance_summary.csv",
    "execution_summary.csv",
    "cost_summary.csv",
    "stale_valuation_summary.csv",
    "daily_nav.csv",
    "daily_returns.csv",
    "monthly_returns.csv",
    "contract_status.csv",
    "report.md",
    "cumulative_return.png",
    "drawdown.png",
    "turnover.png",
)


def resolve(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else (PROJECT_ROOT / path).resolve()


def _atomic_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, default=str)
        + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _atomic_csv(path: Path, frame: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    frame.to_csv(temporary, index=False, encoding="utf-8-sig", lineterminator="\n")
    temporary.replace(path)


def load_backtest_config(path: str | Path) -> dict[str, Any]:
    config = yaml.safe_load(resolve(path).read_text(encoding="utf-8"))
    if config.get("stage_id") != STAGE_ID:
        raise ValueError("historical portfolio backtest stage is not frozen")
    if tuple(config.get("development_splits", ())) != DEVELOPMENT_SPLITS:
        raise ValueError("development splits must be split_001 and split_002")
    if config.get("holdout_split") != HOLDOUT_SPLIT:
        raise ValueError("holdout split must be split_003")
    expected = [
        ("P01", 50, 5),
        ("P02", 100, 5),
        ("P03", 200, 5),
        ("P04", 50, 20),
        ("P05", 100, 20),
        ("P06", 200, 20),
    ]
    observed = [
        (str(row["portfolio_id"]), int(row["top_k"]), int(row["rebalance_interval"]))
        for row in config.get("portfolio_candidates", ())
    ]
    if observed != expected:
        raise ValueError("portfolio candidate table differs from the frozen six rules")
    frozen_values = {
        "benchmark": "SH000985",
        "initial_cash": 10_000_000.0,
        "risk_degree": 0.95,
        "lot_size": 100,
        "buy_commission_rate": 0.0003,
        "sell_commission_rate": 0.0003,
        "sell_tax_rate": 0.001,
        "minimum_commission": 5.0,
        "slippage_bps": 10.0,
        "max_participation_rate": 0.05,
        "signal_lag_trading_days": 1,
        "strict_t_plus_one": True,
        "research_valuation_fallback": "carry_last_valid_close",
    }
    for field, expected_value in frozen_values.items():
        if config.get(field) != expected_value:
            raise ValueError(f"frozen backtest field differs: {field}")
    governance = config["governance"]
    if any(
        bool(governance[field])
        for field in (
            "retrain_model",
            "regenerate_predictions",
            "change_features",
            "unbiased_final_estimate",
            "authoritative_historical_execution_ready",
            "production_model_selected",
            "live_trading_ready",
        )
    ):
        raise ValueError("historical backtest governance overclaims authority")
    return config


def _validated_manifest(path: Path, role: str) -> dict[str, Any]:
    manifest = load_artifact_manifest(path)
    if manifest.get("artifact_status") != "pass":
        raise ValueError(f"{role} manifest is not passing")
    issues = validate_manifest_outputs(manifest, path.parent)
    if issues:
        raise ValueError(f"{role} manifest output hashes are invalid: {issues}")
    return manifest


def audit_prediction_inputs(
    config: Mapping[str, Any],
) -> tuple[pd.DataFrame, dict[str, pd.DataFrame], dict[str, Any]]:
    manifest_path = resolve(config["prediction_manifest"])
    manifest = _validated_manifest(manifest_path, "LightGBM prediction")
    receipt_path = resolve(config["prediction_receipt"])
    receipt = pd.read_csv(receipt_path)
    if len(receipt) != 3 or set(receipt["outer_split_id"].astype(str)) != set(SPLITS):
        raise ValueError("prediction receipt must contain exactly three frozen splits")
    assignments = pd.read_csv(resolve(config["date_assignments"]))
    split_column = "split_id" if "split_id" in assignments else "outer_split_id"
    predictions: dict[str, pd.DataFrame] = {}
    audit_rows: list[dict[str, Any]] = []
    for split_id in SPLITS:
        row = receipt.loc[receipt["outer_split_id"].astype(str).eq(split_id)]
        if len(row) != 1 or str(row.iloc[0]["method"]) != "lightgbm":
            raise ValueError(f"prediction receipt method mismatch: {split_id}")
        path = Path(str(row.iloc[0]["runtime_path"]))
        if not path.is_file():
            raise FileNotFoundError(
                f"frozen prediction runtime is missing; do not regenerate: {path}"
            )
        actual_sha = file_sha256(path)
        if actual_sha != str(row.iloc[0]["prediction_sha256"]):
            raise ValueError(
                f"frozen prediction hash mismatch; do not regenerate: {split_id}"
            )
        frame = pd.read_parquet(path)
        if tuple(frame.columns) != PREDICTION_COLUMNS:
            raise ValueError(f"prediction schema/order mismatch: {split_id}")
        frame["datetime"] = pd.to_datetime(frame["datetime"], errors="raise").dt.normalize()
        frame["instrument"] = frame["instrument"].astype(str).str.upper()
        frame["prediction"] = pd.to_numeric(frame["prediction"], errors="coerce")
        if not frame["outer_split_id"].astype(str).eq(split_id).all():
            raise ValueError(f"prediction split payload mismatch: {split_id}")
        if not frame["method"].astype(str).eq("lightgbm").all():
            raise ValueError(f"prediction method payload mismatch: {split_id}")
        if frame.duplicated(["datetime", "instrument"]).any():
            raise ValueError(f"prediction has duplicate date/instrument keys: {split_id}")
        if not np.isfinite(frame["prediction"]).all():
            raise ValueError(f"prediction contains non-finite scores: {split_id}")
        if len(frame) != int(row.iloc[0]["prediction_row_count"]):
            raise ValueError(f"prediction row count mismatch: {split_id}")
        coverage = float(row.iloc[0]["prediction_coverage"])
        if coverage < 0.95:
            raise ValueError(f"prediction coverage is below 0.95: {split_id}")
        expected_dates = pd.DatetimeIndex(
            pd.to_datetime(
                assignments.loc[
                    assignments[split_column].astype(str).eq(split_id)
                    & assignments["fold"].astype(str).eq("test"),
                    "datetime",
                ],
                errors="raise",
            )
        ).normalize()
        actual_dates = pd.DatetimeIndex(sorted(frame["datetime"].unique()))
        if not actual_dates.equals(expected_dates):
            raise ValueError(f"prediction dates escape exact test fold: {split_id}")
        predictions[split_id] = frame
        audit_rows.append(
            {
                "outer_split_id": split_id,
                "method": "lightgbm",
                "prediction_artifact_id": str(row.iloc[0]["prediction_artifact_id"]),
                "runtime_path": path.as_posix(),
                "prediction_sha256": actual_sha,
                "prediction_row_count": len(frame),
                "date_count": len(actual_dates),
                "date_min": actual_dates.min().date().isoformat(),
                "date_max": actual_dates.max().date().isoformat(),
                "prediction_coverage": coverage,
                "schema_valid": True,
                "exact_test_dates": True,
                "duplicate_key_count": 0,
                "predictions_regenerated": False,
            }
        )
    return pd.DataFrame(audit_rows), predictions, manifest


def load_market_inputs(
    config: Mapping[str, Any],
) -> tuple[dict[str, pd.DataFrame], dict[str, dict[str, Any]], dict[str, Any]]:
    manifest_path = resolve(config["market_cache_manifest"])
    manifest = _validated_manifest(manifest_path, "Market Cache V3")
    receipts = pd.read_csv(resolve(config["market_cache_artifacts"]))
    markets: dict[str, pd.DataFrame] = {}
    audit: dict[str, dict[str, Any]] = {}
    for split_id in SPLITS:
        row = receipts.loc[receipts["outer_split_id"].astype(str).eq(split_id)]
        if len(row) != 1:
            raise ValueError(f"market cache receipt mismatch: {split_id}")
        path = Path(str(row.iloc[0]["path"]))
        if not path.is_file() or file_sha256(path) != str(row.iloc[0]["sha256"]):
            raise ValueError(f"Market Cache V3 runtime hash mismatch: {split_id}")
        market = pd.read_parquet(path)
        market = apply_research_valuation_fallback(
            market,
            policy=str(config["research_valuation_fallback"]),
        )
        markets[split_id] = validate_market_frame(market)
        fallback = market["research_valuation_fallback_applied"].astype(bool)
        audit[split_id] = {
            "market_runtime_path": path.as_posix(),
            "market_sha256": str(row.iloc[0]["sha256"]),
            "fallback_row_count": int(fallback.sum()),
            "stale_valuation_date_count": int(market.loc[fallback, "datetime"].nunique()),
            "stale_valuation_instrument_count": int(market.loc[fallback, "instrument"].nunique()),
            "maximum_stale_days": int(
                pd.to_numeric(
                    market.loc[fallback, "valuation_price_age_trading_days"],
                    errors="coerce",
                ).max()
            )
            if fallback.any()
            else 0,
            "affected_instruments": ";".join(
                sorted(market.loc[fallback, "instrument"].astype(str).unique())
            ),
            "unknown_tradability_count": int(
                (~market["market_semantics_authoritative"].fillna(False).astype(bool)).sum()
            ),
        }
    return markets, audit, manifest


def apply_research_valuation_fallback(
    market: pd.DataFrame, *, policy: str
) -> pd.DataFrame:
    if policy != "carry_last_valid_close":
        raise ValueError("only carry_last_valid_close is allowed for research fallback")
    result = market.sort_values(["instrument", "datetime"], kind="stable").copy()
    stale = result["valuation_stale_blocked"].fillna(False).astype(bool)
    historical_close = pd.to_numeric(result["close"], errors="coerce")
    carried = historical_close.groupby(result["instrument"], sort=False).ffill()
    applied = stale & historical_close.isna() & carried.notna()
    result.loc[applied, "close"] = carried.loc[applied]
    result["research_valuation_fallback_applied"] = applied
    return result.sort_values(["datetime", "instrument"], kind="stable").reset_index(drop=True)


def summarize_market_scope(
    market: pd.DataFrame, base_audit: Mapping[str, Any]
) -> dict[str, Any]:
    """Summarize only the dates actually consumed by one execution scenario."""
    fallback = market["research_valuation_fallback_applied"].fillna(False).astype(bool)
    scoped = dict(base_audit)
    scoped.update(
        {
            "fallback_row_count": int(fallback.sum()),
            "stale_valuation_date_count": int(
                market.loc[fallback, "datetime"].nunique()
            ),
            "stale_valuation_instrument_count": int(
                market.loc[fallback, "instrument"].nunique()
            ),
            "maximum_stale_days": int(
                pd.to_numeric(
                    market.loc[fallback, "valuation_price_age_trading_days"],
                    errors="coerce",
                ).max()
            )
            if fallback.any()
            else 0,
            "affected_instruments": ";".join(
                sorted(market.loc[fallback, "instrument"].astype(str).unique())
            ),
            "unknown_tradability_count": int(
                (~market["market_semantics_authoritative"].fillna(False).astype(bool)).sum()
            ),
        }
    )
    return scoped


def adapt_prediction_signal(
    prediction: pd.DataFrame,
    *,
    split_id: str,
    prediction_artifact_id: str,
    config: Mapping[str, Any],
) -> pd.DataFrame:
    signal = prediction[["datetime", "instrument", "prediction"]].rename(
        columns={"prediction": "score"}
    )
    signal["method"] = "lightgbm"
    signal["signal_artifact_id"] = prediction_artifact_id
    signal["profile_name"] = str(config["profile_name"])
    signal["profile_type"] = str(config["profile_type"])
    signal["research_run_family_id"] = str(config["research_run_family_id"])
    validated = validate_signal_frame(signal)
    if validated["datetime"].nunique() != prediction["datetime"].nunique():
        raise ValueError(f"signal date loss during adaptation: {split_id}")
    return validated


def load_benchmark_returns(
    benchmark: str,
    calendars: Mapping[str, pd.DatetimeIndex],
) -> dict[str, pd.DataFrame]:
    from qlib.data import D

    start = min(values.min() for values in calendars.values()) - pd.Timedelta(days=14)
    end = max(values.max() for values in calendars.values())
    features = D.features(
        [benchmark], ["$close"], start_time=start, end_time=end, freq="day"
    ).reset_index()
    features["datetime"] = pd.to_datetime(features["datetime"]).dt.normalize()
    features["close"] = pd.to_numeric(features["$close"], errors="coerce")
    if features.empty or not features["close"].notna().any():
        raise ValueError(f"required benchmark is unavailable in provider: {benchmark}")
    output: dict[str, pd.DataFrame] = {}
    for split_id, calendar in calendars.items():
        history = features.loc[features["datetime"].le(calendar.max())].copy()
        series = history.set_index("datetime")["close"].sort_index()
        union = series.index.union(calendar).sort_values()
        expanded = series.reindex(union).ffill()
        returns = expanded.pct_change(fill_method=None).reindex(calendar)
        series = expanded.reindex(calendar)
        output[split_id] = pd.DataFrame(
            {"datetime": calendar, "benchmark_close": series.to_numpy(), "benchmark_return": returns.to_numpy()}
        )
    return output


def _annualized_return(total_return: float, trading_days: int) -> float:
    if trading_days <= 0 or total_return <= -1:
        return float("nan")
    return float((1.0 + total_return) ** (252.0 / trading_days) - 1.0)


def _ratio(values: pd.Series) -> float:
    clean = pd.to_numeric(values, errors="coerce").dropna()
    if len(clean) < 2 or float(clean.std(ddof=1)) <= 0:
        return float("nan")
    return float(clean.mean() / clean.std(ddof=1) * math.sqrt(252.0))


def calculate_scenario_metrics(
    *,
    result: Mapping[str, pd.DataFrame],
    benchmark: pd.DataFrame,
    market: pd.DataFrame,
    market_audit: Mapping[str, Any],
    receipt_row: Mapping[str, Any],
    portfolio: Mapping[str, Any],
    split_id: str,
    initial_cash: float,
) -> tuple[dict[str, Any], pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    daily = result["daily_accounting"].copy()
    daily["datetime"] = pd.to_datetime(daily["datetime"]).dt.normalize()
    daily = daily.merge(benchmark, on="datetime", how="left", validate="one_to_one")
    daily["portfolio_id"] = str(portfolio["portfolio_id"])
    daily["outer_split_id"] = split_id
    costs = result["transaction_costs"].copy()
    if costs.empty:
        daily_cost = pd.DataFrame({"datetime": daily["datetime"], "implementation_cost": 0.0})
    else:
        costs["datetime"] = pd.to_datetime(costs["datetime"]).dt.normalize()
        daily_cost = costs.groupby("datetime", as_index=False)["implementation_cost"].sum()
    daily = daily.merge(daily_cost, on="datetime", how="left")
    daily["implementation_cost"] = daily["implementation_cost"].fillna(0.0)
    daily["cumulative_cost"] = daily["implementation_cost"].cumsum()
    daily["net_cumulative"] = daily["nav"] / float(initial_cash)
    daily["gross_cumulative_approx"] = (
        daily["nav"] + daily["cumulative_cost"]
    ) / float(initial_cash)
    benchmark_growth = (1.0 + daily["benchmark_return"].fillna(0.0)).cumprod()
    benchmark_growth.loc[daily["benchmark_return"].notna().cumsum().eq(0)] = np.nan
    daily["benchmark_cumulative"] = benchmark_growth
    daily["excess_return"] = daily["return"] - daily["benchmark_return"]
    running_peak = daily["net_cumulative"].cummax().clip(lower=1.0)
    daily["drawdown"] = daily["net_cumulative"] / running_peak - 1.0

    trading_days = len(daily)
    ending_nav = float(daily["nav"].iloc[-1])
    total_return = ending_nav / float(initial_cash) - 1.0
    annualized_return = _annualized_return(total_return, trading_days)
    volatility = float(daily["return"].std(ddof=1) * math.sqrt(252.0))
    max_drawdown = float(daily["drawdown"].min())
    valid_benchmark = daily[["return", "benchmark_return"]].notna().all(axis=1)
    common = daily.loc[valid_benchmark]
    benchmark_total = float((1.0 + common["benchmark_return"]).prod() - 1.0) if len(common) else float("nan")
    portfolio_common_total = float((1.0 + common["return"]).prod() - 1.0) if len(common) else float("nan")
    benchmark_annual = _annualized_return(benchmark_total, len(common))
    portfolio_common_annual = _annualized_return(portfolio_common_total, len(common))
    annualized_excess = portfolio_common_annual - benchmark_annual

    orders = result["orders"]
    fills = result["fills"]
    positions = result["positions"]
    requested = float(pd.to_numeric(orders.get("requested_shares"), errors="coerce").fillna(0).sum()) if not orders.empty else 0.0
    executed = float(pd.to_numeric(orders.get("executed_shares"), errors="coerce").fillna(0).sum()) if not orders.empty else 0.0
    holding_count = positions.groupby("datetime")["instrument"].nunique() if not positions.empty else pd.Series(dtype=float)
    fallback_market = market["research_valuation_fallback_applied"].fillna(False).astype(bool)
    held_fallback = (
        positions[["datetime", "instrument"]]
        .drop_duplicates()
        .merge(
            market.loc[fallback_market, ["datetime", "instrument"]].drop_duplicates(),
            on=["datetime", "instrument"],
            how="inner",
        )
        if not positions.empty
        else pd.DataFrame(columns=["datetime", "instrument"])
    )
    commission = float(costs["commission"].sum()) if not costs.empty else 0.0
    stamp_tax = float(costs["stamp_tax"].sum()) if not costs.empty else 0.0
    slippage = float(costs["slippage_cost"].sum()) if not costs.empty else 0.0
    total_cost = float(costs["implementation_cost"].sum()) if not costs.empty else 0.0
    summary = {
        "portfolio_id": str(portfolio["portfolio_id"]),
        "outer_split_id": split_id,
        "top_k": int(portfolio["top_k"]),
        "rebalance_interval": int(portfolio["rebalance_interval"]),
        "start_date": daily["datetime"].min().date().isoformat(),
        "end_date": daily["datetime"].max().date().isoformat(),
        "trading_days": trading_days,
        "initial_nav": float(initial_cash),
        "ending_nav": ending_nav,
        "total_return": total_return,
        "gross_return_approx": total_return + total_cost / float(initial_cash),
        "annualized_return": annualized_return,
        "benchmark_total_return": benchmark_total,
        "benchmark_annualized_return": benchmark_annual,
        "common_period_portfolio_total_return": portfolio_common_total,
        "annualized_excess_return": annualized_excess,
        "annualized_volatility": volatility,
        "sharpe_ratio": _ratio(daily["return"]),
        "information_ratio": _ratio(daily["excess_return"]),
        "max_drawdown": max_drawdown,
        "calmar_ratio": annualized_return / abs(max_drawdown) if max_drawdown < 0 else float("nan"),
        "positive_day_ratio": float(daily["return"].gt(0).mean()),
        "average_daily_turnover": float(daily["turnover"].mean()),
        "annualized_turnover": float(daily["turnover"].mean() * 252.0),
        "order_count": len(orders),
        "fill_count": len(fills),
        "partial_fill_count": len(result["partial_fills"]),
        "rejected_order_count": len(result["rejected_orders"]),
        "fill_rate": executed / requested if requested > 0 else float("nan"),
        "average_holding_count": float(holding_count.mean()) if len(holding_count) else 0.0,
        "maximum_single_position_weight": float(positions["weight"].max()) if not positions.empty else 0.0,
        "commission": commission,
        "stamp_tax": stamp_tax,
        "slippage_cost": slippage,
        "total_transaction_cost": total_cost,
        "cost_drag": total_cost / float(initial_cash),
        "prediction_coverage": float(receipt_row["prediction_coverage"]),
        "benchmark_coverage": float(valid_benchmark.mean()),
        "benchmark_common_date_count": int(valid_benchmark.sum()),
        "stale_valuation_date_count": int(market_audit["stale_valuation_date_count"]),
        "stale_valuation_instrument_count": int(market_audit["stale_valuation_instrument_count"]),
        "held_stale_valuation_date_count": int(held_fallback["datetime"].nunique()),
        "unknown_tradability_count": int(market_audit["unknown_tradability_count"]),
        "historical_execution_approximate": True,
        "tradability_source_complete": False,
        "authoritative_historical_execution_ready": False,
        "unbiased_final_estimate": False,
        "production_model_selected": False,
        "live_trading_ready": False,
    }
    monthly = daily.assign(month=daily["datetime"].dt.to_period("M").astype(str)).groupby(
        ["portfolio_id", "outer_split_id", "month"], as_index=False
    ).agg(
        net_return=("return", lambda values: float((1.0 + values).prod() - 1.0)),
        benchmark_return=("benchmark_return", lambda values: float((1.0 + values.dropna()).prod() - 1.0) if values.notna().any() else float("nan")),
        turnover=("turnover", "sum"),
        transaction_cost=("implementation_cost", "sum"),
    )
    detail_row = {key: summary[key] for key in (
        "portfolio_id", "outer_split_id", "top_k", "rebalance_interval", "order_count", "fill_count",
        "partial_fill_count", "rejected_order_count", "fill_rate", "average_holding_count",
        "maximum_single_position_weight", "average_daily_turnover", "annualized_turnover",
    )}
    detail_row.update({key: summary[key] for key in (
        "portfolio_id", "outer_split_id", "stale_valuation_date_count",
        "stale_valuation_instrument_count", "held_stale_valuation_date_count",
        "unknown_tradability_count",
    )})
    detail_row["maximum_stale_days"] = int(market_audit["maximum_stale_days"])
    detail_row["affected_instruments"] = str(market_audit["affected_instruments"])
    return summary, daily, monthly, pd.DataFrame([detail_row])


def select_portfolio_rule(development: pd.DataFrame) -> dict[str, Any]:
    expected = {(portfolio, split) for portfolio in [f"P{i:02d}" for i in range(1, 7)] for split in DEVELOPMENT_SPLITS}
    observed = set(zip(development["portfolio_id"], development["outer_split_id"]))
    if observed != expected:
        raise ValueError("development selection requires exactly 6 x 2 results")
    ranked = development.groupby(["portfolio_id", "top_k", "rebalance_interval"], as_index=False).agg(
        development_mean_net_excess_information_ratio=("information_ratio", "mean"),
        development_mean_net_annualized_excess_return=("annualized_excess_return", "mean"),
        development_mean_turnover=("average_daily_turnover", "mean"),
    )
    ranked = ranked.sort_values(
        [
            "development_mean_net_excess_information_ratio",
            "development_mean_net_annualized_excess_return",
            "development_mean_turnover",
            "top_k",
            "portfolio_id",
        ],
        ascending=[False, False, True, True, True],
        na_position="last",
        kind="stable",
    ).reset_index(drop=True)
    winner = ranked.iloc[0].to_dict()
    return {
        "schema_version": 1,
        "selection_status": "frozen_before_holdout",
        "selected_portfolio_id": str(winner["portfolio_id"]),
        "top_k": int(winner["top_k"]),
        "rebalance_interval": int(winner["rebalance_interval"]),
        "development_splits": list(DEVELOPMENT_SPLITS),
        "holdout_split": HOLDOUT_SPLIT,
        "holdout_execution_count_at_selection": 0,
        "holdout_performance_read_count_at_selection": 0,
        "selection_metrics": {
            key: float(winner[key])
            for key in (
                "development_mean_net_excess_information_ratio",
                "development_mean_net_annualized_excess_return",
                "development_mean_turnover",
            )
        },
        "candidate_ranking": ranked.to_dict(orient="records"),
        "portfolio_rule_selected": True,
        "production_model_selected": False,
        "live_trading_ready": False,
    }


def _scenario_runtime_path(output_dir: Path, portfolio_id: str, split_id: str) -> Path:
    name = f"{portfolio_id}_{split_id}" if split_id != HOLDOUT_SPLIT else "selected_split_003"
    return output_dir / "runtime" / name


def _write_runtime(path: Path, result: Mapping[str, pd.DataFrame]) -> None:
    if path.exists():
        raise FileExistsError(f"scenario runtime already exists: {path}")
    path.mkdir(parents=True, exist_ok=False)
    for name in RUNTIME_TABLES:
        result[name].to_parquet(path / f"{name}.parquet", index=False)


def run_scenario(
    *,
    config: Mapping[str, Any],
    portfolio: Mapping[str, Any],
    split_id: str,
    prediction: pd.DataFrame,
    receipt_row: Mapping[str, Any],
    market: pd.DataFrame,
    market_audit: Mapping[str, Any],
    benchmark: pd.DataFrame,
    output_dir: Path,
    smoke_trading_days: int | None = None,
) -> tuple[dict[str, Any], pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    calendar = pd.DatetimeIndex(sorted(market["datetime"].unique()))
    if smoke_trading_days is not None:
        calendar = calendar[: int(smoke_trading_days) + 1]
    market_run = market.loc[market["datetime"].isin(calendar)].copy()
    scenario_market_audit = summarize_market_scope(market_run, market_audit)
    signal_dates = calendar[:-1]
    prediction_run = prediction.loc[prediction["datetime"].isin(signal_dates)].copy()
    signal = adapt_prediction_signal(
        prediction_run,
        split_id=split_id,
        prediction_artifact_id=str(receipt_row["prediction_artifact_id"]),
        config=config,
    )
    execution_dates = calendar[1:]
    expected_rebalances = rebalance_execution_dates(
        execution_dates, int(portfolio["rebalance_interval"])
    )
    run_config = {
        "initial_cash": float(config["initial_cash"]),
        "top_k": int(portfolio["top_k"]),
        "rebalance_interval": int(portfolio["rebalance_interval"]),
        "risk_degree": float(config["risk_degree"]),
        "lot_size": int(config["lot_size"]),
        "dynamic_lot_rules": bool(config["dynamic_lot_rules"]),
        "buy_commission_rate": float(config["buy_commission_rate"]),
        "sell_commission_rate": float(config["sell_commission_rate"]),
        "sell_tax_rate": float(config["sell_tax_rate"]),
        "minimum_commission": float(config["minimum_commission"]),
        "slippage_bps": float(config["slippage_bps"]),
        "max_participation_rate": float(config["max_participation_rate"]),
        "signal_lag_trading_days": 1,
        "strict_t_plus_one": True,
    }
    result = run_qlib_execution(signal, market_run, run_config)
    runtime = _scenario_runtime_path(output_dir, str(portfolio["portfolio_id"]), split_id)
    if smoke_trading_days is not None:
        runtime = output_dir / f"{portfolio['portfolio_id']}_{split_id}"
    _write_runtime(runtime, result)
    summary, daily, monthly, detail = calculate_scenario_metrics(
        result=result,
        benchmark=benchmark.loc[benchmark["datetime"].isin(execution_dates)].copy(),
        market=market_run,
        market_audit=scenario_market_audit,
        receipt_row=receipt_row,
        portfolio=portfolio,
        split_id=split_id,
        initial_cash=float(config["initial_cash"]),
    )
    summary["expected_rebalance_count"] = len(expected_rebalances)
    summary["signal_lag_trading_days"] = 1
    return summary, daily, monthly, detail


def initialize_qlib(config: Mapping[str, Any]) -> None:
    environment = _validated_manifest(resolve(config["environment_manifest"]), "Qlib environment")
    if environment.get("artifact_status") != "pass":
        raise ValueError("Qlib environment is not passing")
    import qlib
    from qlib.config import C, REG_CN

    qlib.init(provider_uri=str(resolve(config["qlib_provider"])), region=REG_CN)
    C.kernels = 1
    C.joblib_backend = "sequential"
    C.trade_unit = 1


def _prepare_inputs(config: Mapping[str, Any]) -> dict[str, Any]:
    receipt, predictions, prediction_manifest = audit_prediction_inputs(config)
    markets, market_audits, market_manifest = load_market_inputs(config)
    calendars = {
        split_id: pd.DatetimeIndex(sorted(markets[split_id]["datetime"].unique()))
        for split_id in SPLITS
    }
    benchmark = load_benchmark_returns(str(config["benchmark"]), calendars)
    return {
        "receipt": receipt,
        "predictions": predictions,
        "prediction_manifest": prediction_manifest,
        "markets": markets,
        "market_audits": market_audits,
        "market_manifest": market_manifest,
        "benchmark": benchmark,
    }


def run_smoke(config: Mapping[str, Any]) -> dict[str, Any]:
    initialize_qlib(config)
    inputs = _prepare_inputs(config)
    smoke = config["smoke"]
    output_dir = resolve(smoke["output_dir"])
    if output_dir.exists():
        shutil.rmtree(output_dir)
    portfolio = next(
        row for row in config["portfolio_candidates"] if row["portfolio_id"] == smoke["portfolio_id"]
    )
    split_id = str(smoke["split_id"])
    receipt_row = inputs["receipt"].loc[
        inputs["receipt"]["outer_split_id"].eq(split_id)
    ].iloc[0]
    summary, _, _, _ = run_scenario(
        config=config,
        portfolio=portfolio,
        split_id=split_id,
        prediction=inputs["predictions"][split_id],
        receipt_row=receipt_row,
        market=inputs["markets"][split_id],
        market_audit=inputs["market_audits"][split_id],
        benchmark=inputs["benchmark"][split_id],
        output_dir=output_dir,
        smoke_trading_days=int(smoke["trading_days"]),
    )
    _atomic_json(output_dir / "smoke_summary.json", summary)
    return summary


def _write_development_outputs(
    output_dir: Path,
    config: Mapping[str, Any],
    input_receipts: pd.DataFrame,
    summaries: list[dict[str, Any]],
    daily_frames: list[pd.DataFrame],
    monthly_frames: list[pd.DataFrame],
    details: list[pd.DataFrame],
) -> dict[str, Any]:
    development = pd.DataFrame(summaries).sort_values(
        ["portfolio_id", "outer_split_id"], kind="stable"
    )
    _atomic_csv(output_dir / "development_results.csv", development)
    selection = select_portfolio_rule(development)
    selection["development_results_sha256"] = file_sha256(
        output_dir / "development_results.csv"
    )
    selection["config_sha256"] = canonical_hash(config)
    _atomic_json(output_dir / "selected_portfolio_rule.json", selection)
    _atomic_json(output_dir / "resolved_config.json", config)
    _atomic_csv(output_dir / "prediction_input_receipts.csv", input_receipts)
    _atomic_csv(output_dir / "performance_summary.csv", development)
    _atomic_csv(output_dir / "execution_summary.csv", pd.concat(details, ignore_index=True).loc[:, ~pd.concat(details, ignore_index=True).columns.duplicated()])
    cost_columns = ["portfolio_id", "outer_split_id", "commission", "stamp_tax", "slippage_cost", "total_transaction_cost", "cost_drag", "gross_return_approx", "total_return"]
    _atomic_csv(output_dir / "cost_summary.csv", development[cost_columns])
    stale_columns = ["portfolio_id", "outer_split_id", "stale_valuation_date_count", "stale_valuation_instrument_count", "held_stale_valuation_date_count", "unknown_tradability_count"]
    stale = development[stale_columns].merge(
        pd.concat(details, ignore_index=True)[["portfolio_id", "outer_split_id", "maximum_stale_days", "affected_instruments"]].drop_duplicates(),
        on=["portfolio_id", "outer_split_id"], how="left", validate="one_to_one",
    )
    _atomic_csv(output_dir / "stale_valuation_summary.csv", stale)
    _atomic_csv(output_dir / "daily_nav.csv", pd.concat(daily_frames, ignore_index=True))
    daily_returns = pd.concat(daily_frames, ignore_index=True)[
        ["datetime", "portfolio_id", "outer_split_id", "return", "benchmark_return", "excess_return", "turnover", "implementation_cost", "drawdown"]
    ]
    _atomic_csv(output_dir / "daily_returns.csv", daily_returns)
    _atomic_csv(output_dir / "monthly_returns.csv", pd.concat(monthly_frames, ignore_index=True))
    return selection


def run_development(config: Mapping[str, Any]) -> dict[str, Any]:
    code_state = capture_code_state(PROJECT_ROOT)
    if code_state.dirty:
        raise ValueError("development run requires clean committed implementation")
    initialize_qlib(config)
    inputs = _prepare_inputs(config)
    output_dir = resolve(config["output_dir"])
    if (output_dir / "selected_portfolio_rule.json").exists():
        raise FileExistsError("development selection already exists")
    summaries: list[dict[str, Any]] = []
    daily_frames: list[pd.DataFrame] = []
    monthly_frames: list[pd.DataFrame] = []
    details: list[pd.DataFrame] = []
    for portfolio in config["portfolio_candidates"]:
        for split_id in DEVELOPMENT_SPLITS:
            receipt_row = inputs["receipt"].loc[
                inputs["receipt"]["outer_split_id"].eq(split_id)
            ].iloc[0]
            summary, daily, monthly, detail = run_scenario(
                config=config,
                portfolio=portfolio,
                split_id=split_id,
                prediction=inputs["predictions"][split_id],
                receipt_row=receipt_row,
                market=inputs["markets"][split_id],
                market_audit=inputs["market_audits"][split_id],
                benchmark=inputs["benchmark"][split_id],
                output_dir=output_dir,
            )
            summaries.append(summary)
            daily_frames.append(daily)
            monthly_frames.append(monthly)
            details.append(detail)
    return _write_development_outputs(
        output_dir,
        config,
        inputs["receipt"],
        summaries,
        daily_frames,
        monthly_frames,
        details,
    )


def _write_plots(output_dir: Path, performance: pd.DataFrame, daily: pd.DataFrame) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    selected = json.loads((output_dir / "selected_portfolio_rule.json").read_text(encoding="utf-8"))["selected_portfolio_id"]
    plot_data = daily.loc[daily["portfolio_id"].eq(selected)].copy()
    for column, title, filename in (
        ("net_cumulative", "Selected Rule: Net Cumulative NAV", "cumulative_return.png"),
        ("drawdown", "Selected Rule: Drawdown", "drawdown.png"),
        ("turnover", "Selected Rule: Daily Turnover", "turnover.png"),
    ):
        fig, axis = plt.subplots(figsize=(10, 5))
        for split_id, group in plot_data.groupby("outer_split_id", sort=True):
            axis.plot(pd.to_datetime(group["datetime"]), group[column], label=split_id)
        axis.set_title(title)
        axis.grid(alpha=0.25)
        axis.legend()
        fig.tight_layout()
        fig.savefig(output_dir / filename, dpi=140)
        plt.close(fig)


def _write_report(output_dir: Path, performance: pd.DataFrame, selection: Mapping[str, Any]) -> None:
    selected_id = str(selection["selected_portfolio_id"])
    selected = performance.loc[performance["portfolio_id"].eq(selected_id)]
    holdout = selected.loc[selected["outer_split_id"].eq(HOLDOUT_SPLIT)].iloc[0]
    development = selected.loc[selected["outer_split_id"].isin(DEVELOPMENT_SPLITS)]
    mean_net = float(development["total_return"].mean())
    mean_excess = float(development["annualized_excess_return"].mean())
    mean_cost = float(development["cost_drag"].mean())
    high_turnover = float(development["annualized_turnover"].mean()) > 12.0
    holdout_supports = bool(
        np.sign(float(holdout["annualized_excess_return"]))
        == np.sign(mean_excess)
    )
    if int(holdout["unknown_tradability_count"]) > 0 or int(holdout["stale_valuation_date_count"]) > 0:
        priority = "数据与可交易性，其次是组合换手和成本"
    elif high_turnover:
        priority = "组合规则与交易成本"
    else:
        priority = "模型与组合规则的前瞻验证"
    text = f"""# Historical Portfolio Backtest V1 Report

## 结论

- 冻结 LightGBM 信号在两个 development split 的平均净收益为 `{mean_net:.2%}`；结果是已观察历史 test 上的个人研究证据。
- 固定开发规则选中 `{selected_id}`（Top K `{int(selection['top_k'])}`，每 `{int(selection['rebalance_interval'])}` 个交易日调仓）。
- development 平均年化超额收益为 `{mean_excess:.2%}`，平均成本拖累为 `{mean_cost:.2%}`。
- split_003 holdout 净收益 `{float(holdout['total_return']):.2%}`、年化超额 `{float(holdout['annualized_excess_return']):.2%}`、最大回撤 `{float(holdout['max_drawdown']):.2%}`。
- holdout 对 development 方向结论的支持：`{str(holdout_supports).lower()}`；无论结果正负，参数均未改变。
- 高换手是否是主要问题：`{str(high_turnover).lower()}`。当前优先优化方向：{priority}。

## 分层解释

模型预测质量由既有 prediction-level Rank IC 证明，本 PR 未重训或重建 prediction。
组合构建只比较预注册的六组等权 Top K/调仓间隔；执行成本包含佣金、印花税和
10 bps 滑点。gross return 是在同一次执行上把累计实现成本加回 NAV 的近似值，
不是另跑的零成本组合。

历史可交易性仍来自代理字段；stale valuation 只用过去最后有效 close 保持研究 NAV
连续，不恢复交易资格。SH000985 的相对指标只使用双方收益同时有效的 common dates。
因此 `historical_execution_approximate=true`、`unbiased_final_estimate=false`、
`production_model_selected=false`、`live_trading_ready=false`。

## 下一步

可以把冻结的 `{selected_id}` 组合规则作为 PR #20B forward prediction 的初始
paper-portfolio 候选，但必须另行冻结 forward 组合协议，并等待真实新日期；本报告
本身不构成生产或实盘授权。
"""
    (output_dir / "report.md").write_text(text, encoding="utf-8")


def run_holdout(config: Mapping[str, Any]) -> dict[str, Any]:
    code_state = capture_code_state(PROJECT_ROOT)
    if code_state.dirty:
        raise ValueError("holdout run requires committed development selection")
    output_dir = resolve(config["output_dir"])
    selection_path = output_dir / "selected_portfolio_rule.json"
    development_path = output_dir / "development_results.csv"
    selection = json.loads(selection_path.read_text(encoding="utf-8"))
    if selection.get("selection_status") != "frozen_before_holdout":
        raise ValueError("portfolio rule is not frozen before holdout")
    if file_sha256(development_path) != selection["development_results_sha256"]:
        raise ValueError("development results changed after portfolio selection")
    if canonical_hash(config) != selection["config_sha256"]:
        raise ValueError("backtest config changed after portfolio selection")
    selected = next(
        row for row in config["portfolio_candidates"]
        if row["portfolio_id"] == selection["selected_portfolio_id"]
    )
    if int(selected["top_k"]) != int(selection["top_k"]) or int(selected["rebalance_interval"]) != int(selection["rebalance_interval"]):
        raise ValueError("selected portfolio rule differs from frozen config")
    initialize_qlib(config)
    inputs = _prepare_inputs(config)
    receipt_row = inputs["receipt"].loc[
        inputs["receipt"]["outer_split_id"].eq(HOLDOUT_SPLIT)
    ].iloc[0]
    summary, daily, monthly, detail = run_scenario(
        config=config,
        portfolio=selected,
        split_id=HOLDOUT_SPLIT,
        prediction=inputs["predictions"][HOLDOUT_SPLIT],
        receipt_row=receipt_row,
        market=inputs["markets"][HOLDOUT_SPLIT],
        market_audit=inputs["market_audits"][HOLDOUT_SPLIT],
        benchmark=inputs["benchmark"][HOLDOUT_SPLIT],
        output_dir=output_dir,
    )
    holdout = pd.DataFrame([summary])
    _atomic_csv(output_dir / "holdout_result.csv", holdout)
    development = pd.read_csv(development_path)
    performance = pd.concat([development, holdout], ignore_index=True)
    _atomic_csv(output_dir / "performance_summary.csv", performance)
    execution = pd.read_csv(output_dir / "execution_summary.csv")
    _atomic_csv(output_dir / "execution_summary.csv", pd.concat([execution, detail.loc[:, ~detail.columns.duplicated()]], ignore_index=True))
    cost = pd.read_csv(output_dir / "cost_summary.csv")
    cost_columns = cost.columns.tolist()
    _atomic_csv(output_dir / "cost_summary.csv", pd.concat([cost, holdout[cost_columns]], ignore_index=True))
    stale = pd.read_csv(output_dir / "stale_valuation_summary.csv")
    stale_row = detail[[column for column in stale.columns if column in detail.columns]].copy()
    _atomic_csv(output_dir / "stale_valuation_summary.csv", pd.concat([stale, stale_row], ignore_index=True))
    daily_all = pd.read_csv(output_dir / "daily_nav.csv", parse_dates=["datetime"])
    daily_all = pd.concat([daily_all, daily], ignore_index=True)
    _atomic_csv(output_dir / "daily_nav.csv", daily_all)
    returns = pd.read_csv(output_dir / "daily_returns.csv")
    holdout_returns = daily[["datetime", "portfolio_id", "outer_split_id", "return", "benchmark_return", "excess_return", "turnover", "implementation_cost", "drawdown"]]
    _atomic_csv(output_dir / "daily_returns.csv", pd.concat([returns, holdout_returns], ignore_index=True))
    monthly_all = pd.read_csv(output_dir / "monthly_returns.csv")
    _atomic_csv(output_dir / "monthly_returns.csv", pd.concat([monthly_all, monthly], ignore_index=True))
    contract = pd.DataFrame(
        [
            {"check_name": "historical_portfolio_backtest_complete", "status": "pass", "observed_value": True, "required_value": True},
            {"check_name": "portfolio_candidate_scan_complete", "status": "pass", "observed_value": len(development), "required_value": 12},
            {"check_name": "portfolio_rule_selected", "status": "pass", "observed_value": selection["selected_portfolio_id"], "required_value": "one frozen rule"},
            {"check_name": "portfolio_holdout_evaluated", "status": "pass", "observed_value": 1, "required_value": 1},
            {"check_name": "historical_execution_approximate", "status": "pass", "observed_value": True, "required_value": True},
            {"check_name": "model_retrained", "status": "pass", "observed_value": False, "required_value": False},
            {"check_name": "predictions_regenerated", "status": "pass", "observed_value": False, "required_value": False},
            {"check_name": "features_changed", "status": "pass", "observed_value": False, "required_value": False},
            {"check_name": "unbiased_final_estimate", "status": "pass", "observed_value": False, "required_value": False},
            {"check_name": "production_model_selected", "status": "pass", "observed_value": False, "required_value": False},
            {"check_name": "live_trading_ready", "status": "pass", "observed_value": False, "required_value": False},
        ]
    )
    _atomic_csv(output_dir / "contract_status.csv", contract)
    _write_report(output_dir, performance, selection)
    _write_plots(output_dir, performance, daily_all)
    output_files = [output_dir / name for name in COMPACT_FILES if (output_dir / name).is_file()]
    manifest = write_stage_artifact_manifest(
        project_root=PROJECT_ROOT,
        stage_id=STAGE_ID,
        config=config,
        output_dir=output_dir,
        output_files=output_files,
        code_state=code_state,
        input_manifest_paths=[
            resolve(config["prediction_manifest"]),
            resolve(config["market_cache_manifest"]),
        ],
        start_date=performance["start_date"].min(),
        end_date=performance["end_date"].max(),
        artifact_status="pass",
        contract_paths=[output_dir / "contract_status.csv"],
    )
    return {
        "selected_portfolio_id": selection["selected_portfolio_id"],
        "holdout_total_return": summary["total_return"],
        "holdout_information_ratio": summary["information_ratio"],
        "artifact_id": manifest["artifact_id"],
    }
