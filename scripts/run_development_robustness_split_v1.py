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

from research_validation.development_split import DevelopmentSplitConfig, build_development_robustness_splits  # noqa: E402
from research_validation.lineage import capture_code_state, content_reference_id, load_artifact_manifest, validate_manifest_outputs, write_stage_artifact_manifest  # noqa: E402
from research_validation.stage_output import StageOutputPublisher  # noqa: E402

CONTROLLED = (
    "artifact_manifest.json", "outer_split_manifest.csv", "inner_split_manifest.csv",
    "development_date_assignments.csv", "outer_development_allowed_dates.csv", "purged_dates.csv",
    "embargoed_dates.csv", "leakage_audit.csv", "contract_status.csv", "resolved_config.json",
    "development_robustness_split_report.md",
)


def resolve(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else (PROJECT_ROOT / path).resolve()


def main() -> int:
    parser = argparse.ArgumentParser(description="Build inner development robustness windows without outer-test access.")
    parser.add_argument("--config", type=Path, default=Path("configs/development_robustness_split_669_v1.yaml"))
    args = parser.parse_args()
    config = yaml.safe_load(resolve(args.config).read_text(encoding="utf-8")) or {}
    input_paths = [resolve(path) for path in config["input_manifests"]]
    manifests = [load_artifact_manifest(path) for path in input_paths]
    issues = [issue for manifest, path in zip(manifests, input_paths) for issue in validate_manifest_outputs(manifest, path.parent)]
    if issues or any(manifest["artifact_status"] != "pass" for manifest in manifests):
        raise ValueError("development split upstream is stale or blocked")
    outer_manifest = pd.read_csv(resolve(config["outer_split_manifest"]), parse_dates=["train_start", "train_end", "validation_start", "validation_end", "test_start", "test_end"])
    outer_assignments = pd.read_csv(resolve(config["outer_date_assignments"]), parse_dates=["datetime"])
    intervals = pd.read_csv(resolve(config["label_intervals"]), parse_dates=["feature_time", "label_start_time", "label_end_time"])
    split_config = DevelopmentSplitConfig(
        validation_dates=int(config["validation_dates"]),
        embargo_trading_days=int(config["embargo_trading_days"]),
        minimum_train_dates=int(config["minimum_train_dates"]),
        minimum_validation_dates=int(config["minimum_validation_dates"]),
        minimum_inner_windows=int(config["minimum_inner_windows"]),
        validation_end_fractions=tuple(map(float, config["validation_end_fractions"])),
    )
    outputs = build_development_robustness_splits(outer_manifest, outer_assignments, intervals, split_config)
    contract = outputs["leakage_audit"]
    ready = bool(contract["status"].eq("pass").all())
    output_dir = resolve(config["output_dir"])
    with StageOutputPublisher(output_dir, CONTROLLED) as publisher:
        outer_manifest.to_csv(publisher.path("outer_split_manifest.csv"), index=False, encoding="utf-8-sig")
        for name in ("inner_split_manifest", "development_date_assignments", "outer_development_allowed_dates", "purged_dates", "embargoed_dates", "leakage_audit"):
            outputs[name].to_csv(publisher.path(f"{name}.csv"), index=False, encoding="utf-8-sig")
        contract.to_csv(publisher.path("contract_status.csv"), index=False, encoding="utf-8-sig")
        publisher.path("resolved_config.json").write_text(json.dumps(config, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        publisher.path("development_robustness_split_report.md").write_text(
            "# Development Robustness Split V1\n\n"
            + f"- Status: `{'pass' if ready else 'blocked'}`\n"
            + f"- Outer / inner splits: `{outer_manifest['split_id'].nunique()}` / `{len(outputs['inner_split_manifest'])}`\n"
            + "- Semantic role: `development_robustness_not_nested_selection_replay`\n"
            + "- Outer test dates are excluded from all development assignments and label intervals.\n",
            encoding="utf-8",
        )
        files = [publisher.path(name) for name in CONTROLLED if name != "artifact_manifest.json"]
        write_stage_artifact_manifest(
            project_root=PROJECT_ROOT, stage_id="development_robustness_split_v1", config=config,
            output_dir=publisher.staging_dir, output_files=files, code_state=capture_code_state(PROJECT_ROOT),
            input_manifest_paths=input_paths,
            split_manifest_id=content_reference_id("development-split-manifest", [publisher.path("inner_split_manifest.csv"), publisher.path("development_date_assignments.csv")]),
            start_date=outputs["development_date_assignments"]["datetime"].min(),
            end_date=outputs["development_date_assignments"]["datetime"].max(),
            lineage_status="complete", artifact_status="pass" if ready else "blocked",
            blocked_reason="" if ready else "blocked_development_split_contract",
        )
        publisher.publish()
    print(contract.to_string(index=False))
    return 0 if ready else 2


if __name__ == "__main__":
    raise SystemExit(main())
