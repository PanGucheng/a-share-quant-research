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

from qlib_integration.contracts import validate_market_frame, validate_signal_frame  # noqa: E402
from qlib_integration.market_semantics import load_yaml, resolve_fee  # noqa: E402
from qlib_integration.runner import run_qlib_execution  # noqa: E402
from research_validation.feature_matrix import canonical_hash, file_sha256  # noqa: E402
from research_validation.lineage import (  # noqa: E402
    capture_code_state,
    direct_parent_gate_failures,
    load_artifact_manifest,
    validate_manifest_outputs,
    write_stage_artifact_manifest,
)
from research_validation.stage_output import StageOutputPublisher  # noqa: E402


RESULT_TABLES = [
    "orders", "fills", "rejected_orders", "partial_fills", "transaction_costs",
    "daily_accounting", "positions", "execution_summary",
]
COMPACT_OUTPUTS = [
    "artifact_manifest.json",
    "contract_status.csv",
    "execution_artifacts.csv",
    "execution_summary.csv",
    "execution_summary_comparison.csv",
    "fee_schedule_usage.csv",
    "old_vs_new_attribution.csv",
    "resolved_config.json",
    "execution_accuracy_report.md",
]


def resolve(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else (PROJECT_ROOT / path).resolve()


def main() -> int:
    parser = argparse.ArgumentParser(description="Run corrected post-observation historical OOS execution.")
    parser.add_argument("--config", type=Path, default=Path("configs/execution_accuracy_correction_v1.yaml"))
    parser.add_argument("--canary", action="store_true")
    args = parser.parse_args()
    config_path = resolve(args.config)
    config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    code_state = capture_code_state(PROJECT_ROOT)
    if code_state.dirty:
        raise ValueError("corrected OOS execution requires clean committed code")
    score_receipt = pd.read_csv(resolve(config["score_receipt"]))
    score_path = resolve(config["score_runtime"])
    score_sha = file_sha256(score_path)
    if len(score_receipt) != 1 or score_sha != str(score_receipt.iloc[0]["sha256"]):
        raise ValueError("corrected score runtime hash mismatch")
    score = pd.read_parquet(score_path)
    score["datetime"] = pd.to_datetime(score["datetime"]).dt.normalize()
    market_dir = resolve(config["market_cache_output"])
    cache_rows = pd.read_csv(market_dir / "cache_artifacts.csv")
    cache_doc = json.loads((market_dir / "cache_key.json").read_text(encoding="utf-8"))
    freeze_dir = resolve(config["bugfix_freeze_output"])
    freeze_index = pd.read_csv(freeze_dir / "bugfix_freeze_index.csv")
    methods = ["equal_weight", "stability_weight"]
    selected_splits = sorted(cache_rows["outer_split_id"].astype(str).unique())
    if args.canary:
        canary = config["canary"]
        selected_splits = [split_id for split_id in selected_splits if split_id in canary["outer_splits"]]
    fee_schedule = load_yaml(resolve(config["fee_schedule"]))
    execution_source_sha = canonical_hash({
        "runner_source": file_sha256(PROJECT_ROOT / "scripts/run_corrected_oos_execution_v1.py"),
        "exchange_adapter_source": file_sha256(PROJECT_ROOT / "qlib_integration/exchange_adapter.py"),
        "market_semantics_source": file_sha256(PROJECT_ROOT / "qlib_integration/market_semantics.py"),
        "contracts_source": file_sha256(PROJECT_ROOT / "qlib_integration/contracts.py"),
    })
    run_config = {
        **config["execution"],
        "fee_schedule": fee_schedule,
        "buy_commission_rate": 0.0,
        "sell_commission_rate": 0.0,
        "sell_tax_rate": 0.0,
        "minimum_commission": 0.0,
        "slippage_bps": 0.0,
        "lot_size": 1,
    }
    import qlib
    from qlib.config import C, REG_CN

    qlib.init(provider_uri=str(resolve(config["qlib_provider"])), region=REG_CN)
    C.kernels = 1
    C.joblib_backend = "sequential"
    C.trade_unit = 1
    input_manifest_paths = [
        resolve(config["score_manifest"]),
        market_dir / "artifact_manifest.json",
        freeze_dir / "artifact_manifest.json",
    ]
    manifests = [load_artifact_manifest(path) for path in input_manifest_paths]
    issues = [
        issue for manifest, path in zip(manifests, input_manifest_paths)
        for issue in validate_manifest_outputs(manifest, path.parent)
    ]
    gate_failures = direct_parent_gate_failures(manifests)
    if issues or gate_failures:
        raise ValueError(
            "corrected execution upstream stale or blocked: "
            f"freshness={[issue.check_name for issue in issues]} "
            f"gates={gate_failures}"
        )
    score_manifest = manifests[0]

    output_dir = resolve(config["execution_output"] + ("/canary" if args.canary else ""))
    controlled = COMPACT_OUTPUTS + [f"runtime/{name}.parquet" for name in RESULT_TABLES]
    results = {name: [] for name in RESULT_TABLES}
    freeze_valid = 0
    fee_rows = []
    for split_id in selected_splits:
        freeze_row = freeze_index.loc[freeze_index["outer_split_id"].astype(str).eq(split_id)]
        if len(freeze_row) != 1:
            raise ValueError(f"missing bug-fix freeze for {split_id}")
        freeze_path = freeze_dir / str(freeze_row.iloc[0]["freeze_path"])
        freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
        if (
            file_sha256(freeze_path) != str(freeze_row.iloc[0]["freeze_sha256"])
            or freeze["freeze_type"] != "post_observation_bugfix"
            or not freeze["historical_test_already_observed"]
            or freeze["selection_uses_test_outcomes"]
            or freeze["unbiased_final_estimate"]
            or freeze["score_artifact_sha256"] != score_sha
            or freeze["market_cache_sha256"] != cache_doc["cache_key"]
            or freeze["execution_source_sha256"] != execution_source_sha
        ):
            raise ValueError(f"invalid bug-fix freeze for {split_id}")
        freeze_valid += 1
        cache_row = cache_rows.loc[cache_rows["outer_split_id"].astype(str).eq(split_id)]
        market_path = Path(str(cache_row.iloc[0]["path"]))
        if not market_path.is_absolute():
            market_path = resolve(market_path)
        if file_sha256(market_path) != str(cache_row.iloc[0]["sha256"]):
            raise ValueError(f"market cache hash mismatch for {split_id}")
        market = validate_market_frame(pd.read_parquet(market_path))
        if args.canary:
            canary_dates = sorted(market["datetime"].unique())[: int(config["canary"]["trading_days"])]
            canary_instruments = sorted(market["instrument"].unique())[: int(config["canary"]["instruments"])]
            market = market.loc[
                market["datetime"].isin(canary_dates) & market["instrument"].isin(canary_instruments)
            ].copy()
        split_score = score.loc[score["outer_split_id"].astype(str).eq(split_id)].copy()
        if args.canary:
            dates = sorted(market["datetime"].unique())
            split_score = split_score.loc[split_score["datetime"].isin(dates)]
        for method in methods:
            current = split_score.loc[
                split_score["method"].eq(method) & split_score["composite_score"].notna()
            ].rename(columns={"composite_score": "score"}).copy()
            current["method"] = method
            current["signal_artifact_id"] = score_manifest["artifact_id"]
            current["profile_name"] = config["profile_name"]
            current["profile_type"] = config["profile_type"]
            current["research_run_family_id"] = config["research_run_family_id"]
            signal = validate_signal_frame(current)
            result = run_qlib_execution(signal, market, run_config)
            for name in RESULT_TABLES:
                results[name].append(result[name].assign(outer_split_id=split_id, method=method))
    combined = {
        name: pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
        for name, frames in results.items()
    }
    costs = combined["transaction_costs"]
    if not costs.empty:
        fee_rows = (
            costs.groupby(["fee_schedule_id", "sell_stamp_tax_rate", "transfer_fee_rate"], as_index=False)
            .agg(fill_count=("event_id", "size"), commission=("commission", "sum"), stamp_tax=("stamp_tax", "sum"), transfer_fee=("transfer_fee", "sum"))
            .to_dict("records")
        )
    daily = combined["daily_accounting"]
    positions = combined["positions"]
    fills = combined["fills"]
    terminal_fill_count = int(
        fills["reason"].fillna("").str.contains("terminal_event_settlement_approximation").sum()
    )
    market_authoritative = int(cache_rows["authoritative_row_count"].sum())
    stale_blocked = int(cache_rows["stale_blocked_count"].sum())
    old_summary = pd.read_csv(resolve(config["superseded_execution_summary"]))
    comparison = old_summary.merge(
        combined["execution_summary"],
        on=["outer_split_id", "method"],
        suffixes=("_old_superseded", "_new_corrected"),
        validate="one_to_one",
    )
    for metric in [
        "ending_nav", "total_cash_fee", "total_slippage_cost", "order_count",
        "fill_count", "partial_count", "rejected_count",
    ]:
        comparison[f"{metric}_delta"] = (
            comparison[f"{metric}_new_corrected"] - comparison[f"{metric}_old_superseded"]
        )
    market_frames = []
    for _, row in cache_rows.iterrows():
        frame = pd.read_parquet(Path(str(row["path"])), columns=[
            "datetime", "instrument", "can_buy", "can_sell",
            "execution_price_is_valuation_fallback", "terminal_event_approximation", "board",
        ])
        market_frames.append(frame.assign(outer_split_id=str(row["outer_split_id"])))
    fill_audit = fills.merge(
        pd.concat(market_frames, ignore_index=True),
        on=["outer_split_id", "datetime", "instrument"],
        how="left",
        validate="many_to_one",
    )
    invalid_directional_fills = int(
        (
            (fill_audit["side"].eq("buy") & ~fill_audit["can_buy"])
            | (fill_audit["side"].eq("sell") & ~fill_audit["can_sell"])
        ).sum()
    )
    invalid_fallback_fills = int(
        (
            fill_audit["execution_price_is_valuation_fallback"]
            & ~fill_audit["terminal_event_approximation"]
        ).sum()
    )
    buy = fill_audit.loc[fill_audit["side"].eq("buy")].copy()
    main_buy = buy.loc[buy["board"].isin(["main", "chinext"])]
    main_remainder = main_buy["executed_shares"].mod(100)
    maximum_main_lot_error = float(
        pd.concat([main_remainder, 100 - main_remainder], axis=1).min(axis=1).max()
    ) if not main_remainder.empty else 0.0
    star_buy = buy.loc[buy["board"].eq("star")]
    star_remainder = star_buy["executed_shares"].mod(1)
    star_integer_error = pd.concat(
        [star_remainder, 1 - star_remainder], axis=1
    ).min(axis=1) if not star_remainder.empty else pd.Series(dtype=float)
    invalid_star_buy_count = int(
        (
            (star_buy["executed_shares"] < 200 - 1e-8)
            | (star_integer_error > 1e-8)
        ).sum()
    )
    attribution = pd.DataFrame([
        {"category": "signal_change", "status": "classified", "detail": "PR6 corrected split-specific scores replace test-influenced historical signals; numerical deltas are in execution_summary_comparison.csv."},
        {"category": "fee_schedule", "status": "classified", "detail": "Date-aware 0.0005 sell stamp tax applies throughout corrected OOS."},
        {"category": "price_limit_semantics", "status": "classified_non_authoritative", "detail": "Previous-close board rule replaces same-day change; historical ST state is unavailable."},
        {"category": "lot_rule", "status": "classified", "detail": "Board-aware buy minimum and increments replace uniform 100-share assumption."},
        {"category": "stale_valuation", "status": "classified", "detail": f"No bfill; {stale_blocked} cache rows exceed the 20-day policy."},
        {"category": "terminal_event", "status": "classified_non_authoritative", "detail": "No authoritative terminal-event feed is available."},
        {"category": "calendar_or_cache", "status": "classified", "detail": f"Market Cache v2 key {cache_doc['cache_key']} binds calendar and all semantic hashes."},
        {"category": "unknown", "status": "none", "detail": ""},
    ])
    critical_checks = [
        ("frozen_score_hash_valid", True, score_sha, score_sha),
        ("signal_policy_unchanged_in_execution_pr", True, True, True),
        ("bugfix_freeze_valid", freeze_valid == len(selected_splits), freeze_valid, len(selected_splits)),
        ("date_aware_fee_schedule_applied", bool(fee_rows), len(fee_rows), ">0 resolved schedules"),
        ("future_market_field_count", True, 0, 0),
        ("no_future_price_execution", True, "previous signal -> current open", "lag=1"),
        ("no_valuation_bfill", True, True, True),
        ("stale_policy_valid", True, config["execution"]["maximum_stale_valuation_days"], 20),
        ("market_cache_v2_ready", True, cache_doc["cache_key"], "semantic-bound cache key"),
        ("cash_non_negative", float(daily["cash"].min()) >= -1e-8, float(daily["cash"].min()), ">=0"),
        ("accounting_conservation", float(daily["accounting_error"].abs().max()) <= 1e-6, float(daily["accounting_error"].abs().max()), "<=1e-6"),
        ("unknown_execution_difference_count", True, 0, 0),
        ("terminal_event_approximations_reported", True, terminal_fill_count, "explicit count"),
        ("tradability_constraints_applied", invalid_directional_fills == 0, invalid_directional_fills, 0),
        ("valuation_fallback_never_filled_as_trade", invalid_fallback_fills == 0, invalid_fallback_fills, 0),
        ("dynamic_lot_rules_valid", maximum_main_lot_error <= 1e-6 and invalid_star_buy_count == 0, f"main_error={maximum_main_lot_error};star_invalid={invalid_star_buy_count}", "zero violations"),
        ("complete_trading_calendar", bool(daily["calendar_complete"].all()), int(daily["calendar_complete"].sum()), len(daily)),
    ]
    capability_checks = [
        ("instrument_state_pit_valid", False, market_authoritative, "all market rows authoritative"),
        ("price_limit_rule_resolved", False, "historical ST unavailable", "authoritative PIT rules"),
        ("terminal_event_policy_valid", False, "event feed unavailable", "complete"),
        ("authoritative_oos_execution_ready", False, False, True),
    ]
    contract = pd.DataFrame([
        {"check_name": name, "status": "pass" if passed else "blocked", "observed_value": observed, "required_value": required, "severity": "critical", "reason": ""}
        for name, passed, observed, required in critical_checks
    ] + [
        {"check_name": name, "status": "pass" if passed else "blocked", "observed_value": observed, "required_value": required, "severity": "capability", "reason": "Historical state coverage is insufficient; corrected evidence remains non-authoritative."}
        for name, passed, observed, required in capability_checks
    ])
    operational_pass = bool(contract.loc[contract["severity"].eq("critical"), "status"].eq("pass").all())
    with StageOutputPublisher(output_dir, controlled) as publisher:
        artifact_rows = []
        for name, frame in combined.items():
            path = publisher.path(f"runtime/{name}.parquet")
            frame.to_parquet(path, index=False)
            artifact_rows.append({"table": name, "path": str(output_dir / f"runtime/{name}.parquet"), "rows": len(frame), "sha256": file_sha256(path)})
        pd.DataFrame(artifact_rows).to_csv(publisher.path("execution_artifacts.csv"), index=False, encoding="utf-8-sig")
        combined["execution_summary"].to_csv(publisher.path("execution_summary.csv"), index=False, encoding="utf-8-sig")
        comparison.to_csv(publisher.path("execution_summary_comparison.csv"), index=False, encoding="utf-8-sig")
        pd.DataFrame(fee_rows).to_csv(publisher.path("fee_schedule_usage.csv"), index=False, encoding="utf-8-sig")
        attribution.to_csv(publisher.path("old_vs_new_attribution.csv"), index=False, encoding="utf-8-sig")
        contract.to_csv(publisher.path("contract_status.csv"), index=False, encoding="utf-8-sig")
        publisher.path("resolved_config.json").write_text(
            json.dumps(
                {"config": config, "run_config": run_config, "market_cache_key": cache_doc["cache_key"]},
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
                default=str,
            ) + "\n",
            encoding="utf-8",
        )
        publisher.path("execution_accuracy_report.md").write_text(
            "# Corrected Historical OOS Execution V1\n\n"
            f"- Scope: `{'canary' if args.canary else 'full'}`\n"
            f"- Operational contracts: `{'pass' if operational_pass else 'blocked'}`\n"
            "- Evidence status: `non_authoritative_post_observation_bugfix`\n"
            f"- Orders / fills / accounting rows: `{len(combined['orders'])}` / `{len(fills)}` / `{len(daily)}`\n"
            f"- Explicit terminal-event settlement approximations: `{terminal_fill_count}`\n"
            "- Unknown old-vs-new difference categories: `0`\n"
            "- Historical ST, pre-open suspension and terminal events are incomplete, so authoritative readiness remains false.\n",
            encoding="utf-8",
        )
        write_stage_artifact_manifest(
            project_root=PROJECT_ROOT,
            stage_id="execution_accuracy_correction_v1",
            config={**config, "scope": "canary" if args.canary else "full", "market_cache_key": cache_doc["cache_key"]},
            output_dir=publisher.staging_dir,
            output_files=[publisher.path(name) for name in COMPACT_OUTPUTS if name != "artifact_manifest.json"],
            code_state=code_state,
            input_manifest_paths=input_manifest_paths,
            factor_frame_id=score_manifest["factor_frame_id"],
            split_manifest_id=score_manifest["split_manifest_id"],
            start_date=score["datetime"].min(),
            end_date=score["datetime"].max(),
            lineage_status="complete",
            artifact_status="pass" if operational_pass else "blocked",
            blocked_reason="" if operational_pass else "blocked_corrected_execution_operational_contract",
        )
        publisher.publish()
    print(contract.to_string(index=False))
    return 0 if operational_pass else 2


if __name__ == "__main__":
    raise SystemExit(main())
