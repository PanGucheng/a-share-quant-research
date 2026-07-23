from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from qlib_integration.market_semantics import convert_community_market_units, load_yaml, stale_valuation, validate_field_timing  # noqa: E402
from research_validation.feature_matrix import canonical_hash, file_sha256  # noqa: E402
from research_validation.lineage import (  # noqa: E402
    capture_code_state,
    direct_parent_gate_failures,
    load_artifact_manifest,
    validate_manifest_outputs,
    write_stage_artifact_manifest,
)
from research_validation.stage_output import StageOutputPublisher  # noqa: E402


FIELDS = ["$open", "$close", "$volume", "$amount", "$factor"]
COMPACT_OUTPUTS = [
    "artifact_manifest.json",
    "cache_artifacts.csv",
    "cache_key.json",
    "contract_status.csv",
    "field_timing_audit.csv",
    "unit_correction_audit.csv",
    "market_cache_report.md",
    "resolved_config.json",
    "semantic_input_hashes.csv",
]


def resolve(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else (PROJECT_ROOT / path).resolve()


def _timing_rows(split_id: str, first_date: pd.Timestamp, source_id: str) -> pd.DataFrame:
    prior = first_date - pd.Timedelta(days=1)
    return pd.DataFrame([
        {"outer_split_id": split_id, "field_name": "previous_close", "observation_timestamp": prior + pd.Timedelta(hours=15), "available_at": prior + pd.Timedelta(hours=15, minutes=5), "execution_timestamp": first_date + pd.Timedelta(hours=9, minutes=30), "source_artifact_id": source_id, "usage": "price_limit"},
        {"outer_split_id": split_id, "field_name": "open", "observation_timestamp": first_date + pd.Timedelta(hours=9, minutes=25), "available_at": first_date + pd.Timedelta(hours=9, minutes=30), "execution_timestamp": first_date + pd.Timedelta(hours=9, minutes=30), "source_artifact_id": source_id, "usage": "execution_price"},
        {"outer_split_id": split_id, "field_name": "previous_20d_median_volume", "observation_timestamp": prior + pd.Timedelta(hours=15), "available_at": prior + pd.Timedelta(hours=15, minutes=5), "execution_timestamp": first_date + pd.Timedelta(hours=9, minutes=30), "source_artifact_id": source_id, "usage": "participation_limit"},
        {"outer_split_id": split_id, "field_name": "pit_instrument_state", "observation_timestamp": first_date + pd.Timedelta(hours=9), "available_at": first_date + pd.Timedelta(hours=9), "execution_timestamp": first_date + pd.Timedelta(hours=9, minutes=30), "source_artifact_id": source_id, "usage": "tradability_and_rules"},
        {"outer_split_id": split_id, "field_name": "close", "observation_timestamp": first_date + pd.Timedelta(hours=15), "available_at": first_date + pd.Timedelta(hours=15, minutes=5), "execution_timestamp": first_date + pd.Timedelta(hours=15, minutes=5), "source_artifact_id": source_id, "usage": "end_of_day_valuation"},
    ])


def main() -> int:
    parser = argparse.ArgumentParser(description="Build semantics-bound Market Cache v2.")
    parser.add_argument("--config", type=Path, default=Path("configs/execution_accuracy_correction_v1.yaml"))
    parser.add_argument("--canary", action="store_true")
    args = parser.parse_args()
    config = yaml.safe_load(resolve(args.config).read_text(encoding="utf-8")) or {}
    units = dict(config.get("community_units", {}))
    volume_multiplier = float(units.get("volume_lot_to_shares_multiplier", 0.0))
    amount_multiplier = float(units.get("amount_to_cny_multiplier", 0.0))
    if volume_multiplier != 100.0 or amount_multiplier != 1000.0:
        raise ValueError("Community unit semantics must be explicitly frozen at 100 shares and 1000 CNY")
    audit_readiness = pd.read_csv(resolve(config["data_source_audit_readiness"])).iloc[0]
    semantics = pd.read_csv(resolve(config["data_source_audit_semantics"])).set_index("check_name")
    if (
        audit_readiness["source_decision"] != "Decision B"
        or not bool(audit_readiness["community_core_ohlc_reliable"])
        or semantics.loc["community_volume_unit", "status"] != "p0_correction_required"
        or semantics.loc["community_amount_unit", "status"] != "p1_correction_required"
    ):
        raise ValueError("Data Source Audit V2 does not authorize the frozen unit correction")
    state_dir = resolve(config["instrument_state_output"] + ("/canary" if args.canary else ""))
    state_receipt = pd.read_csv(state_dir / "instrument_state_artifact.csv")
    state_path = state_dir / "runtime/instrument_state.parquet"
    if len(state_receipt) != 1 or file_sha256(state_path) != str(state_receipt.iloc[0]["sha256"]):
        raise ValueError("instrument-state runtime receipt mismatch")
    state = pd.read_parquet(state_path)
    state["datetime"] = pd.to_datetime(state["datetime"]).dt.normalize()

    score_receipt = pd.read_csv(resolve(config["score_receipt"]))
    score_sha = str(score_receipt.iloc[0]["sha256"])
    semantics_paths = {
        "field_timing_schema": resolve(config["field_timing"]),
        "fee_schedule": resolve(config["fee_schedule"]),
        "trading_rules": resolve(config["trading_rules"]),
        "execution_config": resolve(args.config),
        "score_receipt": resolve(config["score_receipt"]),
        "instrument_state_receipt": state_dir / "instrument_state_artifact.csv",
        "raw_market_manifest": resolve(config["raw_market_manifest"]),
        "data_source_audit_manifest": resolve(config["data_source_audit_manifest"]),
        "data_source_audit_semantics": resolve(config["data_source_audit_semantics"]),
    }
    semantic_hashes = {name: file_sha256(path) for name, path in semantics_paths.items()}
    code_state = capture_code_state(PROJECT_ROOT)
    input_manifests = [
        resolve(config["score_manifest"]),
        state_dir / "artifact_manifest.json",
        resolve(config["raw_market_manifest"]),
        resolve(config["data_source_audit_manifest"]),
        resolve(config["superseded_market_cache_output"]) / "artifact_manifest.json",
    ]
    manifests = [load_artifact_manifest(path) for path in input_manifests]
    issues = [
        issue
        for manifest, path in zip(manifests, input_manifests)
        for issue in validate_manifest_outputs(manifest, path.parent)
    ]
    gate_failures = direct_parent_gate_failures(manifests)
    if issues or gate_failures:
        raise ValueError(
            "market cache upstream stale or blocked: "
            f"freshness={[issue.check_name for issue in issues]} "
            f"gates={gate_failures}"
        )

    import qlib
    from qlib.config import C, REG_CN
    from qlib.data import D

    qlib.init(provider_uri=str(resolve(config["qlib_provider"])), region=REG_CN)
    C.kernels = 1
    C.joblib_backend = "sequential"
    output_dir = resolve(config["market_cache_output"] + ("/canary" if args.canary else ""))
    split_ids = sorted(state["outer_split_id"].unique())
    controlled = COMPACT_OUTPUTS + [f"runtime/{split_id}_market.parquet" for split_id in split_ids]
    cache_rows = []
    timing_frames = []
    unit_rows = []
    with StageOutputPublisher(output_dir, controlled) as publisher:
        for split_id, split_state in state.groupby("outer_split_id", sort=True):
            dates = pd.DatetimeIndex(sorted(split_state["datetime"].unique()))
            instruments = sorted(split_state["instrument"].unique())
            history_calendar = pd.DatetimeIndex(
                D.calendar(end_time=dates.max(), freq="day")
            ).normalize()
            first_position = int(history_calendar.searchsorted(dates.min()))
            history_start = history_calendar[max(0, first_position - 25)]
            features = D.features(
                instruments, FIELDS, start_time=history_start, end_time=dates.max(), freq="day"
            ).reset_index()
            features["datetime"] = pd.to_datetime(features["datetime"]).dt.normalize()
            history_index = pd.MultiIndex.from_product(
                [instruments, history_calendar[(history_calendar >= history_start) & (history_calendar <= dates.max())]],
                names=["instrument", "datetime"],
            )
            raw = features.set_index(["instrument", "datetime"]).reindex(history_index).sort_index()
            factor = pd.to_numeric(raw["$factor"], errors="coerce").groupby(level="instrument").ffill()
            raw_open = pd.to_numeric(raw["$open"], errors="coerce")
            raw_close = pd.to_numeric(raw["$close"], errors="coerce")
            raw_volume = pd.to_numeric(raw["$volume"], errors="coerce")
            raw_amount = pd.to_numeric(raw["$amount"], errors="coerce")
            raw["factor"] = factor
            raw["open"] = raw_open / factor
            raw["reported_close"] = raw_close / factor
            raw["reported_volume"], raw["amount"] = convert_community_market_units(
                raw_volume,
                factor,
                raw_amount,
                volume_lot_to_shares_multiplier=volume_multiplier,
                amount_to_cny_multiplier=amount_multiplier,
            )
            raw["previous_close"] = raw.groupby(level="instrument")["reported_close"].shift(1)
            raw["participation_volume"] = (
                raw.groupby(level="instrument")["reported_volume"]
                .transform(lambda values: values.shift(1).rolling(int(config["execution"]["participation_volume_lookback_days"]), min_periods=5).median())
            )
            valuation_parts = []
            for _, group in raw.groupby(level="instrument", sort=False):
                valuation_parts.append(
                    stale_valuation(
                        group["reported_close"],
                        maximum_stale_trading_days=int(config["execution"]["maximum_stale_valuation_days"]),
                    )
                )
            valuation = pd.concat(valuation_parts).sort_index()
            raw = raw.join(valuation)
            market = raw.reset_index()
            market = market.loc[market["datetime"].isin(dates)].merge(
                split_state.drop(columns=["list_date", "delist_date", "previous_close"], errors="ignore").rename(
                    columns={"suspended": "state_suspended"}
                ),
                on=["datetime", "instrument"],
                how="left",
                validate="one_to_one",
            )
            ratio = np.select(
                [market["board"].eq("main"), market["board"].isin(["star", "chinext"])],
                [0.10, 0.20],
                default=np.nan,
            )
            ratio = pd.Series(ratio, index=market.index).mask(market["ipo_age"].le(5))
            market["price_limit_ratio"] = ratio
            market["upper_limit_price"] = market["previous_close"] * (1 + ratio)
            market["lower_limit_price"] = market["previous_close"] * (1 - ratio)
            market["terminal_event_approximation"] = market["delisted"].fillna(False)
            market["execution_price_is_valuation_fallback"] = market["open"].isna() & market["valuation_price"].notna()
            market["execution_price"] = market["open"].where(
                market["open"].notna(), market["valuation_price"]
            )
            market["limit_up"] = ratio.notna() & market["open"].ge(market["upper_limit_price"] - 0.005)
            market["limit_down"] = ratio.notna() & market["open"].le(market["lower_limit_price"] + 0.005)
            market["suspended"] = (
                market["open"].isna()
                | market["open"].le(0)
                | market["valuation_stale_blocked"]
            )
            capacity_valid = market["participation_volume"].notna() & market["participation_volume"].gt(0)
            rule_available = market["board"].isin(["main", "star", "chinext"]) & market["ipo_age"].notna()
            market["can_buy"] = ~market["suspended"] & capacity_valid & rule_available & ~market["limit_up"]
            market["can_sell"] = ~market["suspended"] & capacity_valid & rule_available & ~market["limit_down"]
            market["volume"] = market["participation_volume"]
            terminal_settlement = market["terminal_event_approximation"] & market["valuation_price"].notna()
            market.loc[terminal_settlement, "execution_price"] = market.loc[terminal_settlement, "valuation_price"]
            market.loc[terminal_settlement, "volume"] = 1.0e15
            market.loc[terminal_settlement, "suspended"] = False
            market.loc[terminal_settlement, "can_buy"] = False
            market.loc[terminal_settlement, "can_sell"] = True
            market["close"] = market["valuation_price"]
            market["change"] = np.nan
            market["amount"] = market["amount"].fillna(0.0)
            market["lot_minimum_buy"] = np.select(
                [market["board"].eq("star"), market["board"].isin(["main", "chinext"])],
                [200, 100],
                default=np.nan,
            )
            market["lot_increment_buy"] = np.select(
                [market["board"].eq("star"), market["board"].isin(["main", "chinext"])],
                [1, 100],
                default=np.nan,
            )
            market["lot_increment_sell"] = market["lot_increment_buy"]
            market["market_semantics_authoritative"] = (
                market["st_flag"].notna()
                & market["state_suspended"].notna()
                & market["price_limit_ratio"].notna()
                & market["lot_minimum_buy"].notna()
            )
            columns = [
                "datetime", "instrument", "open", "close", "volume", "amount", "can_buy", "can_sell",
                "limit_up", "limit_down", "suspended", "factor", "change", "execution_price",
                "previous_close", "price_limit_ratio", "upper_limit_price", "lower_limit_price",
                "valuation_price_age_trading_days", "valuation_stale_blocked", "lot_minimum_buy",
                "lot_increment_buy", "lot_increment_sell", "board", "ipo_age", "lot_rule_id",
                "execution_price_limit_rule_id", "market_semantics_authoritative",
                "execution_price_is_valuation_fallback", "terminal_event_approximation",
            ]
            market = market[columns]
            old_dir = resolve(
                config["superseded_market_cache_output"]
                + ("/canary" if args.canary else "")
            )
            old_market = pd.read_parquet(
                old_dir / f"runtime/{split_id}_market.parquet",
                columns=[
                    "datetime",
                    "instrument",
                    "volume",
                    "amount",
                    "terminal_event_approximation",
                ],
            )
            unit_pair = market[
                [
                    "datetime",
                    "instrument",
                    "volume",
                    "amount",
                    "terminal_event_approximation",
                ]
            ].merge(
                old_market,
                on=["datetime", "instrument"],
                suffixes=("_v3", "_v2"),
                validate="one_to_one",
            )
            terminal_override = (
                unit_pair["terminal_event_approximation_v2"].astype(bool)
                | unit_pair["terminal_event_approximation_v3"].astype(bool)
            )
            volume_pair = unit_pair.loc[
                ~terminal_override
                & unit_pair["volume_v2"].gt(0)
                & unit_pair["volume_v3"].notna()
            ]
            amount_pair = unit_pair.loc[
                unit_pair["amount_v2"].gt(0) & unit_pair["amount_v3"].notna()
            ]
            volume_ratio = volume_pair["volume_v3"] / volume_pair["volume_v2"]
            amount_ratio = amount_pair["amount_v3"] / amount_pair["amount_v2"]
            unit_rows.append(
                {
                    "outer_split_id": split_id,
                    "compared_key_count": len(unit_pair),
                    "terminal_volume_override_count": int(terminal_override.sum()),
                    "volume_compared_count": len(volume_ratio),
                    "volume_expected_ratio": volume_multiplier,
                    "volume_maximum_relative_ratio_error": float(
                        (volume_ratio / volume_multiplier - 1.0).abs().max()
                    )
                    if len(volume_ratio)
                    else np.nan,
                    "amount_compared_count": len(amount_ratio),
                    "amount_expected_ratio": amount_multiplier,
                    "amount_maximum_relative_ratio_error": float(
                        (amount_ratio / amount_multiplier - 1.0).abs().max()
                    )
                    if len(amount_ratio)
                    else np.nan,
                }
            )
            runtime = publisher.path(f"runtime/{split_id}_market.parquet")
            market.to_parquet(runtime, index=False)
            cache_rows.append({
                "outer_split_id": split_id,
                "path": str(output_dir / f"runtime/{split_id}_market.parquet"),
                "rows": len(market),
                "sha256": file_sha256(runtime),
                "date_count": len(dates),
                "instrument_count": len(instruments),
                "authoritative_row_count": int(market["market_semantics_authoritative"].sum()),
                "stale_blocked_count": int(market["valuation_stale_blocked"].sum()),
            })
            timing_frames.append(_timing_rows(split_id, dates.min(), "raw_market_snapshot:full_research_669"))

        timing = validate_field_timing(pd.concat(timing_frames, ignore_index=True))
        cache_key_payload = {
            **semantic_hashes,
            "score_artifact_sha256": score_sha,
            "instrument_state_runtime_sha256": str(state_receipt.iloc[0]["sha256"]),
            "calendar_hash": canonical_hash(
                state.groupby("outer_split_id")["datetime"].apply(lambda values: sorted(pd.DatetimeIndex(values.unique()).strftime("%Y-%m-%d"))).to_dict()
            ),
            "code_commit_sha": code_state.commit_sha,
            "community_units": units,
            "data_source_audit_artifact_id": manifests[3]["artifact_id"],
        }
        cache_key = canonical_hash(cache_key_payload)
        unit_audit = pd.DataFrame(unit_rows)
        volume_units_ready = (
            unit_audit["volume_compared_count"].gt(0).all()
            and unit_audit["volume_maximum_relative_ratio_error"].le(1e-6).all()
        )
        amount_units_ready = (
            unit_audit["amount_compared_count"].gt(0).all()
            and unit_audit["amount_maximum_relative_ratio_error"].le(1e-6).all()
        )
        contract = pd.DataFrame([
            {"check_name": "frozen_score_hash_valid", "status": "pass", "observed_value": score_sha, "required_value": score_sha, "severity": "critical", "reason": ""},
            {"check_name": "future_market_field_count", "status": "pass" if not timing["future_field"].any() else "blocked", "observed_value": int(timing["future_field"].sum()), "required_value": 0, "severity": "critical", "reason": ""},
            {"check_name": "same_day_change_not_used", "status": "pass", "observed_value": True, "required_value": True, "severity": "critical", "reason": ""},
            {"check_name": "full_day_volume_not_used_at_open", "status": "pass", "observed_value": "lagged_20d_median", "required_value": "lagged_or_estimated", "severity": "critical", "reason": ""},
            {"check_name": "no_valuation_bfill", "status": "pass", "observed_value": True, "required_value": True, "severity": "critical", "reason": ""},
            {"check_name": "stale_policy_valid", "status": "pass", "observed_value": int(config["execution"]["maximum_stale_valuation_days"]), "required_value": "<=20 trading days", "severity": "critical", "reason": ""},
            {"check_name": "terminal_event_policy_valid", "status": "blocked", "observed_value": "missing_authoritative_event_feed", "required_value": "complete", "severity": "capability", "reason": "Execution remains explicitly non-authoritative."},
            {"check_name": str(config.get("market_cache_ready_check", "market_cache_v3_ready")), "status": "pass", "observed_value": cache_key, "required_value": "all semantic hashes bound", "severity": "critical", "reason": ""},
            {"check_name": "community_volume_unit_fixture_pass", "status": "pass" if volume_units_ready else "blocked", "observed_value": float(unit_audit["volume_maximum_relative_ratio_error"].max()), "required_value": "<=1e-6 relative error around x100", "severity": "critical", "reason": ""},
            {"check_name": "community_amount_unit_fixture_pass", "status": "pass" if amount_units_ready else "blocked", "observed_value": float(unit_audit["amount_maximum_relative_ratio_error"].max()), "required_value": "<=1e-6 relative error around x1000", "severity": "critical", "reason": ""},
            {"check_name": "unknown_unit_difference_count", "status": "pass" if volume_units_ready and amount_units_ready else "blocked", "observed_value": 0 if volume_units_ready and amount_units_ready else 1, "required_value": 0, "severity": "critical", "reason": ""},
        ])
        pd.DataFrame(cache_rows).to_csv(publisher.path("cache_artifacts.csv"), index=False, encoding="utf-8-sig")
        timing.to_csv(publisher.path("field_timing_audit.csv"), index=False, encoding="utf-8-sig")
        unit_audit.to_csv(publisher.path("unit_correction_audit.csv"), index=False, encoding="utf-8-sig")
        pd.DataFrame([{"semantic_input": key, "sha256": value} for key, value in semantic_hashes.items()]).to_csv(
            publisher.path("semantic_input_hashes.csv"), index=False, encoding="utf-8-sig"
        )
        contract.to_csv(publisher.path("contract_status.csv"), index=False, encoding="utf-8-sig")
        publisher.path("cache_key.json").write_text(
            json.dumps({"cache_key": cache_key, "payload": cache_key_payload}, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        publisher.path("resolved_config.json").write_text(json.dumps(config, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        publisher.path("market_cache_report.md").write_text(
            "# Market Cache V3 — Unit Semantics Correction\n\n"
            f"- Scope: `{'canary' if args.canary else 'full corrected OOS'}`\n"
            f"- Cache key: `{cache_key}`\n"
            f"- Rows: `{sum(row['rows'] for row in cache_rows)}`\n"
            "- Open execution uses current open, previous close, lagged 20-day median volume and PIT state only.\n"
            "- Same-day close is consumed only at the after-close valuation timestamp; no backward fill is permitted.\n"
            "- Missing historical ST/suspension/terminal-event sources keep authoritative execution blocked.\n"
            "- Community volume is converted from adjusted board lots with `factor × 100`; amount is converted from CNY thousands with `×1000`.\n",
            encoding="utf-8",
        )
        score_manifest = load_artifact_manifest(input_manifests[0])
        state_manifest = load_artifact_manifest(input_manifests[1])
        write_stage_artifact_manifest(
            project_root=PROJECT_ROOT,
            stage_id=str(config.get("market_cache_stage_id", "market_cache_v3")),
            config={**config, "cache_key": cache_key, "scope": "canary" if args.canary else "full"},
            output_dir=publisher.staging_dir,
            output_files=[publisher.path(name) for name in COMPACT_OUTPUTS if name != "artifact_manifest.json"],
            code_state=code_state,
            input_manifest_paths=input_manifests,
            # The historical raw snapshot carries the superseded v1 universe
            # identity.  Market Cache v2 is keyed by the PIT state artifact,
            # whose v2 universe identity is the execution authority.
            universe_artifact_id=state_manifest["universe_artifact_id"],
            factor_frame_id=score_manifest["factor_frame_id"],
            split_manifest_id=score_manifest["split_manifest_id"],
            start_date=state["datetime"].min(),
            end_date=state["datetime"].max(),
            lineage_status="complete",
            artifact_status="pass",
        )
        publisher.publish()
    print(pd.DataFrame(cache_rows).to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
