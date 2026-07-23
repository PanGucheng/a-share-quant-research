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

from research_validation.feature_matrix import file_sha256  # noqa: E402
from research_validation.lineage import (  # noqa: E402
    load_artifact_manifest,
    validate_manifest_outputs,
)


def resolve(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else (PROJECT_ROOT / path).resolve()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate lifecycle-clean point-in-time universe v2 outputs."
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/point_in_time_universe_v2.yaml"),
    )
    parser.add_argument("--allow-dirty", action="store_true")
    args = parser.parse_args()
    config = yaml.safe_load(resolve(args.config).read_text(encoding="utf-8")) or {}
    resolved_config = {
        **config,
        "source_intervals_sha256": file_sha256(
            resolve(config["source_intervals"])
        ),
        "lifecycle_intersection_policy": (
            "rolling_universe_interval_intersection_source_lifecycle_interval"
        ),
    }
    output = resolve(config["output_dir"])
    manifest = load_artifact_manifest(output / "artifact_manifest.json")
    assert not validate_manifest_outputs(
        manifest, output, config=resolved_config
    )
    assert manifest["stage_id"] == "point_in_time_universe_v2"
    assert manifest["artifact_status"] == "pass"
    assert manifest["lineage_status"] == "complete"
    if not args.allow_dirty:
        assert not bool(manifest["code_dirty"])

    contract = pd.read_csv(output / "contract_status.csv").set_index(
        "check_name"
    )
    assert contract.loc[
        contract["severity"].eq("critical"), "status"
    ].eq("pass").all()
    for check in [
        "lifecycle_intersection_applied",
        "lifecycle_violation_count",
        "overlapping_membership_interval_count",
        "removed_key_still_active_count",
    ]:
        assert contract.loc[check, "status"] == "pass"
    assert int(contract.loc["lifecycle_violation_count", "observed_value"]) == 0
    assert (
        int(
            contract.loc[
                "overlapping_membership_interval_count", "observed_value"
            ]
        )
        == 0
    )
    assert (
        int(contract.loc["removed_key_still_active_count", "observed_value"])
        == 0
    )

    intervals = pd.read_csv(
        output / "universe_intervals.csv",
        parse_dates=["start_date", "end_date"],
    )
    assert not intervals.empty
    assert not intervals.duplicated(
        ["instrument", "start_date", "end_date"]
    ).any()
    differences = pd.read_csv(output / "lifecycle_difference.csv")
    removed = pd.read_csv(output / "illegal_key_resolution.csv")
    assert int(
        contract.loc["lifecycle_correction_interval_count", "observed_value"]
    ) == len(differences)
    assert int(
        contract.loc["removed_illegal_key_count", "observed_value"]
    ) == len(removed)

    resolved = json.loads(
        (output / "resolved_config.json").read_text(encoding="utf-8")
    )
    assert (
        resolved["lifecycle_intersection_policy"]
        == "rolling_universe_interval_intersection_source_lifecycle_interval"
    )
    assert (
        resolved["source_intervals_sha256"]
        == resolved_config["source_intervals_sha256"]
    )
    print(
        "Point-in-time universe v2 is lifecycle-clean; all removed keys are "
        "disclosed and absent from final membership."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
