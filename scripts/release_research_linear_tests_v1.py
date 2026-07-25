from __future__ import annotations

import argparse
import shlex
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from model_research.linear_models import load_linear_config  # noqa: E402
from model_research.linear_test_release import (  # noqa: E402
    release_linear_model_tests,
)
from model_research.protocol import resolve  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Consume six freezes and release linear outer-test predictions once."
    )
    parser.add_argument(
        "--config",
        default="configs/research_linear_models_v1.yaml",
    )
    parser.add_argument(
        "--output-dir",
        default="outputs/research_linear_models_v1/current",
    )
    parser.add_argument(
        "--runtime-dir",
        default="outputs/research_linear_models_v1/runtime/test_release",
    )
    args = parser.parse_args()
    result = release_linear_model_tests(
        load_linear_config(resolve(args.config)),
        output_dir=resolve(args.output_dir),
        runtime_dir=resolve(args.runtime_dir),
        command=" ".join(shlex.quote(value) for value in sys.argv),
    )
    print(
        "Linear test release passed: "
        f"releases={result['release_count']}; "
        f"predictions={result['prediction_row_count']}; "
        f"minimum_coverage={result['minimum_prediction_coverage']:.6f}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
