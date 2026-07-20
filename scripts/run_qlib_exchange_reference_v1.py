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
from qlib_integration.reference_data import QLIB_FIELDS, build_reference_frames  # noqa: E402
from qlib_integration.runner import run_qlib_execution  # noqa: E402
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
    "selected_instruments.csv",
    "signal_input.csv",
    "tradability_diagnostics.csv",
    "transaction_costs.csv",
]


def resolve(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else (PROJECT_ROOT / path).resolve()


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a transparent-score local-reference Qlib execution.")
    parser.add_argument("--config", type=Path, default=Path("configs/qlib_exchange_reference_v1.yaml"))
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
    history_calendar = pd.DatetimeIndex(
        D.calendar(start_time=config["history_start_date"], end_time=config["end_date"], freq="day")
    )
    required = int(config["trading_day_count"]) + int(config["momentum_lookback"])
    if len(history_calendar) < required:
        raise ValueError(f"provider returned {len(history_calendar)} dates; need at least {required}")
    history_calendar = history_calendar[-required:]
    execution_calendar = history_calendar[-int(config["trading_day_count"]):]
    candidates = sorted(
        instrument
        for instrument in D.list_instruments(
            D.instruments("all"), start_time=history_calendar.min(), end_time=history_calendar.max(), as_list=True
        )
        if str(instrument).startswith(("SH", "SZ"))
    )[: int(config["candidate_limit"])]
    features = D.features(
        candidates,
        QLIB_FIELDS,
        start_time=history_calendar.min(),
        end_time=history_calendar.max(),
        freq="day",
    )
    signal, market, selected = build_reference_frames(
        features,
        history_calendar,
        execution_calendar,
        instrument_count=int(config["instrument_count"]),
        momentum_lookback=int(config["momentum_lookback"]),
        limit_threshold=float(config["limit_threshold_approximation"]),
        profile_name=str(config["profile_name"]),
        research_run_family_id=str(config["research_run_family_id"]),
    )
    signal = validate_signal_frame(signal)
    market = validate_market_frame(market)
    result = run_qlib_execution(signal, market, config)
    fills = result["fills"]
    daily = result["daily_accounting"]
    market_fills = fills.merge(market[["datetime", "instrument", "volume"]], on=["datetime", "instrument"], how="left")
    participation_excess = (
        market_fills["executed_shares"] - market_fills["volume"] * float(config["max_participation_rate"])
    )
    participation_valid = market_fills.empty or bool(participation_excess.le(0.1).all())
    buys = fills.loc[fills["side"].eq("buy")]
    lot_remainder = buys["executed_shares"].mod(int(config["lot_size"])) if not buys.empty else pd.Series(dtype=float)
    lot_valid = buys.empty or bool(
        pd.concat([lot_remainder, int(config["lot_size"]) - lot_remainder], axis=1).min(axis=1).le(1e-6).all()
    )
    operational_checks = [
        contract_row("signal_schema_valid", True, len(signal), ">0"),
        contract_row("market_schema_valid", True, len(market), ">0"),
        contract_row("instrument_count", len(selected) == int(config["instrument_count"]), len(selected), config["instrument_count"]),
        contract_row("complete_trading_calendar", bool(daily["calendar_complete"].all()) and len(daily) == len(execution_calendar) - 1, len(daily), len(execution_calendar) - 1),
        contract_row("no_future_price_execution", int(config["signal_lag_trading_days"]) == 1, config["signal_lag_trading_days"], 1),
        contract_row("lot_size_valid", lot_valid, lot_valid, True),
        contract_row("cash_non_negative", float(daily["cash"].min()) >= -1e-8, float(daily["cash"].min()), ">=0"),
        contract_row("accounting_conservation", float(daily["accounting_error"].abs().max()) <= 1e-8, float(daily["accounting_error"].abs().max()), "<=1e-8"),
        contract_row("volume_participation_respected", participation_valid, participation_valid, True),
        contract_row("target_delta_orders_supported", {"buy", "sell"}.issubset(set(fills["side"])), sorted(set(fills["side"])), ["buy", "sell"]),
        contract_row("reference_execution_operational", not fills.empty, len(fills), ">0"),
    ]
    capability_checks = [
        contract_row("tradability_source_complete", bool(config["tradability_source_complete"]), config["tradability_source_complete"], True, "provider lacks authoritative historical suspension and directional limit labels; change/volume proxies are disclosed", "capability"),
        contract_row("pit_universe_complete", bool(config["pit_universe_complete"]), config["pit_universe_complete"], True, "coverage-selected sample is execution evidence, not a PIT research universe", "capability"),
    ]
    contract = pd.DataFrame(operational_checks + capability_checks)
    operational_ready = not contract.loc[contract["severity"].eq("critical"), "status"].eq("blocked").any()
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
            "daily_accounting.csv": daily,
            "execution_summary.csv": result["execution_summary"],
            "fills.csv": fills,
            "market_input.csv": market,
            "orders.csv": result["orders"],
            "partial_fills.csv": result["partial_fills"],
            "positions.csv": result["positions"],
            "rejected_orders.csv": result["rejected_orders"],
            "selected_instruments.csv": pd.DataFrame({"instrument": selected}),
            "signal_input.csv": signal,
            "tradability_diagnostics.csv": tradability,
            "transaction_costs.csv": result["transaction_costs"],
        }
        for name, frame in tables.items():
            frame.to_csv(publisher.path(name), index=False, encoding="utf-8-sig")
        publisher.path("resolved_config.json").write_text(
            json.dumps(config, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8"
        )
        publisher.path("execution_report.md").write_text(
            "# Qlib Exchange V1 Local Reference Execution\n\n"
            f"- Operational status: `{'pass' if operational_ready else 'blocked'}`\n"
            f"- Reference readiness: `blocked_incomplete_tradability_and_pit_universe`\n"
            f"- Instruments: `{len(selected)}`\n"
            f"- Trading days: `{len(execution_calendar)}`\n"
            f"- Orders / fills: `{len(result['orders'])}` / `{len(fills)}`\n"
            "- Signal: transparent trailing momentum, observed at t close and executed at t+1 open.\n"
            "- Unit semantics: the public schema uses original prices/raw shares; the adapter converts to and from Qlib adjusted units.\n"
            "- Tradability limitation: suspension and price-limit flags are volume/change proxies, not authoritative PIT labels.\n",
            encoding="utf-8",
        )
        files = [publisher.path(name) for name in CONTROLLED if name != "artifact_manifest.json"]
        write_stage_artifact_manifest(
            project_root=PROJECT_ROOT,
            stage_id="qlib_exchange_reference_v1",
            config=config,
            output_dir=publisher.staging_dir,
            output_files=files,
            code_state=code_state,
            input_manifest_paths=[environment_manifest],
            factor_frame_id=content_reference_id("execution-input", [publisher.path("signal_input.csv")]),
            start_date=execution_calendar.min(),
            end_date=execution_calendar.max(),
            missing_lineage_fields=["pit_universe_artifact", "authoritative_historical_tradability"],
            lineage_status="reference_only",
            artifact_status="pass" if operational_ready else "blocked",
            blocked_reason="" if operational_ready else "blocked_qlib_reference_execution_contract",
        )
        publisher.publish()
    print(contract.to_string(index=False))
    return 0 if operational_ready else 2


if __name__ == "__main__":
    raise SystemExit(main())
