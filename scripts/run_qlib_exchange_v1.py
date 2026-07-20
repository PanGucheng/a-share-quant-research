from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd
import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from qlib_integration.contracts import contract_row, validate_market_frame, validate_signal_frame  # noqa: E402
from qlib_integration.runner import run_qlib_execution  # noqa: E402
from qlib_integration.synthetic import build_synthetic_frames  # noqa: E402
from research_validation.lineage import capture_code_state, content_reference_id, write_stage_artifact_manifest  # noqa: E402
from research_validation.stage_output import StageOutputPublisher  # noqa: E402


CONTROLLED = [
    "artifact_manifest.json",
    "contract_status.csv",
    "daily_accounting.csv",
    "execution_report.md",
    "execution_summary.csv",
    "fills.csv",
    "market_input.csv",
    "orders.csv",
    "partial_fills.csv",
    "positions.csv",
    "rejected_orders.csv",
    "resolved_config.json",
    "signal_input.csv",
    "target_positions.csv",
    "tradability_diagnostics.csv",
    "transaction_costs.csv",
]


def resolve(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else (PROJECT_ROOT / path).resolve()


def _target_positions(signal: pd.DataFrame, top_k: int) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for date, group in signal.groupby("datetime", sort=True):
        selected = group.sort_values(["score", "instrument"], ascending=[False, True]).head(top_k)
        weight = 1.0 / len(selected) if len(selected) else 0.0
        for instrument in selected["instrument"]:
            rows.append({"datetime": date, "instrument": instrument, "target_weight": weight})
    return pd.DataFrame(rows, columns=["datetime", "instrument", "target_weight"])


def _contracts(config: dict[str, object], signal: pd.DataFrame, market: pd.DataFrame, result: dict[str, pd.DataFrame]) -> pd.DataFrame:
    fills = result["fills"]
    daily = result["daily_accounting"]
    lot_valid = fills.empty or bool((fills["executed_shares"].round(8) % int(config["lot_size"]) < 1e-8).all())
    calendar_complete = bool(daily["calendar_complete"].all()) and len(daily) == int(config["trading_day_count"]) - 1
    accounting_error = float(daily["accounting_error"].abs().max()) if not daily.empty else float("inf")
    cash_min = float(daily["cash"].min()) if not daily.empty else float("-inf")
    merged = fills.merge(market[["datetime", "instrument", "volume"]], on=["datetime", "instrument"], how="left")
    participation_valid = merged.empty or bool(
        (merged["executed_shares"] <= merged["volume"] * float(config["max_participation_rate"]) + 1e-8).all()
    )
    target_delta_supported = bool({"buy", "sell"}.issubset(set(fills["side"])))
    rows = [
        contract_row("signal_schema_valid", True, len(signal), ">0"),
        contract_row("market_schema_valid", True, len(market), ">0"),
        contract_row("profile_compatible", signal["profile_name"].nunique() == 1, signal["profile_name"].unique().tolist(), "one profile"),
        contract_row("complete_trading_calendar", calendar_complete, len(daily), int(config["trading_day_count"]) - 1),
        contract_row("no_future_price_execution", int(config["signal_lag_trading_days"]) == 1, config["signal_lag_trading_days"], 1),
        contract_row("lot_size_valid", lot_valid, lot_valid, True),
        contract_row("cash_non_negative", cash_min >= -1e-8, cash_min, ">=0"),
        contract_row("accounting_conservation", accounting_error <= 1e-8, accounting_error, "<=1e-8"),
        contract_row("commission_and_tax_reported", {"commission", "stamp_tax", "slippage_cost"}.issubset(result["transaction_costs"].columns), list(result["transaction_costs"].columns), "component columns"),
        contract_row("tradability_constraints_applied", True, "directional prepared quote", "directional"),
        contract_row("t_plus_one_applied_or_explicitly_limited", bool(config["strict_t_plus_one"]), config["strict_t_plus_one"], True),
        contract_row("volume_participation_respected", participation_valid, participation_valid, True),
        contract_row("unfilled_quantities_reported", "unfilled_shares" in result["orders"].columns, "unfilled_shares" in result["orders"].columns, True),
        contract_row("target_delta_orders_supported", target_delta_supported, sorted(set(fills["side"])), ["buy", "sell"]),
        contract_row("synthetic_execution_complete", not fills.empty and calendar_complete, len(fills), ">0 and complete calendar"),
    ]
    return pd.DataFrame(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the Qlib Exchange V1 synthetic execution path.")
    parser.add_argument("--config", type=Path, default=Path("configs/qlib_exchange_synthetic_v1.yaml"))
    args = parser.parse_args()
    config = yaml.safe_load(resolve(args.config).read_text(encoding="utf-8")) or {}
    environment_manifest = resolve(config["environment_manifest"])
    if not environment_manifest.is_file():
        raise FileNotFoundError("run audit_qlib_environment_v1.py before Qlib execution")

    import qlib
    from qlib.config import C, REG_CN
    from qlib.data import D

    qlib.init(provider_uri=str(resolve(config["qlib_provider"])), region=REG_CN)
    C.kernels = 1
    C.joblib_backend = "sequential"
    full_calendar = pd.DatetimeIndex(
        D.calendar(start_time=config["start_date"], end_time=config["end_date"], freq="day")
    )
    calendar = full_calendar[: int(config["trading_day_count"])]
    if len(calendar) != int(config["trading_day_count"]):
        raise ValueError("provider does not contain the configured synthetic trading-day count")
    signal, market = build_synthetic_frames(calendar, list(config["instruments"]))
    signal = validate_signal_frame(signal)
    market = validate_market_frame(market)
    result = run_qlib_execution(signal, market, config)
    contract = _contracts(config, signal, market, result)
    ready = not contract["status"].eq("blocked").any()
    targets = _target_positions(signal, int(config["top_k"]))
    tradability = market.groupby("datetime", as_index=False).agg(
        instrument_count=("instrument", "size"),
        buyable_count=("can_buy", "sum"),
        sellable_count=("can_sell", "sum"),
        suspended_count=("suspended", "sum"),
        limit_up_count=("limit_up", "sum"),
        limit_down_count=("limit_down", "sum"),
    )
    output_dir = resolve(config["output_dir"])
    code_state = capture_code_state(PROJECT_ROOT)
    with StageOutputPublisher(output_dir, CONTROLLED) as publisher:
        tables = {
            "contract_status.csv": contract,
            "daily_accounting.csv": result["daily_accounting"],
            "execution_summary.csv": result["execution_summary"],
            "fills.csv": result["fills"],
            "market_input.csv": market,
            "orders.csv": result["orders"],
            "partial_fills.csv": result["partial_fills"],
            "positions.csv": result["positions"],
            "rejected_orders.csv": result["rejected_orders"],
            "signal_input.csv": signal,
            "target_positions.csv": targets,
            "tradability_diagnostics.csv": tradability,
            "transaction_costs.csv": result["transaction_costs"],
        }
        for name, frame in tables.items():
            frame.to_csv(publisher.path(name), index=False, encoding="utf-8-sig")
        publisher.path("resolved_config.json").write_text(
            json.dumps(config, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8"
        )
        publisher.path("execution_report.md").write_text(
            "# Qlib Exchange V1 Synthetic Execution\n\n"
            f"- Status: `{'pass' if ready else 'blocked'}`\n"
            f"- Trading days: `{len(calendar)}`\n"
            f"- Orders: `{len(result['orders'])}`\n"
            f"- Fills: `{len(result['fills'])}`\n"
            f"- Strict T+1 adapter: `{str(config['strict_t_plus_one']).lower()}`\n"
            f"- Target-delta buy and sell observed: `{str({'buy', 'sell'}.issubset(set(result['fills']['side']))).lower()}`\n",
            encoding="utf-8",
        )
        files = [publisher.path(name) for name in CONTROLLED if name != "artifact_manifest.json"]
        write_stage_artifact_manifest(
            project_root=PROJECT_ROOT,
            stage_id="qlib_exchange_v1",
            config=config,
            output_dir=publisher.staging_dir,
            output_files=files,
            code_state=code_state,
            input_manifest_paths=[environment_manifest],
            factor_frame_id=content_reference_id("execution-input", [publisher.path("signal_input.csv")]),
            start_date=calendar.min(),
            end_date=calendar.max(),
            missing_lineage_fields=["synthetic_universe_no_pit_artifact"],
            lineage_status="reference_only",
            artifact_status="pass" if ready else "blocked",
            blocked_reason="" if ready else "blocked_qlib_synthetic_contract",
        )
        publisher.publish()
    print(contract.to_string(index=False))
    return 0 if ready else 2


if __name__ == "__main__":
    raise SystemExit(main())
