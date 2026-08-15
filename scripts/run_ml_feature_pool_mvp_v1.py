from __future__ import annotations

import argparse
from pathlib import Path

from model_research.feature_pool_experiment import (
    run_all_development_arms,
    run_coordinated_historical_replay,
    run_development_arm,
    run_policy_canary,
)
from model_research.feature_pool_policy import POLICY_IDS
from model_research.feature_pool_comparison import (
    publish_diagnostic_report,
    run_fixed_p01_comparison,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _resolve(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else PROJECT_ROOT / path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "mode", choices=("canary", "development", "replay", "portfolio", "report")
    )
    parser.add_argument("--config", default="configs/ml_feature_pool_mvp_v1.yaml")
    parser.add_argument(
        "--feature-manifest",
        default="outputs/ml_feature_pool_mvp_v1/current/feature_pool_manifest.csv",
    )
    parser.add_argument(
        "--policy-manifest",
        default="outputs/ml_feature_pool_mvp_v1/current/policy_manifest.csv",
    )
    parser.add_argument("--split-id")
    parser.add_argument("--policy-id", choices=POLICY_IDS)
    args = parser.parse_args()
    config_path = _resolve(args.config)
    feature_manifest = _resolve(args.feature_manifest)
    if args.mode == "canary":
        run_policy_canary(
            policy_config_path=config_path,
            policy_manifest_path=_resolve(args.policy_manifest),
            feature_manifest_path=feature_manifest,
            output_dir=_resolve("outputs/ml_feature_pool_mvp_v1/canary"),
        )
        return
    development_root = _resolve("outputs/ml_feature_pool_mvp_v1/development")
    replay_root = _resolve("outputs/ml_feature_pool_mvp_v1/historical_replay")
    if args.mode == "replay":
        run_coordinated_historical_replay(
            policy_config_path=config_path,
            feature_manifest_path=feature_manifest,
            development_root=development_root,
            replay_root=replay_root,
        )
        return
    portfolio_root = _resolve("outputs/ml_feature_pool_mvp_v1/portfolio")
    if args.mode == "portfolio":
        run_fixed_p01_comparison(
            replay_root=replay_root,
            development_root=development_root,
            portfolio_root=portfolio_root,
            historical_backtest_config_path=_resolve(
                "configs/historical_portfolio_backtest_v1.yaml"
            ),
        )
        return
    if args.mode == "report":
        publish_diagnostic_report(
            replay_root=replay_root,
            development_root=development_root,
            portfolio_root=portfolio_root,
            policy_manifest_path=_resolve(args.policy_manifest),
            report_root=_resolve("reports/ml_feature_pool_mvp_v1"),
        )
        return
    runtime_root = _resolve("outputs/ml_feature_pool_mvp_v1/runtime/development")
    if bool(args.split_id) != bool(args.policy_id):
        parser.error("--split-id and --policy-id must be provided together")
    if args.split_id:
        run_development_arm(
            policy_config_path=config_path,
            feature_manifest_path=feature_manifest,
            split_id=str(args.split_id),
            policy_id=str(args.policy_id),
            development_root=development_root,
            runtime_root=runtime_root,
        )
    else:
        run_all_development_arms(
            policy_config_path=config_path,
            feature_manifest_path=feature_manifest,
            development_root=development_root,
            runtime_root=runtime_root,
        )


if __name__ == "__main__":
    main()
