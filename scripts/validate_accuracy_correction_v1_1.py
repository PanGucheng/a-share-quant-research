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
    validate_transitive_lineage,
    write_stage_artifact_manifest,
)
from research_validation.stage_output import StageOutputPublisher  # noqa: E402


OUTPUTS = [
    "artifact_manifest.json",
    "artifact_index.csv",
    "lineage_edges.csv",
    "lineage_issues.csv",
    "score_business_payload_check.csv",
    "contract_status.csv",
    "readiness_summary.csv",
    "accuracy_correction_v1_1_report.md",
    "resolved_config.json",
]


def resolve(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else (PROJECT_ROOT / path).resolve()


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Accuracy Correction V1.1 lineage closure.")
    parser.add_argument("--config", type=Path, default=Path("configs/accuracy_correction_v1_1.yaml"))
    args = parser.parse_args()
    config = yaml.safe_load(resolve(args.config).read_text(encoding="utf-8")) or {}
    semantics = yaml.safe_load(resolve(config["lineage_semantics"]).read_text(encoding="utf-8")) or {}
    start_paths = [resolve(path) for path in config["start_manifests"]]
    nodes, edges, issues = validate_transitive_lineage(
        outputs_root=PROJECT_ROOT / "outputs",
        start_manifest_paths=start_paths,
        semantics=semantics,
    )
    score = load_artifact_manifest(resolve(config["score_manifest"]))
    universe = load_artifact_manifest(resolve(config["universe_manifest"]))
    score_receipt = pd.read_csv(resolve(config["score_receipt"]))
    score_sha = str(score_receipt.iloc[0]["sha256"]) if len(score_receipt) == 1 else ""
    score_unchanged = score_sha == str(config["expected_score_runtime_sha256"])
    score_lineage_ready = (
        score["artifact_status"] == "pass"
        and score["lineage_status"] == "complete"
        and not bool(score["code_dirty"])
        and score["universe_artifact_id"] == universe["universe_artifact_id"]
    )
    state_contract = pd.read_csv(resolve(config["instrument_state_contract"]))
    state_critical = state_contract.loc[state_contract["severity"].eq("critical")]
    state_ready = state_critical["status"].eq("pass").all()
    state_coverage = pd.read_csv(resolve(config["instrument_state_coverage"])).iloc[0]
    unknown_board_count = int(
        state_contract.loc[
            state_contract["check_name"].eq("unknown_board_row_count"), "observed_value"
        ].iloc[0]
    )
    cache_contract = pd.read_csv(resolve(config["market_cache_contract"])).set_index("check_name")
    execution_contract = pd.read_csv(resolve(config["execution_contract"])).set_index("check_name")
    transitive_ready = not issues
    direct_parents_ready = all(
        row["status"] == "pass"
        for row in edges
        if row["child_stage_id"] in {
            "split_transparent_score_v2",
            "instrument_state_v1",
            "market_cache_v2",
            "bugfix_research_freeze_v1",
            "execution_accuracy_correction_v1",
        }
    )
    readiness = {
        "corrected_score_lineage_complete": bool(score_lineage_ready),
        "corrected_score_business_payload_unchanged": bool(score_unchanged),
        "unknown_board_row_count": unknown_board_count,
        "instrument_state_critical_contracts_pass": bool(state_ready),
        "all_consumed_direct_parent_lineage_complete": bool(direct_parents_ready),
        "transitive_lineage_validation_ready": bool(transitive_ready),
        "execution_semantics_accuracy_ready": bool(
            execution_contract.loc[
                execution_contract.index != "authoritative_oos_execution_ready"
            ]
            .loc[lambda frame: frame["severity"].eq("critical"), "status"]
            .eq("pass")
            .all()
        ),
        "market_cache_v2_ready": (
            cache_contract.loc["market_cache_v2_ready", "status"] == "pass"
        ),
        "future_market_field_count": int(
            cache_contract.loc["future_market_field_count", "observed_value"]
        ),
        "authoritative_oos_execution_ready": False,
        "core_model_ready": False,
        "pr5_model_training_ready": False,
        "model_training_started": False,
        "model_entry_hard_stop_active": True,
        "historical_test_already_observed": True,
        "unbiased_final_estimate": False,
    }
    critical_flags = [
        readiness["corrected_score_lineage_complete"],
        readiness["corrected_score_business_payload_unchanged"],
        readiness["unknown_board_row_count"] == 0,
        readiness["instrument_state_critical_contracts_pass"],
        readiness["all_consumed_direct_parent_lineage_complete"],
        readiness["transitive_lineage_validation_ready"],
        readiness["execution_semantics_accuracy_ready"],
        readiness["market_cache_v2_ready"],
        readiness["future_market_field_count"] == 0,
    ]
    contract = pd.DataFrame(
        [
            {
                "check_name": key,
                "status": "pass" if passed else "blocked",
                "observed_value": value,
                "required_value": expected,
                "severity": "critical",
                "reason": "",
            }
            for key, value, expected, passed in [
                ("corrected_score_lineage_complete", readiness["corrected_score_lineage_complete"], True, readiness["corrected_score_lineage_complete"]),
                ("corrected_score_business_payload_unchanged", score_sha, config["expected_score_runtime_sha256"], score_unchanged),
                ("unknown_board_row_count", unknown_board_count, 0, unknown_board_count == 0),
                ("instrument_state_critical_contracts_pass", state_ready, True, state_ready),
                ("all_consumed_direct_parent_lineage_complete", direct_parents_ready, True, direct_parents_ready),
                ("transitive_lineage_validation_ready", transitive_ready, True, transitive_ready),
                ("execution_semantics_accuracy_ready", readiness["execution_semantics_accuracy_ready"], True, readiness["execution_semantics_accuracy_ready"]),
                ("market_cache_v2_ready", readiness["market_cache_v2_ready"], True, readiness["market_cache_v2_ready"]),
                ("future_market_field_count", readiness["future_market_field_count"], 0, readiness["future_market_field_count"] == 0),
            ]
        ]
    )
    output_dir = resolve(config["output_dir"])
    with StageOutputPublisher(output_dir, OUTPUTS) as publisher:
        pd.DataFrame(nodes).to_csv(publisher.path("artifact_index.csv"), index=False, encoding="utf-8-sig")
        pd.DataFrame(edges).to_csv(publisher.path("lineage_edges.csv"), index=False, encoding="utf-8-sig")
        pd.DataFrame(
            [
                {
                    "check_name": issue.check_name,
                    "artifact_id": issue.artifact_id,
                    "stage_id": issue.stage_id,
                    "severity": issue.severity,
                    "reason": issue.reason,
                }
                for issue in issues
            ],
            columns=["check_name", "artifact_id", "stage_id", "severity", "reason"],
        ).to_csv(publisher.path("lineage_issues.csv"), index=False, encoding="utf-8-sig")
        pd.DataFrame(
            [
                {
                    "score_runtime_sha256": score_sha,
                    "expected_sha256": config["expected_score_runtime_sha256"],
                    "business_payload_unchanged": score_unchanged,
                    "row_count": int(score_receipt.iloc[0]["rows"]),
                }
            ]
        ).to_csv(publisher.path("score_business_payload_check.csv"), index=False, encoding="utf-8-sig")
        contract.to_csv(publisher.path("contract_status.csv"), index=False, encoding="utf-8-sig")
        pd.DataFrame([readiness]).to_csv(publisher.path("readiness_summary.csv"), index=False, encoding="utf-8-sig")
        publisher.path("accuracy_correction_v1_1_report.md").write_text(
            "# Accuracy Correction V1.1 Lineage & Gate Closure\n\n"
            f"- Transitive nodes / edges / issues: `{len(nodes)}` / `{len(edges)}` / `{len(issues)}`\n"
            f"- Corrected score payload unchanged: `{score_unchanged}`\n"
            f"- Unknown board rows: `{unknown_board_count}`\n"
            f"- Instrument-state board coverage: `{float(state_coverage['board_coverage']):.6f}`\n"
            "- Corrected historical OOS evidence remains post-observation and non-authoritative.\n"
            "- Model entry remains hard-stopped; this stage does not start PR #5A.\n",
            encoding="utf-8",
        )
        publisher.path("resolved_config.json").write_text(
            json.dumps(config, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        write_stage_artifact_manifest(
            project_root=PROJECT_ROOT,
            stage_id="accuracy_correction_v1_1",
            config=config,
            output_dir=publisher.staging_dir,
            output_files=[publisher.path(name) for name in OUTPUTS if name != "artifact_manifest.json"],
            code_state=capture_code_state(PROJECT_ROOT),
            input_manifest_paths=start_paths,
            universe_artifact_id=score["universe_artifact_id"],
            split_manifest_id=score["split_manifest_id"],
            factor_catalog_id=score["factor_catalog_id"],
            factor_frame_id=score["factor_frame_id"],
            start_date=score["start_date"],
            end_date=score["end_date"],
            artifact_status="pass" if all(critical_flags) else "blocked",
            blocked_reason="" if all(critical_flags) else "blocked_accuracy_correction_v1_1",
        )
        publisher.publish()
    print(contract.to_string(index=False))
    if issues:
        print(pd.DataFrame([issue.__dict__ for issue in issues]).to_string(index=False))
    return 0 if all(critical_flags) else 2


if __name__ == "__main__":
    raise SystemExit(main())
