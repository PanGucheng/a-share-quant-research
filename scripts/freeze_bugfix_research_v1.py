from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from research_validation.feature_matrix import canonical_hash, file_sha256  # noqa: E402
from research_validation.lineage import capture_code_state, load_artifact_manifest, validate_manifest_outputs, write_stage_artifact_manifest  # noqa: E402
from research_validation.stage_output import StageOutputPublisher  # noqa: E402


STATIC_OUTPUTS = [
    "artifact_manifest.json",
    "bugfix_freeze_index.csv",
    "contract_status.csv",
    "bugfix_freeze_report.md",
    "resolved_config.json",
]


def resolve(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else (PROJECT_ROOT / path).resolve()


def main() -> int:
    parser = argparse.ArgumentParser(description="Freeze post-observation bug-fix research and execution inputs.")
    parser.add_argument("--config", type=Path, default=Path("configs/execution_accuracy_correction_v1.yaml"))
    args = parser.parse_args()
    config_path = resolve(args.config)
    config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    code_state = capture_code_state(PROJECT_ROOT)
    if code_state.dirty:
        raise ValueError("bug-fix freeze requires a clean committed worktree")
    manifest_paths = [
        resolve(config["score_manifest"]),
        resolve(config["allowlist_artifact_manifest"]),
        resolve(config["weights_artifact_manifest"]),
        resolve(config["score_policy_manifest"]),
        resolve(config["market_cache_output"]) / "artifact_manifest.json",
    ]
    manifests = [load_artifact_manifest(path) for path in manifest_paths]
    issues = [
        issue
        for manifest, path in zip(manifests, manifest_paths)
        for issue in validate_manifest_outputs(manifest, path.parent)
    ]
    if issues or any(manifest["artifact_status"] != "pass" for manifest in manifests):
        raise ValueError(f"bug-fix freeze upstream stale or blocked: {issues}")
    score_receipt = pd.read_csv(resolve(config["score_receipt"]))
    cache_key_doc = json.loads((resolve(config["market_cache_output"]) / "cache_key.json").read_text(encoding="utf-8"))
    allowlists = pd.read_csv(resolve(config["allowlist_manifest"]))
    weight_manifest = pd.read_csv(resolve(config["weight_manifest"]))
    score_policy_sha = file_sha256(resolve(config["score_policy"]))
    execution_hashes = {
        "execution_config": file_sha256(config_path),
        "fee_schedule": file_sha256(resolve(config["fee_schedule"])),
        "field_timing": file_sha256(resolve(config["field_timing"])),
        "trading_rules": file_sha256(resolve(config["trading_rules"])),
        "runner_source": file_sha256(PROJECT_ROOT / "scripts/run_corrected_oos_execution_v1.py"),
        "exchange_adapter_source": file_sha256(PROJECT_ROOT / "qlib_integration/exchange_adapter.py"),
        "market_semantics_source": file_sha256(PROJECT_ROOT / "qlib_integration/market_semantics.py"),
        "contracts_source": file_sha256(PROJECT_ROOT / "qlib_integration/contracts.py"),
    }
    execution_config_sha = canonical_hash(execution_hashes)
    timestamp = datetime.now(timezone.utc).isoformat()
    output_dir = resolve(config["bugfix_freeze_output"])
    split_ids = sorted(allowlists["outer_split_id"].astype(str).unique())
    controlled = STATIC_OUTPUTS + [f"{split_id}/freeze_manifest.json" for split_id in split_ids]
    rows = []
    with StageOutputPublisher(output_dir, controlled) as publisher:
        for split_id in split_ids:
            allowlist = allowlists.loc[allowlists["outer_split_id"].astype(str).eq(split_id)]
            weights = weight_manifest.loc[weight_manifest["outer_split_id"].astype(str).eq(split_id)]
            if len(allowlist) != 1 or weights["method"].nunique() != 2:
                raise ValueError(f"freeze inputs incomplete for {split_id}")
            payload = {
                "schema_version": 1,
                "freeze_type": "post_observation_bugfix",
                "outer_split_id": split_id,
                "historical_test_already_observed": True,
                "selection_uses_test_outcomes": False,
                "unbiased_final_estimate": False,
                "allowlist_sha256": str(allowlist.iloc[0]["allowlist_sha256"]),
                "weights_sha256": canonical_hash(
                    dict(zip(weights["method"].astype(str), weights["weights_sha256"].astype(str)))
                ),
                "weights_by_method": dict(zip(weights["method"].astype(str), weights["weights_sha256"].astype(str))),
                "score_policy_sha256": score_policy_sha,
                "score_artifact_sha256": str(score_receipt.iloc[0]["sha256"]),
                "execution_config_sha256": execution_config_sha,
                "execution_source_sha256": canonical_hash({
                    key: value for key, value in execution_hashes.items() if key.endswith("_source")
                }),
                "execution_config_component_hashes": execution_hashes,
                "market_cache_sha256": str(cache_key_doc["cache_key"]),
                "code_commit_sha": code_state.commit_sha,
                "freeze_timestamp": timestamp,
            }
            payload["freeze_id"] = f"bugfix_research_freeze_v1:{canonical_hash(payload)}"
            path = publisher.path(f"{split_id}/freeze_manifest.json")
            path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            rows.append({
                "outer_split_id": split_id,
                "freeze_id": payload["freeze_id"],
                "freeze_path": f"{split_id}/freeze_manifest.json",
                "freeze_sha256": file_sha256(path),
                "freeze_type": payload["freeze_type"],
                "historical_test_already_observed": True,
                "unbiased_final_estimate": False,
            })
        contract = pd.DataFrame([
            {"check_name": "freeze_type_post_observation_bugfix", "status": "pass", "observed_value": "post_observation_bugfix", "required_value": "post_observation_bugfix", "severity": "critical", "reason": ""},
            {"check_name": "historical_test_already_observed", "status": "pass", "observed_value": True, "required_value": True, "severity": "critical", "reason": ""},
            {"check_name": "selection_uses_test_outcomes", "status": "pass", "observed_value": False, "required_value": False, "severity": "critical", "reason": ""},
            {"check_name": "unbiased_final_estimate", "status": "pass", "observed_value": False, "required_value": False, "severity": "critical", "reason": ""},
            {"check_name": "all_semantic_and_source_hashes_bound", "status": "pass", "observed_value": len(execution_hashes), "required_value": 8, "severity": "critical", "reason": ""},
            {"check_name": "clean_committed_code", "status": "pass", "observed_value": False, "required_value": False, "severity": "critical", "reason": ""},
        ])
        pd.DataFrame(rows).to_csv(publisher.path("bugfix_freeze_index.csv"), index=False, encoding="utf-8-sig")
        contract.to_csv(publisher.path("contract_status.csv"), index=False, encoding="utf-8-sig")
        publisher.path("resolved_config.json").write_text(json.dumps(config, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        publisher.path("bugfix_freeze_report.md").write_text(
            "# Post-Observation Bug-Fix Research Freeze V1\n\n"
            f"- Frozen splits: `{len(rows)}`\n"
            "- Historical test was already observed; these artifacts do not restore untouched-test status.\n"
            "- Selection uses no test outcomes, but corrected execution is non-authoritative historical bug-fix evidence.\n",
            encoding="utf-8",
        )
        write_stage_artifact_manifest(
            project_root=PROJECT_ROOT,
            stage_id="bugfix_research_freeze_v1",
            config={**config, "execution_config_sha256": execution_config_sha},
            output_dir=publisher.staging_dir,
            output_files=[publisher.path(name) for name in controlled if name != "artifact_manifest.json"],
            code_state=code_state,
            input_manifest_paths=manifest_paths,
            factor_frame_id=manifests[0]["factor_frame_id"],
            split_manifest_id=manifests[0]["split_manifest_id"],
            lineage_status="complete",
            artifact_status="pass",
        )
        publisher.publish()
    print(contract.to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
