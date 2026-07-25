from __future__ import annotations

import argparse
import shlex
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from model_research.lightgbm_models import (  # noqa: E402
    load_lightgbm_config,
    run_lightgbm_development,
)
from model_research.protocol import resolve  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run frozen LightGBM train/validation development."
    )
    parser.add_argument(
        "--config",
        default="configs/research_lightgbm_v1.yaml",
    )
    parser.add_argument(
        "--splits",
        nargs="+",
        default=["split_001"],
    )
    parser.add_argument(
        "--output-dir",
        default="outputs/research_lightgbm_v1/split_001",
    )
    parser.add_argument(
        "--runtime-dir",
        default="outputs/research_lightgbm_v1/runtime/development",
    )
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args()
    config = load_lightgbm_config(resolve(args.config))
    result = run_lightgbm_development(
        config,
        output_dir=resolve(args.output_dir),
        runtime_dir=resolve(args.runtime_dir),
        split_ids=[str(value) for value in args.splits],
        command=" ".join(shlex.quote(value) for value in sys.argv),
        factor_limit=5 if args.smoke else None,
        train_date_limit=20 if args.smoke else None,
        validation_date_limit=10 if args.smoke else None,
        candidate_limit=2 if args.smoke else None,
    )
    print(
        "LightGBM development passed: "
        f"splits={','.join(result['split_ids'])}; "
        f"candidates={result['candidate_rows']}; "
        f"models={result['model_count']}; "
        f"peak_rss_mib={result['peak_rss_mib']:.1f}; "
        f"test_reads={result['test_read_count']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
