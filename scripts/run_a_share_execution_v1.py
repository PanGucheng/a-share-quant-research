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

from portfolio.capacity import capacity_row  # noqa: E402
from portfolio.execution_assumptions import ExecutionAssumptions  # noqa: E402
from portfolio.execution_engine import run_execution  # noqa: E402
from research_validation.lineage import (  # noqa: E402
    capture_code_state, load_artifact_manifest, validate_manifest_outputs, write_stage_artifact_manifest,
)
from research_validation.stage_output import StageOutputPublisher  # noqa: E402


CONTROLLED_OUTPUTS = (
    "order_intents.csv", "executed_orders.csv", "rejected_orders.csv", "partial_fills.csv",
    "transaction_costs.csv", "daily_turnover.csv", "capacity_diagnostics.csv", "contract_status.csv",
    "execution_summary.csv", "execution_report.md", "runtime/positions.csv", "artifact_manifest.json",
)
EMPTY_SCHEMAS = {
    "order_intents.csv": ["signal_date", "execution_date", "instrument", "side", "requested_shares"],
    "executed_orders.csv": ["signal_date", "execution_date", "instrument", "side", "shares", "price", "trade_value"],
    "rejected_orders.csv": ["signal_date", "execution_date", "instrument", "side", "reason", "unfilled_shares"],
    "partial_fills.csv": ["execution_date", "instrument", "side", "requested_shares", "executed_shares", "unfilled_shares"],
    "transaction_costs.csv": ["execution_date", "instrument", "side", "commission", "tax", "total_cost"],
    "daily_turnover.csv": ["datetime", "cash", "nav", "turnover", "accounting_error", "daily_return", "holding_valuation_missing_count", "unfilled_shares", "calendar_mode"],
    "capacity_diagnostics.csv": ["strategy_capital", "order_value", "daily_amount", "participation_rate", "capacity_multiple", "estimated_impact_cost"],
    "execution_summary.csv": ["initial_cash", "final_nav", "executed_orders", "rejected_orders", "partial_fills", "unfilled_shares", "holding_valuation_missing_count", "calendar_mode", "average_turnover"],
    "runtime/positions.csv": ["instrument", "shares", "buy_date"],
}


def _score_is_current(config: dict) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    contract_path = PROJECT_ROOT / config["score_contract"]
    if not contract_path.is_file():
        reasons.append("score_contract_missing")
    else:
        contract = pd.read_csv(contract_path)
        if not contract.loc[contract.status.isin(["fail", "blocked"]) & contract.severity.eq("critical")].empty:
            reasons.append("score_contract_blocked")
    manifest_path = PROJECT_ROOT / config["input_manifests"][0]
    if not manifest_path.is_file():
        reasons.append("score_manifest_missing")
    else:
        manifest = load_artifact_manifest(manifest_path)
        score_config = yaml.safe_load((PROJECT_ROOT / config["score_config"]).read_text(encoding="utf-8")) or {}
        issues = validate_manifest_outputs(manifest, PROJECT_ROOT / score_config["output_dir"], config=score_config)
        reasons.extend(item.check_name for item in issues)
        if manifest.get("artifact_status", "pass") != "pass":
            reasons.append(f"score_artifact_{manifest.get('artifact_status')}")
    score_path = PROJECT_ROOT / config["scores"]
    if not score_path.is_file():
        reasons.append("score_runtime_missing")
    return not reasons, sorted(set(reasons))


