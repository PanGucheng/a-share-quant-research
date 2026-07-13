from __future__ import annotations

import argparse
import sys
from multiprocessing import freeze_support
from pathlib import Path

import pandas as pd
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from portfolio.execution_assumptions import ExecutionAssumptions  # noqa: E402
from portfolio.execution_engine import run_execution  # noqa: E402
from portfolio.final_diagnostics import build_period_comparisons, cost_sensitivity  # noqa: E402
from research_validation.lineage import capture_code_state, load_artifact_manifest, validate_manifest_outputs, write_stage_artifact_manifest  # noqa: E402
from research_validation.stage_output import StageOutputPublisher  # noqa: E402


CONTROLLED_OUTPUTS = (
    "native_period_method_comparison.csv", "common_period_method_comparison.csv", "method_comparison.csv",
    "rolling_performance.csv", "regime_performance.csv", "cost_sensitivity.csv", "capacity_sensitivity.csv",
    "ablation_results.csv", "exposure_diagnostics.csv", "contract_status.csv", "final_portfolio_report.md",
    "artifact_manifest.json",
)
COMPARISON_COLUMNS = ["method", "trading_days", "net_annualized_return", "net_ir", "maximum_drawdown", "average_turnover", "positive_day_ratio", "period_growth", "normalized_final_nav", "account_ending_nav", "source_method", "start_date", "end_date"]


def _upstream_ready(config: dict) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    pairs = [
        ("score", config["score_contract"], config["input_manifests"][1], config["score_config"]),
        ("execution", config["execution_contract"], config["input_manifests"][0], config["execution_config"]),
    ]
    for name, contract_name, manifest_name, config_name in pairs:
        contract_path = PROJECT_ROOT / contract_name
        if not contract_path.is_file():
            reasons.append(f"{name}_contract_missing")
        else:
            contract = pd.read_csv(contract_path)
            if not contract.loc[contract.status.isin(["fail", "blocked"]) & contract.severity.eq("critical")].empty:
                reasons.append(f"{name}_contract_blocked")
        manifest_path = PROJECT_ROOT / manifest_name
        if not manifest_path.is_file():
            reasons.append(f"{name}_manifest_missing")
            continue
        manifest = load_artifact_manifest(manifest_path)
        stage_config = yaml.safe_load((PROJECT_ROOT / config_name).read_text(encoding="utf-8")) or {}
        reasons.extend(f"{name}_{item.check_name}" for item in validate_manifest_outputs(manifest, PROJECT_ROOT / stage_config["output_dir"], config=stage_config))
        if manifest.get("artifact_status", "pass") != "pass":
            reasons.append(f"{name}_artifact_{manifest.get('artifact_status')}")
    return not reasons, sorted(set(reasons))


