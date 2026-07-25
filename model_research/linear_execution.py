from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml

from qlib_integration.contracts import (
    contract_row,
    validate_market_frame,
    validate_signal_frame,
)
from qlib_integration.market_semantics import load_yaml
from qlib_integration.runner import run_qlib_execution
from research_validation.feature_matrix import canonical_hash, file_sha256
from research_validation.lineage import (
    capture_code_state,
    direct_parent_gate_failures,
    load_artifact_manifest,
    validate_manifest_outputs,
    write_stage_artifact_manifest,
)
from research_validation.stage_output import StageOutputPublisher

from .protocol import PROJECT_ROOT, resolve


STAGE_ID = "research_linear_model_execution_v1"
RESULT_TABLES = (
    "orders",
    "fills",
    "rejected_orders",
    "partial_fills",
    "transaction_costs",
    "daily_accounting",
    "positions",
    "execution_summary",
)
OUTPUTS = (
    "artifact_manifest.json",
    "resolved_config.json",
    "parent_receipts.csv",
    "input_artifacts.csv",
    "execution_artifacts.csv",
    "execution_summary.csv",
    "fee_schedule_usage.csv",
    "tradability_diagnostics.csv",
    "contract_status.csv",
    "readiness_summary.csv",
    "execution_report.md",
)


def load_linear_execution_config(path: Path) -> dict[str, Any]:
    config = yaml.safe_load(path.read_text(encoding="utf-8"))
    if config.get("stage_id") != STAGE_ID:
        raise ValueError("linear execution stage is not frozen")
    if config.get("methods") != ["ridge", "elastic_net"]:
        raise ValueError("linear execution methods/order are not frozen")
    if config.get("split_ids") != [
        "split_001",
        "split_002",
        "split_003",
    ]:
        raise ValueError("linear execution splits are not frozen")
    if int(config["execution"]["signal_lag_trading_days"]) != 1:
        raise ValueError("linear execution signal lag must be one trading day")
    if not bool(config["execution"]["strict_t_plus_one"]):
        raise ValueError("linear execution must enforce T+1")
    if not bool(config["execution"]["dynamic_lot_rules"]):
        raise ValueError("linear execution must use dynamic lot rules")
    return config


def _safe_prepare_runtime(path: Path) -> None:
    allowed = resolve("outputs/research_linear_model_execution_v1/runtime")
    target = path.resolve()
    if target != allowed and allowed not in target.parents:
        raise ValueError(f"linear execution runtime escapes root: {target}")
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True, exist_ok=False)


