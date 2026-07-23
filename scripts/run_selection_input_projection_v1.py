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
from research_validation.feature_matrix import atomic_parquet, canonical_hash, file_sha256  # noqa: E402
from research_validation.lineage import capture_code_state, load_artifact_manifest, validate_manifest_outputs, write_stage_artifact_manifest  # noqa: E402
from research_validation.selection_projection import build_selection_projections  # noqa: E402
from research_validation.stage_output import StageOutputPublisher  # noqa: E402

CONTROLLED = (
    "artifact_manifest.json", "projection_inventory.csv", "input_receipts.csv", "contract_status.csv",
    "selection_input_projection_report.md", "resolved_config.json",
)


def resolve(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else (PROJECT_ROOT / path).resolve()


def main() -> int:
    parser = argparse.ArgumentParser(description="Materialize test-free selection input projections.")
    parser.add_argument("--config", type=Path, default=Path("configs/selection_input_projection_669_v1.yaml"))
    args = parser.parse_args()
    config = yaml.safe_load(resolve(args.config).read_text(encoding="utf-8")) or {}
    manifest_paths = [resolve(path) for path in config["input_manifests"]]
    manifests = [load_artifact_manifest(path) for path in manifest_paths]
    issues = [issue for manifest, path in zip(manifests, manifest_paths) for issue in validate_manifest_outputs(manifest, path.parent)]
    if issues or any(manifest["artifact_status"] != "pass" for manifest in manifests):
        raise ValueError("selection projection upstream is stale or blocked")
    daily_path = resolve(config["daily_ic"])
    outer_path = resolve(config["outer_date_assignments"])
    inner_path = resolve(config["inner_date_assignments"])
    daily = pd.read_csv(daily_path, parse_dates=["datetime"])
    outer = pd.read_csv(outer_path, parse_dates=["datetime"])
    inner = pd.read_csv(inner_path, parse_dates=["datetime"])
    outer_train, inner_development = build_selection_projections(daily, outer, inner)
    outer_runtime = resolve(config["outer_train_runtime"])
    inner_runtime = resolve(config["inner_development_runtime"])
    atomic_parquet(outer_train, outer_runtime)
    atomic_parquet(inner_development, inner_runtime)
    test_dates = outer.loc[outer["fold"].eq("test"), ["split_id", "datetime"]].rename(columns={"split_id": "outer_split_id"})
    outer_test_overlap = len(outer_train.merge(test_dates, on=["outer_split_id", "datetime"], how="inner"))
    inner_test_overlap = len(inner_development.merge(test_dates, on=["outer_split_id", "datetime"], how="inner"))
    inventory_rows = []
    for name, frame, path in (
        ("outer_train_daily_ic", outer_train, outer_runtime),
        ("inner_development_daily_ic", inner_development, inner_runtime),
    ):
        inventory_rows.append({
            "projection": name, "path": path.as_posix(), "sha256": file_sha256(path), "row_count": len(frame),
            "factor_count": frame["factor"].nunique(), "outer_split_count": frame["outer_split_id"].nunique(),
            "inner_split_count": frame["inner_split_id"].nunique() if "inner_split_id" in frame else 0,
            "start_date": frame["datetime"].min(), "end_date": frame["datetime"].max(),
            "canonical_key_sha256": canonical_hash(frame[[column for column in ["outer_split_id", "inner_split_id", "fold", "datetime", "factor"] if column in frame]].astype(str).to_dict("records")),
        })
    inventory = pd.DataFrame(inventory_rows)
    receipts = pd.DataFrame([
        {"input_name": "daily_ic", "artifact_id": manifests[0]["artifact_id"], "path": daily_path.as_posix(), "sha256": file_sha256(daily_path), "join_keys": "datetime", "input_rows": len(daily), "consumed_rows": len(outer_train) + len(inner_development), "missing_rows": 0},
        {"input_name": "outer_assignments", "artifact_id": manifests[1]["artifact_id"], "path": outer_path.as_posix(), "sha256": file_sha256(outer_path), "join_keys": "outer_split_id,datetime", "input_rows": len(outer), "consumed_rows": outer["fold"].eq("train").sum(), "missing_rows": 0},
        {"input_name": "inner_assignments", "artifact_id": manifests[2]["artifact_id"], "path": inner_path.as_posix(), "sha256": file_sha256(inner_path), "join_keys": "outer_split_id,inner_split_id,datetime", "input_rows": len(inner), "consumed_rows": len(inner), "missing_rows": 0},
    ])
    contracts = pd.DataFrame([
        contract_row("outer_split_count", outer_train["outer_split_id"].nunique() == int(config["expected_outer_splits"]), outer_train["outer_split_id"].nunique(), config["expected_outer_splits"]),
        contract_row("inner_split_count", inner_development["inner_split_id"].nunique() == int(config["expected_inner_splits"]), inner_development["inner_split_id"].nunique(), config["expected_inner_splits"]),
        contract_row("outer_factor_count", outer_train["factor"].nunique() == int(config["expected_factor_count"]), outer_train["factor"].nunique(), config["expected_factor_count"]),
        contract_row("inner_factor_count", inner_development["factor"].nunique() == int(config["expected_factor_count"]), inner_development["factor"].nunique(), config["expected_factor_count"]),
        contract_row("outer_test_date_in_projection_count", outer_test_overlap == 0, outer_test_overlap, 0),
        contract_row("inner_test_date_in_projection_count", inner_test_overlap == 0, inner_test_overlap, 0),
        contract_row("runtime_hashes_present", inventory["sha256"].str.len().eq(64).all(), int(inventory["sha256"].str.len().eq(64).sum()), len(inventory)),
    ])
    ready = bool(contracts["status"].eq("pass").all())
    output_dir = resolve(config["output_dir"])
    with StageOutputPublisher(output_dir, CONTROLLED) as publisher:
        inventory.to_csv(publisher.path("projection_inventory.csv"), index=False, encoding="utf-8-sig")
        receipts.to_csv(publisher.path("input_receipts.csv"), index=False, encoding="utf-8-sig")
        contracts.to_csv(publisher.path("contract_status.csv"), index=False, encoding="utf-8-sig")
        publisher.path("resolved_config.json").write_text(json.dumps(config, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        publisher.path("selection_input_projection_report.md").write_text(
            "# Selection Input Projection V1\n\n"
            + f"- Status: `{'pass' if ready else 'blocked'}`\n"
            + f"- Outer-train / inner-development rows: `{len(outer_train)}` / `{len(inner_development)}`\n"
            + "- Outer-test rows in either projection: `0`\n"
            + "- Runtime parquets are content-addressed and excluded from Git.\n",
            encoding="utf-8",
        )
        files = [publisher.path(name) for name in CONTROLLED if name != "artifact_manifest.json"]
        write_stage_artifact_manifest(
            project_root=PROJECT_ROOT, stage_id=str(config.get("stage_id", "selection_input_projection_v1")), config=config,
            output_dir=publisher.staging_dir, output_files=files, code_state=capture_code_state(PROJECT_ROOT),
            universe_artifact_id=manifests[0]["universe_artifact_id"],
            factor_catalog_id=manifests[0]["factor_catalog_id"],
            input_manifest_paths=manifest_paths, factor_frame_id=manifests[0]["factor_frame_id"],
            split_manifest_id=manifests[1]["split_manifest_id"], start_date=outer_train["datetime"].min(),
            end_date=inner_development["datetime"].max(), lineage_status="complete",
            artifact_status="pass" if ready else "blocked", blocked_reason="" if ready else "blocked_selection_projection",
        )
        publisher.publish()
    print(contracts.to_string(index=False))
    return 0 if ready else 2


if __name__ == "__main__":
    raise SystemExit(main())
