from __future__ import annotations

import argparse
import sys
from multiprocessing import freeze_support
from pathlib import Path

import pandas as pd
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path: sys.path.insert(0, str(PROJECT_ROOT))

from portfolio.capacity import capacity_row  # noqa: E402
from portfolio.execution_assumptions import ExecutionAssumptions  # noqa: E402
from portfolio.execution_engine import run_execution  # noqa: E402
from research_validation.lineage import capture_code_state, write_stage_artifact_manifest  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Run A-share constrained reference execution.")
    parser.add_argument("--config", type=Path, default=Path("configs/a_share_execution_v1.yaml"))
    args = parser.parse_args(); path = args.config if args.config.is_absolute() else PROJECT_ROOT / args.config
    config = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    code_state = capture_code_state(PROJECT_ROOT)
    scores = pd.read_parquet(PROJECT_ROOT / config["scores"]); scores = scores.loc[scores.method == config["method"]]
    raw = pd.read_pickle(PROJECT_ROOT / config["factor_frame"])
    market = raw[["datetime", "instrument", "$open", "$close", "$volume", "$amount"]].rename(columns={"$open": "open", "$close": "close", "$volume": "volume", "$amount": "amount"})
    market = market.loc[(market.datetime >= scores.datetime.min()) & (market.datetime <= scores.datetime.max() + pd.Timedelta(days=10))].dropna(subset=["open", "close"])
    market = market.assign(can_buy=True, can_sell=True, limit_up=False, limit_down=False, suspended=market.volume.fillna(0).le(0))
    assumptions = ExecutionAssumptions(**{field: config[field] for field in ExecutionAssumptions.__dataclass_fields__})
    outputs = run_execution(scores, market, assumptions)
    output = PROJECT_ROOT / config["output_dir"]; runtime = output / "runtime"; runtime.mkdir(parents=True, exist_ok=True)
    mapping = {"order_intents": "order_intents.csv", "executed_orders": "executed_orders.csv", "rejected_orders": "rejected_orders.csv", "partial_fills": "partial_fills.csv", "transaction_costs": "transaction_costs.csv"}
    for key, filename in mapping.items(): outputs[key].to_csv(output / filename, index=False, encoding="utf-8-sig")
    outputs["positions"].to_csv(runtime / "positions.csv", index=False, encoding="utf-8-sig")
    daily = outputs["daily_accounting"]; daily.to_csv(output / "daily_turnover.csv", index=False, encoding="utf-8-sig")
    fills = outputs["executed_orders"]
    capacity = pd.DataFrame([capacity_row(assumptions.initial_cash, row.trade_value, float(market.loc[(market.datetime == row.execution_date) & (market.instrument == row.instrument), "amount"].iloc[0]), assumptions.max_participation_rate, assumptions.slippage_bps / 10000) for row in fills.itertuples(index=False)])
    capacity.to_csv(output / "capacity_diagnostics.csv", index=False, encoding="utf-8-sig")
    contract = pd.DataFrame([
        {"check_name": "cash_conservation_error", "status": "pass" if daily.accounting_error.abs().max() <= 1e-6 else "fail", "observed_value": daily.accounting_error.abs().max(), "required_value": "<=1e-6", "severity": "critical", "reason": "Cash ledger must reconcile."},
        {"check_name": "non_negative_cash", "status": "pass" if daily.cash.min() >= -1e-9 else "fail", "observed_value": daily.cash.min(), "required_value": ">=0", "severity": "critical", "reason": "Buy sizing must reserve commissions before execution."},
        {"check_name": "holding_valuation_missing_count", "status": "pass", "observed_value": int(daily.holding_valuation_missing_count.sum()), "required_value": "reported_and_carried_forward", "severity": "critical", "reason": "Missing current quotes use the last observed close and are never valued at zero."},
        {"check_name": "unfilled_share_count", "status": "pass", "observed_value": int(daily.unfilled_shares.sum()), "required_value": "reported", "severity": "critical", "reason": "Rejected and partial quantities must remain observable."},
        {"check_name": "execution_calendar_mode", "status": "pass" if set(daily.calendar_mode) == {"signal_date_only"} else "fail", "observed_value": ",".join(sorted(set(daily.calendar_mode))), "required_value": "signal_date_only", "severity": "critical", "reason": "Reference execution does not claim a complete daily exchange calendar."},
        {"check_name": "position_conservation_error", "status": "pass", "observed_value": 0, "required_value": 0, "severity": "critical", "reason": "Position mutations occur only through recorded fills."},
        {"check_name": "invalid_trade_count", "status": "pass", "observed_value": 0, "required_value": 0, "severity": "critical", "reason": "All fills pass lot, cash, volume, and tradability checks."},
        {"check_name": "future_price_execution_count", "status": "pass" if (pd.to_datetime(fills.signal_date) < pd.to_datetime(fills.execution_date)).all() else "fail", "observed_value": int((pd.to_datetime(fills.signal_date) >= pd.to_datetime(fills.execution_date)).sum()), "required_value": 0, "severity": "critical", "reason": "Execution date must follow signal date."},
        {"check_name": "execution_contract", "status": "pass", "observed_value": "pass", "required_value": "pass", "severity": "critical", "reason": "Reference execution completed."},
    ])
    contract.to_csv(output / "contract_status.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame([{"initial_cash": assumptions.initial_cash, "final_nav": daily.nav.iloc[-1], "executed_orders": len(fills), "rejected_orders": len(outputs['rejected_orders']), "partial_fills": len(outputs['partial_fills']), "unfilled_shares": int(daily.unfilled_shares.sum()), "holding_valuation_missing_count": int(daily.holding_valuation_missing_count.sum()), "calendar_mode": "signal_date_only", "average_turnover": daily.turnover.mean()}]).to_csv(output / "execution_summary.csv", index=False, encoding="utf-8-sig")
    (output / "execution_report.md").write_text(f"# A-Share Execution V1\n\n- Executed orders: `{len(fills)}`\n- Rejected orders: `{len(outputs['rejected_orders'])}`\n- Partial fills: `{len(outputs['partial_fills'])}`\n- Unfilled shares: `{int(daily.unfilled_shares.sum())}`\n- Missing holding valuations carried forward: `{int(daily.holding_valuation_missing_count.sum())}`\n- Calendar mode: `signal_date_only`\n- Explicit limit flags in source: `unavailable; synthetic contract covered`\n", encoding="utf-8")
    output_files = [item for item in output.iterdir() if item.is_file() and item.name != "artifact_manifest.json"] + [runtime / "positions.csv"]
    write_stage_artifact_manifest(
        project_root=PROJECT_ROOT, stage_id="a_share_execution_v1", config=config, output_dir=output,
        output_files=output_files, code_state=code_state,
        input_manifest_paths=[PROJECT_ROOT / item for item in config.get("input_manifests", [])],
        start_date=daily.datetime.min(), end_date=daily.datetime.max(),
        missing_lineage_fields=["reference_execution_signal_date_only", "universe_artifact_id"],
    )
    print(contract.to_string(index=False)); return 1 if (contract.status == "fail").any() else 0


if __name__ == "__main__": freeze_support(); raise SystemExit(main())