def _publish_blocked(publisher: StageOutputPublisher, config: dict, code_state, reasons: list[str]) -> None:
    for name in ("native_period_method_comparison.csv", "common_period_method_comparison.csv", "method_comparison.csv"):
        pd.DataFrame(columns=COMPARISON_COLUMNS).to_csv(publisher.path(name), index=False, encoding="utf-8-sig")
    pd.DataFrame(columns=["datetime", "cash", "nav", "turnover", "daily_return", "method"]).to_csv(publisher.path("rolling_performance.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(columns=["regime", "method", "start", "end", "return", "days"]).to_csv(publisher.path("regime_performance.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(columns=["method", "cost_bps", "annualized_return", "ir"]).to_csv(publisher.path("cost_sensitivity.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(columns=["method", "capital", "max_scaled_participation"]).to_csv(publisher.path("capacity_sensitivity.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(columns=["split_id", "method", "max_factor_weight", "cluster_count", "status"]).to_csv(publisher.path("ablation_results.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame([
        {"exposure": "legacy_baselines", "status": "pass" if config.get("additional_scores") and (PROJECT_ROOT / config["additional_scores"]).is_file() else "blocked", "reason": "Independent display only."},
        {"exposure": "current_stability_pipeline", "status": "blocked", "reason": "blocked_no_current_reference_pipeline"},
    ]).to_csv(publisher.path("exposure_diagnostics.csv"), index=False, encoding="utf-8-sig")
    contract = pd.DataFrame([
        {"check_name": "pre_model_diagnostics_status", "status": "blocked", "observed_value": "blocked_no_current_reference_pipeline", "required_value": "pass", "severity": "critical", "reason": ";".join(reasons)},
        {"check_name": "legacy_baselines_available", "status": "pass", "observed_value": bool(config.get("additional_scores") and (PROJECT_ROOT / config["additional_scores"]).is_file()), "required_value": "reported", "severity": "warning", "reason": "Legacy baselines do not substitute for current methods."},
        {"check_name": "current_stability_pipeline_available", "status": "blocked", "observed_value": False, "required_value": True, "severity": "critical", "reason": "Current score/execution chain is blocked."},
    ])
    contract.to_csv(publisher.path("contract_status.csv"), index=False, encoding="utf-8-sig")
    publisher.path("final_portfolio_report.md").write_text("# Pre-Model Diagnostics V1\n\n- Status: `blocked_no_current_reference_pipeline`\n- Legacy baselines remain independent diagnostics only.\n", encoding="utf-8")
    output_files = [publisher.staging_dir / item for item in CONTROLLED_OUTPUTS if item != "artifact_manifest.json" and (publisher.staging_dir / item).is_file()]
    write_stage_artifact_manifest(
        project_root=PROJECT_ROOT, stage_id="pre_model_diagnostics_v1", config=config,
        output_dir=publisher.staging_dir, output_files=output_files, code_state=code_state,
        input_manifest_paths=[PROJECT_ROOT / item for item in config.get("input_manifests", [])],
        missing_lineage_fields=["reference_execution_signal_date_only", "universe_artifact_id"],
        lineage_status="reference_only", artifact_status="blocked", blocked_reason="blocked_no_current_reference_pipeline",
    )


def main(default_config: Path = Path("configs/final_portfolio_diagnostics_v1.yaml")) -> int:
    parser = argparse.ArgumentParser(description="Run common-assumption pre-model diagnostics.")
    parser.add_argument("--config", type=Path, default=default_config)
    args = parser.parse_args()
    path = args.config if args.config.is_absolute() else PROJECT_ROOT / args.config
    config = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    code_state = capture_code_state(PROJECT_ROOT)
    output = PROJECT_ROOT / config["output_dir"]
    with StageOutputPublisher(output, CONTROLLED_OUTPUTS) as publisher:
        upstream_ready, reasons = _upstream_ready(config)
        if not upstream_ready:
            _publish_blocked(publisher, config, code_state, reasons)
            publisher.publish()
            print("pre-model diagnostics blocked: no current reference pipeline")
            return 2

        scores = pd.read_parquet(PROJECT_ROOT / config["scores"])
        if config.get("additional_scores"):
            scores = pd.concat([scores, pd.read_parquet(PROJECT_ROOT / config["additional_scores"])], ignore_index=True)
        raw = pd.read_pickle(PROJECT_ROOT / config["factor_frame"])
        market = raw[["datetime", "instrument", "$open", "$close", "$volume", "$amount"]].rename(columns={"$open": "open", "$close": "close", "$volume": "volume", "$amount": "amount"})
        market = market.loc[(market.datetime >= scores.datetime.min()) & (market.datetime <= scores.datetime.max() + pd.Timedelta(days=10))].dropna(subset=["open", "close"])
        market = market.assign(can_buy=True, can_sell=True, limit_up=False, limit_down=False, suspended=market.volume.fillna(0).le(0))
        assumptions = ExecutionAssumptions(**config["execution"])
        rolling: list[pd.DataFrame] = []
        costs: list[pd.DataFrame] = []
        capacities: list[pd.DataFrame] = []
        daily_by_method: dict[str, pd.DataFrame] = {}
        for method in config["methods"]:
            result = run_execution(scores.loc[scores.method == method], market, assumptions)
            daily = result["daily_accounting"].copy()
            daily["method"] = method
            daily_by_method[method] = daily
            rolling.append(daily)
            costs.append(cost_sensitivity(daily, method, config["cost_scenarios_bps"], int(config["base_cost_bps"])))
            fills = result["executed_orders"]
            capacities.append(pd.DataFrame([{"method": method, "capital": capital, "max_scaled_participation": ((fills.trade_value * capital / assumptions.initial_cash) / fills.instrument.map(market.groupby("instrument").amount.median())).replace([float("inf")], pd.NA).max()} for capital in config["capital_scenarios"]]))
        aliases = {"stable_equal": "equal_directional_zscore"}
        native, common, common_contract = build_period_comparisons(daily_by_method, config["required_methods"], aliases)
        rolling_frame = pd.concat(rolling, ignore_index=True)
        regime_rows = []
        for regime in config["regimes"]:
            subset = rolling_frame.loc[pd.to_datetime(rolling_frame.datetime).between(pd.Timestamp(regime["start"]), pd.Timestamp(regime["end"]))]
            for method, group in subset.groupby("method"):
                regime_rows.append({"regime": regime["name"], "method": method, "start": regime["start"], "end": regime["end"], "return": (1 + group.daily_return.fillna(0)).prod() - 1, "days": len(group)})
        weights = pd.read_csv(PROJECT_ROOT / config["factor_weights"])
        ablation = weights.groupby(["split_id", "method"]).agg(max_factor_weight=("weight", "max"), cluster_count=("cluster_id", "nunique")).reset_index()
        ablation["status"] = "diagnostic_only_not_reexecuted"
        exposure = pd.DataFrame([{"exposure": "current_stability_pipeline", "status": "pass", "reason": "Current score and execution artifacts validated."}])
        contract = pd.DataFrame([
            {"check_name": "pre_model_diagnostics_status", "status": "pass", "observed_value": "pass", "required_value": "pass", "severity": "critical", "reason": "Current pipeline diagnostics completed."},
            {"check_name": "common_trading_days", "status": "pass", "observed_value": common_contract["common_trading_days"], "required_value": ">0", "severity": "critical", "reason": "Common-period rankings only."},
        ])
        native.to_csv(publisher.path("native_period_method_comparison.csv"), index=False, encoding="utf-8-sig")
        common.to_csv(publisher.path("common_period_method_comparison.csv"), index=False, encoding="utf-8-sig")
        common.to_csv(publisher.path("method_comparison.csv"), index=False, encoding="utf-8-sig")
        rolling_frame.to_csv(publisher.path("rolling_performance.csv"), index=False, encoding="utf-8-sig")
        pd.DataFrame(regime_rows).to_csv(publisher.path("regime_performance.csv"), index=False, encoding="utf-8-sig")
        pd.concat(costs, ignore_index=True).to_csv(publisher.path("cost_sensitivity.csv"), index=False, encoding="utf-8-sig")
        pd.concat(capacities, ignore_index=True).to_csv(publisher.path("capacity_sensitivity.csv"), index=False, encoding="utf-8-sig")
        ablation.to_csv(publisher.path("ablation_results.csv"), index=False, encoding="utf-8-sig")
        exposure.to_csv(publisher.path("exposure_diagnostics.csv"), index=False, encoding="utf-8-sig")
        contract.to_csv(publisher.path("contract_status.csv"), index=False, encoding="utf-8-sig")
        publisher.path("final_portfolio_report.md").write_text(f"# Pre-Model Diagnostics V1\n\n- Status: `pass`\n- Common trading days: `{common_contract['common_trading_days']}`\n", encoding="utf-8")
        output_files = [publisher.staging_dir / item for item in CONTROLLED_OUTPUTS if item != "artifact_manifest.json" and (publisher.staging_dir / item).is_file()]
        write_stage_artifact_manifest(
            project_root=PROJECT_ROOT, stage_id="pre_model_diagnostics_v1", config=config,
            output_dir=publisher.staging_dir, output_files=output_files, code_state=code_state,
            input_manifest_paths=[PROJECT_ROOT / item for item in config.get("input_manifests", [])],
            start_date=common_contract["common_start_date"], end_date=common_contract["common_end_date"],
            missing_lineage_fields=["reference_execution_signal_date_only", "universe_artifact_id"],
        )
        publisher.publish()
    print(contract.to_string(index=False))
    return 0


if __name__ == "__main__":
    freeze_support()
    raise SystemExit(main())
