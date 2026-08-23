from __future__ import annotations

import argparse
from pathlib import Path

from model_research.clustering_ablation import (
    build_clustering_ablation_manifests,
    load_clustering_ablation_config,
    write_clustering_ablation_manifests,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _resolve(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else PROJECT_ROOT / path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/ml_clustering_ablation_v1.yaml")
    parser.add_argument("--output-dir")
    args = parser.parse_args()
    config = load_clustering_ablation_config(_resolve(args.config))
    features, policies, exclusions = build_clustering_ablation_manifests(config)
    output_dir = _resolve(args.output_dir or config["output_dir"])
    write_clustering_ablation_manifests(
        output_dir=output_dir,
        features=features,
        policies=policies,
        exclusions=exclusions,
    )
    print(policies.to_string(index=False))


if __name__ == "__main__":
    main()
