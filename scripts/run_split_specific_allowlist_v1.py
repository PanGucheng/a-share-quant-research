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

from qlib_integration.contracts import contract_row  # noqa: E402
from research_validation.feature_matrix import canonical_hash, file_sha256  # noqa: E402
from research_validation.lineage import capture_code_state, load_artifact_manifest, validate_manifest_outputs, write_stage_artifact_manifest  # noqa: E402
from research_validation.stage_output import StageOutputPublisher  # noqa: E402

CONTROLLED = (
    "artifact_manifest.json", "split_allowlist.csv", "split_allowlist_manifest.csv", "selection_status.csv",
    "selection_date_audit.csv", "input_receipts.csv", "contract_status.csv", "split_allowlist_report.md",
    "resolved_config.json",
)


def resolve(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else (PROJECT_ROOT / path).resolve()


def allowlist_payload_hash(frame: pd.DataFrame) -> str:
    columns = ["factor", "frozen_direction", "cluster_id"]
    return canonical_hash(frame[columns].sort_values("factor", kind="stable").to_dict("records"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Freeze one holdout-clean factor allowlist per outer split.")
    parser.add_argument("--config", type=Path, default=Path("configs/split_specific_allowlist_669_v1.yaml"))
    args = parser.parse_args()
    config = yaml.safe_load(resolve(args.config).read_text(encoding="utf-8")) or {}
    manifest_paths = [resolve(path) for path in config["input_manifests"]]
    manifests = [load_artifact_manifest(path) for path in manifest_paths]
    issues = [issue for manifest, path in zip(manifests, manifest_paths) for issue in validate_manifest_outputs(manifest, path.parent)]
    if issues or any(manifest["artifact_status"] != "pass" for manifest in manifests):
        raise ValueError("split allowlist upstream is stale or blocked")
    clustering_contract = pd.read_csv(resolve(config["clustering_contract"]))
    if not clustering_contract["status"].eq("pass").all():
        raise ValueError("split clustering contract is not fully passing")
    representatives = pd.read_csv(resolve(config["representatives"]))
    stability = pd.read_csv(resolve(config["stability_board"]))
    allowed = pd.read_csv(resolve(config["allowed_dates"]), parse_dates=["datetime"])
    outer = pd.read_csv(resolve(config["outer_split_manifest"]), parse_dates=["train_start", "train_end", "validation_start", "validation_end", "test_start", "test_end"])
    audit = pd.read_csv(resolve(config["selection_date_audit"]))
    selected_outer = sorted(representatives["outer_split_id"].astype(str).unique())
    allowlist_rows = []
    manifest_rows = []
    for outer_split_id in selected_outer:
        reps = representatives.loc[representatives["outer_split_id"].astype(str).eq(outer_split_id)].copy()
        split_stability = stability.loc[stability["outer_split_id"].astype(str).eq(outer_split_id)]
        if not reps["factor"].isin(split_stability.loc[split_stability["stability_role"].eq("stable_core"), "factor"]).all():
            raise ValueError(f"allowlist contains a non-stable-core factor: {outer_split_id}")
        if len(reps) < int(config["minimum_components"]):
            raise ValueError(f"allowlist has fewer than minimum_components: {outer_split_id}")
        split_allowed = pd.DatetimeIndex(allowed.loc[allowed["outer_split_id"].astype(str).eq(outer_split_id), "datetime"]).sort_values().unique()
        split_outer = outer.loc[outer["split_id"].astype(str).eq(outer_split_id)]
        if len(split_outer) != 1:
            raise ValueError(f"outer split manifest mismatch: {outer_split_id}")
        reps = reps.sort_values("factor", kind="stable").reset_index(drop=True)
        reps["feature_order"] = range(len(reps))
        reps["allowlist_sha256"] = allowlist_payload_hash(reps)
        reps["holdout_clean"] = True
        allowlist_rows.append(reps)
        manifest_rows.append({
            "outer_split_id": outer_split_id,
            "development_start": split_allowed.min(), "development_end": split_allowed.max(),
            "outer_test_start": split_outer.iloc[0]["test_start"], "outer_test_end": split_outer.iloc[0]["test_end"],
            "allowed_date_count": len(split_allowed),
            "allowed_dates_sha256": canonical_hash([date.date().isoformat() for date in split_allowed]),
            "factor_count": len(reps), "allowlist_sha256": reps.iloc[0]["allowlist_sha256"],
            "feature_order_sha256": canonical_hash(reps["factor"].tolist()),
            "stability_artifact_id": manifests[1]["artifact_id"],
            "clustering_artifact_id": manifests[0]["artifact_id"],
            "development_split_artifact_id": manifests[2]["artifact_id"],
            "holdout_clean": True,
        })
    allowlist = pd.concat(allowlist_rows, ignore_index=True)
    allowlist_manifest = pd.DataFrame(manifest_rows)
    expected_splits = int(config["expected_outer_splits"])
    date_audit_ok = audit[[column for column in audit.columns if column.endswith("outside_allowed_count")]].sum().sum() == 0
    contracts = pd.DataFrame([
        contract_row("outer_split_count", len(allowlist_manifest) == expected_splits, len(allowlist_manifest), expected_splits),
        contract_row("split_allowlist_unique", not allowlist.duplicated(["outer_split_id", "factor"]).any(), int(allowlist.duplicated(["outer_split_id", "factor"]).sum()), 0),
        contract_row("minimum_components", allowlist_manifest["factor_count"].ge(int(config["minimum_components"])).all(), allowlist_manifest["factor_count"].tolist(), f">={config['minimum_components']}"),
        contract_row("all_factors_stable_core", allowlist["stability_role"].eq("stable_core").all(), int(allowlist["stability_role"].ne("stable_core").sum()), 0),
        contract_row("clustering_holdout_clean", date_audit_ok and allowlist_manifest["holdout_clean"].all(), bool(date_audit_ok and allowlist_manifest["holdout_clean"].all()), True),
        contract_row("split_allowlists_frozen", allowlist_manifest["allowlist_sha256"].str.len().eq(64).all(), int(allowlist_manifest["allowlist_sha256"].str.len().eq(64).sum()), len(allowlist_manifest)),
        contract_row("single_global_allowlist_absent", "global" not in set(allowlist["outer_split_id"].str.lower()), sorted(allowlist["outer_split_id"].unique()), "split-specific only"),
    ])
    selection_status = pd.DataFrame([{
        "selection_name": "split_specific_holdout_clean_allowlists_v1",
        "selection_status": "holdout_clean",
        "model_input_allowed": False,
        "outer_split_count": len(allowlist_manifest),
        "reason": "allowlists are frozen; model gate remains closed until mutation and pre-test contracts pass",
    }])
    receipts = pd.DataFrame([
        {"input_name": name, "artifact_id": manifest["artifact_id"], "path": path.as_posix(), "sha256": file_sha256(path), "join_keys": keys}
        for name, manifest, path, keys in (
            ("representatives", manifests[0], resolve(config["representatives"]), "outer_split_id,factor"),
            ("stability", manifests[1], resolve(config["stability_board"]), "outer_split_id,factor"),
            ("allowed_dates", manifests[2], resolve(config["allowed_dates"]), "outer_split_id,datetime"),
            ("outer_split_manifest", manifests[3], resolve(config["outer_split_manifest"]), "outer_split_id"),
        )
    ])
    ready = bool(contracts["status"].eq("pass").all())
    output_dir = resolve(config["output_dir"])
    with StageOutputPublisher(output_dir, CONTROLLED) as publisher:
        allowlist.to_csv(publisher.path("split_allowlist.csv"), index=False, encoding="utf-8-sig")
        allowlist_manifest.to_csv(publisher.path("split_allowlist_manifest.csv"), index=False, encoding="utf-8-sig")
        selection_status.to_csv(publisher.path("selection_status.csv"), index=False, encoding="utf-8-sig")
        audit.to_csv(publisher.path("selection_date_audit.csv"), index=False, encoding="utf-8-sig")
        receipts.to_csv(publisher.path("input_receipts.csv"), index=False, encoding="utf-8-sig")
        contracts.to_csv(publisher.path("contract_status.csv"), index=False, encoding="utf-8-sig")
        publisher.path("resolved_config.json").write_text(json.dumps(config, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        publisher.path("split_allowlist_report.md").write_text(
            "# Split-Specific Allowlist V1\n\n"
            + f"- Status: `{'pass' if ready else 'blocked'}`\n"
            + f"- Outer splits / total representatives: `{len(allowlist_manifest)}` / `{len(allowlist)}`\n"
            + "- Each allowlist is independently hash-frozen and bound to exact development dates.\n"
            + "- Model input remains disabled until mutation and pre-test gates pass.\n",
            encoding="utf-8",
        )
        files = [publisher.path(name) for name in CONTROLLED if name != "artifact_manifest.json"]
        write_stage_artifact_manifest(
            project_root=PROJECT_ROOT, stage_id="split_specific_allowlist_v1", config=config,
            output_dir=publisher.staging_dir, output_files=files, code_state=capture_code_state(PROJECT_ROOT),
            input_manifest_paths=manifest_paths, factor_frame_id=manifests[0]["factor_frame_id"],
            split_manifest_id=manifests[3]["split_manifest_id"], start_date=allowlist_manifest["development_start"].min(),
            end_date=allowlist_manifest["development_end"].max(), lineage_status="complete",
            artifact_status="pass" if ready else "blocked", blocked_reason="" if ready else "blocked_split_allowlist",
        )
        publisher.publish()
    print(contracts.to_string(index=False))
    return 0 if ready else 2


if __name__ == "__main__":
    raise SystemExit(main())
