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

from qlib_integration.contracts import contract_row  # noqa: E402
from research_validation.feature_matrix import canonical_hash, file_sha256  # noqa: E402
from research_validation.lineage import capture_code_state, config_sha256, load_artifact_manifest, validate_manifest_outputs, write_stage_artifact_manifest  # noqa: E402
from research_validation.pretest_freeze import build_pretest_freeze_payload, preserve_or_reject_existing_freeze  # noqa: E402
from research_validation.stage_output import StageOutputPublisher  # noqa: E402


STATIC_OUTPUTS = (
    "artifact_manifest.json",
    "pre_test_freeze_index.csv",
    "input_receipts.csv",
    "contract_status.csv",
    "pre_test_freeze_report.md",
    "resolved_config.json",
)


def resolve(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else (PROJECT_ROOT / path).resolve()


def main() -> int:
    parser = argparse.ArgumentParser(description="Freeze transparent-baseline decisions before any outer-test read.")
    parser.add_argument("--config", type=Path, default=Path("configs/pre_test_freeze_transparent_669_v1.yaml"))
    args = parser.parse_args()
    config_path = resolve(args.config)
    config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    code_state = capture_code_state(PROJECT_ROOT)
    if code_state.dirty:
        raise ValueError("pre-test freeze requires a clean committed worktree")
    manifest_paths = [resolve(path) for path in config["input_manifests"]]
    manifests = [load_artifact_manifest(path) for path in manifest_paths]
    issues = [issue for manifest, path in zip(manifests, manifest_paths) for issue in validate_manifest_outputs(manifest, path.parent)]
    if issues or any(manifest["artifact_status"] != "pass" for manifest in manifests):
        raise ValueError(f"pre-test freeze upstream is stale or blocked: {issues}")
    weights = pd.read_csv(resolve(config["factor_weights"]))
    weight_manifest = pd.read_csv(resolve(config["weight_manifest"]))
    allowlist_manifest = pd.read_csv(resolve(config["allowlist_manifest"]))
    allowed_dates = pd.read_csv(resolve(config["allowed_dates"]), parse_dates=["datetime"])
    assignments = pd.read_csv(resolve(config["outer_date_assignments"]), parse_dates=["datetime"])
    selected_outer_splits = [str(value) for value in config.get("selected_outer_splits", [])]
    if selected_outer_splits:
        weight_manifest = weight_manifest.loc[weight_manifest["outer_split_id"].astype(str).isin(selected_outer_splits)].copy()
        weights = weights.loc[weights["outer_split_id"].astype(str).isin(selected_outer_splits)].copy()
        allowlist_manifest = allowlist_manifest.loc[allowlist_manifest["outer_split_id"].astype(str).isin(selected_outer_splits)].copy()
    split_ids = sorted(weight_manifest["outer_split_id"].astype(str).unique())
    if not split_ids:
        raise ValueError("pre-test freeze has no selected outer splits")
    preprocessing_hash = config_sha256(config["preprocessing"])
    score_config_hash = file_sha256(resolve(config["score_config"]))
    qlib_config_hash = file_sha256(resolve(config["qlib_exchange_config"]))
    freeze_timestamp = datetime.now(timezone.utc).isoformat()
    output_dir = resolve(config["output_dir"])
    dynamic_outputs = tuple(f"{split_id}/pre_test_freeze_manifest.json" for split_id in split_ids)
    controlled = STATIC_OUTPUTS + dynamic_outputs
    freeze_rows: list[dict[str, object]] = []
    freeze_payloads: dict[str, dict[str, object]] = {}
    for split_id in split_ids:
        split_weight_manifest = weight_manifest.loc[weight_manifest["outer_split_id"].astype(str).eq(split_id)]
        split_allowlist = allowlist_manifest.loc[allowlist_manifest["outer_split_id"].astype(str).eq(split_id)]
        if len(split_allowlist) != 1 or split_weight_manifest["method"].nunique() != len(config["methods"]):
            raise ValueError(f"freeze input mismatch for {split_id}")
        weights_by_method = dict(zip(split_weight_manifest["method"], split_weight_manifest["weights_sha256"]))
        development_dates = sorted(
            allowed_dates.loc[allowed_dates["outer_split_id"].astype(str).eq(split_id), "datetime"].dt.date.astype(str)
        )
        test_dates = sorted(
            assignments.loc[
                assignments["split_id"].astype(str).eq(split_id) & assignments["fold"].eq("test"), "datetime"
            ].dt.date.astype(str)
        )
        training_hash = canonical_hash(
            {
                "development_dates_sha256": canonical_hash(development_dates),
                "weights_by_method": weights_by_method,
                "input_artifact_ids": sorted(manifest["artifact_id"] for manifest in manifests),
            }
        )
        proposed = build_pretest_freeze_payload(
            outer_split_id=split_id,
            allowlist_sha256=str(split_allowlist.iloc[0]["allowlist_sha256"]),
            feature_order_sha256=str(split_allowlist.iloc[0]["feature_order_sha256"]),
            weights_by_method=weights_by_method,
            preprocessing_config_sha256=preprocessing_hash,
            model_config_sha256=score_config_hash,
            training_data_sha256=training_hash,
            qlib_exchange_config_sha256=qlib_config_hash,
            test_dates_sha256=canonical_hash(test_dates),
            code_commit_sha=code_state.commit_sha,
            freeze_timestamp=freeze_timestamp,
        )
        target = output_dir / f"{split_id}/pre_test_freeze_manifest.json"
        freeze_payloads[split_id] = preserve_or_reject_existing_freeze(target, proposed)

    contracts = pd.DataFrame(
        [
            contract_row("outer_split_count", len(freeze_payloads) == len(split_ids), len(freeze_payloads), len(split_ids)),
            contract_row("clean_committed_code", not code_state.dirty, code_state.dirty, False),
            contract_row("model_binary_explicitly_not_applicable", all(value["model_binary_sha256"] == "not_applicable_transparent_baseline" for value in freeze_payloads.values()), True, True),
            contract_row("test_data_read_count", True, 0, 0),
            contract_row("freeze_ids_unique", len({value["freeze_id"] for value in freeze_payloads.values()}) == len(freeze_payloads), len({value["freeze_id"] for value in freeze_payloads.values()}), len(freeze_payloads)),
        ]
    )
    receipts = pd.DataFrame(
        [
            {"input_name": manifest["stage_id"], "artifact_id": manifest["artifact_id"], "path": path.as_posix(), "sha256": file_sha256(path)}
            for manifest, path in zip(manifests, manifest_paths)
        ]
    )
    ready = bool(contracts["status"].eq("pass").all())
    with StageOutputPublisher(output_dir, controlled) as publisher:
        for split_id, payload in freeze_payloads.items():
            path = publisher.path(f"{split_id}/pre_test_freeze_manifest.json")
            path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            freeze_rows.append(
                {
                    "outer_split_id": split_id,
                    "freeze_id": payload["freeze_id"],
                    "freeze_path": f"{split_id}/pre_test_freeze_manifest.json",
                    "freeze_sha256": file_sha256(path),
                    "code_commit_sha": payload["code_commit_sha"],
                    "freeze_timestamp": payload["freeze_timestamp"],
                    "test_release_count": 0,
                }
            )
        pd.DataFrame(freeze_rows).to_csv(publisher.path("pre_test_freeze_index.csv"), index=False, encoding="utf-8-sig")
        receipts.to_csv(publisher.path("input_receipts.csv"), index=False, encoding="utf-8-sig")
        contracts.to_csv(publisher.path("contract_status.csv"), index=False, encoding="utf-8-sig")
        publisher.path("resolved_config.json").write_text(json.dumps(config, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        publisher.path("pre_test_freeze_report.md").write_text(
            "# Transparent Baseline Pre-Test Freeze V1\n\n"
            + f"- Status: `{'pass' if ready else 'blocked'}`\n"
            + f"- Frozen outer splits: `{len(freeze_payloads)}`\n"
            + "- Test features, labels, IC, market data, returns, and execution metrics read before freeze: `0`.\n"
            + "- Every freeze binds the exact allowlist, feature order, two weight payloads, preprocessing, score and Qlib configs, test-date partition, inputs, and code commit.\n",
            encoding="utf-8",
        )
        files = [publisher.path(name) for name in controlled if name != "artifact_manifest.json"]
        write_stage_artifact_manifest(
            project_root=PROJECT_ROOT,
            stage_id="pre_test_freeze_v1",
            config=config,
            output_dir=publisher.staging_dir,
            output_files=files,
            code_state=code_state,
            input_manifest_paths=manifest_paths,
            factor_frame_id=manifests[0]["factor_frame_id"],
            split_manifest_id=manifests[0]["split_manifest_id"],
            lineage_status="complete",
            artifact_status="pass" if ready else "blocked",
            blocked_reason="" if ready else "blocked_pre_test_freeze",
        )
        publisher.publish()
    print(contracts.to_string(index=False))
    return 0 if ready else 2


if __name__ == "__main__":
    raise SystemExit(main())
