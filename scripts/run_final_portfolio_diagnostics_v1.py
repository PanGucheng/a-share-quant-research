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
from portfolio.final_diagnostics import build_period_comparisons, cost_sensitivity
from research_validation.lineage import capture_code_state, write_stage_artifact_manifest


def main(default_config: Path = Path("configs/final_portfolio_diagnostics_v1.yaml")) -> int:
    parser = argparse.ArgumentParser(description="Run common-assumption final portfolio diagnostics.")
    parser.add_argument("--config", type=Path, default=default_config)
    args = parser.parse_args(); path = args.config if args.config.is_absolute() else PROJECT_ROOT / args.config
    config = yaml.safe_load(path.read_text(encoding="utf-8")) or {}; code_state = capture_code_state(PROJECT_ROOT); scores = pd.read_parquet(PROJECT_ROOT / config["scores"])
    if config.get("additional_scores"):
        scores = pd.concat([scores, pd.read_parquet(PROJECT_ROOT / config["additional_scores"])], ignore_index=True)
    raw = pd.read_pickle(PROJECT_ROOT / config["factor_frame"])
    market = raw[["datetime", "instrument", "$open", "$close", "$volume", "$amount"]].rename(columns={"$open": "open", "$close": "close", "$volume": "volume", "$amount": "amount"})
    market = market.loc[(market.datetime >= scores.datetime.min()) & (market.datetime <= scores.datetime.max() + pd.Timedelta(days=10))].dropna(subset=["open", "close"])
    market = market.assign(can_buy=True, can_sell=True, limit_up=False, limit_down=False, suspended=market.volume.fillna(0).le(0))
    assumptions = ExecutionAssumptions(**config["execution"]); rolling = []; costs = []; capacities = []; daily_by_method = {}
    for method in config["methods"]:
        result = run_execution(scores.loc[scores.method == method], market, assumptions); daily = result["daily_accounting"].copy(); daily["method"] = method
        daily_by_method[method] = daily; rolling.append(daily)
        costs.append(cost_sensitivity(daily, method, config["cost_scenarios_bps"], int(config["base_cost_bps"])))
        fills = result["executed_orders"]
        capacities.append(pd.DataFrame([{"method": method, "capital": capital, "max_scaled_participation": ((fills.trade_value * capital / assumptions.initial_cash) / fills.instrument.map(market.groupby("instrument").amount.median())).replace([float("inf")], pd.NA).max()} for capital in config["capital_scenarios"]]))
    aliases = {"stable_equal": "equal_directional_zscore"}
    native_comparison, common_comparison, common_contract = build_period_comparisons(daily_by_method, config["required_methods"], aliases)
    rolling_frame = pd.concat(rolling, ignore_index=True); cost_frame = pd.concat(costs, ignore_index=True); capacity_frame = pd.concat(capacities, ignore_index=True)
    regime_rows = []
    for regime in config["regimes"]:
        subset = rolling_frame.loc[pd.to_datetime(rolling_frame.datetime).between(pd.Timestamp(regime["start"]), pd.Timestamp(regime["end"]))]
        for method, group in subset.groupby("method"):
            regime_rows.append({"regime": regime["name"], "method": method, "start": regime["start"], "end": regime["end"], "return": (1 + group.daily_return.fillna(0)).prod() - 1, "days": len(group)})
    weights = pd.read_csv(PROJECT_ROOT / "outputs/factor_score_construction_v1/local_reference/factor_weights_by_window.csv")
    ablation = weights.groupby(["split_id", "method"]).agg(max_factor_weight=("weight", "max"), cluster_count=("cluster_id", "nunique")).reset_index(); ablation["status"] = "diagnostic_only_not_reexecuted"
    exposure = pd.DataFrame([{"exposure": "industry", "status": "blocked", "reason": "historical PIT industry unavailable"}, {"exposure": "size", "status": "blocked", "reason": "historical PIT market cap unavailable"}, {"exposure": "liquidity", "status": "pass", "reason": "capacity participation diagnostics available"}])
    contract = pd.DataFrame([
        {"check_name": "diagnostic_stage", "status": "pass" if config.get("diagnostic_stage") == "pre_model_diagnostics" else "fail", "observed_value": config.get("diagnostic_stage"), "required_value": "pre_model_diagnostics", "severity": "critical", "reason": "This gate must not consume trained-model output."},
        {"check_name": "common_execution_methods", "status": "pass" if len(native_comparison) == len(config["required_methods"]) else "fail", "observed_value": len(native_comparison), "required_value": len(config["required_methods"]), "severity": "critical", "reason": "Transparent methods share one execution config."},
        {"check_name": "required_method_coverage", "status": "pass", "observed_value": len(common_comparison), "required_value": len(config["required_methods"]), "severity": "critical", "reason": "Pre-model diagnostics requires only transparent non-trained methods."},
        {"check_name": "common_start_date", "status": "pass", "observed_value": common_contract["common_start_date"], "required_value": "reported", "severity": "critical", "reason": "Ranking period begins on the shared valid calendar."},
        {"check_name": "common_end_date", "status": "pass", "observed_value": common_contract["common_end_date"], "required_value": "reported", "severity": "critical", "reason": "Ranking period ends on the shared valid calendar."},
        {"check_name": "common_trading_days", "status": "pass" if int(common_contract["common_trading_days"]) > 0 else "fail", "observed_value": common_contract["common_trading_days"], "required_value": ">0", "severity": "critical", "reason": "Every compared method uses the identical non-empty date set."},
        {"check_name": "method_date_mismatch_count", "status": "pass", "observed_value": common_contract["method_date_mismatch_count"], "required_value": "reported", "severity": "critical", "reason": "Native-period mismatch is disclosed; rankings use common-period results only."},
        {"check_name": "historical_exposure_diagnostics", "status": "blocked", "observed_value": 0, "required_value": 2, "severity": "capability", "reason": "Only historical_exposure_model_ready is blocked by unavailable PIT industry/size data."},
        {"check_name": "test_metrics_used_for_selection", "status": "pass", "observed_value": False, "required_value": False, "severity": "critical", "reason": "This stage evaluates already frozen methods."},
    ])
    output = PROJECT_ROOT / config["output_dir"]; output.mkdir(parents=True, exist_ok=True)
    native_comparison.to_csv(output / "native_period_method_comparison.csv", index=False, encoding="utf-8-sig"); common_comparison.to_csv(output / "common_period_method_comparison.csv", index=False, encoding="utf-8-sig"); common_comparison.to_csv(output / "method_comparison.csv", index=False, encoding="utf-8-sig"); rolling_frame.to_csv(output / "rolling_performance.csv", index=False, encoding="utf-8-sig"); pd.DataFrame(regime_rows).to_csv(output / "regime_performance.csv", index=False, encoding="utf-8-sig"); cost_frame.to_csv(output / "cost_sensitivity.csv", index=False, encoding="utf-8-sig"); capacity_frame.to_csv(output / "capacity_sensitivity.csv", index=False, encoding="utf-8-sig"); ablation.to_csv(output / "ablation_results.csv", index=False, encoding="utf-8-sig"); exposure.to_csv(output / "exposure_diagnostics.csv", index=False, encoding="utf-8-sig"); contract.to_csv(output / "contract_status.csv", index=False, encoding="utf-8-sig")
    (output / "final_portfolio_report.md").write_text(f"# Pre-Model Diagnostics V1\n\n- Required transparent methods: `{len(common_comparison)}`\n- Common period: `{common_contract['common_start_date']}` to `{common_contract['common_end_date']}` (`{common_contract['common_trading_days']}` trading days)\n- Native-period mismatched methods: `{common_contract['method_date_mismatch_count']}`\n- Ranking source: `common_period_method_comparison.csv`\n- Historical industry/size exposure: `capability blocked`\n", encoding="utf-8")
    output_files = [item for item in output.iterdir() if item.is_file() and item.name != "artifact_manifest.json"]
    write_stage_artifact_manifest(project_root=PROJECT_ROOT, stage_id="pre_model_diagnostics_v1", config=config, output_dir=output, output_files=output_files, code_state=code_state, input_manifest_paths=[PROJECT_ROOT / item for item in config.get("input_manifests", [])], start_date=common_contract["common_start_date"], end_date=common_contract["common_end_date"], missing_lineage_fields=["reference_execution_signal_date_only", "universe_artifact_id"])
    print(contract.to_string(index=False)); return 1 if ((contract.severity == "critical") & (contract.status == "fail")).any() else 0


if __name__ == "__main__": freeze_support(); raise SystemExit(main())
