from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from model_research.feature_eligibility import (
    apply_eligibility_thresholds,
    load_eligibility_config,
    run_feature_only_profile,
    validate_threshold_freeze,
    write_feature_only_profile,
    write_freeze,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _resolve(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else PROJECT_ROOT / path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("profile", "freeze"))
    parser.add_argument(
        "--config", default="configs/ml_feature_eligibility_mvp_v1.yaml"
    )
    parser.add_argument("--output-dir")
    args = parser.parse_args()
    config = load_eligibility_config(_resolve(args.config))
    output_dir = _resolve(args.output_dir or config["output_dir"])
    if args.mode == "profile":
        profile, resources, access = run_feature_only_profile(
            config, project_root=PROJECT_ROOT
        )
        write_feature_only_profile(
            output_dir=output_dir,
            config=config,
            profile=profile,
            resources=resources,
            access=access,
            project_root=PROJECT_ROOT,
        )
        return

    thresholds = validate_threshold_freeze(config)
    profile_path = output_dir / "feature_quality_profile.csv"
    profile = pd.read_csv(profile_path)
    parents = config["parents"]
    decisions = apply_eligibility_thresholds(
        profile,
        inventory=pd.read_csv(_resolve(parents["factor_inventory"])),
        dependencies=pd.read_csv(_resolve(parents["dependency_inventory"])),
        thresholds=thresholds,
    )
    write_freeze(
        output_dir=output_dir,
        config=config,
        profile_path=profile_path,
        decisions=decisions,
    )


if __name__ == "__main__":
    main()
