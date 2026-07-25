from __future__ import annotations

import argparse
import shlex
import sys

from model_research.linear_models import load_linear_config, run_solver_canary
from model_research.protocol import resolve


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Freeze the deterministic Ridge solver using train-only data."
    )
    parser.add_argument(
        "--config",
        default="configs/research_linear_models_v1.yaml",
    )
    parser.add_argument("--output-dir", default=None)
    args = parser.parse_args()
    config = load_linear_config(resolve(args.config))
    output_dir = resolve(
        args.output_dir or config["execution"]["canary_output_dir"]
    )
    command = " ".join(shlex.quote(value) for value in sys.argv)
    result = run_solver_canary(
        config,
        output_dir=output_dir,
        command=command,
    )
    print(
        "Research linear solver canary passed: "
        f"solver={result['selected_solver']}; "
        f"test_reads={result['test_read_count']}; "
        f"output={result['output_dir']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

