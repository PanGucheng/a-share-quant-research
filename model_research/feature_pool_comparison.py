from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from qlib_integration.historical_portfolio_backtest import (
    initialize_qlib,
    load_backtest_config,
    load_benchmark_returns,
    load_market_inputs,
    run_scenario,
)

from .feature_pool_policy import POLICY_IDS
from .runtime_timing import RuntimeTimingRecorder


def run_fixed_p01_comparison(
    *,
    replay_root: Path,
    development_root: Path,
    portfolio_root: Path,
    historical_backtest_config_path: Path,
) -> pd.DataFrame:
    if portfolio_root.exists():
        raise FileExistsError("fixed P01 comparison already exists")
    replay_receipt = json.loads(
        (replay_root / "replay_receipt.json").read_text(encoding="utf-8")
    )
    if replay_receipt.get("released_arm_count") != 9:
        raise PermissionError("P01 comparison requires the complete nine-arm replay")
    if replay_receipt.get("decision_authority") != "diagnostic_only":
        raise PermissionError("replay authority is not diagnostic_only")
    config = load_backtest_config(historical_backtest_config_path)
    initialize_qlib(config)
    markets, market_audits, _ = load_market_inputs(config)
    calendars = {
        split_id: pd.DatetimeIndex(sorted(market["datetime"].unique()))
        for split_id, market in markets.items()
    }
    benchmarks = load_benchmark_returns(str(config["benchmark"]), calendars)
    test_metrics = pd.read_csv(replay_root / "test_metrics.csv")
    staging = portfolio_root.parent / ".staging_portfolio"
    staging.mkdir(parents=True, exist_ok=False)
    timing = RuntimeTimingRecorder(
        execution_class="portfolio_replay",
        execution_profile="ml_feature_pool_mvp_v1",
        execution_dtype="float64",
    )
    summary_rows: list[dict[str, Any]] = []
    p01 = {"portfolio_id": "P01", "top_k": 50, "rebalance_interval": 5}
    for split_id in ("split_001", "split_002", "split_003"):
        for policy_id in POLICY_IDS:
            prediction_path = (
                replay_root / "predictions" / f"{split_id}__{policy_id}.parquet"
            )
            prediction = pd.read_parquet(prediction_path)
            metric = test_metrics.loc[
                test_metrics["outer_split_id"].astype(str).eq(split_id)
                & test_metrics["policy_id"].astype(str).eq(policy_id)
            ]
            if len(metric) != 1:
                raise ValueError(f"missing replay metric: {split_id}/{policy_id}")
            receipt_row = {
                "prediction_artifact_id": str(prediction["model_freeze_id"].iloc[0]),
                "prediction_coverage": float(metric.iloc[0]["prediction_coverage"]),
            }
            for cost_bps in (0.0, 10.0, 20.0):
                scenario_config = dict(config)
                scenario_config["slippage_bps"] = cost_bps
                scenario_output = staging / policy_id / f"cost_{int(cost_bps)}"
                with timing.measure(
                    "portfolio_replay",
                    outer_split_id=split_id,
                    policy_id=policy_id,
                    output_rows=len(prediction),
                    cost_scenario_bps=cost_bps,
                ):
                    summary, _, _, _ = run_scenario(
                        config=scenario_config,
                        portfolio=p01,
                        split_id=split_id,
                        prediction=prediction,
                        receipt_row=receipt_row,
                        market=markets[split_id],
                        market_audit=market_audits[split_id],
                        benchmark=benchmarks[split_id],
                        output_dir=scenario_output,
                    )
                summary_rows.append(
                    {
                        **summary,
                        "policy_id": policy_id,
                        "cost_scenario_bps": cost_bps,
                        "decision_authority": "diagnostic_only",
                        "selection_authorized": False,
                        "strategy_v2_authorized": False,
                    }
                )
    comparison = pd.DataFrame(summary_rows)
    if len(comparison) != 27:
        raise AssertionError("P01 comparison requires 3 splits x 3 policies x 3 costs")
    comparison.to_csv(staging / "portfolio_comparison.csv", index=False)
    timing.write_csv(staging / "runtime_timing.csv")
    receipt = {
        "schema_version": 1,
        "status": "pass",
        "portfolio_id": "P01",
        "top_k": 50,
        "rebalance_interval": 5,
        "primary_cost_bps": 10.0,
        "secondary_cost_bps": [0.0, 20.0],
        "scenario_count": 27,
        "decision_authority": "diagnostic_only",
        "selection_authorized": False,
        "strategy_v2_authorized": False,
        "historical_execution_approximate": True,
    }
    (staging / "portfolio_receipt.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    staging.replace(portfolio_root)
    return comparison


def publish_diagnostic_report(
    *,
    replay_root: Path,
    development_root: Path,
    portfolio_root: Path,
    policy_manifest_path: Path,
    report_root: Path,
) -> None:
    if report_root.exists():
        raise FileExistsError("MVP V1 diagnostic report already exists")
    report_root.mkdir(parents=True, exist_ok=False)
    policies = pd.read_csv(policy_manifest_path)
    metrics = pd.read_csv(replay_root / "test_metrics.csv")
    portfolio = pd.read_csv(portfolio_root / "portfolio_comparison.csv")
    resources = pd.concat(
        [
            pd.read_csv(path)
            for path in development_root.glob("split_*/*/resource_summary.csv")
        ],
        ignore_index=True,
    )
    policies.to_csv(report_root / "policy_inventory.csv", index=False)
    metrics.to_csv(report_root / "prediction_comparison.csv", index=False)
    resources.to_csv(report_root / "model_resource_comparison.csv", index=False)
    portfolio.to_csv(report_root / "portfolio_comparison.csv", index=False)
    limitations = {
        "decision_authority": "diagnostic_only",
        "selection_authorized": False,
        "strategy_v2_authorized": False,
        "historical_test_already_observed": True,
        "unbiased_final_estimate": False,
        "historical_execution_approximate": True,
        "policy_winner_artifact": "forbidden",
        "deferred": [
            "policy winner selection",
            "clustering ablation",
            "SHAP/permutation",
            "bootstrap",
            "feature-importance stability",
        ],
    }
    (report_root / "limitations.json").write_text(
        json.dumps(limitations, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    primary = portfolio.loc[portfolio["cost_scenario_bps"].eq(10.0)]
    lines = [
        "# ML Feature Pool MVP V1 — Historical Diagnostic Report",
        "",
        "- `decision_authority=diagnostic_only`",
        "- `selection_authorized=false`",
        "- `strategy_v2_authorized=false`",
        "- Historical test periods were already observed; results are not an unbiased final estimate.",
        "",
        "## Scope",
        "",
        "Three arms are reported in parallel: `strict_current_baseline`, "
        "`current_plus_existing_conditional_signal`, and `broad_data_qualified`.",
        "No policy winner, leader, recommendation, or Strategy V2 candidate is produced.",
        "",
        "## Completion",
        "",
        f"- Frozen development arms: {len(resources)} / 9.",
        f"- Historical model metrics: {len(metrics)} / 9.",
        f"- Fixed P01 primary-cost rows: {len(primary)} / 9.",
        "",
        "Machine-readable comparisons are adjacent to this report. Interpret differences "
        "as historical diagnostics only.",
    ]
    (report_root / "REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
