from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import pandas as pd
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from research_validation.feature_matrix import file_sha256  # noqa: E402
from research_validation.lineage import (  # noqa: E402
    capture_code_state,
    load_artifact_manifest,
    write_stage_artifact_manifest,
)
from research_validation.stage_output import StageOutputPublisher  # noqa: E402


COMPACT = [
    "artifact_manifest.json",
    "scope_manifest.csv",
    "terminal_approximation_inventory.csv",
    "terminal_instrument_summary.csv",
    "state_boundary_candidates.csv",
    "contract_status.csv",
    "readiness_summary.csv",
    "scope_report.md",
    "resolved_config.json",
]
RUNTIME = [
    "runtime/decision_scope.parquet",
    "runtime/valuation_scope.parquet",
]


def resolve(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else (PROJECT_ROOT / path).resolve()


def key_hash(frame: pd.DataFrame, columns: list[str]) -> str:
    ordered = frame.loc[:, columns].astype(str).sort_values(columns, kind="stable")
    row_hashes = pd.util.hash_pandas_object(
        ordered, index=False, categorize=False
    ).to_numpy(dtype="uint64", copy=False)
    digest = hashlib.sha256()
    digest.update("\x1f".join(columns).encode("utf-8"))
    digest.update(row_hashes.tobytes())
    return digest.hexdigest()


def require_parent(path: Path) -> dict[str, object]:
    manifest = load_artifact_manifest(path)
    if manifest["artifact_status"] != "pass":
        raise ValueError(f"parent artifact is not pass: {path}")
    if manifest["lineage_status"] != "complete":
        raise ValueError(f"parent lineage is not complete: {path}")
    if bool(manifest["code_dirty"]):
        raise ValueError(f"parent artifact is dirty: {path}")
    return manifest


def build_boundary_candidates(baostock: pd.DataFrame) -> pd.DataFrame:
    frame = baostock.sort_values(["instrument", "date"], kind="stable").copy()
    frame["previous_is_st"] = frame.groupby("instrument")["is_st"].shift()
    frame["previous_is_trading"] = frame.groupby("instrument")["is_trading"].shift()
    st = frame.loc[
        frame["previous_is_st"].notna()
        & frame["is_st"].ne(frame["previous_is_st"]),
        ["instrument", "date", "previous_is_st", "is_st", "source_row_id"],
    ].rename(
        columns={
            "previous_is_st": "old_value",
            "is_st": "new_value",
        }
    )
    st["state_type"] = "st"
    trading = frame.loc[
        frame["previous_is_trading"].notna()
        & frame["is_trading"].ne(frame["previous_is_trading"]),
        [
            "instrument",
            "date",
            "previous_is_trading",
            "is_trading",
            "source_row_id",
        ],
    ].rename(
        columns={
            "previous_is_trading": "old_value",
            "is_trading": "new_value",
        }
    )
    trading["state_type"] = "tradestatus"
    candidates = pd.concat([st, trading], ignore_index=True)
    candidates["candidate_source"] = "baostock"
    candidates["source_tier"] = "tier_1"
    candidates["available_before_open"] = "unknown"
    candidates["official_evidence_status"] = "pending"
    candidates["window_start"] = pd.to_datetime(candidates["date"]) - pd.Timedelta(
        days=10
    )
    candidates["window_end"] = pd.to_datetime(candidates["date"]) + pd.Timedelta(
        days=10
    )
    return candidates.sort_values(
        ["state_type", "instrument", "date"], kind="stable"
    ).reset_index(drop=True)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Freeze Historical Instrument State V2 affected scope."
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/historical_instrument_state_v2.yaml"),
    )
    args = parser.parse_args()
    config = yaml.safe_load(resolve(args.config).read_text(encoding="utf-8")) or {}

    score_path = resolve(config["score_runtime"])
    receipt = pd.read_csv(resolve(config["score_receipt"]))
    if len(receipt) != 1:
        raise ValueError("score receipt must contain exactly one row")
    score_sha = file_sha256(score_path)
    expected_score_sha = str(config["expected_score_runtime_sha256"])
    if score_sha != expected_score_sha or score_sha != str(receipt.iloc[0]["sha256"]):
        raise ValueError("frozen score runtime hash mismatch")

    execution_dir = resolve(config["execution_output"])
    decision = pd.read_parquet(
        score_path, columns=["datetime", "instrument", "outer_split_id"]
    ).drop_duplicates()
    decision["datetime"] = pd.to_datetime(decision["datetime"]).dt.normalize()
    positions = pd.read_parquet(
        execution_dir / "runtime/positions.parquet",
        columns=["datetime", "instrument", "outer_split_id", "method"],
    ).drop_duplicates()
    positions["datetime"] = pd.to_datetime(positions["datetime"]).dt.normalize()
    valuation = positions.sort_values(
        ["outer_split_id", "method", "datetime", "instrument"], kind="stable"
    ).reset_index(drop=True)

    fills = pd.read_parquet(execution_dir / "runtime/fills.parquet")
    terminal = fills.loc[
        fills["reason"]
        .fillna("")
        .str.contains("terminal_event_settlement_approximation")
    ].copy()
    terminal["current_semantics"] = "synthetic_last_price_liquidation"
    terminal["authoritative_semantics"] = "blocked_suspension_not_disposition"
    terminal["authoritative_evidence_status"] = "pending_tier_0"
    terminal = terminal.sort_values(
        ["instrument", "datetime", "outer_split_id", "method"], kind="stable"
    )
    terminal_summary = (
        terminal.groupby("instrument", as_index=False)
        .agg(
            fill_count=("event_id", "size"),
            first_approximation_date=("datetime", "min"),
            last_approximation_date=("datetime", "max"),
            executed_shares=("executed_shares", "sum"),
            gross_value=("gross_value", "sum"),
            cash_fee=("cash_fee", "sum"),
        )
        .sort_values("instrument")
    )

    snapshot_index = pd.read_csv(resolve(config["data_source_audit_snapshot_manifest"]))
    baostock_path = resolve(config["baostock_normalized_snapshot"])
    expected_snapshot = snapshot_index.loc[
        snapshot_index["path"].eq("normalized/baostock_daily.parquet"), "sha256"
    ]
    if len(expected_snapshot) != 1 or file_sha256(baostock_path) != str(
        expected_snapshot.iloc[0]
    ):
        raise ValueError("BaoStock normalized snapshot hash mismatch")
    baostock = pd.read_parquet(baostock_path)
    boundaries = build_boundary_candidates(baostock)

    focus = set(str(item) for item in config["terminal_focus_instruments"])
    observed_terminal = set(terminal["instrument"].astype(str))
    parents = [
        resolve(config["score_manifest"]),
        resolve(config["execution_manifest"]),
        resolve(config["market_cache_manifest"]),
        resolve(config["universe_manifest"]),
        resolve(config["data_source_audit_manifest"]),
    ]
    parent_manifests = [require_parent(path) for path in parents]
    score_manifest = parent_manifests[0]

    output_dir = resolve(config["scope_output"])
    controlled = COMPACT + RUNTIME
    with StageOutputPublisher(output_dir, controlled) as publisher:
        decision_path = publisher.path("runtime/decision_scope.parquet")
        valuation_path = publisher.path("runtime/valuation_scope.parquet")
        decision.to_parquet(decision_path, index=False)
        valuation.to_parquet(valuation_path, index=False)
        scope = pd.DataFrame(
            [
                {
                    "scope_name": "decision_scope",
                    "row_count": len(decision),
                    "instrument_count": decision["instrument"].nunique(),
                    "date_count": decision["datetime"].nunique(),
                    "key_sha256": key_hash(
                        decision, ["datetime", "instrument", "outer_split_id"]
                    ),
                    "runtime_sha256": file_sha256(decision_path),
                    "runtime_path": "runtime/decision_scope.parquet",
                },
                {
                    "scope_name": "valuation_scope",
                    "row_count": len(valuation),
                    "instrument_count": valuation["instrument"].nunique(),
                    "date_count": valuation["datetime"].nunique(),
                    "key_sha256": key_hash(
                        valuation,
                        [
                            "datetime",
                            "instrument",
                            "outer_split_id",
                            "method",
                        ],
                    ),
                    "runtime_sha256": file_sha256(valuation_path),
                    "runtime_path": "runtime/valuation_scope.parquet",
                },
                {
                    "scope_name": "state_boundary_scope",
                    "row_count": len(boundaries),
                    "instrument_count": boundaries["instrument"].nunique(),
                    "date_count": boundaries["date"].nunique(),
                    "key_sha256": key_hash(
                        boundaries, ["state_type", "instrument", "date"]
                    ),
                    "runtime_sha256": "",
                    "runtime_path": "state_boundary_candidates.csv",
                },
                {
                    "scope_name": "terminal_scope",
                    "row_count": len(terminal),
                    "instrument_count": terminal["instrument"].nunique(),
                    "date_count": terminal["datetime"].nunique(),
                    "key_sha256": key_hash(
                        terminal,
                        [
                            "datetime",
                            "instrument",
                            "outer_split_id",
                            "method",
                            "event_id",
                        ],
                    ),
                    "runtime_sha256": "",
                    "runtime_path": "terminal_approximation_inventory.csv",
                },
            ]
        )
        checks = [
            ("score_payload_unchanged", score_sha, expected_score_sha),
            ("decision_scope_nonempty", len(decision) > 0, True),
            ("valuation_scope_nonempty", len(valuation) > 0, True),
            ("state_boundary_scope_nonempty", len(boundaries) > 0, True),
            ("terminal_approximation_count", len(terminal), 8),
            ("terminal_instrument_count", terminal["instrument"].nunique(), 3),
            ("terminal_focus_exact", observed_terminal == focus, True),
            (
                "all_consumed_parents_ready",
                len(parent_manifests),
                len(parents),
            ),
            (
                "synthetic_terminal_liquidation_authoritative",
                False,
                False,
            ),
        ]
        contracts = pd.DataFrame(
            [
                {
                    "check_name": name,
                    "status": "pass" if observed == required else "blocked",
                    "observed_value": observed,
                    "required_value": required,
                    "severity": "critical",
                    "reason": "",
                }
                for name, observed, required in checks
            ]
            + [
                {
                    "check_name": "official_event_evidence_complete",
                    "status": "blocked",
                    "observed_value": 0,
                    "required_value": "canary minimums",
                    "severity": "capability",
                    "reason": "Tier-0 event canary is the next phase.",
                }
            ]
        )
        critical_ready = contracts.loc[
            contracts["severity"].eq("critical"), "status"
        ].eq("pass").all()
        readiness = {
            "scope_frozen": bool(critical_ready),
            "terminal_approximation_inventory_complete": len(terminal) == 8,
            "evidence_schema_ready": False,
            "official_canary_complete": False,
            "candidate_source_reconciliation_complete": False,
            "historical_instrument_state_v2_ready": False,
            "authoritative_oos_execution_ready": False,
            "core_model_ready": False,
            "pr5_model_training_ready": False,
            "model_training_started": False,
            "model_entry_hard_stop_active": True,
            "historical_test_already_observed": True,
            "unbiased_final_estimate": False,
        }
        scope.to_csv(publisher.path("scope_manifest.csv"), index=False, encoding="utf-8-sig")
        terminal.to_csv(
            publisher.path("terminal_approximation_inventory.csv"),
            index=False,
            encoding="utf-8-sig",
        )
        terminal_summary.to_csv(
            publisher.path("terminal_instrument_summary.csv"),
            index=False,
            encoding="utf-8-sig",
        )
        boundaries.to_csv(
            publisher.path("state_boundary_candidates.csv"),
            index=False,
            encoding="utf-8-sig",
        )
        contracts.to_csv(
            publisher.path("contract_status.csv"), index=False, encoding="utf-8-sig"
        )
        pd.DataFrame([readiness]).to_csv(
            publisher.path("readiness_summary.csv"), index=False, encoding="utf-8-sig"
        )
        publisher.path("scope_report.md").write_text(
            "# Historical Instrument State V2 Scope Freeze\n\n"
            f"- Decision rows / instruments: `{len(decision)}` / `{decision['instrument'].nunique()}`.\n"
            f"- Valuation rows / instruments: `{len(valuation)}` / `{valuation['instrument'].nunique()}`.\n"
            f"- Tier-1 state-boundary candidates: `{len(boundaries)}` across `{boundaries['instrument'].nunique()}` instruments.\n"
            f"- Synthetic terminal fills: `{len(terminal)}` across `{terminal['instrument'].nunique()}` instruments.\n"
            "- The terminal fills are explicitly non-authoritative: a suspension or listing termination is not a cash disposition.\n"
            "- Official evidence is not yet complete; authoritative execution and every model-entry capability remain blocked.\n",
            encoding="utf-8",
        )
        publisher.path("resolved_config.json").write_text(
            json.dumps(config, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        write_stage_artifact_manifest(
            project_root=PROJECT_ROOT,
            stage_id=str(config["scope_stage_id"]),
            config=config,
            output_dir=publisher.staging_dir,
            output_files=[
                publisher.path(name)
                for name in COMPACT
                if name != "artifact_manifest.json"
            ],
            code_state=capture_code_state(PROJECT_ROOT),
            input_manifest_paths=parents,
            universe_artifact_id=score_manifest["universe_artifact_id"],
            split_manifest_id=score_manifest["split_manifest_id"],
            factor_catalog_id=score_manifest["factor_catalog_id"],
            factor_frame_id=score_manifest["factor_frame_id"],
            start_date=decision["datetime"].min(),
            end_date=decision["datetime"].max(),
            artifact_status="pass" if critical_ready else "blocked",
            blocked_reason="" if critical_ready else "blocked_scope_contract",
        )
        publisher.publish()
    print(scope.to_string(index=False))
    print(terminal_summary.to_string(index=False))
    print(contracts.to_string(index=False))
    return 0 if critical_ready else 2


if __name__ == "__main__":
    raise SystemExit(main())
