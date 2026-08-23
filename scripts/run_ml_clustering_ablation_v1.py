from __future__ import annotations

import argparse
from pathlib import Path

from model_research.clustering_ablation import (
    POLICY_D,
    POLICY_IDS,
    build_ablation_freeze_index,
    freeze_metadata_for_split,
    load_clustering_ablation_config,
)
from model_research.feature_pool_comparison import run_fixed_p01_comparison
from model_research.feature_pool_experiment import (
    run_coordinated_historical_replay,
    run_development_arm,
    run_policy_canary,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _resolve(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else PROJECT_ROOT / path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("canary", "development", "freeze-index", "replay", "portfolio"))
    parser.add_argument("--config", default="configs/ml_clustering_ablation_v1.yaml")
    parser.add_argument("--split-id", choices=("split_001", "split_002", "split_003"))
    args = parser.parse_args()
    config_path = _resolve(args.config)
    config = load_clustering_ablation_config(config_path)
    output_dir = _resolve(config["output_dir"])
    feature_manifest = output_dir / "feature_pool_manifest.csv"
    policy_manifest = output_dir / "policy_manifest.csv"
    development_root = _resolve(config["development_dir"])
    if args.mode == "canary":
        run_policy_canary(
            policy_config_path=config_path,
            policy_manifest_path=policy_manifest,
            feature_manifest_path=feature_manifest,
            output_dir=_resolve("outputs/ml_clustering_ablation_v1/canary"),
            policy_ids=POLICY_IDS,
            config_loader=load_clustering_ablation_config,
            allowed_policy_ids=POLICY_IDS,
            execution_profile="ml_clustering_ablation_canary_v1",
            receipt_stage_id="ml_clustering_ablation_v1_canary",
        )
        return
    if args.mode == "development":
        if not args.split_id:
            parser.error("development requires --split-id")
        run_development_arm(
            policy_config_path=config_path,
            feature_manifest_path=feature_manifest,
            split_id=args.split_id,
            policy_id=POLICY_D,
            development_root=development_root,
            runtime_root=_resolve(config["runtime_dir"]) / "development",
            config_loader=load_clustering_ablation_config,
            allowed_policy_ids=POLICY_IDS,
            execution_profile="ml_clustering_ablation_full_v1",
            freeze_metadata=freeze_metadata_for_split(
                config=config,
                policy_manifest_path=policy_manifest,
                split_id=args.split_id,
            ),
        )
        return
    if args.mode == "freeze-index":
        build_ablation_freeze_index(
            config=config,
            baseline_development_root=_resolve("outputs/ml_feature_pool_mvp_v1/development"),
            ablation_development_root=development_root,
        )
        return
    replay_root = _resolve(config["historical_replay_dir"])
    if args.mode == "replay":
        run_coordinated_historical_replay(
            policy_config_path=config_path,
            feature_manifest_path=feature_manifest,
            development_root=development_root,
            replay_root=replay_root,
            config_loader=load_clustering_ablation_config,
            policy_ids=POLICY_IDS,
            execution_profile="ml_clustering_ablation_historical_v1",
        )
        return
    run_fixed_p01_comparison(
        replay_root=replay_root,
        development_root=development_root,
        portfolio_root=_resolve(config["portfolio_dir"]),
        historical_backtest_config_path=_resolve("configs/historical_portfolio_backtest_v1.yaml"),
        policy_ids=POLICY_IDS,
        split_ids=tuple(str(value) for value in config["split_ids"]),
        execution_profile="ml_clustering_ablation_portfolio_v1",
    )


if __name__ == "__main__":
    main()