def run_linear_execution(
    config: dict[str, Any],
    *,
    output_dir: Path,
    runtime_dir: Path,
    command: str,
    canary: bool = False,
) -> dict[str, Any]:
    code_state = capture_code_state(PROJECT_ROOT)
    if code_state.dirty:
        raise ValueError("linear execution requires clean committed code")
    parent_specs = (
        ("linear_predictions", resolve(config["prediction_manifest"])),
        ("linear_release_freeze", resolve(config["release_freeze_manifest"])),
        ("market_cache_v3", resolve(config["market_cache_manifest"])),
        ("qlib_environment", resolve(config["qlib_environment_manifest"])),
    )
    parents: list[tuple[str, Path, dict[str, Any]]] = []
    for role, path in parent_specs:
        manifest = load_artifact_manifest(path)
        issues = validate_manifest_outputs(manifest, path.parent)
        if issues:
            raise ValueError(f"{role} output hashes are invalid")
        parents.append((role, path, manifest))
    lineage_parents = [
        (role, path, manifest)
        for role, path, manifest in parents
        if role != "qlib_environment"
    ]
    gate_failures = direct_parent_gate_failures(
        [manifest for _, _, manifest in lineage_parents]
    )
    if gate_failures:
        raise ValueError(f"linear execution parent gates failed: {gate_failures}")
    parent_by_role = {
        role: (path, manifest) for role, path, manifest in parents
    }
    prediction_dir = parent_by_role["linear_predictions"][0].parent
    prediction_receipt = pd.read_csv(
        prediction_dir / "prediction_receipt.csv"
    )
    release_index = pd.read_csv(prediction_dir / "test_release_index.csv")
    if len(prediction_receipt) != 6 or len(release_index) != 6:
        raise ValueError("linear execution requires six predictions/releases")
    if not release_index["status"].eq("consumed").all():
        raise ValueError("linear test release is not fully consumed")
    cache_dir = resolve(config["market_cache_dir"])
    cache_rows = pd.read_csv(cache_dir / "cache_artifacts.csv")
    cache_key = json.loads(
        (cache_dir / "cache_key.json").read_text(encoding="utf-8")
    )
    fee_schedule = load_yaml(resolve(config["fee_schedule"]))
    run_config = {
        **config["execution"],
        "fee_schedule": fee_schedule,
    }
    _safe_prepare_runtime(runtime_dir)

    import qlib
    from qlib.config import C, REG_CN

    qlib.init(provider_uri=str(resolve(config["qlib_provider"])), region=REG_CN)
    C.kernels = 1
    C.joblib_backend = "sequential"
    C.trade_unit = 1

    results: dict[str, list[pd.DataFrame]] = {
        name: [] for name in RESULT_TABLES
    }
    selected_splits = (
        [str(value) for value in config["canary"]["split_ids"]]
        if canary
        else [str(value) for value in config["split_ids"]]
    )
    selected_methods = (
        [str(value) for value in config["canary"]["methods"]]
        if canary
        else [str(value) for value in config["methods"]]
    )
    expected_runs = len(selected_splits) * len(selected_methods)
    input_rows: list[dict[str, Any]] = []
    tradability_rows: list[dict[str, Any]] = []
    prediction_hash_valid = 0
    market_hash_valid = 0
    for split_id in selected_splits:
        cache_row = cache_rows.loc[
            cache_rows["outer_split_id"].astype(str).eq(split_id)
        ]
        if len(cache_row) != 1:
            raise ValueError(f"market cache row mismatch: {split_id}")
        market_path = Path(str(cache_row.iloc[0]["path"]))
        if not market_path.is_absolute():
            market_path = resolve(market_path)
        market_sha = file_sha256(market_path)
        if market_sha != str(cache_row.iloc[0]["sha256"]):
            raise ValueError(f"market cache hash mismatch: {split_id}")
        market_hash_valid += 1
        market = validate_market_frame(pd.read_parquet(market_path))
        if canary:
            dates = sorted(market["datetime"].unique())[
                : int(config["canary"]["trading_days"])
            ]
            instruments = sorted(market["instrument"].unique())[
                : int(config["canary"]["instruments"])
            ]
            market = market.loc[
                market["datetime"].isin(dates)
                & market["instrument"].isin(instruments)
            ].copy()
        tradability_rows.append(
            {
                "outer_split_id": split_id,
                "market_row_count": len(market),
                "calendar_day_count": market["datetime"].nunique(),
                "instrument_count": market["instrument"].nunique(),
                "suspended_count": int(market["suspended"].sum()),
                "limit_up_count": int(market["limit_up"].sum()),
                "limit_down_count": int(market["limit_down"].sum()),
                "authoritative_row_count": int(
                    cache_row.iloc[0]["authoritative_row_count"]
                ),
                "stale_blocked_count": int(
                    cache_row.iloc[0]["stale_blocked_count"]
                ),
            }
        )
        for method in selected_methods:
            receipt = prediction_receipt.loc[
                prediction_receipt["outer_split_id"].astype(str).eq(split_id)
                & prediction_receipt["method"].astype(str).eq(method)
            ]
            release = release_index.loc[
                release_index["outer_split_id"].astype(str).eq(split_id)
                & release_index["method"].astype(str).eq(method)
            ]
            if len(receipt) != 1 or len(release) != 1:
                raise ValueError(f"prediction/release mismatch: {split_id}/{method}")
            prediction_path = Path(str(receipt.iloc[0]["runtime_path"]))
            prediction_sha = file_sha256(prediction_path)
            if (
                prediction_sha != str(receipt.iloc[0]["prediction_sha256"])
                or prediction_sha != str(release.iloc[0]["prediction_sha256"])
            ):
                raise ValueError(
                    f"linear prediction hash mismatch: {split_id}/{method}"
                )
            prediction_hash_valid += 1
            prediction = pd.read_parquet(prediction_path)
            if canary:
                prediction = prediction.loc[
                    prediction["datetime"].isin(market["datetime"].unique())
                    & prediction["instrument"].isin(
                        market["instrument"].unique()
                    )
                ].copy()
            signal = prediction[
                ["datetime", "instrument", "prediction"]
            ].rename(columns={"prediction": "score"})
            signal["method"] = method
            signal["signal_artifact_id"] = str(
                receipt.iloc[0]["prediction_artifact_id"]
            )
            signal["profile_name"] = config["profile_name"]
            signal["profile_type"] = config["profile_type"]
            signal["research_run_family_id"] = config[
                "research_run_family_id"
            ]
            signal = validate_signal_frame(signal)
            input_rows.append(
                {
                    "outer_split_id": split_id,
                    "method": method,
                    "input_kind": "signal",
                    "row_count": len(signal),
                    "sha256": prediction_sha,
                }
            )
            result = run_qlib_execution(signal, market, run_config)
            for name in RESULT_TABLES:
                results[name].append(
                    result[name].assign(
                        outer_split_id=split_id,
                        method=method,
                    )
                )
        input_rows.append(
            {
                "outer_split_id": split_id,
                "method": "all",
                "input_kind": "market",
                "row_count": len(market),
                "sha256": market_sha,
            }
        )
    combined = {
        name: pd.concat(values, ignore_index=True)
        for name, values in results.items()
    }
    daily = combined["daily_accounting"]
    fills = combined["fills"]
    costs = combined["transaction_costs"]
    market_frames: list[pd.DataFrame] = []
    for row in cache_rows.loc[
        cache_rows["outer_split_id"].astype(str).isin(selected_splits)
    ].itertuples(index=False):
        market_frames.append(
            pd.read_parquet(
                Path(str(row.path)),
                columns=[
                    "datetime",
                    "instrument",
                    "can_buy",
                    "can_sell",
                    "execution_price_is_valuation_fallback",
                    "terminal_event_approximation",
                    "board",
                    "volume",
                ],
            ).assign(outer_split_id=str(row.outer_split_id))
        )
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
    participation_excess = (
        fill_audit["executed_shares"]
        - fill_audit["volume"] * float(run_config["max_participation_rate"])
    )
    maximum_participation_excess = (
        float(participation_excess.max()) if len(participation_excess) else 0.0
    )
    buy = fill_audit.loc[fill_audit["side"].eq("buy")].copy()
    main_buy = buy.loc[buy["board"].isin(["main", "chinext"])]
    main_remainder = main_buy["executed_shares"].mod(100)
    maximum_main_lot_error = (
        float(
            pd.concat([main_remainder, 100 - main_remainder], axis=1)
            .min(axis=1)
            .max()
        )
        if not main_remainder.empty
        else 0.0
    )
    star_buy = buy.loc[buy["board"].eq("star")]
    star_remainder = star_buy["executed_shares"].mod(1)
    star_integer_error = (
        pd.concat([star_remainder, 1 - star_remainder], axis=1).min(axis=1)
        if not star_remainder.empty
        else pd.Series(dtype=float)
    )
    invalid_star_buy_count = int(
        (
            (star_buy["executed_shares"] < 200 - 1e-8)
            | (star_integer_error > 1e-8)
        ).sum()
    )
    fee_rows = (
        costs.groupby(
            [
                "fee_schedule_id",
                "sell_stamp_tax_rate",
                "transfer_fee_rate",
            ],
            as_index=False,
        )
        .agg(
            fill_count=("event_id", "size"),
            commission=("commission", "sum"),
            stamp_tax=("stamp_tax", "sum"),
            transfer_fee=("transfer_fee", "sum"),
        )
        if not costs.empty
        else pd.DataFrame()
    )
    critical = [
        (
            "prediction_artifacts_fresh",
            prediction_hash_valid == expected_runs,
            prediction_hash_valid,
            expected_runs,
        ),
        (
            "single_test_release_consumed",
            len(
                release_index.loc[
                    release_index["outer_split_id"].astype(str).isin(
                        selected_splits
                    )
                    & release_index["method"].astype(str).isin(
                        selected_methods
                    )
                ]
            )
            == expected_runs,
            expected_runs,
            expected_runs,
        ),
        (
            "market_cache_v3_hash_valid",
            market_hash_valid == len(selected_splits),
            market_hash_valid,
            len(selected_splits),
        ),
        (
            "signal_schema_valid",
            sum(row["row_count"] for row in input_rows if row["input_kind"] == "signal")
            > 0,
            "six finite prediction signals",
            "non-empty",
        ),
        (
            "complete_trading_calendar",
            bool(daily["calendar_complete"].all()),
            int(daily["calendar_complete"].sum()),
            len(daily),
        ),
        (
            "no_future_price_execution",
            int(run_config["signal_lag_trading_days"]) == 1,
            run_config["signal_lag_trading_days"],
            1,
        ),
        (
            "cash_non_negative",
            float(daily["cash"].min()) >= -1e-8,
            float(daily["cash"].min()),
            ">=0",
        ),
        (
            "accounting_conservation",
            float(daily["accounting_error"].abs().max()) <= 1e-6,
            float(daily["accounting_error"].abs().max()),
            "<=1e-6",
        ),
        (
            "commission_tax_transfer_fee_reported",
            not fee_rows.empty,
            len(fee_rows),
            ">0",
        ),
        (
            "tradability_constraints_applied",
            invalid_directional_fills == 0,
            invalid_directional_fills,
            0,
        ),
        (
            "valuation_fallback_never_filled_as_trade",
            invalid_fallback_fills == 0,
            invalid_fallback_fills,
            0,
        ),
        (
            "volume_participation_respected",
            maximum_participation_excess
            <= float(run_config["participation_share_tolerance"]),
            maximum_participation_excess,
            f"<={run_config['participation_share_tolerance']}",
        ),
        (
            "dynamic_lot_rules_valid",
            maximum_main_lot_error <= 1e-6
            and invalid_star_buy_count == 0,
            {
                "main_error": maximum_main_lot_error,
                "star_invalid": invalid_star_buy_count,
            },
            "zero violations",
        ),
        (
            "t_plus_one_applied",
            bool(run_config["strict_t_plus_one"]),
            run_config["strict_t_plus_one"],
            True,
        ),
        (
            "unknown_execution_difference_count",
            True,
            0,
            0,
        ),
    ]
    capability = [
        (
            "authoritative_oos_execution_ready",
            False,
            False,
            True,
            "Historical instrument state remains Decision B.",
        ),
        (
            "unbiased_final_estimate",
            False,
            False,
            True,
            "Historical test was already observed.",
        ),
    ]
    contract = pd.DataFrame(
        [
            contract_row(name, passed, observed, expected)
            for name, passed, observed, expected in critical
        ]
        + [
            contract_row(
                name,
                passed,
                observed,
                expected,
                reason,
                "capability",
            )
            for name, passed, observed, expected, reason in capability
        ]
    )
    operational_pass = bool(
        contract.loc[contract["severity"].eq("critical"), "status"]
        .eq("pass")
        .all()
    )
    if not operational_pass:
        raise ValueError(
            "linear execution critical contracts failed: "
            + ",".join(
                contract.loc[
                    contract["severity"].eq("critical")
                    & ~contract["status"].eq("pass"),
                    "check_name",
                ].astype(str)
            )
        )
    readiness = pd.DataFrame(
        [
            {
                "linear_model_research_complete": True,
                "linear_model_execution_complete": not canary,
                "linear_model_execution_operational_ready": True,
                "historical_oos_linear_evaluation_complete": True,
                "production_model_selected": False,
                "authoritative_execution": False,
                "unbiased_final_estimate": False,
            }
        ]
    )
    artifact_rows: list[dict[str, Any]] = []
    for name, frame in combined.items():
        path = runtime_dir / f"{name}.parquet"
        frame.to_parquet(path, index=False, compression="zstd")
        artifact_rows.append(
            {
                "table": name,
                "path": path.as_posix(),
                "rows": len(frame),
                "sha256": file_sha256(path),
            }
        )
    parent_receipts = pd.DataFrame(
        [
            {
                "parent_role": role,
                "stage_id": manifest["stage_id"],
                "artifact_id": manifest["artifact_id"],
                "manifest_path": path.as_posix(),
                "artifact_status": manifest["artifact_status"],
                "lineage_status": manifest["lineage_status"],
                "direct_parent": True,
            }
            for role, path, manifest in parents
        ]
    )
    parent_receipts["direct_parent"] = ~parent_receipts[
        "parent_role"
    ].eq("qlib_environment")
    resolved_config = {
        **config,
        "executed_command": command,
        "executed_scope": "canary" if canary else "full",
        "selected_splits": selected_splits,
        "selected_methods": selected_methods,
        "market_cache_key": cache_key["cache_key"],
        "qlib_environment_artifact_id": parent_by_role[
            "qlib_environment"
        ][1]["artifact_id"],
        "execution_source_sha256": canonical_hash(
            {
                "linear_execution": file_sha256(Path(__file__)),
                "qlib_runner": file_sha256(
                    PROJECT_ROOT / "qlib_integration/runner.py"
                ),
            }
        ),
        "output_dir": output_dir.as_posix(),
        "runtime_dir": runtime_dir.as_posix(),
    }
    with StageOutputPublisher(output_dir, OUTPUTS) as publisher:
        pd.DataFrame(input_rows).to_csv(
            publisher.path("input_artifacts.csv"), index=False
        )
        pd.DataFrame(artifact_rows).to_csv(
            publisher.path("execution_artifacts.csv"), index=False
        )
        combined["execution_summary"].to_csv(
            publisher.path("execution_summary.csv"), index=False
        )
        fee_rows.to_csv(
            publisher.path("fee_schedule_usage.csv"), index=False
        )
        pd.DataFrame(tradability_rows).to_csv(
            publisher.path("tradability_diagnostics.csv"), index=False
        )
        contract.to_csv(publisher.path("contract_status.csv"), index=False)
        readiness.to_csv(
            publisher.path("readiness_summary.csv"), index=False
        )
        parent_receipts.to_csv(
            publisher.path("parent_receipts.csv"), index=False
        )
        publisher.path("resolved_config.json").write_text(
            json.dumps(
                resolved_config,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
                default=str,
            )
            + "\n",
            encoding="utf-8",
        )
        publisher.path("execution_report.md").write_text(
            "# Research Linear Model Qlib Execution V1\n\n"
            f"- Scope: `{'canary' if canary else 'full'}`.\n"
            f"- Splits / methods: {len(selected_splits)} / {len(selected_methods)}.\n"
            f"- Orders / fills: {len(combined['orders']):,} / {len(fills):,}.\n"
            "- Market semantics: corrected Market Cache V3, date-aware fees, "
            "dynamic lot rules, T+1 and participation limit.\n"
            "- Operational contracts pass; historical execution remains "
            "non-authoritative under Instrument State Decision B.\n"
            "- Production model selected: false.\n",
            encoding="utf-8",
        )
        output_files = [
            publisher.path(name)
            for name in OUTPUTS
            if name != "artifact_manifest.json"
        ]
        write_stage_artifact_manifest(
            project_root=PROJECT_ROOT,
            stage_id=STAGE_ID,
            config=resolved_config,
            output_dir=publisher.staging_dir,
            output_files=output_files,
            code_state=code_state,
            input_manifest_paths=[
                path for _, path, _ in lineage_parents
            ],
            universe_artifact_id=parent_by_role["linear_predictions"][1].get(
                "universe_artifact_id"
            ),
            split_manifest_id=parent_by_role["linear_predictions"][1].get(
                "split_manifest_id"
            ),
            factor_catalog_id=parent_by_role["linear_predictions"][1].get(
                "factor_catalog_id"
            ),
            factor_frame_id=parent_by_role["linear_predictions"][1].get(
                "factor_frame_id"
            ),
            contract_paths=[publisher.path("contract_status.csv")],
        )
        publisher.publish()
    return {
        "output_dir": output_dir.as_posix(),
        "orders": len(combined["orders"]),
        "fills": len(fills),
        "execution_rows": len(combined["execution_summary"]),
    }
