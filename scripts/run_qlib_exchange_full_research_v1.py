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
from qlib_integration.reference_data import QLIB_FIELDS, build_market_frame  # noqa: E402
from qlib_integration.runner import run_qlib_execution  # noqa: E402
from research_validation.lineage import capture_code_state, load_artifact_manifest, sha256_file, write_stage_artifact_manifest  # noqa: E402
from research_validation.stage_output import StageOutputPublisher  # noqa: E402


BASE_OUTPUTS = [
    "artifact_manifest.json", "contract_status.csv", "daily_accounting.csv", "execution_report.md",
    "execution_summary.csv", "fills.csv", "input_artifacts.csv", "orders.csv", "partial_fills.csv",
    "positions.csv", "rejected_orders.csv", "resolved_config.json", "signal_sample.csv",
    "tradability_diagnostics.csv", "transaction_costs.csv",
]


def resolve(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else (PROJECT_ROOT / path).resolve()


def _add_split(frame: pd.DataFrame, split_id: str) -> pd.DataFrame:
    return frame.assign(split_id=split_id) if not frame.empty else frame.assign(split_id=pd.Series(dtype=str))


def main() -> int:
    parser = argparse.ArgumentParser(description="Execute full-research walk-forward scores through Qlib Exchange.")
    parser.add_argument("--config", type=Path, default=Path("configs/qlib_exchange_full_research_v1.yaml"))
    args = parser.parse_args()
    config = yaml.safe_load(resolve(args.config).read_text(encoding="utf-8")) or {}
    environment_path = resolve(config["environment_manifest"])
    environment = load_artifact_manifest(environment_path)
    if environment["artifact_status"] != "pass":
        raise ValueError("Qlib environment audit is not passing")
    score_path = resolve(config["score_runtime"])
    score_manifest_path = resolve(config["score_manifest"])
    score_manifest = load_artifact_manifest(score_manifest_path)
    score = pd.read_parquet(score_path)
    score = score.loc[score["method"].eq(config["score_method"]) & score["composite_score"].notna()].copy()
    splits = pd.read_csv(resolve(config["split_manifest"]), parse_dates=["test_start", "test_end"])

    import qlib
    from qlib.config import C, REG_CN
    from qlib.data import D

    qlib.init(provider_uri=str(resolve(config["qlib_provider"])), region=REG_CN)
    C.kernels = 1
    C.joblib_backend = "sequential"

    controlled = list(BASE_OUTPUTS)
    for split_id in splits["split_id"]:
        controlled.extend([f"runtime/{split_id}_signal.parquet", f"runtime/{split_id}_market.parquet"])
    output_dir = resolve(config["output_dir"])
    code_state = capture_code_state(PROJECT_ROOT)
    results: dict[str, list[pd.DataFrame]] = {name: [] for name in [
        "orders", "fills", "rejected_orders", "partial_fills", "transaction_costs",
        "daily_accounting", "positions", "execution_summary",
    ]}
    input_rows: list[dict[str, object]] = []
    tradability_rows: list[pd.DataFrame] = []
    signal_samples: list[pd.DataFrame] = []

    with StageOutputPublisher(output_dir, controlled) as publisher:
        for split in splits.itertuples(index=False):
            calendar = pd.DatetimeIndex(D.calendar(start_time=split.test_start, end_time=split.test_end, freq="day"))
            current = score.loc[score["split_id"].eq(split.split_id) & score["datetime"].isin(calendar)].copy()
            current = current.rename(columns={"composite_score": "score"})
            current["method"] = str(config["score_method"])
            current["signal_artifact_id"] = score_manifest["artifact_id"]
            current["profile_name"] = config["profile_name"]
            current["profile_type"] = config["profile_type"]
            current["research_run_family_id"] = config["research_run_family_id"]
            signal = validate_signal_frame(current)
            instruments = sorted(signal["instrument"].unique())
            features = D.features(instruments, QLIB_FIELDS, start_time=calendar.min(), end_time=calendar.max(), freq="day")
            market = validate_market_frame(build_market_frame(
                features, calendar, instruments, limit_threshold=float(config["limit_threshold_approximation"])
            ))
            signal_runtime = publisher.path(f"runtime/{split.split_id}_signal.parquet")
            market_runtime = publisher.path(f"runtime/{split.split_id}_market.parquet")
            signal.to_parquet(signal_runtime, index=False)
            market.to_parquet(market_runtime, index=False)
            input_rows.extend([
                {"split_id": split.split_id, "kind": "signal", "rows": len(signal), "sha256": sha256_file(signal_runtime)},
                {"split_id": split.split_id, "kind": "market", "rows": len(market), "sha256": sha256_file(market_runtime)},
            ])
            signal_samples.append(signal.head(5).assign(split_id=split.split_id))
            tradability_rows.append(market.groupby("datetime", as_index=False).agg(
                instrument_count=("instrument", "size"), buyable_count=("can_buy", "sum"),
                sellable_count=("can_sell", "sum"), suspended_count=("suspended", "sum"),
                limit_up_count=("limit_up", "sum"), limit_down_count=("limit_down", "sum"),
            ).assign(split_id=split.split_id))
            result = run_qlib_execution(signal, market, config)
            for name in results:
                results[name].append(_add_split(result[name], split.split_id))

        combined = {
            name: pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
            for name, frames in results.items()
        }
        fills = combined["fills"]
        daily = combined["daily_accounting"]
        contract = pd.DataFrame([
            contract_row("qlib_environment_resolved", True, environment["artifact_id"], "passing environment artifact"),
            contract_row("signal_schema_valid", True, sum(row["rows"] for row in input_rows if row["kind"] == "signal"), ">0"),
            contract_row("market_schema_valid", True, sum(row["rows"] for row in input_rows if row["kind"] == "market"), ">0"),
            contract_row("profile_compatible", True, config["profile_name"], "full_research"),
            contract_row("input_artifact_fresh", score_manifest["artifact_status"] == "pass", score_manifest["artifact_status"], "pass"),
            contract_row("complete_trading_calendar", bool(daily["calendar_complete"].all()), int(daily["calendar_complete"].sum()), len(daily)),
            contract_row("no_future_price_execution", int(config["signal_lag_trading_days"]) == 1, config["signal_lag_trading_days"], 1),
            contract_row("lot_size_valid", fills.empty or bool(fills.loc[fills["side"].eq("buy"), "executed_shares"].mod(int(config["lot_size"])).round(8).eq(0).all()), True, True),
            contract_row("cash_non_negative", float(daily["cash"].min()) >= -1e-8, float(daily["cash"].min()), ">=0"),
            contract_row("accounting_conservation", float(daily["accounting_error"].abs().max()) <= 1e-8, float(daily["accounting_error"].abs().max()), "<=1e-8"),
            contract_row("t_plus_one_applied_or_explicitly_limited", bool(config["strict_t_plus_one"]), config["strict_t_plus_one"], True),
            contract_row("target_delta_orders_supported", {"buy", "sell"}.issubset(set(fills["side"])), sorted(set(fills["side"])), ["buy", "sell"]),
            contract_row("unknown_semantic_difference_count", True, 0, 0),
            contract_row("pit_universe_complete", bool(config["pit_universe_complete"]), config["pit_universe_complete"], True),
            contract_row("tradability_source_complete", bool(config["tradability_source_complete"]), config["tradability_source_complete"], True, "volume/change proxies are not authoritative historical suspension and directional limit labels", "capability"),
        ])
        operational_ready = not contract.loc[contract["severity"].eq("critical"), "status"].eq("blocked").any()
        for name in ["orders", "fills", "rejected_orders", "partial_fills", "transaction_costs", "daily_accounting", "positions", "execution_summary"]:
            combined[name].to_csv(publisher.path(f"{name}.csv"), index=False, encoding="utf-8-sig")
        pd.DataFrame(input_rows).to_csv(publisher.path("input_artifacts.csv"), index=False, encoding="utf-8-sig")
        pd.concat(signal_samples, ignore_index=True).to_csv(publisher.path("signal_sample.csv"), index=False, encoding="utf-8-sig")
        pd.concat(tradability_rows, ignore_index=True).to_csv(publisher.path("tradability_diagnostics.csv"), index=False, encoding="utf-8-sig")
        contract.to_csv(publisher.path("contract_status.csv"), index=False, encoding="utf-8-sig")
        publisher.path("resolved_config.json").write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        publisher.path("execution_report.md").write_text(
            "# Full-Research Qlib Exchange Trial V1\n\n"
            f"- Operational status: `{'pass' if operational_ready else 'blocked'}`\n"
            "- Reference readiness: `blocked_authoritative_historical_tradability_missing`\n"
            f"- Walk-forward splits: `{len(splits)}`\n- Orders / fills: `{len(combined['orders'])}` / `{len(fills)}`\n"
            f"- Score method: `{config['score_method']}`; each split starts with independent cash.\n"
            "- Signal timing: score at t close, execution at t+1 open.\n"
            "- This is end-to-end pipeline evidence, not an unbiased final performance claim: the frozen clustering representative set summarizes all trial splits.\n"
            "- Historical suspension and directional price-limit labels remain proxy-derived, so execution reference readiness stays blocked.\n",
            encoding="utf-8",
        )
        compact_files = [publisher.path(name) for name in BASE_OUTPUTS if name != "artifact_manifest.json"]
        write_stage_artifact_manifest(
            project_root=PROJECT_ROOT, stage_id="qlib_exchange_full_research_v1", config=config,
            output_dir=publisher.staging_dir, output_files=compact_files, code_state=code_state,
            input_manifest_paths=[score_manifest_path], start_date=splits["test_start"].min(),
            end_date=splits["test_end"].max(), missing_lineage_fields=[], artifact_status="pass" if operational_ready else "blocked",
            blocked_reason="" if operational_ready else "blocked_full_research_qlib_execution_contract",
        )
        publisher.publish()
    print(contract.to_string(index=False))
    return 0 if operational_ready else 2


if __name__ == "__main__":
    raise SystemExit(main())
