from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from qlib_integration.historical_portfolio_backtest import (  # noqa: E402
    load_backtest_config,
    run_development,
    run_holdout,
    run_smoke,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run frozen LightGBM portfolio backtest")
    parser.add_argument(
        "--config",
        default="configs/historical_portfolio_backtest_v1.yaml",
    )
    parser.add_argument(
        "--mode",
        required=True,
        choices=["smoke", "development", "holdout"],
    )
    args = parser.parse_args()
    config = load_backtest_config(args.config)
    if args.mode == "smoke":
        result = run_smoke(config)
    elif args.mode == "development":
        result = run_development(config)
    else:
        result = run_holdout(config)
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
