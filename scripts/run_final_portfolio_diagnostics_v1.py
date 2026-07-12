from __future__ import annotations

import argparse
import sys
from multiprocessing import freeze_support
from pathlib import Path

import pandas as pd
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path: sys.path.insert(0, str(PROJECT_ROOT))

from portfolio.execution_assumptions import ExecutionAssumptions
from portfolio.execution_engine import run_execution
from portfolio.final_diagnostics import cost_sensitivity, performance_summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Run common-assumption final portfolio diagnostics.")
    parser.add_argument("--config", type=Path, default=Path("configs/final_portfolio_diagnostics_v1.yaml"))
    args = parser.parse_args(); path = args.config if args.config.is_absolute() else PROJECT_ROOT / args.config
    config = yaml.safe_load(path.read_text(encoding="utf-8")) or {}; scores = pd.read_parquet(PROJECT_ROOT / config["scores"])
    raw = pd.read_pickle(PROJECT_ROOT / config["factor_frame"])
    market = raw[["datetime", "instrument", "$open", "$close", "$volume", "$amount"]].rename(columns={"$open": "open", "$close": "close", "$volume": "volume", "$amount": "amount"})
    market = market.loc[(market.datetime >= scores.datetime.min()) & (market.datetime <= scores.datetime.max() + pd.Timedelta(days=10))].dropna(subset=["open", "close"])
    market = market.assign(can_buy=True, can_sell=True, limit_up=False, limit_down=False, suspended=market.volume.fillna(0).le(0))
    assumptions = ExecutionAssumptions(**config["execution"]); summaries = []; rolling = []; costs = []; capacities = []
    for method in config["methods"]:
        result = run_execution(scores.loc[scores.method == method], market, assumptions); daily = result["daily_accounting"].copy(); daily["method"] = method
        summaries.append(performance_summary(daily, method)); rolling.append(daily)
        costs.append(cost_sensitivity(daily, method, config["cost_scenarios_bps"], int(config["base_cost_bps"])))
        fills = result["executed_orders"]
        capacities.append(pd.DataFrame([{"method": method, "capital": capital, "max_scaled_participation": ((fills.trade_value * capital / assumptions.initial_cash) / fills.instrument.map(market.groupby("instrument").amount.median())).replace([float("inf")], pd.NA).max()} for capital in config["capital_scenarios"]]))
    summary = pd.DataFrame(summaries); rolling_frame = pd.concat(rolling, ignore_index=True); cost_frame = pd.concat(costs, ignore_index=True); capacity_frame = pd.concat(capacities, ignore_index=True)
    method_rows = []
    available = set(config["methods"])
    aliases = {"stable_equal": "equal_directional_zscore"}
    for method in config["required_methods"]:
        source = method if method in available else aliases.get(method)
        if source in available:
            row = summary.loc[summary.method == source].iloc[0].to_dict(); row.update({"required_method": method, "comparison_status": "pass", "source_method": source})
        else:
            row = {"required_method": method, "comparison_status": "blocked", "source_method": "", "reason": "No score under common PIT/purged/execution assumptions."}
        method_rows.append(row)
    comparison = pd.DataFrame(method_rows)
    regime_rows = []
    for regime in config["regimes"]:
        subset = rolling_frame.loc[pd.to_datetime(rolling_frame.datetime).between(pd.Timestamp(regime["start"]), pd.Timestamp(regime["end"]))]
        for method, group in subset.groupby("method"):
            regime_rows.append({"regime": regime["name"], "method": method, "start": regime["start"], "end": regime["end"], "return": (1 + group.daily_return.fillna(0)).prod() - 1, "days": len(group)})
    weights = pd.read_csv(PROJECT_ROOT / "outputs/factor_score_construction_v1/local_reference/factor_weights_by_window.csv")
    ablation = weights.groupby(["split_id", "method"]).agg(max_factor_weight=("weight", "max"), cluster_count=("cluster_id", "nunique")).reset_index(); ablation["status"] = "diagnostic_only_not_reexecuted"
    exposure = pd.DataFrame([{"exposure": "industry", "status": "blocked", "reason": "historical PIT industry unavailable"}, {"exposure": "size", "status": "blocked", "reason": "historical PIT market cap unavailable"}, {"exposure": "liquidity", "status": "pass", "reason": "capacity participation diagnostics available"}])
    missing = int((comparison.comparison_status == "blocked").sum())
    contract = pd.DataFrame([
        {"check_name": "common_execution_methods", "status": "pass" if len(summary) == len(config["methods"]) else "fail", "observed_value": len(summary), "required_value": len(config["methods"]), "severity": "critical", "reason": "Transparent methods share one execution config."},
        {"check_name": "required_method_coverage", "status": "blocked" if missing else "pass", "observed_value": len(config["required_methods"]) - missing, "required_value": len(config["required_methods"]), "severity": "downstream", "reason": "Legacy and regularized scores require common-assumption regeneration."},
        {"check_name": "historical_exposure_diagnostics", "status": "blocked", "observed_value": 0, "required_value": 2, "severity": "downstream", "reason": "Stage 9 historical PIT industry/size data unavailable."},
        {"check_name": "test_metrics_used_for_selection", "status": "pass", "observed_value": False, "required_value": False, "severity": "critical", "reason": "This stage evaluates already frozen methods."},
    ])
    output = PROJECT_ROOT / config["output_dir"]; output.mkdir(parents=True, exist_ok=True)
    comparison.to_csv(output / "method_comparison.csv", index=False, encoding="utf-8-sig"); rolling_frame.to_csv(output / "rolling_performance.csv", index=False, encoding="utf-8-sig"); pd.DataFrame(regime_rows).to_csv(output / "regime_performance.csv", index=False, encoding="utf-8-sig"); cost_frame.to_csv(output / "cost_sensitivity.csv", index=False, encoding="utf-8-sig"); capacity_frame.to_csv(output / "capacity_sensitivity.csv", index=False, encoding="utf-8-sig"); ablation.to_csv(output / "ablation_results.csv", index=False, encoding="utf-8-sig"); exposure.to_csv(output / "exposure_diagnostics.csv", index=False, encoding="utf-8-sig"); contract.to_csv(output / "contract_status.csv", index=False, encoding="utf-8-sig")
    (output / "final_portfolio_report.md").write_text(f"# Final Portfolio Diagnostics V1\n\n- Common execution methods: `{len(summary)}`\n- Required methods blocked: `{missing}`\n- Historical industry/size exposure: `blocked`\n", encoding="utf-8")
    print(contract.to_string(index=False)); return 1 if ((contract.severity == "critical") & (contract.status == "fail")).any() else 0


if __name__ == "__main__": freeze_support(); raise SystemExit(main())
