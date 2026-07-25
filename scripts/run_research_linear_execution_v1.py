from __future__ import annotations

import argparse
import shlex
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from model_research.linear_execution import (  # noqa: E402
    load_linear_execution_config,
    run_linear_execution,
)
from model_research.protocol import resolve  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run frozen linear predictions through corrected Qlib execution."
    )
    parser.add_argument(
        "--config",
        default="configs/research_linear_execution_v1.yaml",
    )
    parser.add_argument("--canary", action="store_true")
    args = parser.parse_args()
    config = load_linear_execution_config(resolve(args.config))
    result = run_linear_execution(
        config,
        output_dir=resolve(
            config["canary"]["output_dir"]
            if args.canary
            else config["output_dir"]
        ),
        runtime_dir=resolve(
            config["canary"]["runtime_dir"]
            if args.canary
            else config["runtime_dir"]
        ),
        command=" ".join(shlex.quote(value) for value in sys.argv),
        canary=args.canary,
    )
    print(
        "Linear Qlib execution passed: "
        f"summary_rows={result['execution_rows']}; "
        f"orders={result['orders']}; fills={result['fills']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