def _publish_blocked(publisher: StageOutputPublisher, config: dict, code_state, reasons: list[str]) -> None:
    for name, columns in EMPTY_SCHEMAS.items():
        pd.DataFrame(columns=columns).to_csv(publisher.path(name), index=False, encoding="utf-8-sig")
    contract = pd.DataFrame([
        {"check_name": "execution_status", "status": "blocked", "observed_value": "blocked_no_valid_current_score", "required_value": "pass", "severity": "critical", "reason": ";".join(reasons)},
        {"check_name": "executed_order_count", "status": "blocked", "observed_value": 0, "required_value": ">0", "severity": "critical", "reason": "No current valid score artifact."},
    ])
    contract.to_csv(publisher.path("contract_status.csv"), index=False, encoding="utf-8-sig")
    publisher.path("execution_report.md").write_text("# A-Share Execution V1\n\n- Status: `blocked_no_valid_current_score`\n- Old execution runtime retained: `false`\n", encoding="utf-8")
    output_files = [publisher.staging_dir / item for item in CONTROLLED_OUTPUTS if item != "artifact_manifest.json" and (publisher.staging_dir / item).is_file()]
    write_stage_artifact_manifest(
        project_root=PROJECT_ROOT, stage_id="a_share_execution_v1", config=config,
        output_dir=publisher.staging_dir, output_files=output_files, code_state=code_state,
        input_manifest_paths=[PROJECT_ROOT / item for item in config.get("input_manifests", [])],
        missing_lineage_fields=["reference_execution_signal_date_only", "universe_artifact_id"],
        lineage_status="reference_only", artifact_status="blocked", blocked_reason="blocked_no_valid_current_score",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Run A-share constrained reference execution.")
    parser.add_argument("--config", type=Path, default=Path("configs/a_share_execution_v1.yaml"))
    args = parser.parse_args()
    path = args.config if args.config.is_absolute() else PROJECT_ROOT / args.config
    config = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    code_state = capture_code_state(PROJECT_ROOT)
    output = PROJECT_ROOT / config["output_dir"]
    with StageOutputPublisher(output, CONTROLLED_OUTPUTS) as publisher:
        score_ready, score_reasons = _score_is_current(config)
        if not score_ready:
            _publish_blocked(publisher, config, code_state, score_reasons)
            publisher.publish()
            print("execution blocked: no valid current score")
            return 2

        scores = pd.read_parquet(PROJECT_ROOT / config["scores"])
        scores = scores.loc[scores.method == config["method"]]
        if scores.empty or not scores.composite_score.notna().any():
            _publish_blocked(publisher, config, code_state, ["score_runtime_empty"])
            publisher.publish()
            return 2
        raw = pd.read_pickle(PROJECT_ROOT / config["factor_frame"])
        market = raw[["datetime", "instrument", "$open", "$close", "$volume", "$amount"]].rename(columns={"$open": "open", "$close": "close", "$volume": "volume", "$amount": "amount"})
        market = market.loc[(market.datetime >= scores.datetime.min()) & (market.datetime <= scores.datetime.max() + pd.Timedelta(days=10))].dropna(subset=["open", "close"])
        market = market.assign(can_buy=True, can_sell=True, limit_up=False, limit_down=False, suspended=market.volume.fillna(0).le(0))
        assumptions = ExecutionAssumptions(**{field: config[field] for field in ExecutionAssumptions.__dataclass_fields__})
        outputs = run_execution(scores, market, assumptions)
        mapping = {"order_intents": "order_intents.csv", "executed_orders": "executed_orders.csv", "rejected_orders": "rejected_orders.csv", "partial_fills": "partial_fills.csv", "transaction_costs": "transaction_costs.csv"}
        for key, filename in mapping.items():
            outputs[key].to_csv(publisher.path(filename), index=False, encoding="utf-8-sig")
        outputs["positions"].to_csv(publisher.path("runtime/positions.csv"), index=False, encoding="utf-8-sig")
        daily = outputs["daily_accounting"]
        daily.to_csv(publisher.path("daily_turnover.csv"), index=False, encoding="utf-8-sig")
        fills = outputs["executed_orders"]
        capacity = pd.DataFrame([capacity_row(assumptions.initial_cash, row.trade_value, float(market.loc[(market.datetime == row.execution_date) & (market.instrument == row.instrument), "amount"].iloc[0]), assumptions.max_participation_rate, assumptions.slippage_bps / 10000) for row in fills.itertuples(index=False)])
        capacity.to_csv(publisher.path("capacity_diagnostics.csv"), index=False, encoding="utf-8-sig")
        contract = pd.DataFrame([
            {"check_name": "execution_status", "status": "pass", "observed_value": "pass", "required_value": "pass", "severity": "critical", "reason": "Current score artifact executed."},
            {"check_name": "cash_conservation_error", "status": "pass" if daily.accounting_error.abs().max() <= 1e-6 else "fail", "observed_value": daily.accounting_error.abs().max(), "required_value": "<=1e-6", "severity": "critical", "reason": "Cash ledger must reconcile."},
            {"check_name": "non_negative_cash", "status": "pass" if daily.cash.min() >= -1e-9 else "fail", "observed_value": daily.cash.min(), "required_value": ">=0", "severity": "critical", "reason": "Buy sizing reserves fees."},
        ])
        contract.to_csv(publisher.path("contract_status.csv"), index=False, encoding="utf-8-sig")
        pd.DataFrame([{"initial_cash": assumptions.initial_cash, "final_nav": daily.nav.iloc[-1], "executed_orders": len(fills), "rejected_orders": len(outputs["rejected_orders"]), "partial_fills": len(outputs["partial_fills"]), "unfilled_shares": int(daily.unfilled_shares.sum()), "holding_valuation_missing_count": int(daily.holding_valuation_missing_count.sum()), "calendar_mode": "signal_date_only", "average_turnover": daily.turnover.mean()}]).to_csv(publisher.path("execution_summary.csv"), index=False, encoding="utf-8-sig")
        publisher.path("execution_report.md").write_text(f"# A-Share Execution V1\n\n- Status: `pass`\n- Executed orders: `{len(fills)}`\n", encoding="utf-8")
        output_files = [publisher.staging_dir / item for item in CONTROLLED_OUTPUTS if item != "artifact_manifest.json" and (publisher.staging_dir / item).is_file()]
        write_stage_artifact_manifest(
            project_root=PROJECT_ROOT, stage_id="a_share_execution_v1", config=config,
            output_dir=publisher.staging_dir, output_files=output_files, code_state=code_state,
            input_manifest_paths=[PROJECT_ROOT / item for item in config.get("input_manifests", [])],
            start_date=daily.datetime.min(), end_date=daily.datetime.max(),
            missing_lineage_fields=["reference_execution_signal_date_only", "universe_artifact_id"],
        )
        publisher.publish()
    print(contract.to_string(index=False))
    return 1 if (contract.status == "fail").any() else 0


if __name__ == "__main__":
    freeze_support()
    raise SystemExit(main())
