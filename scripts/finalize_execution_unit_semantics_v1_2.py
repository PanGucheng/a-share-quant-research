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

from research_validation.lineage import (  # noqa: E402
    capture_code_state,
    load_artifact_manifest,
    write_stage_artifact_manifest,
)
from research_validation.stage_output import StageOutputPublisher  # noqa: E402


OUTPUTS = [
    "artifact_manifest.json",
    "contract_status.csv",
    "readiness_summary.csv",
    "instrument_unit_attribution.csv",
    "unit_supersession.csv",
    "governance_report.md",
    "resolved_config.json",
]


def resolve(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else (PROJECT_ROOT / path).resolve()


def _assert_manifest_ready(path: Path) -> dict[str, object]:
    manifest = load_artifact_manifest(path)
    if manifest["artifact_status"] != "pass":
        raise ValueError(f"parent artifact is not pass: {path}")
    if manifest["lineage_status"] != "complete":
        raise ValueError(f"parent lineage is not complete: {path}")
    if bool(manifest["code_dirty"]):
        raise ValueError(f"parent artifact was produced from dirty code: {path}")
    return manifest


def _aggregate_fills(path: Path, prefix: str) -> pd.DataFrame:
    frame = pd.read_parquet(path)
    grouped = (
        frame.groupby("instrument", as_index=False)
        .agg(
            fill_count=("event_id", "size"),
            buy_executed_shares=(
                "executed_shares",
                lambda values: float(
                    values[frame.loc[values.index, "side"].eq("buy")].sum()
                ),
            ),
            sell_executed_shares=(
                "executed_shares",
                lambda values: float(
                    values[frame.loc[values.index, "side"].eq("sell")].sum()
                ),
            ),
            gross_value=("gross_value", "sum"),
            cash_fee=("cash_fee", "sum"),
            slippage_cost=("slippage_cost", "sum"),
        )
        .rename(columns=lambda name: name if name == "instrument" else f"{prefix}_{name}")
    )
    return grouped


def _update_central_governance(
    config: dict[str, object], execution_artifact_id: str
) -> dict[str, object]:
    readiness_path = resolve(config["central_readiness"])
    readiness = pd.read_csv(readiness_path)
    if len(readiness) != 1:
        raise ValueError("central readiness must contain exactly one row")
    updates: dict[str, object] = {
        "data_source_audit_v2_ready": True,
        "execution_unit_semantics_ready": True,
        "market_cache_volume_unit_ready": True,
        "market_cache_amount_unit_ready": True,
        "execution_semantics_accuracy_ready": True,
        "market_cache_v2_ready": False,
        "market_cache_v3_ready": True,
        "authoritative_oos_execution_ready": False,
        "core_model_ready": False,
        "pr5_model_training_ready": False,
        "model_training_started": False,
        "model_entry_hard_stop_active": True,
        "accuracy_correction_status": (
            "execution_unit_semantics_corrected_authoritative_state_blocked"
        ),
        "unbiased_final_estimate": False,
    }
    for key, value in updates.items():
        readiness[key] = value
    readiness.to_csv(readiness_path, index=False, encoding="utf-8-sig")

    contract_path = resolve(config["central_contracts"])
    contracts = pd.read_csv(contract_path)
    changes = {
        "accuracy_correction_status": (
            updates["accuracy_correction_status"],
            updates["accuracy_correction_status"],
            "V1.2 unit semantics are corrected; authoritative historical state remains unavailable.",
        ),
        "execution_semantics_accuracy_ready": (
            True,
            True,
            "Market Cache v3 and corrected execution pass all critical unit semantics contracts.",
        ),
        "market_cache_v2_ready": (
            False,
            False,
            "Market Cache v2 remains superseded and is never re-authorized.",
        ),
        "execution_unit_semantics_ready": (
            True,
            True,
            "Volume and amount units are explicit and full corrected execution passed.",
        ),
        "market_cache_volume_unit_ready": (
            True,
            True,
            "Community volume is converted from adjusted board lots to shares with factor*100.",
        ),
    }
    for name, (observed, required, reason) in changes.items():
        mask = contracts["check_name"].eq(name)
        if mask.sum() != 1:
            raise ValueError(f"missing unique central contract: {name}")
        contracts.loc[
            mask, ["status", "observed_value", "required_value", "reason"]
        ] = ["pass", observed, required, reason]
    additions = pd.DataFrame(
        [
            {
                "check_name": "market_cache_amount_unit_ready",
                "status": "pass",
                "observed_value": True,
                "required_value": True,
                "severity": "critical",
                "reason": "Community amount is converted from CNY thousands to CNY with *1000.",
            },
            {
                "check_name": "market_cache_v3_ready",
                "status": "pass",
                "observed_value": True,
                "required_value": True,
                "severity": "critical",
                "reason": "Market Cache v3 passed full unit correction and lineage contracts.",
            },
        ]
    )
    contracts = pd.concat(
        [contracts.loc[~contracts["check_name"].isin(additions["check_name"])], additions],
        ignore_index=True,
    )
    contracts.to_csv(contract_path, index=False, encoding="utf-8-sig")

    selection_path = resolve(config["central_selection_status"])
    selections = pd.read_csv(selection_path)
    mask = selections["selection_name"].eq(
        "split_specific_accuracy_corrected_allowlists_v2"
    )
    if mask.sum() != 1:
        raise ValueError("corrected selection status is not unique")
    selections.loc[mask, "selection_status"] = (
        "research_and_unit_accuracy_ready_authoritative_state_blocked"
    )
    selections.loc[mask, "superseded_by"] = execution_artifact_id
    selections.loc[mask, "reason"] = (
        "Research selection and execution unit semantics are corrected, but historical "
        "ST, before-open suspension and terminal-event authority remain blocked."
    )
    selections.loc[mask, "model_input_allowed"] = False
    selections.to_csv(selection_path, index=False, encoding="utf-8-sig")
    return updates


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Finalize V1.2 unit attribution and fail-closed governance."
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/execution_unit_semantics_correction_v1_2.yaml"),
    )
    args = parser.parse_args()
    config = yaml.safe_load(resolve(args.config).read_text(encoding="utf-8")) or {}

    execution_dir = resolve(config["execution_output"])
    cache_dir = resolve(config["market_cache_output"])
    freeze_dir = resolve(config["bugfix_freeze_output"])
    old_execution_dir = resolve("outputs/execution_accuracy_correction_v1/current")
    parent_paths = [
        execution_dir / "artifact_manifest.json",
        cache_dir / "artifact_manifest.json",
        freeze_dir / "artifact_manifest.json",
        resolve(config["data_source_audit_manifest"]),
        resolve(config["score_manifest"]),
        resolve(config["selection_closure_manifest"]),
        resolve(config["matrix_manifest"]),
        old_execution_dir / "artifact_manifest.json",
    ]
    manifests = [_assert_manifest_ready(path) for path in parent_paths]
    execution = manifests[0]
    cache = manifests[1]
    score = manifests[4]
    selection = manifests[5]
    matrix = manifests[6]

    score_receipt = pd.read_csv(resolve(config["score_receipt"]))
    if len(score_receipt) != 1:
        raise ValueError("score receipt must contain exactly one row")
    score_sha = str(score_receipt.iloc[0]["sha256"])

    cache_contracts = pd.read_csv(cache_dir / "contract_status.csv")
    execution_contracts = pd.read_csv(execution_dir / "contract_status.csv")
    cache_critical_ready = cache_contracts.loc[
        cache_contracts["severity"].eq("critical"), "status"
    ].eq("pass").all()
    execution_critical_ready = execution_contracts.loc[
        execution_contracts["severity"].eq("critical"), "status"
    ].eq("pass").all()
    comparison = pd.read_csv(execution_dir / "execution_summary_comparison.csv")
    attribution = pd.read_csv(execution_dir / "old_vs_new_attribution.csv")
    unknown_count = int(attribution["category"].eq("unknown").mul(
        ~attribution["status"].eq("none")
    ).sum())

    old_fill = _aggregate_fills(old_execution_dir / "runtime/fills.parquet", "old")
    new_fill = _aggregate_fills(execution_dir / "runtime/fills.parquet", "new")
    instrument = old_fill.merge(new_fill, on="instrument", how="outer").fillna(0)
    metrics = [
        "fill_count",
        "buy_executed_shares",
        "sell_executed_shares",
        "gross_value",
        "cash_fee",
        "slippage_cost",
    ]
    for metric in metrics:
        instrument[f"delta_{metric}"] = (
            instrument[f"new_{metric}"] - instrument[f"old_{metric}"]
        )
    focus = {str(item) for item in config.get("focus_instruments", [])}
    for item in sorted(focus - set(instrument["instrument"].astype(str))):
        instrument = pd.concat(
            [instrument, pd.DataFrame([{"instrument": item}])], ignore_index=True
        ).fillna(0)
    instrument["is_focus_instrument"] = instrument["instrument"].astype(str).isin(focus)
    instrument["absolute_gross_value_impact"] = instrument["delta_gross_value"].abs()
    instrument = instrument.sort_values(
        ["is_focus_instrument", "absolute_gross_value_impact", "instrument"],
        ascending=[False, False, True],
    ).reset_index(drop=True)

    checks = [
        (
            "market_cache_v3_critical_contracts",
            bool(cache_critical_ready),
            True,
        ),
        (
            "execution_v1_2_critical_contracts",
            bool(execution_critical_ready),
            True,
        ),
        ("score_business_payload_unchanged", score_sha, config["expected_score_runtime_sha256"]),
        ("matrix_v4_artifact_unchanged", matrix["artifact_id"], config["expected_matrix_artifact_id"]),
        (
            "selection_artifact_unchanged",
            selection["artifact_id"],
            config["expected_selection_artifact_id"],
        ),
        ("execution_comparison_scenarios", len(comparison), 6),
        ("unknown_semantic_difference_count", unknown_count, 0),
        (
            "execution_unit_semantics_ready",
            execution_contracts.set_index("check_name").loc[
                "execution_unit_semantics_ready", "status"
            ],
            "pass",
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
    )
    ready = contracts["status"].eq("pass").all()
    if not ready:
        raise ValueError("V1.2 governance prerequisites are not all satisfied")

    updates = _update_central_governance(config, str(execution["artifact_id"]))
    readiness = {
        **updates,
        "matrix_v4_artifact_unchanged": True,
        "selection_artifact_unchanged": True,
        "score_business_payload_unchanged": True,
        "execution_comparison_scenario_count": len(comparison),
        "unknown_semantic_difference_count": unknown_count,
        "historical_oos_comparison_complete": False,
        "production_model_selected": False,
    }
    supersession = pd.DataFrame(
        [
            {
                "artifact_type": "market_cache",
                "superseded_artifact": manifests[7]["input_artifact_ids"][1]
                if len(manifests[7]["input_artifact_ids"]) > 1
                else "market_cache_v2",
                "corrected_artifact": cache["artifact_id"],
                "status": "superseded_unit_error",
            },
            {
                "artifact_type": "execution",
                "superseded_artifact": manifests[7]["artifact_id"],
                "corrected_artifact": execution["artifact_id"],
                "status": "corrected_non_authoritative",
            },
        ]
    )

    output_dir = resolve(config["governance_output"])
    with StageOutputPublisher(output_dir, OUTPUTS) as publisher:
        contracts.to_csv(publisher.path("contract_status.csv"), index=False, encoding="utf-8-sig")
        pd.DataFrame([readiness]).to_csv(
            publisher.path("readiness_summary.csv"), index=False, encoding="utf-8-sig"
        )
        instrument.to_csv(
            publisher.path("instrument_unit_attribution.csv"),
            index=False,
            encoding="utf-8-sig",
        )
        supersession.to_csv(
            publisher.path("unit_supersession.csv"), index=False, encoding="utf-8-sig"
        )
        focus_rows = instrument.loc[instrument["is_focus_instrument"]]
        publisher.path("governance_report.md").write_text(
            "# Execution Unit Semantics Correction V1.2 Governance\n\n"
            "- Market Cache v3 converts Community volume with `factor × 100` shares and amount with `×1000` CNY.\n"
            "- The frozen score, Matrix v4 and split-specific selection artifacts are byte/ID unchanged.\n"
            f"- Full old/new execution comparison covers `{len(comparison)}` split-method scenarios; unknown differences: `{unknown_count}`.\n"
            f"- Instrument attribution rows: `{len(instrument)}`; focus rows: `{len(focus_rows)}`.\n"
            "- Research and unit semantics are ready, but historical ST, before-open suspension and terminal-event authority remain blocked.\n"
            "- `core_model_ready`, `pr5_model_training_ready` and `model_training_started` remain false.\n",
            encoding="utf-8",
        )
        publisher.path("resolved_config.json").write_text(
            json.dumps(config, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        write_stage_artifact_manifest(
            project_root=PROJECT_ROOT,
            stage_id=str(config["governance_stage_id"]),
            config=config,
            output_dir=publisher.staging_dir,
            output_files=[
                publisher.path(name) for name in OUTPUTS if name != "artifact_manifest.json"
            ],
            code_state=capture_code_state(PROJECT_ROOT),
            input_manifest_paths=parent_paths,
            universe_artifact_id=execution["universe_artifact_id"],
            split_manifest_id=execution["split_manifest_id"],
            factor_catalog_id=execution["factor_catalog_id"],
            factor_frame_id=execution["factor_frame_id"],
            start_date=execution["start_date"],
            end_date=execution["end_date"],
            artifact_status="pass",
        )
        publisher.publish()
    print(contracts.to_string(index=False))
    print(instrument.loc[instrument["is_focus_instrument"]].to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
