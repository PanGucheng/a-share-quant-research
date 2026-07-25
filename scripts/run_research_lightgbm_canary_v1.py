from __future__ import annotations

import argparse
import shlex
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from model_research.lightgbm_models import (  # noqa: E402
    load_lightgbm_config,
    run_lightgbm_canary,
)
from model_research.protocol import resolve  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the frozen train-only LightGBM V1 canary."
    )
    parser.add_argument(
        "--config",
        default="configs/research_lightgbm_v1.yaml",
    )
    parser.add_argument("--resource-canary", action="store_true")
    args = parser.parse_args()
    config = load_lightgbm_config(resolve(args.config))
    result = run_lightgbm_canary(
        config,
        output_dir=resolve(
            config[
                "resource_canary"
                if args.resource_canary
                else "canary"
            ]["output_dir"]
        ),
        command=" ".join(shlex.quote(value) for value in sys.argv),
        resource_canary=args.resource_canary,
    )
    print(
        f"LightGBM {result['scope']} passed: "
        f"rows={result['sample_rows']}; "
        f"factors={result['factor_count']}; "
        f"candidate_runs={result['candidate_runs']}; "
        f"peak_rss_mib={result['peak_rss_mib']:.1f}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
