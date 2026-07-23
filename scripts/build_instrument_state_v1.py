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

from qlib_integration.market_semantics import infer_board, load_yaml, resolve_lot_rule, resolve_price_limit_rule  # noqa: E402
from research_validation.feature_matrix import file_sha256  # noqa: E402
from research_validation.lineage import capture_code_state, load_artifact_manifest, write_stage_artifact_manifest  # noqa: E402
from research_validation.stage_output import StageOutputPublisher  # noqa: E402


COMPACT_OUTPUTS = [
    "artifact_manifest.json",
    "contract_status.csv",
    "instrument_state_artifact.csv",
    "instrument_state_coverage.csv",
    "resolved_config.json",
    "instrument_state_report.md",
]


def resolve(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else (PROJECT_ROOT / path).resolve()


def main() -> int:
    parser = argparse.ArgumentParser(description="Build fail-closed PIT instrument state for corrected OOS execution.")
    parser.add_argument("--config", type=Path, default=Path("configs/execution_accuracy_correction_v1.yaml"))
    parser.add_argument("--canary", action="store_true")
    args = parser.parse_args()
    config = yaml.safe_load(resolve(args.config).read_text(encoding="utf-8")) or {}
    score_path = resolve(config["score_runtime"])
    receipt = pd.read_csv(resolve(config["score_receipt"]))
    if len(receipt) != 1 or file_sha256(score_path) != str(receipt.iloc[0]["sha256"]):
        raise ValueError("corrected score runtime receipt mismatch")
    score = pd.read_parquet(score_path, columns=["datetime", "instrument", "outer_split_id"])
    score["datetime"] = pd.to_datetime(score["datetime"]).dt.normalize()
    score = score.drop_duplicates(["datetime", "instrument", "outer_split_id"])
    if args.canary:
        canary = config["canary"]
        score = score.loc[score["outer_split_id"].isin(canary["outer_splits"])]
        dates = sorted(score["datetime"].unique())[: int(canary["trading_days"])]
        instruments = sorted(score["instrument"].unique())[: int(canary["instruments"])]
        score = score.loc[score["datetime"].isin(dates) & score["instrument"].isin(instruments)]

    intervals = pd.read_csv(
        resolve(config["instrument_lifecycle_source"]),
        sep="\t",
        names=["instrument", "list_date", "delist_date"],
        parse_dates=["list_date", "delist_date"],
    ).drop_duplicates("instrument", keep="last")
    state = score.merge(intervals, on="instrument", how="left", validate="many_to_one")
    state["board"] = state["instrument"].map(infer_board)
    state["listed"] = state["list_date"].notna() & state["datetime"].ge(state["list_date"])
    state["delisted"] = state["delist_date"].notna() & state["datetime"].gt(state["delist_date"])
    state["ipo_age"] = (state["datetime"] - state["list_date"]).dt.days
    state["st_flag"] = pd.Series(pd.NA, index=state.index, dtype="boolean")
    state["suspended"] = pd.Series(pd.NA, index=state.index, dtype="boolean")
    state["previous_close"] = float("nan")
    state["state_available_at"] = state["datetime"] + pd.Timedelta(hours=9)
    state["source_artifact_id"] = "provider_lifecycle:community_20260609"
    rules = load_yaml(resolve(config["trading_rules"]))

    state["price_limit_rule_id"] = "unresolved_missing_historical_st_state"
    state["lot_rule_id"] = state["board"].map(
        lambda board: (
            resolve_lot_rule(rules, board=board, side="buy")["rule_id"]
            if board in {"main", "star", "chinext"} else "unresolved_unknown_board"
        )
    )
    # An explicit non-authoritative approximation is retained for execution only.
    state["execution_st_flag_approximation"] = False
    state["execution_suspended_approximation"] = False
    state["execution_price_limit_rule_id"] = state.apply(
        lambda row: (
            resolve_price_limit_rule(
                rules,
                board=row["board"],
                st_flag=False,
                ipo_age=max(1, int(row["ipo_age"])) if pd.notna(row["ipo_age"]) else None,
                trading_date=row["datetime"],
            )["rule_id"]
            if row["board"] in {"main", "star", "chinext"} and pd.notna(row["ipo_age"])
            else "unresolved"
        ),
        axis=1,
    )
    state = state.sort_values(["outer_split_id", "datetime", "instrument"], kind="stable")
    output_dir = resolve(config["instrument_state_output"] + ("/canary" if args.canary else ""))
    controlled = COMPACT_OUTPUTS + ["runtime/instrument_state.parquet"]
    with StageOutputPublisher(output_dir, controlled) as publisher:
        runtime = publisher.path("runtime/instrument_state.parquet")
        state.to_parquet(runtime, index=False)
        runtime_sha = file_sha256(runtime)
        coverage = pd.DataFrame([{
            "row_count": len(state),
            "instrument_count": state["instrument"].nunique(),
            "date_count": state["datetime"].nunique(),
            "lifecycle_coverage": float(state["list_date"].notna().mean()),
            "board_coverage": float(state["board"].ne("unknown").mean()),
            "st_flag_authoritative_coverage": float(state["st_flag"].notna().mean()),
            "suspension_authoritative_coverage": float(state["suspended"].notna().mean()),
            "terminal_event_authoritative_coverage": 0.0,
            "runtime_sha256": runtime_sha,
        }])
        contract = pd.DataFrame([
            {"check_name": "score_runtime_hash_valid", "status": "pass", "observed_value": True, "required_value": True, "severity": "critical", "reason": ""},
            {"check_name": "lifecycle_source_complete_for_score_keys", "status": "pass" if coverage.iloc[0]["lifecycle_coverage"] == 1 else "blocked", "observed_value": coverage.iloc[0]["lifecycle_coverage"], "required_value": 1.0, "severity": "critical", "reason": ""},
            {"check_name": "instrument_state_pit_valid", "status": "blocked", "observed_value": "historical_st_suspension_terminal_missing", "required_value": "authoritative complete", "severity": "capability", "reason": "Provider has listing intervals and OHLCVA but no authoritative historical ST, pre-open suspension, or terminal-event feed."},
            {"check_name": "price_limit_rule_resolved", "status": "blocked", "observed_value": "explicit_non_authoritative_st_false_approximation", "required_value": "historical ST state resolved", "severity": "capability", "reason": "No uniform 10% fallback is presented as authoritative."},
            {"check_name": "lot_rule_resolved", "status": "pass" if state["lot_rule_id"].str.startswith(("main_", "star_", "chinext_")).all() else "blocked", "observed_value": int(state["lot_rule_id"].nunique()), "required_value": "all score keys", "severity": "critical", "reason": ""},
        ])
        coverage.to_csv(publisher.path("instrument_state_coverage.csv"), index=False, encoding="utf-8-sig")
        contract.to_csv(publisher.path("contract_status.csv"), index=False, encoding="utf-8-sig")
        pd.DataFrame([{"path": str(runtime), "rows": len(state), "sha256": runtime_sha}]).to_csv(
            publisher.path("instrument_state_artifact.csv"), index=False, encoding="utf-8-sig"
        )
        publisher.path("resolved_config.json").write_text(
            json.dumps(config, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        publisher.path("instrument_state_report.md").write_text(
            "# PIT Instrument State V1\n\n"
            f"- Scope: `{'canary' if args.canary else 'full corrected OOS'}`\n"
            f"- Rows / instruments / dates: `{len(state)}` / `{state['instrument'].nunique()}` / `{state['datetime'].nunique()}`\n"
            "- Listing lifecycle, board and IPO age are materialized from the frozen provider lifecycle.\n"
            "- Historical ST, pre-open suspension and terminal-event state are unavailable and fail closed for authoritative readiness.\n"
            "- `execution_*_approximation` columns are explicit non-authoritative inputs; they are never evidence of PIT completeness.\n",
            encoding="utf-8",
        )
        code_state = capture_code_state(PROJECT_ROOT)
        input_manifests = [resolve(config["score_manifest"]), resolve(config["universe_manifest"])]
        score_manifest = load_artifact_manifest(input_manifests[0])
        write_stage_artifact_manifest(
            project_root=PROJECT_ROOT,
            stage_id="instrument_state_v1",
            config={**config, "scope": "canary" if args.canary else "full"},
            output_dir=publisher.staging_dir,
            output_files=[publisher.path(name) for name in COMPACT_OUTPUTS if name != "artifact_manifest.json"],
            code_state=code_state,
            input_manifest_paths=input_manifests,
            factor_frame_id=score_manifest["factor_frame_id"],
            split_manifest_id=score_manifest["split_manifest_id"],
            start_date=state["datetime"].min(),
            end_date=state["datetime"].max(),
            lineage_status="complete",
            artifact_status="pass",
        )
        publisher.publish()
    print(coverage.to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
