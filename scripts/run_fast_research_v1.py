from __future__ import annotations

import argparse
from pathlib import Path

from model_research.fast_research import run_fast_research_pair
from model_research.protocol import PROJECT_ROOT


def _resolve(value: str) -> Path:
    path = Path(value)
    return path.resolve() if path.is_absolute() else (PROJECT_ROOT / path).resolve()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run non-authoritative Fast Research V1")
    parser.add_argument("--config", default="configs/fast_research_v1.yaml")
    parser.add_argument("--baseline", default="strict_current_baseline")
    parser.add_argument("--proposal", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--feature-manifest")
    parser.add_argument("--policy-manifest")
    parser.add_argument("--changed-dimension", default="feature_pool_policy")
    parser.add_argument(
        "--cache-root", default="tmp/research_productivity_v1/projection_spool_cache"
    )
    parser.add_argument(
        "--runtime-root", default="outputs/research_productivity_v1/runtime/fast"
    )
    args = parser.parse_args()
    receipt = run_fast_research_pair(
        config_path=_resolve(args.config),
        baseline_id=args.baseline,
        proposal_id=args.proposal,
        output_dir=_resolve(args.output_dir),
        cache_root=_resolve(args.cache_root),
        runtime_root=_resolve(args.runtime_root),
        feature_manifest_path=(
            _resolve(args.feature_manifest) if args.feature_manifest else None
        ),
        policy_manifest_path=(
            _resolve(args.policy_manifest) if args.policy_manifest else None
        ),
        changed_dimension=args.changed_dimension,
    )
    print(receipt)


if __name__ == "__main__":
    main()
