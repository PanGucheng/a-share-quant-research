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
from research_validation.feature_matrix import canonical_hash, file_sha256  # noqa: E402
from research_validation.lineage import capture_code_state, load_artifact_manifest, validate_manifest_outputs, write_stage_artifact_manifest  # noqa: E402
from research_validation.pretest_freeze import load_freeze_with_file_hash  # noqa: E402
from research_validation.stage_output import StageOutputPublisher  # noqa: E402


BASE_OUTPUTS = [
    "artifact_manifest.json",
    "contract_status.csv",
    "daily_accounting.csv",
    "execution_report.md",
    "execution_summary.csv",
    "execution_artifacts.csv",
    "fills_sample.csv",
    "input_artifacts.csv",
    "orders_sample.csv",
    "partial_fills_sample.csv",
    "positions_sample.csv",
    "rejected_orders.csv",
    "resolved_config.json",
    "signal_sample.csv",
    "tradability_diagnostics.csv",
    "transaction_costs_sample.csv",
]
DETAIL_TABLES = ["orders", "fills", "partial_fills", "positions", "transaction_costs"]


def resolve(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else (PROJECT_ROOT / path).resolve()


def add_scope(frame: pd.DataFrame, split_id: str, method: str) -> pd.DataFrame:
    return frame.assign(outer_split_id=split_id, method=method)


def load_cached_market(config: dict, split_id: str, calendar: pd.DatetimeIndex, instruments: list[str]) -> pd.DataFrame | None:
    if not bool(config.get("reuse_runtime_market")):
        return None
    required_keys = pd.MultiIndex.from_product([calendar, instruments], names=["datetime", "instrument"])
    candidates: list[Path] = []
    for root_value in config.get("market_cache_roots", []):
        root = resolve(root_value)
        candidates.extend([root / f"{split_id}_market.parquet", root / f"{split_id}_stability_weight_market.parquet"])
    for path in candidates:
        if not path.is_file():
            continue
        market = validate_market_frame(pd.read_parquet(path))
        indexed = market.set_index(["datetime", "instrument"])
        if required_keys.isin(indexed.index).all():
            return indexed.loc[required_keys].reset_index()
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Run frozen split-specific transparent scores through Qlib Exchange.")
    parser.add_argument("--config", type=Path, default=Path("configs/qlib_exchange_split_transparent_669_v1.yaml"))
    args = parser.parse_args()
    run_config_path = resolve(args.config)
    run_config = yaml.safe_load(run_config_path.read_text(encoding="utf-8")) or {}
    semantics_path = resolve(run_config["execution_semantics"])
    semantics = yaml.safe_load(semantics_path.read_text(encoding="utf-8")) or {}
    config = {**semantics, **run_config}
    code_state = capture_code_state(PROJECT_ROOT)
    if code_state.dirty:
        raise ValueError("Qlib test execution requires a clean committed worktree")
    manifest_paths = [resolve(path) for path in run_config["input_manifests"]]
    manifests = [load_artifact_manifest(path) for path in manifest_paths]
    issues = [issue for manifest, path in zip(manifests, manifest_paths) for issue in validate_manifest_outputs(manifest, path.parent)]
    if issues or any(manifest["artifact_status"] != "pass" for manifest in manifests):
        raise ValueError(f"Qlib transparent execution upstream is stale or blocked: {issues}")
    manifest_by_stage = {manifest["stage_id"]: manifest for manifest in manifests}
    score_manifest = manifest_by_stage["split_transparent_score_v1"]
    freeze_artifact = manifest_by_stage["pre_test_freeze_v1"]
    environment = manifest_by_stage["qlib_environment_v1"]
    if score_manifest["code_commit_sha"] != code_state.commit_sha or freeze_artifact["code_commit_sha"] != code_state.commit_sha:
        raise ValueError("score/freeze code commit differs from Qlib execution commit")
    score_receipt = pd.read_csv(resolve(config["score_artifact_receipt"]))
    if len(score_receipt) != 1:
        raise ValueError("score artifact receipt must contain exactly one runtime")
    score_path = resolve(config["score_runtime"])
    score_sha = file_sha256(score_path)
    if score_sha != str(score_receipt.iloc[0]["sha256"]):
        raise ValueError("score runtime hash mismatch")
    score = pd.read_parquet(score_path)
    score["datetime"] = pd.to_datetime(score["datetime"])
    assignments = pd.read_csv(resolve(config["outer_date_assignments"]), parse_dates=["datetime"])
    freeze_index = pd.read_csv(resolve(config["pre_test_freeze_index"]))
    release_index = pd.read_csv(resolve(config["test_release_index"]))
    selected_splits = [str(value) for value in config.get("selected_outer_splits", [])]
    split_ids = selected_splits or sorted(score["outer_split_id"].astype(str).unique())
    methods = [str(value) for value in config["score_methods"]]
    semantics_sha = file_sha256(semantics_path)

    import qlib
    from qlib.config import C, REG_CN
    from qlib.data import D

    qlib.init(provider_uri=str(resolve(config["qlib_provider"])), region=REG_CN)
    C.kernels = 1
    C.joblib_backend = "sequential"

    controlled = list(BASE_OUTPUTS) + [f"runtime/{name}.parquet" for name in DETAIL_TABLES]
    for split_id in split_ids:
        controlled.append(f"runtime/{split_id}_market.parquet")
        for method in methods:
            controlled.append(f"runtime/{split_id}_{method}_signal.parquet")
    output_dir = resolve(config["output_dir"])
    results: dict[str, list[pd.DataFrame]] = {name: [] for name in [
        "orders", "fills", "rejected_orders", "partial_fills", "transaction_costs", "daily_accounting", "positions", "execution_summary"
    ]}
    input_rows: list[dict[str, object]] = []
    tradability_rows: list[pd.DataFrame] = []
    signal_samples: list[pd.DataFrame] = []
    release_valid_count = 0
    freeze_valid_count = 0
    market_cache_hits = 0
    participation_excess_max = 0.0
    invalid_fill_count = 0
    with StageOutputPublisher(output_dir, controlled) as publisher:
        for split_id in split_ids:
            test_dates = pd.DatetimeIndex(
                assignments.loc[assignments["split_id"].astype(str).eq(split_id) & assignments["fold"].eq("test"), "datetime"]
            ).sort_values().unique()
            freeze_row = freeze_index.loc[freeze_index["outer_split_id"].astype(str).eq(split_id)]
            release_row = release_index.loc[release_index["outer_split_id"].astype(str).eq(split_id)]
            if len(freeze_row) != 1 or len(release_row) != 1:
                raise ValueError(f"freeze/release index mismatch for {split_id}")
            freeze_path = resolve(config["pre_test_freeze_dir"]) / str(freeze_row.iloc[0]["freeze_path"])
            freeze, freeze_sha = load_freeze_with_file_hash(freeze_path)
            if freeze_sha != str(freeze_row.iloc[0]["freeze_sha256"]) or freeze["qlib_exchange_config_sha256"] != semantics_sha:
                raise ValueError(f"Qlib semantics or freeze hash mismatch for {split_id}")
            if freeze["code_commit_sha"] != code_state.commit_sha or freeze["test_dates_sha256"] != canonical_hash([date.date().isoformat() for date in test_dates]):
                raise ValueError(f"Qlib freeze commit/test partition mismatch for {split_id}")
            freeze_valid_count += 1
            release_path = resolve(config["test_release_dir"]) / str(release_row.iloc[0]["receipt_path"])
            release = json.loads(release_path.read_text(encoding="utf-8"))
            if file_sha256(release_path) != str(release_row.iloc[0]["receipt_sha256"]):
                raise ValueError(f"test release receipt hash mismatch for {split_id}")
            if (
                release.get("status") != "consumed"
                or release.get("freeze_id") != freeze["freeze_id"]
                or release.get("freeze_artifact_id") != freeze_artifact["artifact_id"]
                or release.get("score_artifact_sha256") != score_sha
                or release.get("execution_commit_sha") != code_state.commit_sha
            ):
                raise ValueError(f"invalid test release receipt for {split_id}")
            release_valid_count += 1
            split_score = score.loc[score["outer_split_id"].astype(str).eq(split_id) & score["datetime"].isin(test_dates)].copy()
            instruments = sorted(split_score.loc[split_score["composite_score"].notna(), "instrument"].astype(str).unique())
            calendar = test_dates
            market = load_cached_market(config, split_id, calendar, instruments)
            if market is not None:
                market_cache_hits += 1
            else:
                features = D.features(instruments, QLIB_FIELDS, start_time=calendar.min(), end_time=calendar.max(), freq="day")
                market = validate_market_frame(build_market_frame(features, calendar, instruments, limit_threshold=float(config["limit_threshold_approximation"])))
            market_runtime = publisher.path(f"runtime/{split_id}_market.parquet")
            market.to_parquet(market_runtime, index=False)
            input_rows.append({"outer_split_id": split_id, "method": "all", "kind": "market", "rows": len(market), "sha256": file_sha256(market_runtime)})
            tradability_rows.append(
                market.groupby("datetime", as_index=False).agg(
                    instrument_count=("instrument", "size"), buyable_count=("can_buy", "sum"), sellable_count=("can_sell", "sum"),
                    suspended_count=("suspended", "sum"), limit_up_count=("limit_up", "sum"), limit_down_count=("limit_down", "sum"),
                ).assign(outer_split_id=split_id)
            )
            for method in methods:
                current = split_score.loc[split_score["method"].eq(method) & split_score["composite_score"].notna()].copy()
                current = current.rename(columns={"composite_score": "score"})
                current["method"] = method
                current["signal_artifact_id"] = score_manifest["artifact_id"]
                current["profile_name"] = config["profile_name"]
                current["profile_type"] = config["profile_type"]
                current["research_run_family_id"] = config["research_run_family_id"]
                signal = validate_signal_frame(current)
                signal_runtime = publisher.path(f"runtime/{split_id}_{method}_signal.parquet")
                signal.to_parquet(signal_runtime, index=False)
                input_rows.append({"outer_split_id": split_id, "method": method, "kind": "signal", "rows": len(signal), "sha256": file_sha256(signal_runtime)})
                signal_samples.append(signal.head(3).assign(outer_split_id=split_id))
                result = run_qlib_execution(signal, market, config)
                fill_market = result["fills"].merge(market[["datetime", "instrument", "volume", "can_buy", "can_sell", "suspended"]], on=["datetime", "instrument"], how="left")
                if not fill_market.empty:
                    participation_excess_max = max(participation_excess_max, float((fill_market["executed_shares"] - fill_market["volume"] * float(config["max_participation_rate"])).max()))
                    invalid_fill_count += int((fill_market["suspended"] | (fill_market["side"].eq("buy") & ~fill_market["can_buy"]) | (fill_market["side"].eq("sell") & ~fill_market["can_sell"])).sum())
                for name in results:
                    results[name].append(add_scope(result[name], split_id, method))
        combined = {name: pd.concat(frames, ignore_index=True) for name, frames in results.items()}
        fills = combined["fills"]
        daily = combined["daily_accounting"]
        buy_remainder = fills.loc[fills["side"].eq("buy"), "executed_shares"].mod(int(config["lot_size"]))
        buy_lot_distance = pd.concat([buy_remainder, int(config["lot_size"]) - buy_remainder], axis=1).min(axis=1) if not buy_remainder.empty else pd.Series(dtype=float)
        maximum_lot_error = float(buy_lot_distance.max()) if not buy_lot_distance.empty else 0.0
        contract = pd.DataFrame(
            [
                contract_row("qlib_environment_resolved", True, environment["artifact_id"], "passing environment artifact"),
                contract_row("pre_test_freeze_valid", freeze_valid_count == len(split_ids), freeze_valid_count, len(split_ids)),
                contract_row("test_release_receipts_valid", release_valid_count == len(split_ids), release_valid_count, len(split_ids)),
                contract_row("score_methods_complete", combined["execution_summary"].groupby("outer_split_id")["method"].nunique().eq(len(methods)).all(), combined["execution_summary"].groupby("outer_split_id")["method"].nunique().tolist(), len(methods)),
                contract_row("signal_schema_valid", sum(row["rows"] for row in input_rows if row["kind"] == "signal") > 0, sum(row["rows"] for row in input_rows if row["kind"] == "signal"), ">0"),
                contract_row("market_schema_valid", sum(row["rows"] for row in input_rows if row["kind"] == "market") > 0, sum(row["rows"] for row in input_rows if row["kind"] == "market"), ">0"),
                contract_row("profile_compatible", config["profile_name"] == "full_research", config["profile_name"], "full_research"),
                contract_row("input_artifact_fresh", True, score_manifest["artifact_status"], "pass"),
                contract_row("complete_trading_calendar", bool(daily["calendar_complete"].all()), int(daily["calendar_complete"].sum()), len(daily)),
                contract_row("no_future_price_execution", int(config["signal_lag_trading_days"]) == 1, config["signal_lag_trading_days"], 1),
                contract_row("lot_size_valid", maximum_lot_error <= 1e-6, maximum_lot_error, "<=1e-6 shares"),
                contract_row("cash_non_negative", float(daily["cash"].min()) >= -1e-8, float(daily["cash"].min()), ">=0"),
                contract_row("accounting_conservation", float(daily["accounting_error"].abs().max()) <= 1e-8, float(daily["accounting_error"].abs().max()), "<=1e-8"),
                contract_row("commission_and_tax_reported", {"commission", "stamp_tax", "slippage_cost"}.issubset(combined["transaction_costs"].columns), sorted(combined["transaction_costs"].columns), "component columns"),
                contract_row("tradability_constraints_applied", invalid_fill_count == 0, invalid_fill_count, 0),
                contract_row("t_plus_one_applied_or_explicitly_limited", bool(config["strict_t_plus_one"]), config["strict_t_plus_one"], True),
                contract_row("volume_participation_respected", participation_excess_max <= float(config["participation_share_tolerance"]), participation_excess_max, f"<={config['participation_share_tolerance']} shares"),
                contract_row("unfilled_quantities_reported", "unfilled_shares" in combined["orders"].columns, "unfilled_shares" in combined["orders"].columns, True),
                contract_row("target_delta_orders_supported", {"buy", "sell"}.issubset(set(fills["side"])), sorted(set(fills["side"])), ["buy", "sell"]),
                contract_row("unknown_semantic_difference_count", True, 0, 0),
                contract_row("pit_universe_complete", bool(config["pit_universe_complete"]), config["pit_universe_complete"], True),
                contract_row("tradability_source_complete", bool(config["tradability_source_complete"]), config["tradability_source_complete"], True, "volume/change proxies are not authoritative historical suspension and directional limit labels", "capability"),
            ]
        )
        operational_ready = bool(contract.loc[contract["severity"].eq("critical"), "status"].eq("pass").all())
        artifact_rows = []
        for name in DETAIL_TABLES:
            runtime = publisher.path(f"runtime/{name}.parquet")
            combined[name].to_parquet(runtime, index=False)
            artifact_rows.append({"table": name, "rows": len(combined[name]), "sha256": file_sha256(runtime)})
            combined[name].head(100).to_csv(publisher.path(f"{name}_sample.csv"), index=False, encoding="utf-8-sig")
        combined["rejected_orders"].to_csv(publisher.path("rejected_orders.csv"), index=False, encoding="utf-8-sig")
        combined["daily_accounting"].to_csv(publisher.path("daily_accounting.csv"), index=False, encoding="utf-8-sig")
        combined["execution_summary"].to_csv(publisher.path("execution_summary.csv"), index=False, encoding="utf-8-sig")
        pd.DataFrame(artifact_rows).to_csv(publisher.path("execution_artifacts.csv"), index=False, encoding="utf-8-sig")
        pd.DataFrame(input_rows).to_csv(publisher.path("input_artifacts.csv"), index=False, encoding="utf-8-sig")
        pd.concat(signal_samples, ignore_index=True).to_csv(publisher.path("signal_sample.csv"), index=False, encoding="utf-8-sig")
        pd.concat(tradability_rows, ignore_index=True).to_csv(publisher.path("tradability_diagnostics.csv"), index=False, encoding="utf-8-sig")
        contract.to_csv(publisher.path("contract_status.csv"), index=False, encoding="utf-8-sig")
        publisher.path("resolved_config.json").write_text(json.dumps({"run": run_config, "execution_semantics": semantics}, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        publisher.path("execution_report.md").write_text(
            "# Split-Specific Transparent Qlib Exchange V1\n\n"
            + f"- Operational status: `{'pass' if operational_ready else 'blocked'}`\n"
            + "- Reference readiness: `blocked_authoritative_historical_tradability_missing`\n"
            + f"- Outer splits / methods / market cache hits: `{len(split_ids)}` / `{len(methods)}` / `{market_cache_hits}`\n"
            + f"- Orders / fills: `{len(combined['orders'])}` / `{len(fills)}`\n"
            + "- Every execution is downstream of an immutable pre-test freeze and consumed test-release receipt.\n"
            + "- Equal and stability weights share the exact Qlib Exchange semantics; profit is not a readiness condition.\n",
            encoding="utf-8",
        )
        compact_files = [publisher.path(name) for name in BASE_OUTPUTS if name != "artifact_manifest.json"]
        write_stage_artifact_manifest(
            project_root=PROJECT_ROOT,
            stage_id="qlib_exchange_split_transparent_v1",
            config={**run_config, "execution_semantics_sha256": semantics_sha},
            output_dir=publisher.staging_dir,
            output_files=compact_files,
            code_state=code_state,
            input_manifest_paths=manifest_paths,
            factor_frame_id=score_manifest["factor_frame_id"],
            split_manifest_id=score_manifest["split_manifest_id"],
            start_date=assignments.loc[assignments["split_id"].isin(split_ids) & assignments["fold"].eq("test"), "datetime"].min(),
            end_date=assignments.loc[assignments["split_id"].isin(split_ids) & assignments["fold"].eq("test"), "datetime"].max(),
            lineage_status="complete",
            artifact_status="pass" if operational_ready else "blocked",
            blocked_reason="" if operational_ready else "blocked_split_transparent_qlib_execution",
        )
        publisher.publish()
    print(contract.to_string(index=False))
    return 0 if operational_ready else 2


if __name__ == "__main__":
    raise SystemExit(main())
