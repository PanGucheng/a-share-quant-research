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
from research_validation.feature_matrix import file_sha256  # noqa: E402
from research_validation.lineage import capture_code_state, load_artifact_manifest, validate_manifest_outputs, write_stage_artifact_manifest  # noqa: E402
from research_validation.stage_output import StageOutputPublisher  # noqa: E402
from research_validation.transparent_baseline import build_transparent_weights  # noqa: E402


CONTROLLED = (
    "artifact_manifest.json",
    "factor_weights_by_split.csv",
    "weight_manifest.csv",
    "input_receipts.csv",
    "contract_status.csv",
    "transparent_weights_report.md",
    "resolved_config.json",
)


def resolve(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else (PROJECT_ROOT / path).resolve()


def main() -> int:
    parser = argparse.ArgumentParser(description="Freeze holdout-clean transparent factor weights by outer split.")
    parser.add_argument("--config", type=Path, default=Path("configs/split_transparent_weights_669_v1.yaml"))
    args = parser.parse_args()
    config = yaml.safe_load(resolve(args.config).read_text(encoding="utf-8")) or {}
    manifest_paths = [resolve(path) for path in config["input_manifests"]]
    manifests = [load_artifact_manifest(path) for path in manifest_paths]
    issues = [issue for manifest, path in zip(manifests, manifest_paths) for issue in validate_manifest_outputs(manifest, path.parent)]
    if issues or any(manifest["artifact_status"] != "pass" for manifest in manifests):
        raise ValueError(f"transparent-weight upstream is stale or blocked: {issues}")
    allowlist = pd.read_csv(resolve(config["split_allowlist"]))
    selected_outer_splits = [str(value) for value in config.get("selected_outer_splits", [])]
    if selected_outer_splits:
        allowlist = allowlist.loc[allowlist["outer_split_id"].astype(str).isin(selected_outer_splits)].copy()
    if allowlist.empty:
        raise ValueError("transparent-weight allowlist is empty")
    weights, weight_manifest = build_transparent_weights(
        allowlist,
        methods=[str(value) for value in config["methods"]],
        maximum_factor_weight=float(config["maximum_factor_weight"]),
    )
    expected_splits = len(selected_outer_splits) if selected_outer_splits else int(config["expected_outer_splits"])
    expected_methods = len(config["methods"])
    weight_sum_error = float(weight_manifest["weight_sum"].sub(1.0).abs().max())
    maximum_weight = float(weight_manifest["maximum_weight"].max())
    contracts = pd.DataFrame(
        [
            contract_row("outer_split_count", weight_manifest["outer_split_id"].nunique() == expected_splits, weight_manifest["outer_split_id"].nunique(), expected_splits),
            contract_row("method_count_per_split", weight_manifest.groupby("outer_split_id")["method"].nunique().eq(expected_methods).all(), weight_manifest.groupby("outer_split_id")["method"].nunique().tolist(), expected_methods),
            contract_row("minimum_components", weight_manifest["factor_count"].ge(int(config["minimum_components"])).all(), weight_manifest["factor_count"].tolist(), f">={config['minimum_components']}"),
            contract_row("weight_sum_error", weight_sum_error <= 1e-12, weight_sum_error, "<=1e-12"),
            contract_row("maximum_factor_weight", maximum_weight <= float(config["maximum_factor_weight"]) + 1e-12, maximum_weight, f"<={config['maximum_factor_weight']}"),
            contract_row("unique_cluster_vote", not weights.duplicated(["outer_split_id", "method", "cluster_id"]).any(), int(weights.duplicated(["outer_split_id", "method", "cluster_id"]).sum()), 0),
            contract_row("direction_frozen", weights["direction"].isin([-1, 1]).all(), sorted(weights["direction"].unique()), [-1, 1]),
            contract_row("holdout_clean", weight_manifest["holdout_clean"].all(), bool(weight_manifest["holdout_clean"].all()), True),
            contract_row("test_fields_consumed", not any(str(column).startswith("test_") or "oos" in str(column).lower() for column in allowlist), [], []),
        ]
    )
    receipts = pd.DataFrame(
        [
            {
                "input_name": manifest["stage_id"],
                "artifact_id": manifest["artifact_id"],
                "path": path.as_posix(),
                "sha256": file_sha256(path),
            }
            for manifest, path in zip(manifests, manifest_paths)
        ]
    )
    ready = bool(contracts["status"].eq("pass").all())
    output_dir = resolve(config["output_dir"])
    with StageOutputPublisher(output_dir, CONTROLLED) as publisher:
        weights.to_csv(publisher.path("factor_weights_by_split.csv"), index=False, encoding="utf-8-sig")
        weight_manifest.to_csv(publisher.path("weight_manifest.csv"), index=False, encoding="utf-8-sig")
        receipts.to_csv(publisher.path("input_receipts.csv"), index=False, encoding="utf-8-sig")
        contracts.to_csv(publisher.path("contract_status.csv"), index=False, encoding="utf-8-sig")
        publisher.path("resolved_config.json").write_text(json.dumps(config, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        publisher.path("transparent_weights_report.md").write_text(
            "# Split-Specific Transparent Weights V1\n\n"
            + f"- Status: `{'pass' if ready else 'blocked'}`\n"
            + f"- Outer splits / methods / weight rows: `{expected_splits}` / `{expected_methods}` / `{len(weights)}`\n"
            + "- Equal and stability weights consume only the split-specific holdout-clean allowlist and its development evidence.\n"
            + "- No test feature, label, IC, return, or execution metric is consumed.\n",
            encoding="utf-8",
        )
        files = [publisher.path(name) for name in CONTROLLED if name != "artifact_manifest.json"]
        write_stage_artifact_manifest(
            project_root=PROJECT_ROOT,
            stage_id="split_transparent_weights_v1",
            config=config,
            output_dir=publisher.staging_dir,
            output_files=files,
            code_state=capture_code_state(PROJECT_ROOT),
            input_manifest_paths=manifest_paths,
            factor_frame_id=manifests[0]["factor_frame_id"],
            split_manifest_id=manifests[0]["split_manifest_id"],
            lineage_status="complete",
            artifact_status="pass" if ready else "blocked",
            blocked_reason="" if ready else "blocked_transparent_weights",
        )
        publisher.publish()
    print(contracts.to_string(index=False))
    return 0 if ready else 2


if __name__ == "__main__":
    raise SystemExit(main())
