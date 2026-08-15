from __future__ import annotations

import argparse
from pathlib import Path

from model_research.feature_pool_experiment import run_policy_canary


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _resolve(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else PROJECT_ROOT / path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/ml_feature_pool_mvp_v1.yaml")
    parser.add_argument(
        "--policy-manifest",
        default="outputs/ml_feature_pool_mvp_v1/current/policy_manifest.csv",
    )
    parser.add_argument(
        "--feature-manifest",
        default="outputs/ml_feature_pool_mvp_v1/current/feature_pool_manifest.csv",
    )
    parser.add_argument(
        "--output-dir", default="outputs/ml_feature_pool_mvp_v1/canary"
    )
    args = parser.parse_args()
    run_policy_canary(
        policy_config_path=_resolve(args.config),
        policy_manifest_path=_resolve(args.policy_manifest),
        feature_manifest_path=_resolve(args.feature_manifest),
        output_dir=_resolve(args.output_dir),
    )


if __name__ == "__main__":
    main()
