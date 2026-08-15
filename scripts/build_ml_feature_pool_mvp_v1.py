from __future__ import annotations

import argparse
from pathlib import Path

from model_research.feature_pool_policy import (
    build_policy_manifests,
    load_policy_config,
    write_policy_manifests,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _resolve(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else PROJECT_ROOT / path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/ml_feature_pool_mvp_v1.yaml")
    parser.add_argument("--output-dir")
    args = parser.parse_args()
    config = load_policy_config(_resolve(args.config))
    parents = config["parents"]
    features, policies = build_policy_manifests(
        split_ids=[str(value) for value in config["split_ids"]],
        weights_path=_resolve(parents["factor_weights"]),
        allowlist_path=_resolve(parents["allowlist_manifest"]),
        eligibility_freeze_path=_resolve(parents["eligibility_freeze"]),
        eligibility_decisions_path=_resolve(parents["eligibility_decisions"]),
        stability_path=_resolve(parents["stability_board"]),
    )
    write_policy_manifests(
        output_dir=_resolve(args.output_dir or config["output_dir"]),
        features=features,
        policies=policies,
    )


if __name__ == "__main__":
    main()
