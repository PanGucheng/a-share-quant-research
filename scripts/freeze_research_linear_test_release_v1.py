from __future__ import annotations

import argparse
import shlex
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from model_research.linear_models import load_linear_config  # noqa: E402
from model_research.linear_release_freeze import (  # noqa: E402
    publish_linear_test_release_freezes,
)
from model_research.protocol import resolve  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Bind six frozen linear models to exact outer-test dates."
    )
    parser.add_argument(
        "--config",
        default="configs/research_linear_models_v1.yaml",
    )
    parser.add_argument(
        "--output-dir",
        default="outputs/research_linear_models_v1/test_release_freeze",
    )
    args = parser.parse_args()
    result = publish_linear_test_release_freezes(
        load_linear_config(resolve(args.config)),
        output_dir=resolve(args.output_dir),
        command=" ".join(shlex.quote(value) for value in sys.argv),
    )
    print(
        "Linear test release freeze passed: "
        f"freezes={result['freeze_count']}; "
        f"test_reads={result['test_read_count']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
